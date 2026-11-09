"""Broken-link check with a deliberate nonsense-path control per host."""
import secrets
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests

from .security import SSRFError, UnresolvableError, safe_fetch
from .states import FAILED, PASSED, UNKNOWN, aggregate

MAX_LINKS = 150


def check_one(url, fetch=safe_fetch):
    """Return (state, detail). Each link is requested once (HEAD, GET only if HEAD is refused)."""
    try:
        r = fetch(url, method="HEAD", timeout=8)
        if r.status in (405, 501) or r.status >= 400 and r.status != 404:
            r = fetch(url, method="GET", timeout=8)
        if r.status in (404, 410) or r.status >= 500:
            return FAILED, f"HTTP {r.status}"
        if r.status in (401, 403, 429):
            return UNKNOWN, f"HTTP {r.status}"
        return PASSED, f"HTTP {r.status}"
    except (SSRFError, UnresolvableError, requests.RequestException) as e:
        return UNKNOWN, type(e).__name__


def control(base, fetch=safe_fetch):
    """Ask for a path that cannot exist. A site that answers 200 makes every other answer meaningless."""
    u = urllib.parse.urljoin(base, f"/shc-nonsense-{secrets.token_hex(6)}/x")
    try:
        r = fetch(u, method="GET", timeout=8)
    except (SSRFError, UnresolvableError, requests.RequestException) as e:
        return UNKNOWN, type(e).__name__
    if r.status == 200:
        return FAILED, "200"
    return PASSED, str(r.status)


def run(links_by_source, base, robots=None, fetch=safe_fetch):
    """links_by_source: {link: first page that linked to it}. Returns a language-independent result."""
    ctrl_state, ctrl_detail = control(base, fetch)
    links = list(links_by_source)[:MAX_LINKS]
    res = {"control": {"state": ctrl_state, "detail": ctrl_detail}, "examined": 0, "total": len(links_by_source),
           "broken": [], "unknown": [], "skipped_robots": 0}
    if ctrl_state != PASSED:
        res["state"] = UNKNOWN
        return res
    todo = []
    for l in links:
        if robots is not None and not robots.allowed(l):
            res["skipped_robots"] += 1
        else:
            todo.append(l)
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda l: check_one(l, fetch), todo))
    states = []
    for l, (st, detail) in zip(todo, results):
        states.append(st)
        res["examined"] += 1
        if st == FAILED:
            res["broken"].append({"url": l, "detail": detail, "source": links_by_source[l]})
        elif st == UNKNOWN:
            res["unknown"].append({"url": l, "detail": detail, "source": links_by_source[l]})
    capped = len(links_by_source) > MAX_LINKS or res["skipped_robots"] > 0
    state = aggregate(states) if states else UNKNOWN
    if state == PASSED and capped:
        state = UNKNOWN          # not every link was examined: not a clean result
    res["state"] = state
    return res
