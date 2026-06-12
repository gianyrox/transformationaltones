# Transformational Tones — static replica

An exact, self-contained static replica of **transformationaltones.com** (originally
built on GoHighLevel / GHL, a Nuxt SSR funnel) for deployment on Vercel. Authorized
rebuild for the site owner (KT / Kaitlynn Tassone).

The replica preserves the original server-rendered DOM and CSS so it stays
pixel-faithful — no design was hand-recreated. The GHL HTML was **sanitized**, not
rebuilt: runtime/tracking JS stripped, every CDN asset localized, internal links
cleaned, and the few inter-page inconsistencies (titles, fonts, footer links)
normalized.

## What's in the repo

```
site/            ← the deployable static site (what Vercel serves)
  index.html               (= /)
  <route>/index.html       (clean URLs)
  post/<slug>/index.html
  assets/                  ← ONLY the assets the site actually references
    fonts/                 ← localized Google Fonts + FontAwesome + flag sprites
content/         ← founder-provided source content (KT Moonsters bio)
tools/
  build.py                 ← the reproducible sanitizer/builder
  build_moonsters.py       ← generates the new /moonsters page from the bio
vercel.json      ← outputDirectory=site, cleanUrls, redirects
```

Build **inputs** are intentionally *not* committed (see `.gitignore`):

