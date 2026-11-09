import socket
import pytest
from shc.security import SSRFError, UnresolvableError, check_url, ip_allowed, safe_fetch, RateLimiter


def resolver_for(mapping):
    def r(host, port, type=0):
        if host not in mapping:
            raise socket.gaierror("nope")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in mapping[host]]
    return r


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.1.2.3", "172.16.0.5", "192.168.1.1", "169.254.169.254",
                                "100.64.0.1", "100.127.255.255", "0.0.0.0", "::1", "fe80::1", "fd00:ec2::254",
                                "::ffff:127.0.0.1", "224.0.0.1", "198.18.0.1"])
def test_private_ips_refused(ip):
    assert not ip_allowed(ip)


@pytest.mark.parametrize("ip", ["93.184.216.34", "8.8.8.8", "2606:4700:4700::1111"])
def test_public_ips_allowed(ip):
    assert ip_allowed(ip)


def test_public_host_allowed_with_mocked_resolver():
    p = check_url("https://example.test/a", resolver_for({"example.test": ["93.184.216.34"]}))
    assert p.hostname == "example.test"


def test_host_resolving_to_private_refused():
    with pytest.raises(SSRFError):
        check_url("http://evil.test/", resolver_for({"evil.test": ["10.0.0.7"]}))


def test_one_private_among_public_refused():
    with pytest.raises(SSRFError):
        check_url("http://mix.test/", resolver_for({"mix.test": ["93.184.216.34", "127.0.0.1"]}))


def test_literal_ips_and_metadata_refused():
    for u in ("http://127.0.0.1/", "http://169.254.169.254/latest/meta-data/", "http://[::1]/", "http://100.64.0.1/"):
        with pytest.raises(SSRFError):
            check_url(u, resolver_for({}))


@pytest.mark.parametrize("u", ["ftp://example.test/", "file:///etc/passwd", "http://user:pw@example.test/",
                               "http://example.test:22/", "http:///nohost"])
def test_bad_scheme_port_credentials_refused(u):
    with pytest.raises(SSRFError):
        check_url(u, resolver_for({"example.test": ["93.184.216.34"]}))


def test_dns_failure_is_unresolvable_not_ok():
    with pytest.raises(UnresolvableError):
        check_url("https://nowhere.test/", resolver_for({}))


class FakeResp:
    def __init__(self, status, headers=None, body=b""):
        self.status_code, self.headers, self.encoding, self._b = status, headers or {}, "utf-8", body
    def iter_content(self, n):
        yield self._b
    def close(self):
        pass


def test_redirect_to_private_is_refused_after_redirect():
    res = resolver_for({"ok.test": ["93.184.216.34"], "internal.test": ["10.0.0.1"]})
    calls = []
    def http(method, url, **kw):
        calls.append(url)
        if "ok.test" in url:
            return FakeResp(302, {"Location": "http://internal.test/admin"})
        return FakeResp(200, body=b"secret")
    with pytest.raises(SSRFError):
        safe_fetch("http://ok.test/", resolver=res, http=http)
    assert calls == ["http://ok.test/"]       # the private hop was never requested


def test_redirect_to_literal_metadata_refused():
    res = resolver_for({"ok.test": ["93.184.216.34"]})
    def http(method, url, **kw):
        return FakeResp(301, {"Location": "http://169.254.169.254/"})
    with pytest.raises(SSRFError):
        safe_fetch("http://ok.test/", resolver=res, http=http)


def test_rate_limiter_window():
    rl = RateLimiter(limit=2, window=100)
    assert rl.allow("a", 0) and rl.allow("a", 1)
    assert not rl.allow("a", 2)
    assert rl.allow("b", 2)           # other clients unaffected
    assert rl.allow("a", 101)         # window passed


# --- DNS rebinding: the validated address is the one that is connected to --------------------------------
import http.server, threading, socket as _socket
from shc import security


class _H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = ("host=" + str(self.headers.get("Host"))).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass


@pytest.fixture
def local_server():
    srv = http.server.HTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


def test_connection_goes_to_the_validated_ip_not_to_a_fresh_dns_answer(local_server, monkeypatch):
    monkeypatch.setattr(security, "_check_peer", lambda s, ip: None)   # the spy below redirects to loopback
    # Checker sees a public IP; "real" DNS (what the HTTP client would have asked) says 127.0.0.1.
    real = _socket.getaddrinfo
    def hostile(host, port, *a, **k):
        if host == "rebind.test":
            return [(_socket.AF_INET, _socket.SOCK_STREAM, 6, "", ("127.0.0.1", local_server))]
        return real(host, port, *a, **k)
    monkeypatch.setattr(_socket, "getaddrinfo", hostile)
    connected = []
    orig = _socket.create_connection
    def spy(addr, *a, **k):
        connected.append(addr[0])
        return orig(("127.0.0.1", local_server) if addr[0] == "93.184.216.34" else addr, *a, **k)
    monkeypatch.setattr(security.socket, "create_connection", spy)
    res = resolver_for({"rebind.test": ["93.184.216.34"]})
    # the pinned connect targets 93.184.216.34 (redirected by the spy to our local server only to stay offline)
    r = safe_fetch("http://rebind.test/", resolver=res)
    assert connected == ["93.184.216.34"]          # never the name, never 127.0.0.1
    assert r.status == 200 and r.text == "host=rebind.test"   # Host header stays the original name


def test_connection_without_validated_address_is_refused():
    with pytest.raises(SSRFError):
        security.pinned_request("GET", "http://x.test/", ip=None, timeout=2)


def test_pinned_private_ip_refused_even_if_it_reaches_the_connector():
    with pytest.raises(SSRFError):
        security.pinned_request("GET", "http://x.test/", ip="127.0.0.1", timeout=2)


def test_hostile_dns_flip_private_second_answer_is_not_used(local_server, monkeypatch):
    monkeypatch.setattr(security, "_check_peer", lambda s, ip: None)
    # first answer public (validated), any later lookup would be private: the client must not look again
    calls = {"n": 0}
    def flip(host, port, type=0):
        calls["n"] += 1
        ip = "93.184.216.34" if calls["n"] == 1 else "127.0.0.1"
        return [(_socket.AF_INET, _socket.SOCK_STREAM, 6, "", (ip, port))]
    seen = []
    orig = _socket.create_connection
    monkeypatch.setattr(security.socket, "create_connection",
                        lambda addr, *a, **k: (seen.append(addr[0]), orig(("127.0.0.1", local_server), *a, **k))[1])
    safe_fetch("http://flip.test/", resolver=flip)
    assert calls["n"] == 1 and seen == ["93.184.216.34"]


def test_peer_address_revalidated_after_connect(local_server):
    # a connection that lands on loopback is refused even if the pinned IP looked public
    s = _socket.create_connection(("127.0.0.1", local_server))
    with pytest.raises(SSRFError):
        security._check_peer(s, "93.184.216.34")
    s.close()
