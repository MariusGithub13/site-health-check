"""Rendered checks in one headless Chromium: accessibility, phone overflow and text contrast.

Adapted from Devaland's own daily audit tools. Every browser request is re-checked by the SSRF guard.
Findings are language-independent: {"sev": "fail"|"warn", "code": str, "params": {...}}.
"""
import socket
import urllib.parse

from playwright.sync_api import sync_playwright

from . import USER_AGENT
from .security import SSRFError, UnresolvableError, check_url
from .states import FAILED, PASSED, UNKNOWN

NAV_TIMEOUT = 30000
VAGUE = ("click aici", "aici", "citește mai mult", "citeste mai mult", "read more", "click here", "more",
         "află mai multe", "afla mai multe", "vezi", "here", "learn more")

JS_HREFS = "()=>[...document.querySelectorAll('a[href]')].map(a=>a.href)"

JS_FOCUS = """()=>{const a=document.activeElement;if(!a||a===document.body)return null;
 const s=getComputedStyle(a);return {st:s.outlineStyle,w:s.outlineWidth,sh:s.boxShadow}}"""

JS_ALT = "()=>{const i=[...document.querySelectorAll('img')];return {n:i.length,missing:i.filter(x=>x.getAttribute('alt')===null).length}}"

JS_MOTION = """()=>{let n=0;document.querySelectorAll('*').forEach(e=>{const s=getComputedStyle(e);
 if(s.animationName&&s.animationName!=='none'&&s.animationIterationCount==='infinite')n++});return n}"""

JS_TARGETS = """()=>{const els=[...document.querySelectorAll('header a, header button, nav a, nav button')];
 return els.map(e=>{const r=e.getBoundingClientRect();const s=getComputedStyle(e);
  if(s.display==='none'||s.visibility==='hidden'||r.width===0) return null;
  if(r.width>=44&&r.height>=44) return null;
  const name=(e.innerText||e.getAttribute('aria-label')||(e.querySelector('img')||{}).alt||'link').trim();
  return name.slice(0,28)+' '+Math.round(r.width)+'x'+Math.round(r.height)}).filter(Boolean)}"""

JS_OVERFLOW = """()=>{const vw=document.documentElement.clientWidth;const bad=[];
 const clipped=(el)=>{for(let a=el.parentElement;a&&a!==document.body&&a!==document.documentElement;a=a.parentElement){
   const s=getComputedStyle(a);if(/(hidden|auto|scroll|clip)/.test(s.overflowX)&&a.getBoundingClientRect().right<=vw+1)return true}return false};
 for(const el of document.body.querySelectorAll('*')){const r=el.getBoundingClientRect();if(r.width===0||r.height===0)continue;
  if(r.right>vw+1&&r.left<vw){const s=getComputedStyle(el);if(s.position==='fixed')continue;if(clipped(el))continue;
   const p=el.parentElement.getBoundingClientRect();if(p.right>vw+1&&el.parentElement!==document.body)continue;
   bad.push(el.tagName.toLowerCase()+' right='+Math.round(r.right)+' "'+(el.innerText||'').slice(0,40).replace(/\\n/g,' ')+'"')}}
 return {vw,n:bad.length,bad:bad.slice(0,3),text:document.body.innerText.length}}"""

