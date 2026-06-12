#!/usr/bin/env python3
"""
build_moonsters.py — generates the /moonsters page by cloning the chrome
(nav/header/footer + typography) of the scraped privacy.html page and swapping
its single text section for KT's Moonsters DAO bio. This guarantees the new
page is pixel-consistent with the rest of the site (same GHL section/heading/
paragraph markup, same CSS classes) without hand-recreating any design.

Called from build.py with the shared sanitizing helpers.
"""
import re, os, html as htmlmod


def _bio_to_blocks(md_path):
    """Parse the founder-provided markdown bio into (title, [paragraphs])."""
    lines = open(md_path, encoding="utf-8").read().splitlines()
    title = "Kaitlynn Tassone — Moonsters DAO"
    paras = []
    buf = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("# "):
            title = s[2:].strip()
            continue
        if not s:
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        buf.append(s)
    if buf:
        paras.append(" ".join(buf))
    return title, paras


def build(SITE, SCRAPE, TITLES, strip_runtime, rewrite_assets,
          rewrite_links, normalize_head, MOBILE_MENU_SHIM, ROOT):
    src = os.path.join(SCRAPE, "privacy.html")
    text = open(src, encoding="utf-8").read()

    md = os.path.join(ROOT, "content", "kt-moonsters-bio.md")
    title, paras = _bio_to_blocks(md)

    # --- swap the H1 text ----------------------------------------------------
    text = re.sub(
        r'<h1>Transformational Tones LLC — Privacy Policy</h1>',
        "<h1>" + htmlmod.escape(title, quote=False) + "</h1>",
        text, count=1)

    # --- build the bio paragraph HTML (matches GHL <p> output) ---------------
    # add an eyebrow intro line consistent with site tone, then the bio paras.
    p_html = "".join(
        "<p>" + htmlmod.escape(p, quote=False) + "</p>" for p in paras
    )
    # cross-link back to /meetkt at the end, styled as a normal paragraph link.
    p_html += ('<p></p><p><a href="/meetkt">&larr; Back to Meet KT the Alchemist</a></p>')

    # The privacy page's first paragraph block id is paragraph-srKSmhO3gGg.
    # Replace its inner content div with our bio, then strip the remaining
    # privacy paragraph blocks in that section.
    def replace_first_paragraph(t):
        m = re.search(
            r'(<div class="paragraph-srKSmhO3gGg text-output cparagraph-srKSmhO3gGg[^"]*"[^>]*><div>)(.*?)(</div></div>)',
            t, re.S)
        if not m:
            raise SystemExit("moonsters: could not locate first paragraph block in privacy.html template")
        return t[:m.start()] + m.group(1) + p_html + m.group(3) + t[m.end():]

    text = replace_first_paragraph(text)

    # Remove every OTHER privacy paragraph block (keep only the one we filled).
    # Each block is: <!--[--><div id="paragraph-XXXX" class="c-paragraph c-wrapper">...</div><!--]-->
    def strip_other_paragraphs(t):
        pat = re.compile(
            r'<!--\[--><div id="paragraph-(\w+)" class="c-paragraph c-wrapper">.*?</div><!--\]-->',
            re.S)
        def repl(m):
            return m.group(0) if m.group(1) == "srKSmhO3gGg" else ""
        return pat.sub(repl, t)

    text = strip_other_paragraphs(text)

    # --- repurpose the privacy-page pre-footer CTA banner --------------------
    # The privacy template's pre-footer banner reads "Our memberships are
    # exclusive and private…" with a CONTACT US button. That copy is wrong on a
    # bio page, but the banner is shared site chrome and is welded into the same
    # GHL section as the footer — so instead of deleting it (which would take the
    # footer with it), we just swap the headline to fitting copy and keep the
    # existing CONTACT US button + layout intact.
    text = text.replace(
        "Our memberships are exclusive and private. In order to be a member with us, you must be approved.",
        "Want to bring this work to your community, team, or event?",
        1)

    # --- sanitize identically to the other pages -----------------------------
    text = strip_runtime(text)
    text, _ = rewrite_assets(text)
    text = rewrite_links(text)
    text = normalize_head(text, "/moonsters")
    text = text.replace("</body>", MOBILE_MENU_SHIM + "</body>", 1)

    dest = os.path.join(SITE, "moonsters", "index.html")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w", encoding="utf-8").write(text)
    print("moonsters page built (", len(paras), "bio paragraphs )")
