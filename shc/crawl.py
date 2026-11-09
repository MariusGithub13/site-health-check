"""Find up to N pages of one site: homepage links first, then sitemap.xml. Same host only."""
import re
import urllib.parse
from html.parser import HTMLParser

SKIP_EXT = re.compile(r"\.(pdf|jpe?g|png|gif|webp|svg|ico|zip|gz|mp4|mp3|css|js|json|xml|txt|docx?|xlsx?|pptx?)$", re.I)


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.hrefs.append(v)


def normalize(base, href):
    href = href.strip()
    if href.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
        return None
    u = urllib.parse.urldefrag(urllib.parse.urljoin(base, href))[0]
    p = urllib.parse.urlsplit(u)
    if p.scheme not in ("http", "https"):
        return None
    return u


def same_host(a, b):
    return urllib.parse.urlsplit(a).hostname == urllib.parse.urlsplit(b).hostname


def links_from_html(base, html):
    parser = _Links()
    try:
        parser.feed(html)
    except Exception:
        pass
    out = []
    for h in parser.hrefs:
        u = normalize(base, h)
        if u and same_host(u, base):
            out.append(u)
    return out


def sitemap_urls(base, fetch, limit=200):
    """Read /sitemap.xml (and up to 3 child sitemaps). Returns [] when absent; never raises."""
    out = []
    try:
        r = fetch(urllib.parse.urljoin(base, "/sitemap.xml"))
        if r.status != 200:
            return []
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
        if "<sitemapindex" in r.text:
            for child in locs[:3]:
                try:
                    c = fetch(child)
                    if c.status == 200:
                        out += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", c.text)
                except Exception:
                    continue
        else:
            out = locs
    except Exception:
        return []
    return out[:limit]


def pick_pages(home_url, home_html, sitemap, max_pages):
    """Homepage first, then homepage links, then sitemap entries; same host, deduped, capped."""
    seen, pages = set(), []
    cands = [home_url] + links_from_html(home_url, home_html) + [
        u for u in (normalize(home_url, s) for s in sitemap) if u and same_host(u, home_url)]
    for u in cands:
        key = u.rstrip("/")
        if key in seen or SKIP_EXT.search(urllib.parse.urlsplit(u).path):
            continue
        seen.add(key)
        pages.append(u)
        if len(pages) >= max_pages:
            break
    return pages
