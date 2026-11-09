"""Orchestrates one scan. Returns a language-independent report dict; nothing is written to disk."""
import datetime
import urllib.parse

import requests

from . import browser, crawl, linkcheck
from .security import Robots, SSRFError, UnresolvableError, safe_fetch
from .states import UNKNOWN, aggregate, clamp_pages

CHECKS = ("a11y", "overflow", "contrast", "links")


def normalize_input(raw):
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("empty")
    if "://" not in raw:
        raw = "https://" + raw
    p = urllib.parse.urlsplit(raw)
    if not p.hostname:
        raise ValueError("no host")
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path or "/", p.query, ""))


def _all_unknown(url, host, reason_code, params=None, requested=0):
    return {"url": url, "host": host, "when": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "requested": requested, "pages": [], "skipped": [], "fatal": {"code": reason_code, "params": params or {}},
            "checks": {c: {"state": UNKNOWN, "pages": []} for c in CHECKS}, "links": None}


def scan(url, max_pages=None, fetch=safe_fetch, run_browser=browser.run_browser):
    n = clamp_pages(max_pages)
    host = urllib.parse.urlsplit(url).hostname
    try:
        home = fetch(url)
    except SSRFError as e:
        return _all_unknown(url, host, "refused", {"why": str(e)}, n)
    except (UnresolvableError, requests.RequestException) as e:
        return _all_unknown(url, host, "unreachable", {"why": type(e).__name__}, n)
    if home.status >= 400:
        return _all_unknown(url, host, "home_status", {"status": home.status}, n)
    final = home.url
    base = f"{urllib.parse.urlsplit(final).scheme}://{urllib.parse.urlsplit(final).netloc}/"
    robots = Robots(base, fetch)
    if robots.state == "unknown":
        return _all_unknown(url, host, "robots_unreadable", {"why": robots.reason}, n)
    if not robots.allowed(final):
        return _all_unknown(url, host, "robots_blocked", {}, n)
    candidates = crawl.pick_pages(final, home.text, crawl.sitemap_urls(base, fetch), n)
    pages, skipped = [], []
    for u in candidates:
        (pages if robots.allowed(u) else skipped).append(u)
    skipped = [{"url": u, "code": "robots"} for u in skipped]

    results = run_browser(pages)
    checks = {}
    for c in ("a11y", "overflow", "contrast"):
        per = [{"url": r["url"], "state": r[c]["state"], "findings": r[c]["findings"],
                **({"total": r[c].get("total"), "failing": r[c].get("failing")} if c == "contrast" else {})}
               for r in results]
        checks[c] = {"state": aggregate([p["state"] for p in per]), "pages": per}
    links_by_source = {}
    for r in results:
        for h in r.get("hrefs", []):
            u = crawl.normalize(r["url"], h)
            if u and crawl.same_host(u, final) and not crawl.SKIP_EXT.search(urllib.parse.urlsplit(u).path):
                links_by_source.setdefault(u, r["url"])
    lk = linkcheck.run(links_by_source, base, robots, fetch)
    checks["links"] = {"state": lk["state"], "pages": []}
    return {"url": url, "host": host, "when": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "requested": n, "pages": pages, "skipped": skipped, "fatal": None, "checks": checks, "links": lk}
