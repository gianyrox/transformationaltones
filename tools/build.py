#!/usr/bin/env python3
"""
build.py — Reproducible sanitizer/builder for the transformationaltones.com static replica.

Reads raw GoHighLevel (GHL/Nuxt SSR) HTML from scrape/, the asset manifest from
assets/manifest.json, and produces a clean static site in site/ with:
  - GHL runtime/tracking JS stripped (Nuxt hydration data, _preview module scripts)
  - every CDN asset URL rewritten to local /assets/<file>
  - internal transformationaltones.com links rewritten to clean relative URLs
  - external booking/social links (go.transformationaltones.com, eventbrite,
    instagram, facebook, momence, google maps, mindbody) left intact
  - a normalized <head> (consistent title, local Google Fonts, favicon)
  - a tiny vanilla mobile-menu shim injected (replaces stripped GHL nav JS)

Only the standard library is used. Run from repo root: python3 tools/build.py
"""
import re, json, os, html as htmlmod, shutil, glob, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPE = os.path.join(ROOT, "scrape")
ASSETS = os.path.join(ROOT, "assets")
SITE = os.path.join(ROOT, "site")
SITE_ASSETS = os.path.join(SITE, "assets")

MANIFEST = json.load(open(os.path.join(ASSETS, "manifest.json")))

# ---- page routing -----------------------------------------------------------
# source file (relative to scrape/) -> output clean path (no trailing slash)
PAGES = {
    "home.html": "/",
    "contact.html": "/contact",
    "cosmic-connection.html": "/cosmic-connection",
    "events.html": "/events",
    "meetkt.html": "/meetkt",
    "membership.html": "/membership",
    "nsny-studio.html": "/nsny-studio",
    "privacy.html": "/privacy",
    "sound-bath-sunday.html": "/sound-bath-sunday",
    "soundtherapy.html": "/soundtherapy",
    "terms.html": "/terms",
    "transformationalblog.html": "/transformationalblog",
    "brooklyn-studio.html": "/brooklyn-studio",
    "post/astologycare.html": "/post/astologycare",
    "post/gemini-full-moon-120425.html": "/post/gemini-full-moon-120425",
    "post/new-moon-121925.html": "/post/new-moon-121925",
    "post/quiethobby.html": "/post/quiethobby",
}

# Consistent <title> per page (some scraped pages had no <title>).
TITLES = {
    "/": "Transformational Sound Therapy & Creative Wellness",
    "/contact": "Contact — Transformational Tones",
    "/cosmic-connection": "Cosmic Connection — Transformational Tones",
    "/events": "Events — Transformational Tones",
    "/meetkt": "Meet KT the Alchemist — Transformational Tones",
    "/membership": "Memberships — Transformational Tones",
    "/nsny-studio": "Syracuse Studio — Transformational Tones",
    "/privacy": "Privacy Policy — Transformational Tones",
    "/sound-bath-sunday": "Sound Bath Sunday — Transformational Tones",
    "/soundtherapy": "Sound Therapy — Transformational Tones",
    "/terms": "Terms of Use — Transformational Tones",
    "/transformationalblog": "Transformational Tones Blog — Sound, Movement & Healing Insights",
    "/brooklyn-studio": "Brooklyn Studio — Transformational Tones",
    "/moonsters": "KT × Moonsters DAO — Transformational Tones",
    "/post/astologycare": "Astrology as Self-Care — Transformational Tones",
    "/post/gemini-full-moon-120425": "Gemini Full Moon — Transformational Tones",
    "/post/new-moon-121925": "New Moon — Transformational Tones",
    "/post/quiethobby": "The Quiet Hobby — Transformational Tones",
}

# internal site paths (for link rewriting) — everything under the apex domain.
INTERNAL_PATHS = {
    "/home", "/contact", "/cosmic-connection", "/events", "/meetkt",
    "/membership", "/nsny-studio", "/privacy", "/sound-bath-sunday",
    "/soundtherapy", "/terms", "/transformationalblog", "/blog",
    "/brooklyn-studio", "/moonsters",
    "/post/astologycare", "/post/gemini-full-moon-120425",
    "/post/new-moon-121925", "/post/quiethobby",
}