JS_CONTRAST = r"""()=>{
 const parseRGB=s=>{const m=s.match(/rgba?\(([^)]+)\)/);if(!m)return null;const p=m[1].split(',').map(x=>parseFloat(x.trim()));return{r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}};
 const over=(f,b)=>({r:f.r*f.a+b.r*(1-f.a),g:f.g*f.a+b.g*(1-f.a),b:f.b*f.a+b.b*(1-f.a),a:1});
 const bgOf=el=>{const layers=[];let n=el;while(n&&n.nodeType===1){const st=getComputedStyle(n);const c=parseRGB(st.backgroundColor);
   if(c&&c.a>0)layers.push(c);if(c&&c.a===1)break;
   const bi=st.backgroundImage||'';if(/gradient\(/.test(bi)){const stops=(bi.match(/rgba?\([^)]*\)/g)||[]).map(parseRGB).filter(x=>x&&x.a>=0.6);
    if(stops.length){const m=stops.reduce((a,x)=>({r:a.r+x.r,g:a.g+x.g,b:a.b+x.b}),{r:0,g:0,b:0});layers.push({r:m.r/stops.length,g:m.g/stops.length,b:m.b/stops.length,a:1});break}}
   n=n.parentElement}
  let acc={r:255,g:255,b:255,a:1};for(let i=layers.length-1;i>=0;i--)acc=over(layers[i],acc);return acc};
 const lum=c=>{const f=x=>{x/=255;return x<=0.04045?x/12.92:Math.pow((x+0.055)/1.055,2.4)};return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b)};
 const ratio=(a,b)=>{const [hi,lo]=[lum(a),lum(b)].sort((x,y)=>y-x);return (hi+0.05)/(lo+0.05)};
 const out=[];const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);const seen=new Set();let node;
 while((node=w.nextNode())){const text=node.textContent.trim();if(!text)continue;const el=node.parentElement;if(!el||seen.has(el))continue;
  if(['SCRIPT','STYLE','NOSCRIPT'].includes(el.tagName))continue;if(el.closest('svg'))continue;
  const st=getComputedStyle(el);if(st.visibility==='hidden'||st.display==='none'||+st.opacity===0)continue;
  const rect=el.getBoundingClientRect();if(rect.width<=1||rect.height<=1)continue;seen.add(el);
  const fg=over(parseRGB(st.color),bgOf(el));const bg=bgOf(el);const px=parseFloat(st.fontSize);const wt=parseInt(st.fontWeight,10)||400;
  const large=px>=24||(px>=18.66&&wt>=700);
  out.push({text:text.slice(0,50),tag:el.tagName.toLowerCase(),px,ratio:Math.round(ratio(fg,bg)*100)/100,need:large?3:4.5})}
 return out}"""


def _guard_route(cache):
    def handler(route):
        url = route.request.url
        if url.startswith(("data:", "blob:", "about:")):
            return route.continue_()
        host = urllib.parse.urlsplit(url).hostname
        ok = cache.get(host)
        if ok is None:
            try:
                check_url(url)
                ok = True
            except (SSRFError, UnresolvableError):
                ok = False
            cache[host] = ok
        return route.continue_() if ok else route.abort()
    return handler


def _result(state, findings=None, **extra):
    d = {"state": state, "findings": findings or []}
    d.update(extra)
    return d


def _finish(findings):
    return FAILED if any(f["sev"] == "fail" for f in findings) else PASSED


