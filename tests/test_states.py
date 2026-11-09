from shc import linkcheck
from shc.states import FAILED, PASSED, UNKNOWN, aggregate, clamp_pages, DEFAULT_PAGES, HARD_MAX_PAGES
from shc.security import UnresolvableError


def test_aggregate_three_states():
    assert aggregate([PASSED, PASSED]) == PASSED
    assert aggregate([PASSED, FAILED, UNKNOWN]) == FAILED
    assert aggregate([PASSED, UNKNOWN]) == UNKNOWN


def test_nothing_measured_is_never_passed():
    assert aggregate([]) == UNKNOWN


def test_page_limit_cap():
    assert clamp_pages(None) == DEFAULT_PAGES == 10
    assert clamp_pages("abc") == 10
    assert clamp_pages(500) == HARD_MAX_PAGES == 25
    assert clamp_pages(25) == 25
    assert clamp_pages(0) == 1
    assert clamp_pages(-4) == 1
    assert clamp_pages("7") == 7


class R:
    def __init__(self, status):
        self.status = status


def test_failed_fetch_is_unknown_not_passed():
    def fetch(url, method="GET", timeout=8):
        raise UnresolvableError("dns")
    st, _ = linkcheck.check_one("https://x.test/a", fetch)
    assert st == UNKNOWN


def test_host_answering_200_to_everything_is_reported_and_blocks_verdict():
    def fetch(url, method="GET", timeout=8):
        return R(200)
    res = linkcheck.run({"https://x.test/a": "https://x.test/"}, "https://x.test/", None, fetch)
    assert res["control"]["state"] == FAILED
    assert res["state"] == UNKNOWN          # cannot call anything passed


def test_links_clean_broken_and_unknown():
    def fetch(url, method="GET", timeout=8):
        if "nonsense" in url or url.endswith("/gone"):
            return R(404)
        if url.endswith("/err"):
            raise UnresolvableError("dns")
        return R(200)
    links = {"https://x.test/ok": "p", "https://x.test/gone": "p"}
    res = linkcheck.run(links, "https://x.test/", None, fetch)
    assert res["state"] == FAILED and len(res["broken"]) == 1
    res = linkcheck.run({"https://x.test/ok": "p"}, "https://x.test/", None, fetch)
    assert res["state"] == PASSED
    res = linkcheck.run({"https://x.test/ok": "p", "https://x.test/err": "p"}, "https://x.test/", None, fetch)
    assert res["state"] == UNKNOWN


def test_scan_unreachable_home_marks_every_check_unknown():
    from shc import scanner
    def fetch(url, **kw):
        raise UnresolvableError("dns")
    rep = scanner.scan("https://x.test/", 50, fetch=fetch, run_browser=lambda p: [])
    assert rep["requested"] == 25
    assert all(c["state"] == UNKNOWN for c in rep["checks"].values())
    assert rep["fatal"]["code"] == "unreachable"


def test_pick_pages_caps_and_stays_on_host():
    from shc import crawl
    html = "".join(f'<a href="/p{i}">x</a>' for i in range(40)) + '<a href="https://other.test/z">o</a>'
    pages = crawl.pick_pages("https://x.test/", html, ["https://x.test/s1", "https://other.test/s2"], 25)
    assert len(pages) == 25 and pages[0] == "https://x.test/"
    assert all("other.test" not in p for p in pages)
