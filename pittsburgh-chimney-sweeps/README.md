# Pittsburgh Chimney Sweeps — website

A 52-page static website: home, 9 service pages, 15 town pages, 9 homeowner guides,
5 ad landing pages, booking, about, reviews, FAQ, realtors, careers, privacy and 404.
No framework and no dependencies beyond Node.js.

## Deploy

Upload the contents of **`site/`** to any static host (Netlify, Cloudflare Pages, Hostinger,
GitHub Pages, S3). Configure the host to serve `404.html` for missing pages.

## Edit

| What | Where |
|---|---|
| Phone, email, license, rating, hours, announcement bar, booking endpoint | `site.config.json` |
| Services list, service-area towns and ZIP codes, reviews | `site.config.json` |
| Page content | `src/pages/**.html` |
| Header, footer, booking form, shared sections | `src/partials/` |
| Styles / behavior | `src/assets/css/site.css`, `src/assets/js/site.js` |

Then rebuild:

```
node build.mjs            # build site/ and check links, titles, tokens
node build.mjs --launch   # same, but fails while placeholder business details remain
```

Writing a new page? Read `AUTHORING.md`. Every component is shown on `site/styleguide.html`.

## Before launch

`node build.mjs` prints a "Before launch" list. Today it includes:

1. Real phone number (`phone`, `phoneTel`) and PA HIC number (`license`).
2. Real Google reviews in `reviews` (delete `"sample": true`), the real `rating` and `reviewCount`,
   then set `"ratingVerified": true`, plus your Google review link (`googleReviewsUrl`).
3. `bookingEndpoint`: where the booking form posts (a Workiz online-booking webhook, Formspree,
   Netlify Forms, etc.). Until it's set, forms show their success screen but send nothing.
4. Review the `<!-- OWNER: … -->` notes in `src/pages` (`grep -rn OWNER src/pages`): sweep
   durations, liner brands, payment methods, careers details, founder story and similar facts only
   you can confirm.
5. Confirm the standard promises used site-wide are true for your business: CSIA-certified
   technicians, licensed and insured, written upfront pricing, photo reports the same day, 2-hour arrival
   window with on-the-way text, drop cloths and HEPA vacuums, Saturday hours, reply within one
   business hour, free written repair estimates.
6. Recommended: real photos (crew, trucks, before/after, a sample photo report), a Google Business
   Profile, analytics and ad conversion tracking (update `privacy.html` when you add them).

## Ad landing pages

`site/lp/*.html` are noindex pages for paid traffic, with no navigation:
`chimney-sweep`, `home-buyer-inspection`, `chimney-leak`, `masonry-repair`, `dryer-vent`.