# ---- asset URL rewriting ----------------------------------------------------
# Build a lookup that tolerates &amp; vs & and trailing variations.
_ASSET_MAP = {}
for url, local in MANIFEST.items():
    if not url.startswith("http"):
        continue
    _ASSET_MAP[url] = local
    _ASSET_MAP[htmlmod.unescape(url)] = local
    _ASSET_MAP[url.replace("&", "&amp;")] = local

ASSET_HOSTS = (
    "images.leadconnectorhq.com",
    "assets.cdn.filesafe.space",
    "firebasestorage.googleapis.com",
    "storage.googleapis.com",
    "stcdn.leadconnectorhq.com",
)

def local_for(url):
    """Return /assets/<file> for a CDN url, or None if not a mapped asset."""
    if url in _ASSET_MAP:
        return "/assets/" + _ASSET_MAP[url]
    u = htmlmod.unescape(url)
    if u in _ASSET_MAP:
        return "/assets/" + _ASSET_MAP[u]
    return None

# A regex matching any CDN asset URL (with optional &amp; entities) inside attrs/CSS.
_URL_RE = re.compile(r'https?://(?:' + '|'.join(re.escape(h) for h in ASSET_HOSTS) + r')[^\s"\'<>()]+')

def rewrite_assets(text):
    """Rewrite every mapped CDN asset URL in the text to its local path."""
    misses = set()
    def repl(m):
        url = m.group(0)
        # strip trailing punctuation that isn't part of the URL
        trail = ""
        while url and url[-1] in ".,;":
            trail = url[-1] + trail
            url = url[:-1]
        loc = local_for(url)
        if loc:
            return loc + trail
        # also try without trailing &amp; fragment differences already handled
        misses.add(url)
        return m.group(0)
    out = _URL_RE.sub(repl, text)
    return out, misses

# ---- internal link rewriting ------------------------------------------------
def rewrite_links(text):
    """transformationaltones.com/X -> /X (clean). go.transformationaltones.com kept."""
    # apex domain (NOT go. subdomain). Handle http/https and optional www.
    def repl(m):
        path = m.group(2)
        # normalize /home -> /
        clean = path or "/"
        if clean == "/home":
            clean = "/"
        return 'href="' + clean + '"'
    # match href="https://(www.)?transformationaltones.com<path>"  (no 'go.' / no '.com/' subdomain)
    pat = re.compile(r'href="https?://(?:www\.)?transformationaltones\.com(/[^"]*)?"')
    text = pat.sub(lambda m: 'href="' + ((m.group(1) or "/") if (m.group(1) or "/") != "/home" else "/") + '"', text)
    return text

# ---- HTML head/script sanitizing -------------------------------------------
MOBILE_MENU_SHIM = """
<script>
/* minimal nav/menu shim — replaces stripped GHL runtime. Toggles the GHL
   mobile nav popup and any submenu open/close on click. */
(function(){
  function ready(fn){ if(document.readyState!='loading') fn(); else document.addEventListener('DOMContentLoaded',fn); }
  ready(function(){
    var popup=document.getElementById('nav-menu-popup');
    // hamburger / open buttons
    document.querySelectorAll('.open-menu, .nav-menu-icon, [class*="open-menu"]').forEach(function(b){
      b.addEventListener('click',function(e){ e.preventDefault(); if(popup){popup.style.display='block'; popup.classList.remove('hide');} });
    });
    document.querySelectorAll('.close-menu, [class*="close-menu"]').forEach(function(b){
      b.addEventListener('click',function(e){ e.preventDefault(); if(popup){popup.style.display='none'; popup.classList.add('hide');} });
    });
    // submenu toggles on mobile
    document.querySelectorAll('.menu-item-title-icon, .submenu-content-container').forEach(function(t){
      t.addEventListener('click',function(){
        var sub=this.parentElement && this.parentElement.querySelector('.submenu');
        if(sub){ sub.classList.toggle('open'); }
      });
    });
  });
})();
</script>
"""

# Third-party booking scripts to PRESERVE (kept remote so booking keeps working).
KEEP_SCRIPT_HOSTS = ("mindbodyonline.com",)