def audit_page(page, url):
    """Return {'a11y':..., 'overflow':..., 'contrast':..., 'hrefs': [...]} for one URL."""
    out = {"url": url}
    try:
        resp = page.goto(url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass
        page.wait_for_timeout(800)
    except Exception as e:
        for k in ("a11y", "overflow", "contrast"):
            out[k] = _result(UNKNOWN, [{"sev": "fail", "code": "open_failed", "params": {"why": type(e).__name__}}])
        out["hrefs"] = []
        return out
    if resp is None or resp.status >= 400:
        st = resp.status if resp else 0
        for k in ("a11y", "overflow", "contrast"):
            out[k] = _result(UNKNOWN, [{"sev": "fail", "code": "http_status", "params": {"status": st}}])
        out["hrefs"] = []
        return out
    try:
        out["hrefs"] = page.evaluate(JS_HREFS)
    except Exception:
        out["hrefs"] = []

    # ---- accessibility (desktop part) ----
    f, unk = [], 0
    def attempt(code, fn):
        nonlocal unk
        try:
            fn()
        except Exception:
            unk += 1
            f.append({"sev": "warn", "code": "test_unavailable", "params": {"test": code}})
    def t_focus():
        page.keyboard.press("Tab")
        x = page.evaluate(JS_FOCUS)
        if not x:
            f.append({"sev": "fail", "code": "focus_none", "params": {}})
        elif x["st"] == "none" and x["sh"] in ("none", ""):
            f.append({"sev": "fail", "code": "focus_invisible", "params": {}})
    def t_alt():
        x = page.evaluate(JS_ALT)
        if x["missing"]:
            f.append({"sev": "fail", "code": "alt_missing", "params": {"n": x["missing"], "total": x["n"]}})
    def t_links():
        txts = page.eval_on_selector_all("a", "e=>e.map(x=>(x.innerText||'').trim().toLowerCase())")
        bad = sorted({t for t in txts if t in VAGUE})
        if bad:
            f.append({"sev": "fail", "code": "link_text", "params": {"texts": ", ".join(bad[:4])}})
    def t_h1():
        n = page.eval_on_selector_all("h1", "e=>e.length")
        if n != 1:
            f.append({"sev": "fail", "code": "h1_count", "params": {"n": n}})
    def t_motion():
        n = page.evaluate(JS_MOTION)
        if n:
            f.append({"sev": "warn", "code": "motion", "params": {"n": n}})
    def t_decl():
        hrefs = [h.lower() for h in out["hrefs"]]
        if not any("accesibilit" in h or "accessib" in h for h in hrefs):
            f.append({"sev": "warn", "code": "no_statement", "params": {}})
    def t_lang():
        if not page.evaluate("()=>(document.documentElement.getAttribute('lang')||'').trim()"):
            f.append({"sev": "fail", "code": "no_lang", "params": {}})
    def t_title():
        if not page.title().strip():
            f.append({"sev": "fail", "code": "no_title", "params": {}})
    for code, fn in (("focus", t_focus), ("alt", t_alt), ("links", t_links), ("h1", t_h1), ("motion", t_motion),
                     ("statement", t_decl), ("lang", t_lang), ("title", t_title)):
        attempt(code, fn)

    # contrast at desktop width
    try:
        rows = page.evaluate(JS_CONTRAST)
        bad = sorted([r for r in rows if r["ratio"] < r["need"]], key=lambda r: r["ratio"])
        cf = [{"sev": "fail", "code": "contrast_low",
               "params": {"ratio": r["ratio"], "need": r["need"], "px": round(r["px"]), "text": r["text"]}}
              for r in bad[:5]]
        if rows:
            out["contrast"] = _result(FAILED if bad else PASSED, cf, total=len(rows), failing=len(bad))
        else:
            out["contrast"] = _result(UNKNOWN, [{"sev": "warn", "code": "no_text", "params": {}}])
    except Exception:
        out["contrast"] = _result(UNKNOWN, [{"sev": "warn", "code": "test_unavailable", "params": {"test": "contrast"}}])

    # ---- phone width: touch targets, overflow ----
    try:
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        small = page.evaluate(JS_TARGETS)
        if small:
            f.append({"sev": "fail", "code": "touch_target", "params": {"items": " | ".join(small[:4])}})
        r = page.evaluate(JS_OVERFLOW)
        if r["text"] < 200:
            out["overflow"] = _result(UNKNOWN, [{"sev": "warn", "code": "rendered_little", "params": {"n": r["text"]}}])
        elif r["n"]:
            out["overflow"] = _result(FAILED, [{"sev": "fail", "code": "overflow", "params": {"n": r["n"], "items": " | ".join(r["bad"])}}])
        else:
            out["overflow"] = _result(PASSED)
    except Exception:
        unk += 1
        out["overflow"] = _result(UNKNOWN, [{"sev": "warn", "code": "test_unavailable", "params": {"test": "overflow"}}])
    try:
        page.set_viewport_size({"width": 320, "height": 900})
        page.wait_for_timeout(500)
        if page.evaluate("()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+2"):
            f.append({"sev": "fail", "code": "zoom", "params": {}})
        page.set_viewport_size({"width": 1280, "height": 900})
    except Exception:
        f.append({"sev": "warn", "code": "test_unavailable", "params": {"test": "zoom"}})
    state = _finish(f)
    if state == PASSED and unk:
        state = UNKNOWN
    out["a11y"] = _result(state, f)
    return out


def run_browser(pages):
    """Audit pages one after another in ONE browser. Returns a list of per-page dicts."""
    results = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--no-sandbox"])
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, user_agent=USER_AGENT,
                            service_workers="block")
        ctx.route("**/*", _guard_route({}))
        page = ctx.new_page()
        for u in pages:
            try:
                results.append(audit_page(page, u))
            except Exception as e:
                try:
                    page.close()
                except Exception:
                    pass
                page = ctx.new_page()
                r = {"url": u, "hrefs": []}
                for k in ("a11y", "overflow", "contrast"):
                    r[k] = _result(UNKNOWN, [{"sev": "fail", "code": "open_failed", "params": {"why": type(e).__name__}}])
                results.append(r)
        b.close()
    return results
