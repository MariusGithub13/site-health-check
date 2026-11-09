"""SSRF guard, safe fetching, robots.txt and rate limiting.

Rule: a host is fetched only if EVERY address it resolves to is a public one. The check runs for the
first URL and again for every redirect hop. The headless browser re-checks every request it makes.
"""
import contextvars
import ipaddress
import socket
import threading
import time
import urllib.parse
import urllib.robotparser
from collections import defaultdict, deque

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool

from . import USER_AGENT

ALLOWED_PORTS = {None, 80, 443}
EXTRA_BLOCKED = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12",
    "192.0.0.0/24", "192.168.0.0/16", "198.18.0.0/15", "224.0.0.0/4", "240.0.0.0/4",
    "::1/128", "fc00::/7", "fe80::/10", "fd00:ec2::/32", "::/128", "ff00::/8",
)]
MAX_BODY = 2_000_000
TIMEOUT = 10


class SSRFError(Exception):
    """The URL points somewhere we refuse to fetch."""


class UnresolvableError(Exception):
    """DNS gave no answer. This is 'could not check', never 'no problems'."""


def ip_allowed(ip) -> bool:
    ip = ipaddress.ip_address(ip)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    if not ip.is_global:
        return False
    return not any(ip in net for net in EXTRA_BLOCKED if net.version == ip.version)


def check_url(url, resolver=socket.getaddrinfo):
    """Return the parsed URL if it is safe to fetch, else raise SSRFError / UnresolvableError."""
    return resolve_public(url, resolver)[0]


