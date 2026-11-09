"""Flask app: one form, one report, one PDF. Reports live in memory for 15 minutes, never on disk."""
import os
import secrets
import threading
import time

from flask import Flask, Response, abort, render_template, request, url_for
from playwright.sync_api import sync_playwright

from . import i18n, scanner
from .security import RateLimiter
from .states import DEFAULT_PAGES, HARD_MAX_PAGES, clamp_pages

REPORT_TTL = 15 * 60
ORDER = ("a11y", "overflow", "contrast", "links")

app = Flask(__name__)
if os.environ.get("SHC_TRUST_PROXY") == "1":
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

limiter = RateLimiter(limit=int(os.environ.get("SHC_RATE_LIMIT", "6")), window=3600)
BROWSER = threading.Lock()          # one browser at a time on the whole server
_REPORTS = {}                       # token -> (expires, report)
_RLOCK = threading.Lock()


def _purge():
    now = time.time()
    with _RLOCK:
        for k in [k for k, (exp, _) in _REPORTS.items() if exp < now]:
            del _REPORTS[k]


def _store(report):
    token = secrets.token_urlsafe(16)
    with _RLOCK:
        _REPORTS[token] = (time.time() + REPORT_TTL, report)
    return token


def _get(token):
    _purge()
    with _RLOCK:
        item = _REPORTS.get(token)
    return item[1] if item else None


def _ctx(lang, switch_url):
    other = "ro" if lang == "en" else "en"
    return dict(lang=lang, other=other, switch_url=switch_url, t=lambda k, *a: i18n.ui(k, lang, *a))


def _page(template, lang, switch_url, status=200, **kw):
    html = render_template(template, **_ctx(lang, switch_url), **kw)
    return Response(html, status=status, mimetype="text/html")


def _form(lang, error=None, url=None, status=200):
    other = "ro" if lang == "en" else "en"
    return _page("index.html", lang, url_for("index", lang=other), status, error=error, url=url,
                 hard_max=HARD_MAX_PAGES, default_pages=DEFAULT_PAGES)


@app.after_request
def headers(resp):
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    return resp


@app.get("/")
def index():
    return _form(i18n.norm_lang(request.args.get("lang")))


@app.get("/healthz")
def healthz():
    return "ok"


@app.post("/scan")
def scan_route():
    lang = i18n.norm_lang(request.form.get("lang"))
    raw = request.form.get("url", "")
    try:
        url = scanner.normalize_input(raw)
    except ValueError:
        return _form(lang, i18n.ui("err_url", lang), raw, 400)
    if not limiter.allow(request.remote_addr or "?"):
        return _form(lang, i18n.ui("err_rate", lang), raw, 429)
    if not BROWSER.acquire(blocking=False):
        return _form(lang, i18n.ui("err_busy", lang), raw, 503)
    try:
        report = scanner.scan(url, clamp_pages(request.form.get("pages")))
    finally:
        BROWSER.release()
    token = _store(report)
    return _render_report(report, token, lang)


def _fatal_text(report, lang):
    f = report["fatal"]
    if not f:
        return ""
    why = f["params"].get("why") or f["params"].get("status") or ""
    key = "fatal_" + f["code"]
    return i18n.ui(key, lang, why) if "%" in i18n.UI[key][0] else i18n.ui(key, lang)


def _render_report(report, token, lang, pdf=False):
    other = "ro" if lang == "en" else "en"
    return _page("report.html", lang, url_for("report", token=token, lang=other), r=report, order=ORDER, pdf=pdf,
                 pdf_url=url_for("report_pdf", token=token, lang=lang), fatal_text=_fatal_text(report, lang),
                 finding=lambda f: i18n.finding(f, lang))


@app.get("/report/<token>")
def report(token):
    lang = i18n.norm_lang(request.args.get("lang"))
    r = _get(token)
    if r is None:
        return _form(lang, i18n.ui("err_gone", lang), None, 404)
    return _render_report(r, token, lang)


def html_to_pdf(html):
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--no-sandbox"])
        try:
            ctx = b.new_context()
            ctx.route("**/*", lambda route: route.abort())     # the PDF page loads nothing from anywhere
            page = ctx.new_page()
            page.set_content(html, wait_until="domcontentloaded")
            return page.pdf(format="A4", print_background=True, margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"})
        finally:
            b.close()


@app.get("/report/<token>.pdf")
def report_pdf(token):
    lang = i18n.norm_lang(request.args.get("lang"))
    r = _get(token)
    if r is None:
        return _form(lang, i18n.ui("err_gone", lang), None, 404)
    html = _render_report(r, token, lang, pdf=True).get_data(as_text=True)
    if not BROWSER.acquire(timeout=60):
        return _form(lang, i18n.ui("err_busy", lang), None, 503)
    try:
        pdf = html_to_pdf(html)
    finally:
        BROWSER.release()
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="site-health-check.pdf"'})


def main():
    app.run(host=os.environ.get("SHC_HOST", "127.0.0.1"), port=int(os.environ.get("SHC_PORT", "8000")), threaded=True)


if __name__ == "__main__":
    main()
