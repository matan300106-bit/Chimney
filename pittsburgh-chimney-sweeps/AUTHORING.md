# Authoring guide

How pages are built for the Pittsburgh Chimney Sweeps site. Read this before adding or editing a page.

## How it works

```
site.config.json     business details, services list, service areas, reviews  (single source of truth)
build.mjs            node build.mjs → writes the finished site to site/
src/pages/**.html    one file per page (body content only + front matter)
src/partials/*.html  shared blocks, included with {{> name}}
src/assets/          css, js, img (copied to site/assets/)
site/                GENERATED. Never edit by hand. This folder is what gets uploaded.
```

Run `node build.mjs` after every change. It prints problems: broken links, unfilled `{{tokens}}`,
missing title/description, wrong number of `<h1>`. `node build.mjs --strict` fails on any problem.
**A page is not done until the build reports no problems for it.**

Preview: open `site/<page>.html` in a browser (file:// works, all links are relative).

## Page file format

```html
<!--page
{
  "title": "Chimney Sweeping in Pittsburgh | Pittsburgh Chimney Sweeps",
  "description": "150–160 characters. What the page offers, where, and why us.",
  "nav": "services",
  "crumbs": [["Services", "services/index.html"], ["Chimney Sweeping"]],
  "faqSchema": true,
  "schema": {"@type": "Service", "name": "Chimney Sweeping", "serviceType": "Chimney sweeping", "provider": {"@id": "https://www.pittsburghchimneysweeps.com/#business"}, "areaServed": "Greater Pittsburgh, PA"}
}
-->
<section class="phero on-dark"> … </section>
<section class="section"> … </section>
{{> cta-band}}
```

Front-matter fields (JSON, double quotes, no trailing commas):

| field | use |
|---|---|
| `title` | `<title>`. Pattern: `Primary keyword + Pittsburgh | Pittsburgh Chimney Sweeps`, ≤ 65 chars where possible |
| `description` | meta description, 140–160 chars |
| `nav` | highlights a header link: `services`, `areas`, `reviews`, `about`, `resources`, `contact` |
| `crumbs` | breadcrumb trail after Home. Paths are from the site root, no leading slash. Last item has no path. Rendered wherever the page writes `{{crumbs}}` (put it at the top of the hero) and emitted as BreadcrumbList schema |
| `faqSchema` | `true` → FAQPage schema generated from the page's `<details><summary>Q</summary><div class="ans">A</div></details>` items |
| `schema` | extra JSON-LD object or array (Service, Article…). `@context` is added for you |
| `layout` | `"landing"` → minimal header (logo + phone), no nav, minimal footer. For ad landing pages |
| `noindex` | `true` → robots noindex, left out of sitemap (thank-you, 404, style guide) |
| `css` | list of extra stylesheet names in `src/assets/css/` (avoid; prefer shared classes) |
| `bodyClass` | extra class on `<body>` |
| `bookService` | preselects this service in the page's booking form (exact service name from config) |

## Tokens

Write these instead of hard-coding business details. **Never type the phone number, email or license by hand.**

`{{root}}` relative prefix to site root, **required on every internal link and asset**: `href="{{root}}services/chimney-liners.html"` ·
`{{name}}` · `{{phone}}` · `{{phoneTel}}` (for `tel:` links) · `{{email}}` · `{{license}}` · `{{rating}}` · `{{reviewCount}}` ·
`{{hoursWeekday}}` · `{{hoursSaturday}}` · `{{hoursSunday}}` · `{{googleReviewsUrl}}` · `{{year}}` · `{{crumbs}}`

## Partials

Layout (added automatically): header, footer, util bar, mobile call/book bar, icon sprite.

Include in page bodies with `{{> name}}`:

| partial | what |
|---|---|
| `skyline` | Pittsburgh rooftop/bridge silhouette. Put as the last child of a `.hero` or `.phero` section |
| `trust` | 5-item credentials strip |
| `quickbook` | short booking card (hero aside on home/landing). Sends details to the booking form |
| `booking-form` | full booking form card (no band around it). One per page |
| `book-section` | dark band with booking copy + `booking-form`, `id="book"`. One per page |
| `cta-band` | dark band: "Ready when you are" + Book / Call buttons → book.html. End most interior pages with this |
| `inspection-levels` | Level 1/2/3 tabs (dark band, `id="inspections"`) |
| `compare` | us vs typical sweep table |
| `process` | 4-step "how it works" |
| `self-check` | warning-sign checklist with live verdict (`id="self-check"`) |
| `map` | stylised three-rivers map card |
| `services-grid` | 9 service cards (from config) linking to service pages |
| `areas-grid` / `areas-chips` | service-area links (from config) |
| `reviews` / `reviews-all` | first 3 / all review cards from config (auto-labelled "Sample" until real ones are added) |
| `rating-badge` | big rating number + stars |
| `service-options` | `<option>`s for a service `<select>` |

Preselect the service on the page's booking form with front matter `"bookService": "Chimney Liners"` (must match a service `name` in config exactly).

## Components (see site/styleguide.html for live examples)

Bands: `section.section` (96px padding), modifiers `.tight`, `.flush-top`; backgrounds `.band-paper`, `.band-sand`,
`.band-dark` (add `on-dark` too). Alternate light bands; don't stack two dark bands.
Inner: `.wrap` (1200px + gutters), `.wrap.wrap-narrow` (820px).
Heads: `.section-head` (+`.center`) containing `.eyebrow`, `h2`, `.lede`.
Hero: `.phero.on-dark` (+`.no-aside`, `.short`) with `{{crumbs}}`, eyebrow, `h1` (gold word in `<em>`), `.lede`, `.hero-ctas`, optional `aside.phero-aside`.
Grids: `.grid-2`, `.grid-3`, `.grid-4`, `.split` (+`.reverse`), `.stack`, `.row`.
Cards: `.card`, `a.card`, `.card-dark`, `.svc` (service card with `.ico`), `.area-card`, `.figure-card` (dark frame for an inline SVG illustration).
Lists: `.checklist` (+`.cols-2`), `.xlist` (warning signs), `.kv` (dl), `.steps` (+`.cols-3`, only for real sequences; use `<ol>`/`<li class="step">`).
Notes: `.callout`, `.callout-warn` (safety only), `.callout-good`. Tags: `.tag`, `.tag-brick`, `.tag-dark`.
Buttons: `.btn` + `.btn-gold` (primary), `.btn-dark`, `.btn-outline`, `.btn-ghost` (on dark), `.btn-white`, size `.btn-sm`, `.btn-block`. `.link-arrow` for text links with an arrow.
Text: `.prose` for long copy (articles, privacy), `.lede`, `.muted`, `.hl` (gold).
FAQ: `.faq-wrap` > (intro col) + `.faq` > `details`.
Articles: `.article` (content + 300px sidebar), `.aside-sticky`, `.toc`, `.resource-card`.
Landing: `.offer`, `.badge-row` > `.badge`, `.lp-hero` on the hero section.
Tables: wrap in `.table-wrap`; `table.table`.
Spacing helpers: `.mt-8 .mt-16 .mt-24 .mt-32 .mt-48`. Add `.reveal` to cards for a subtle scroll-in.

Icons: `<svg><use href="#i-NAME"/></svg>`. Available: phone cal check x star shield badge camera home clock dollar
brush bricks cap liner drop vent flame bird chevron arrow pin mail key alert info users doc wrench snow book.
Inline SVG illustrations are welcome (diagrams of a chimney, flue, crown, flashing, dryer vent run). Use the palette:
#141414 soot, #1A1A1A/#2A2A2A panels, #B8432A brick, #8E3019 mortar lines, #FFB81C gold, #F4F1EB / #B3ADA4 text, #3B6E8F river/water.
Avoid duplicate `id`s inside SVGs (gradients): prefix them with the page slug.

## Content rules

1. **No invented facts about the business.** No founding year, years in business, job counts, staff names,
   awards, prices, dollar figures, percentages, or guarantees beyond what the home page already promises
   (CSIA-certified technicians, licensed & insured, upfront written pricing, photo reports, 2-hour arrival
   windows with on-the-way text, drop cloths/HEPA, Saturday hours, reply within one business hour, free repair estimates).
   Where the owner must supply something, write around it or leave a clearly marked HTML comment `<!-- OWNER: … -->`.
2. **No fake reviews or quotes.** Use `{{> reviews}}` (config-driven, labelled Sample). Never write testimonials inline.
3. **Technical claims must be accurate and conservative.** NFPA 211 (annual inspection; Level 2 at property
   transfer or system change), CSIA, creosote stages, carbon monoxide, freeze-thaw. When unsure, say less.
   No medical/legal advice; safety notes go in `.callout-warn`.
4. **Local content must be true.** Only use ZIP codes from `site.config.json`. Describe neighbourhoods/towns in
   general, well-known terms (housing age, terrain, rivers, neighbouring towns). No invented landmarks, statistics or "we've served X homes here".
5. **Voice:** plain, confident, local. Short sentences. Talk to the homeowner ("your chimney"). No hype words
   (best-in-class, cutting-edge, unparalleled), no exclamation marks in headings, no emoji.
6. **Every page:** one `<h1>`, unique title and description, breadcrumbs (except home and landing pages), at least one
   Book and one Call action, internal links to 2+ related pages, ends with `{{> cta-band}}` or `{{> book-section}}`.
7. **Accessibility:** headings in order (h1 → h2 → h3), descriptive link text, `aria-hidden="true"` on decorative SVG,
   labels on every input, no text in images.
8. **Don't edit shared files** (`site.css`, `site.js`, partials, config, build.mjs) unless you were asked to.
   Need a new component? Note it in your report; for a one-off, a small `<style>` block at the top of your page body is acceptable.