- `scrape/` — the raw GHL HTML for every page (the build's source).
- `assets/` — the full 105 MB deduplicated asset pool + `assets/manifest.json`
  (every original CDN URL → local filename). The build copies only the
  **used** assets into `site/assets/`, so unused/oversized files never enter
  the repo. The largest shipped asset is ~18 MB (well under Vercel/GitHub limits).

To rebuild, you need those two input folders present locally, then run the build.

## Pages

| Route | Source page | Notes |
|-------|-------------|-------|
| `/` | home.html | `/home` redirects here |
| `/contact` | contact.html | |
| `/cosmic-connection` | cosmic-connection.html | |
| `/events` | events.html | |
| `/meetkt` | meetkt.html | "KT the Alchemist" bio; cross-links to `/moonsters` |
| `/membership` | membership.html | embeds MindBody widget (kept remote, see below) |
| `/nsny-studio` | nsny-studio.html | Syracuse studio |
| `/privacy` | privacy.html | |
| `/sound-bath-sunday` | sound-bath-sunday.html | |
| `/soundtherapy` | soundtherapy.html | |
| `/terms` | terms.html | |
| `/transformationalblog` | transformationalblog.html | canonical blog; `/blog` redirects here |
| `/brooklyn-studio` | brooklyn-studio.html | embeds MindBody widget (kept remote) |
| `/post/astologycare` | post/astologycare.html | |
| `/post/gemini-full-moon-120425` | post/gemini-full-moon-120425.html | |
| `/post/new-moon-121925` | post/new-moon-121925.html | |
| `/post/quiethobby` | post/quiethobby.html | |
| `/moonsters` | **new** (from `content/kt-moonsters-bio.md`) | built on the privacy-page chrome for visual consistency |

### Blog choice (`/blog` vs `/transformationalblog`)

Two blog scrapes existed. `transformationalblog.html` is the **canonical** one: it is
what the site's top nav links to, and it is the only variant containing the featured
post cards that link to all four `/post/*` articles. It is served at
`/transformationalblog`; `/blog` 301-redirects to it. `blog.html` was a richer-looking
but post-less variant and is not shipped.

## How it was built

`tools/build.py` (stdlib-only Python) does, per page:

1. **Strip GHL runtime/tracking.** Removes all `<script>` blocks (Nuxt hydration
   data + `stcdn.leadconnectorhq.com/_preview/*.js` module loaders) and dead
   modulepreload/prefetch links. No analytics pixels were present. Inline `<style>`
   blocks are kept verbatim (they carry the layout).
2. **Localize every asset.** Each `images.leadconnectorhq.com`,
   `assets.cdn.filesafe.space`, `firebasestorage.googleapis.com`, and
   `stcdn.leadconnectorhq.com` URL (in `src`, `srcset`, `poster`, CSS
   `background-image`, favicon, etc.) is rewritten to `/assets/<file>` via
   `assets/manifest.json`. `&amp;`/`&` variants are matched. **Result: zero remote
   render-critical references remain in any page.**
3. **Fonts localized.** The original loaded Google Fonts (16 families across head
   `<link>`s and inline `@import`s) and FontAwesome + intl-tel flag sprites from the
   GHL CDN. All were downloaded and bundled into `site/assets/fonts/`
   (`google-fonts.local.css` + 174 woff2 + the FontAwesome webfonts), and every
   font reference rewritten to the local bundle.
4. **Clean internal links.** `https://transformationaltones.com/X` → relative `/X`
   (and `/home` → `/`). External links are preserved as-is: the
   `go.transformationaltones.com` booking funnel, Eventbrite, Momence, Instagram,
   Facebook, Google Maps, and MindBody — **all booking / class-signup links keep
   working.**
5. **Normalize cross-page drift.** Inject a consistent `<title>` per page (several
   scraped pages had none); point the previously JS-driven footer "COMPANY" links
   (`ABOUT US`, `OUR TEAM` — were `href="#"`) at real destinations (`/meetkt`,
   `/moonsters`). Nav/header/footer markup is already identical across pages in the
   source, so it is preserved.
6. **Mobile-menu shim.** A ~25-line vanilla-JS shim is injected before `</body>` to
   restore the hamburger / submenu toggle behavior that the stripped GHL runtime
   used to provide. No other JS runs.

The new **/moonsters** page (`tools/build_moonsters.py`) is generated by cloning the
privacy page's chrome (same GHL `c-section` / `c-heading` / `c-paragraph` markup and
CSS classes → guaranteed visual consistency), swapping its hero `<h1>` and text body
for KT's Moonsters DAO bio (verbatim from `content/kt-moonsters-bio.md`), and removing
the privacy-specific CTA section. It is cross-linked from `/meetkt` (a "KT × Moonsters
DAO" card) and from every page's footer.

## Forms & embeds

- **No HTML `<form>` elements and no form iframes exist** in the source. GHL's
  contact/opt-in forms were rendered client-side by the (now-stripped) runtime, so
  there is nothing to submit. The site funnels contact through the **`/contact`
  page** and the external **`go.transformationaltones.com` booking funnel**, both of
  which are preserved and functional. No `mailto:` fallback was needed because no
  inline form markup survived in the SSR HTML.
- **MindBody class widgets** (on `/membership` and `/brooklyn-studio`) load from
  `widgets.mindbodyonline.com` / `brandedweb.mindbodyonline.com`. These are the live
  booking widgets — they were **kept remote** so class booking keeps working. They
  are the only remaining third-party script references in the build.

## JS-rendered content

The scraped GHL pages are **server-rendered**: real `<h1>`/`<h2>`/`<p>` content lives
in the HTML (verified per page), so stripping the JS does not remove visible content.
The only things that were JS-only were (a) the mobile menu toggle — restored via the
shim, (b) the footer COMPANY links — re-wired to real targets, and (c) the MindBody
booking widgets — kept remote.

## Rebuild

```bash
# requires the local build inputs: scrape/ and assets/ (with manifest.json)
python3 tools/build.py
```

The build is idempotent — it wipes and regenerates `site/` each run, and copies only
the assets the regenerated pages reference (resolving transitive CSS `url()` refs).

## Deploy

Static deployment on Vercel; `vercel.json` sets `outputDirectory: "site"`,
`cleanUrls: true`, and the `/home` → `/` and `/blog` → `/transformationalblog`
redirects.

```bash
vercel deploy --prod --yes
```