def resolve_public(url, resolver=socket.getaddrinfo):
    """Return (parsed URL, sorted list of validated public IP strings), else raise SSRFError / UnresolvableError."""
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https"):
        raise SSRFError("only http and https are allowed")
    if not p.hostname:
        raise SSRFError("no host")
    if p.username or p.password:
        raise SSRFError("credentials in the URL are refused")
    try:
        port = p.port
    except ValueError:
        raise SSRFError("bad port")
    if port not in ALLOWED_PORTS:
        raise SSRFError(f"port {port} is not allowed")
    host = p.hostname
    try:
        ips = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            infos = resolver(host, port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except OSError as e:
            raise UnresolvableError(f"DNS failed for {host}: {e}")
        ips = {ipaddress.ip_address(i[4][0].split("%")[0]) for i in infos}
        if not ips:
            raise UnresolvableError(f"no address for {host}")
    bad = [str(i) for i in ips if not ip_allowed(i)]
    if bad:
        raise SSRFError(f"{host} resolves to a non-public address ({', '.join(sorted(bad))})")
    return p, sorted(str(i) for i in ips)


class Fetched:
    def __init__(self, status, headers, text, url):
        self.status, self.headers, self.text, self.url = status, headers, text, url


# --- DNS pinning -------------------------------------------------------------------------------
# The address that was validated is the address that is connected to. The HTTP client never resolves the
# name itself, so a DNS server that answers differently the second time (DNS rebinding) changes nothing.
# The URL, the Host header and the TLS server name stay the original host name.
_PIN = contextvars.ContextVar("shc_pin", default=None)     # (host, ip)


def _check_peer(sock, ip):
    """Belt and braces: the address actually connected to must still be a public one."""
    peer = sock.getpeername()[0].split("%")[0]
    if not ip_allowed(peer):
        raise SSRFError("peer address is not public")


def _pinned_socket(conn):
    pin = _PIN.get()
    if not pin or not pin[1] or pin[0] != conn._dns_host:
        raise SSRFError("connection without a validated address was refused")
    ip = pin[1]
    if not ip_allowed(ip):
        raise SSRFError(f"{ip} is not a public address")
    sock = socket.create_connection((ip, conn.port), conn.timeout, source_address=conn.source_address)
    try:
        _check_peer(sock, ip)
        for opt in conn.socket_options or ():
            sock.setsockopt(*opt)
    except BaseException:
        sock.close()
        raise
    return sock


class _PinnedHTTP(HTTPConnection):
    def _new_conn(self):
        return _pinned_socket(self)


class _PinnedHTTPS(HTTPSConnection):
    def _new_conn(self):
        return _pinned_socket(self)


class _PinnedHTTPPool(HTTPConnectionPool):
    ConnectionCls = _PinnedHTTP


class _PinnedHTTPSPool(HTTPSConnectionPool):
    ConnectionCls = _PinnedHTTPS


class _PinnedAdapter(HTTPAdapter):
    def init_poolmanager(self, *a, **kw):
        super().init_poolmanager(*a, **kw)
        self.poolmanager.pool_classes_by_scheme = {"http": _PinnedHTTPPool, "https": _PinnedHTTPSPool}


def pinned_request(method, url, ip=None, **kw):
    """requests.request that connects only to `ip` (a validated address of the URL's host)."""
    host = urllib.parse.urlsplit(url).hostname
    token = _PIN.set((host, ip))
    try:
        s = requests.Session()                         # fresh session: no connection survives to the next hop
        s.trust_env = False
        a = _PinnedAdapter(max_retries=0)
        s.mount("http://", a)
        s.mount("https://", a)
        try:
            r = s.request(method, url, **kw)
        except BaseException:
            s.close()
            raise
        r._shc_session = s                             # closed by the caller together with the response
        return r
    finally:
        _PIN.reset(token)


def safe_fetch(url, method="GET", timeout=TIMEOUT, max_redirects=5, resolver=socket.getaddrinfo,
               http=None):
    """Fetch with the SSRF check on every hop. Raises SSRFError / UnresolvableError / requests errors.
    By default the validated IP is pinned for the connection (see above). `http` is a test hook."""
    for _ in range(max_redirects + 1):
        _, ips = resolve_public(url, resolver)
        hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        if http is None:
            r, last = None, None
            for ip in sorted(ips, key=lambda i: ":" in i):          # IPv4 first, then the other validated addresses
                try:
                    r = pinned_request(method, url, ip=ip, headers=hdrs, timeout=timeout,
                                       allow_redirects=False, stream=True)
                    break
                except requests.ConnectionError as e:
                    last = e
            if r is None:
                raise last
        else:
            r = http(method, url, headers=hdrs, timeout=timeout, allow_redirects=False, stream=True)
        try:
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
                url = urllib.parse.urljoin(url, r.headers["Location"])
                continue
            body = b""
            if method == "GET":
                for chunk in r.iter_content(65536):
                    body += chunk
                    if len(body) > MAX_BODY:
                        break
            text = body.decode(r.encoding or "utf-8", "replace")
            return Fetched(r.status_code, dict(r.headers), text, url)
        finally:
            r.close()
            sess = getattr(r, "_shc_session", None)
            if sess is not None:
                sess.close()
    raise requests.TooManyRedirects("too many redirects")


class Robots:
    """robots.txt for one host. If it cannot be read the answer is 'allowed' only on a clean 404."""

    def __init__(self, base, fetch=safe_fetch):
        self.rp = urllib.robotparser.RobotFileParser()
        self.state = "allowed"
        self.reason = ""
        try:
            r = fetch(urllib.parse.urljoin(base, "/robots.txt"))
            if r.status == 200:
                self.rp.parse(r.text.splitlines())
            elif 400 <= r.status < 500:
                self.rp.parse([])
            else:
                self.state, self.reason = "unknown", f"robots.txt answered {r.status}"
        except (SSRFError, UnresolvableError, requests.RequestException) as e:
            self.state, self.reason = "unknown", f"robots.txt: {type(e).__name__}"

    def allowed(self, url):
        if self.state == "unknown":
            return False
        return self.rp.can_fetch("SiteHealthCheck", url)


class RateLimiter:
    """Sliding window per client key, in memory only."""

    def __init__(self, limit=6, window=3600):
        self.limit, self.window = limit, window
        self.hits = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key, now=None):
        now = time.time() if now is None else now
        with self.lock:
            q = self.hits[key]
            while q and q[0] <= now - self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True