def strip_runtime(text):
    """Remove Nuxt hydration data + GHL module scripts; keep inline <style> and
    third-party booking scripts (MindBody) so class signup keeps working."""
    def script_repl(m):
        block = m.group(0)
        # keep external booking widget scripts (MindBody healcode + branded embed)
        if any(h in block for h in KEEP_SCRIPT_HOSTS):
            return block
        return ""
    text = re.sub(r'<script\b[^>]*>.*?</script>', script_repl, text, flags=re.S|re.I)
    # Remove self-closing/standalone module preload + prefetch links to stcdn JS.
    text = re.sub(r'<link\b[^>]*stcdn\.leadconnectorhq\.com/_preview/[^>]*\.js[^>]*>', '', text, flags=re.I)
    text = re.sub(r'<link\b[^>]*rel="(?:modulepreload|prefetch|preload)"[^>]*\.js[^>]*>', '', text, flags=re.I)
    return text

def normalize_head(text, out_path):
    """Ensure a <title>, localize google-fonts link, drop dead preconnects to CDNs."""
    title = TITLES.get(out_path, "Transformational Tones")
    title_tag = "<title>" + htmlmod.escape(title, quote=False) + "</title>"

    # Replace existing <title>...</title> or inject after <meta charset>.
    if re.search(r'<title>.*?</title>', text, flags=re.S):
        text = re.sub(r'<title>.*?</title>', title_tag, text, count=1, flags=re.S)
    else:
        text = re.sub(r'(<meta charset="[^"]*">)', r'\1' + title_tag, text, count=1)

    # Replace the remote Google Fonts stylesheet link(s) with our local one.
    local_fonts = '<link rel="stylesheet" href="/assets/fonts/google-fonts.local.css">'
    # remove google fonts <link> tags (stylesheet + preload)
    text = re.sub(r'<link\b[^>]*fonts\.googleapis\.com[^>]*>', '', text, flags=re.I)
    # neutralize inline @import url('https://fonts.googleapis.com/...') in <style> blocks
    # (the combined local bundle already contains every family used site-wide).
    text = re.sub(r"@import\s+url\(['\"]?https://fonts\.googleapis\.com/[^)]*\)\s*;?", "", text, flags=re.I)
    # drop now-dead preconnect / dns-prefetch hints to remote CDNs.
    text = re.sub(r'<link\b[^>]*rel="(?:preconnect|dns-prefetch)"[^>]*(?:gstatic|googleapis|leadconnectorhq|filesafe)[^>]*>', '', text, flags=re.I)
    # inject local fonts css right before </head>
    text = text.replace("</head>", local_fonts + "</head>", 1)
    return text

def set_favicon(text):
    """Point favicon at local asset if available, else leave the stcdn ico (small, fine)."""
    return text


# Footer "COMPANY" column links were href="#" placeholders wired by stripped GHL
# JS. Point them at real destinations: ABOUT US -> /meetkt, OUR TEAM -> /moonsters.
FOOTER_FIXES = {
    "button-MV4Ucvs8L5_btn": "/meetkt",     # ABOUT US
    "button-ZfGYv6T7ry_btn": "/moonsters",  # OUR TEAM
}

def fix_footer_links(text):
    for btn_id, dest in FOOTER_FIXES.items():
        text = re.sub(
            r'(<a id="' + re.escape(btn_id) + r'" )href="#"',
            r'\1href="' + dest + '"',
            text)
    return text

# ---- per-page build ---------------------------------------------------------
# A cross-link card to /moonsters, injected into the meetkt page. Uses the
# site's own c-section / c-heading / c-paragraph / c-button classes so it
# inherits the existing design system (no new styling introduced).
MOONSTERS_CARD = (
    '<div class="fullSection noBorder radius0 none c-section c-wrapper section-moonsters-xlink" '
    'style="padding:60px 20px;" id="section-moonsters-xlink">'
    '<div class="inner">'
    '<div class="row-align-center noBorder radius0 none c-row c-wrapper">'
    '<div class="inner"><div class="noBorder radius0 none c-column c-wrapper">'
    '<div class="vertical inner" style="max-width:760px;margin:0 auto;text-align:center;">'
    '<div class="c-heading c-wrapper"><div class="text-output"><div>'
    '<h2>KT &times; Moonsters DAO</h2></div></div></div>'
    '<div class="c-paragraph c-wrapper"><div class="text-output"><div>'
    '<p>Before Transformational Tones, Kaitlynn helped build community, wellness '
    'programming, and creative strategy for Moonsters DAO &mdash; bridging emerging '
    'Web3 technology with real-world human connection.</p>'
    '<p><a href="/moonsters">Read more about KT &times; Moonsters DAO &rarr;</a></p>'
    '</div></div></div>'
    '</div></div></div></div></div></div>'
)


