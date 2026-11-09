#!/usr/bin/env python3
"""Smoke test: start the app on 127.0.0.1 (free port), scan a site with few pages, download the PDF, stop the app.
Usage: python scripts/smoke.py [URL] [PAGES]"""
import os, re, socket, subprocess, sys, time, urllib.parse, urllib.request

url = sys.argv[1] if len(sys.argv) > 1 else "https://devaland.cloud"
pages = sys.argv[2] if len(sys.argv) > 2 else "3"
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, SHC_HOST="127.0.0.1", SHC_PORT=str(port))
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
proc = subprocess.Popen([sys.executable, "-m", "shc"], cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "/healthz", timeout=2); break
        except Exception:
            time.sleep(0.2)
    else:
        sys.exit("app did not start")
    data = urllib.parse.urlencode({"url": url, "pages": pages, "lang": "en"}).encode()
    html = urllib.request.urlopen(urllib.request.Request(base + "/scan", data=data), timeout=300).read().decode()
    assert "Report for" in html, "no report rendered"
    for m in re.finditer(r'<th scope="row">(.*?)</th><td><span class="badge s-(\w+)">(.*?)</span>', html):
        print(f"{m.group(1)}: {m.group(3).upper()}")
    print("pages:", re.search(r"Pages examined: (\d+ of \d+)", html).group(1))
    pdf_url = re.search(r'href="(/report/[^"]+\.pdf[^"]*)"', html).group(1).replace("&amp;", "&")
    resp = urllib.request.urlopen(base + pdf_url, timeout=120)
    pdf = resp.read()
    assert pdf[:5] == b"%PDF-" and resp.headers["Content-Type"] == "application/pdf", "not a PDF"
    print(f"PDF ok: {len(pdf)} bytes")
finally:
    proc.terminate(); proc.wait(10)
