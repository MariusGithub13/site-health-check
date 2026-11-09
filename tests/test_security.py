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