def build_page(src_rel, out_path):
    src = os.path.join(SCRAPE, src_rel)
    text = open(src, encoding="utf-8").read()

    # inject the Moonsters cross-link card into the meetkt page (before the
    # "A Note From Kaitlynn" section).
    if out_path == "/meetkt":
        anchor = '<div class="fullSection noBorder radius0 none c-section c-wrapper section-j0cF6tN5yG"'
        if anchor in text:
            text = text.replace(anchor, MOONSTERS_CARD + anchor, 1)

    text = strip_runtime(text)
    text, misses = rewrite_assets(text)
    text = rewrite_links(text)
    text = fix_footer_links(text)
    text = normalize_head(text, out_path)
    text = set_favicon(text)

    # inject mobile menu shim before </body>
    text = text.replace("</body>", MOBILE_MENU_SHIM + "</body>", 1)

    write_output(out_path, text)
    return misses

def write_output(out_path, text):
    if out_path == "/":
        dest = os.path.join(SITE, "index.html")
    else:
        dest = os.path.join(SITE, out_path.lstrip("/"), "index.html")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w", encoding="utf-8").write(text)

# ---- assets copy (only what the site references) ----------------------------
def collect_used_assets(site_files):
    used = set()
    asset_re = re.compile(r'/assets/([^\s"\'<>()?#]+)')
    for f in site_files:
        txt = open(f, encoding="utf-8").read()
        for m in asset_re.finditer(txt):
            used.add(m.group(1))
    return used

def copy_assets(used):
    os.makedirs(SITE_ASSETS, exist_ok=True)
    copied = 0
    # Always include fonts dir referenced by css (google-fonts.local.css + gf/* + fa + flags)
    # Expand: any css we copy may reference more /assets/ files — resolve transitively.
    pending = set(used)
    resolved = set()
    asset_re = re.compile(r'/assets/([^\s"\'<>()?#]+)')
    while pending:
        name = pending.pop()
        if name in resolved:
            continue
        resolved.add(name)
        srcp = os.path.join(ASSETS, name)
        if not os.path.exists(srcp):
            continue
        if name.endswith(".css"):
            txt = open(srcp, encoding="utf-8", errors="ignore").read()
            for m in asset_re.finditer(txt):
                pending.add(m.group(1))
    for name in sorted(resolved):
        srcp = os.path.join(ASSETS, name)
        if not os.path.exists(srcp):
            continue
        dstp = os.path.join(SITE_ASSETS, name)
        os.makedirs(os.path.dirname(dstp), exist_ok=True)
        shutil.copy2(srcp, dstp)
        copied += 1
    return copied, resolved

# ---- main -------------------------------------------------------------------
def main():
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(SITE)

    all_misses = {}
    for src_rel, out_path in PAGES.items():
        misses = build_page(src_rel, out_path)
        if misses:
            all_misses[out_path] = misses

    # Moonsters page is generated separately by build_moonsters (imported below).
    import build_moonsters
    build_moonsters.build(SITE, SCRAPE, TITLES, strip_runtime, rewrite_assets,
                          rewrite_links, normalize_head, MOBILE_MENU_SHIM, ROOT)

    # collect + copy assets the site actually uses
    site_files = glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)
    used = collect_used_assets(site_files)
    copied, resolved = copy_assets(used)

    print("pages built:", len(PAGES) + 1)
    print("assets referenced+resolved:", len(resolved), "| copied:", copied)
    if all_misses:
        print("\nUNMAPPED asset URLs (left remote):")
        for p, ms in all_misses.items():
            for u in ms:
                print(" ", p, u[:120])
    else:
        print("no unmapped asset URLs — all CDN assets localized")

if __name__ == "__main__":
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    main()
