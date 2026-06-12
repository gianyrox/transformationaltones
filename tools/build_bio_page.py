#!/usr/bin/env python3
"""
build_bio_page.py — generic builder for bio pages (e.g. /moonsters,
/kt-the-alchemist). Clones the chrome (nav/header/footer + typography) of the
scraped privacy.html page and swaps its single text section for a founder-
provided markdown bio. This guarantees each new page is pixel-consistent with
the rest of the site (same GHL section/heading/paragraph markup, same CSS
classes) without hand-recreating any design.

A bio page is described by a small spec dict:
    {
      "md": "content/<file>.md",   # founder-provided bio markdown (verbatim)
      "out": "/kt-the-alchemist",  # clean output path / slug
      "h1": "KT The Alchemist",    # H1 + page heading (overrides md '# ...')
      "links": [                   # cross-links appended as a final paragraph
          ("/moonsters", "Read about KT × Moonsters DAO →"),
          ("/meetkt", "← Back to Meet KT the Alchemist"),
      ],
      "cta": "Want to bring this work to your community, team, or event?",
    }

Called from build.py with the shared sanitizing helpers + fix_footer_links so
bio pages get the same localized assets, links, and footer fixes as every
other page.
"""
import re, os, html as htmlmod


def _bio_paragraphs(md_path):
    """Parse founder markdown into [paragraphs] (verbatim, blank-line split)."""
    lines = open(md_path, encoding="utf-8").read().splitlines()
    paras, buf = [], []
    for ln in lines:
        s = ln.strip()
        if s.startswith("# "):
            continue  # H1 comes from the spec, not the md heading
        if not s:
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        buf.append(s)
    if buf:
        paras.append(" ".join(buf))
    return paras


def build_one(spec, SITE, SCRAPE, ROOT,
              strip_runtime, rewrite_assets, rewrite_links,
              normalize_head, fix_footer_links, MOBILE_MENU_SHIM):
    src = os.path.join(SCRAPE, "privacy.html")
    text = open(src, encoding="utf-8").read()

    md = os.path.join(ROOT, spec["md"])
    paras = _bio_paragraphs(md)
    h1 = spec["h1"]
    out_path = spec["out"]

    # --- swap the H1 text ----------------------------------------------------
    text = re.sub(
        r'<h1>Transformational Tones LLC — Privacy Policy</h1>',
        "<h1>" + htmlmod.escape(h1, quote=False) + "</h1>",
        text, count=1)

    # --- build the bio paragraph HTML (matches GHL <p> output) ---------------
    p_html = "".join(
        "<p>" + htmlmod.escape(p, quote=False) + "</p>" for p in paras
    )
    # cross-links, styled as normal paragraph links.
    if spec.get("links"):
        p_html += "<p></p>"
        for href, label in spec["links"]:
            p_html += ('<p><a href="' + href + '">'
                       + htmlmod.escape(label, quote=False) + "</a></p>")

    # The privacy page's first paragraph block id is paragraph-srKSmhO3gGg.
    def replace_first_paragraph(t):
        m = re.search(
            r'(<div class="paragraph-srKSmhO3gGg text-output cparagraph-srKSmhO3gGg[^"]*"[^>]*><div>)(.*?)(</div></div>)',
            t, re.S)
        if not m:
            raise SystemExit(
                "bio_page: could not locate first paragraph block in privacy.html template")
        return t[:m.start()] + m.group(1) + p_html + m.group(3) + t[m.end():]

    text = replace_first_paragraph(text)

    # Remove every OTHER privacy paragraph block (keep only the one we filled).
    def strip_other_paragraphs(t):
        pat = re.compile(
            r'<!--\[--><div id="paragraph-(\w+)" class="c-paragraph c-wrapper">.*?</div><!--\]-->',
            re.S)
        def repl(m):
            return m.group(0) if m.group(1) == "srKSmhO3gGg" else ""
        return pat.sub(repl, t)

    text = strip_other_paragraphs(text)

    # --- repurpose the shared pre-footer CTA banner --------------------------
    cta = spec.get("cta", "Want to bring this work to your community, team, or event?")
    text = text.replace(
        "Our memberships are exclusive and private. In order to be a member with us, you must be approved.",
        cta, 1)

    # --- sanitize identically to the other pages -----------------------------
    text = strip_runtime(text)
    text, _ = rewrite_assets(text)
    text = rewrite_links(text)
    text = fix_footer_links(text)
    text = normalize_head(text, out_path)
    text = text.replace("</body>", MOBILE_MENU_SHIM + "</body>", 1)

    dest = os.path.join(SITE, out_path.lstrip("/"), "index.html")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w", encoding="utf-8").write(text)
    print("bio page built:", out_path, "(", len(paras), "paragraphs )")


def build(SITE, SCRAPE, ROOT, strip_runtime, rewrite_assets, rewrite_links,
          normalize_head, fix_footer_links, MOBILE_MENU_SHIM):
    specs = [
        {
            "md": "content/kt-moonsters-bio.md",
            "out": "/moonsters",
            "h1": "Kaitlynn Tassone — Moonsters DAO",
            "cta": "Want to bring this work to your community, team, or event?",
            "links": [
                ("/kt-the-alchemist", "Read the full KT The Alchemist bio →"),
                ("/meetkt", "← Back to Meet KT the Alchemist"),
            ],
        },
        {
            "md": "content/kt-the-alchemist-bio.md",
            "out": "/kt-the-alchemist",
            "h1": "KT The Alchemist",
            "cta": "Want to bring this work to your community, team, or event?",
            "links": [
                ("/moonsters", "Read about KT × Moonsters DAO →"),
                ("/meetkt", "← Back to Meet KT the Alchemist"),
            ],
        },
    ]
    for spec in specs:
        build_one(spec, SITE, SCRAPE, ROOT,
                  strip_runtime, rewrite_assets, rewrite_links,
                  normalize_head, fix_footer_links, MOBILE_MENU_SHIM)
