#!/usr/bin/env node
// Static site builder for Pittsburgh Chimney Sweeps. No dependencies.
//
//   node build.mjs           build src/ → site/, report broken links as warnings
//   node build.mjs --strict  same, but exit 1 on broken links or unfilled {{tokens}}
//   node build.mjs --launch  strict, and also exit 1 while placeholder business details remain
//   node build.mjs --preview --out=DIR   design preview with a placeholder banner, written to DIR
//
// Page files live in src/pages/**.html and start with a front-matter comment:
//   <!--page {"title": "...", "description": "...", "nav": "services", ...} -->
// See AUTHORING.md for every field, token and partial.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(ROOT, "src");
const outArg = process.argv.find(a => a.startsWith("--out="));
const OUT = outArg ? path.resolve(outArg.slice(6)) : path.join(ROOT, "site");
// --preview: adds a banner to every page saying which business details are placeholders (for sharing design previews)
const PREVIEW = process.argv.includes("--preview");
const LAUNCH = process.argv.includes("--launch");
const STRICT = LAUNCH || process.argv.includes("--strict");
const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, "site.config.json"), "utf8"));

const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const walk = dir => fs.readdirSync(dir, { withFileTypes: true }).flatMap(d => {
  const p = path.join(dir, d.name);
  return d.isDirectory() ? walk(p) : [p];
});
const readPartial = name => {
  const p = path.join(SRC, "partials", name + ".html");
  if (!fs.existsSync(p)) throw new Error(`Unknown partial "${name}"`);
  return fs.readFileSync(p, "utf8");
};
const stars = n => Array.from({ length: n }, () => '<svg><use href="#i-star"/></svg>').join("");

// ---------- generated partials (built from site.config.json) ----------
const generated = {
  "services-menu": () => cfg.services.map(s =>
    `<a class="dd-item" href="{{root}}services/${s.slug}.html"><span class="dd-ico"><svg><use href="#${s.icon}"/></svg></span><span><b>${esc(s.name)}</b><small>${esc(s.short)}</small></span></a>`).join("\n"),
  "services-mlist": () => cfg.services.map(s =>
    `<a href="{{root}}services/${s.slug}.html">${esc(s.name)}</a>`).join("\n"),
  "services-grid": () => `<div class="svc-grid cols-3">` + cfg.services.map(s =>
    `<a class="svc svc-link" href="{{root}}services/${s.slug}.html"><div class="ico"><svg><use href="#${s.icon}"/></svg></div><h3>${esc(s.name)}</h3><p>${esc(s.short)}</p><span class="more">Learn more <span aria-hidden="true">→</span></span></a>`).join("\n") + `</div>`,
  "services-footer": () => cfg.services.map(s => `<li><a href="{{root}}services/${s.slug}.html">${esc(s.name)}</a></li>`).join(""),
  "areas-chips": () => `<div class="chips">` + cfg.areas.map(a =>
    `<a class="chip" href="{{root}}service-areas/${a.slug}.html">${esc(a.short)}</a>`).join("") + `</div>`,
  "areas-footer": () => cfg.areas.slice(0, 8).map(a => `<li><a href="{{root}}service-areas/${a.slug}.html">${esc(a.name)}</a></li>`).join("") +
    `<li><a href="{{root}}service-areas/index.html">All service areas →</a></li>`,
  "areas-grid": () => `<div class="area-grid">` + cfg.areas.map(a =>
    `<a class="area-card" href="{{root}}service-areas/${a.slug}.html"><b>${esc(a.name)}</b><small>${esc(a.county)} County · ${a.zips.slice(0, 3).join(", ")}${a.zips.length > 3 ? "…" : ""}</small><span aria-hidden="true">→</span></a>`).join("\n") + `</div>`,
  "reviews": () => reviewsHtml(cfg.reviews.slice(0, 3)),
  "reviews-all": () => reviewsHtml(cfg.reviews),
  "rating-badge": () => `<div class="score"><b>${esc(cfg.rating)}</b><div><span class="stars" aria-label="Rated ${esc(cfg.rating)} out of 5">${stars(5)}</span><small>${esc(cfg.reviewCount)} Google reviews</small></div></div>`,
  "service-options": () => cfg.services.map(s => `<option>${esc(s.name)}</option>`).join("") + `<option>Not sure — help me figure it out</option>`,
};
function reviewsHtml(list) {
  const anySample = list.some(r => r.sample);
  return `<div class="rev-grid">` + list.map(r => `<article class="rev">
  <span class="stars" aria-label="5 stars">${stars(5)}</span>
  <blockquote>${esc(r.text)}</blockquote>
  <footer><span class="avatar">${esc(r.initial)}</span><div><b>${esc(r.name)}</b><small>${esc(r.place)} · ${esc(r.service)}</small></div>${r.sample ? '<span class="sample-tag">Sample</span>' : ""}</footer>
</article>`).join("\n") + `</div>` + (anySample ? `<p class="sample-note">Sample reviews shown for layout. Real Google reviews replace these before launch.</p>` : "");
}

// ---------- templating ----------
function render(html, ctx, depth = 0) {
  if (depth > 8) throw new Error("Partial nesting too deep");
  html = html.replace(/\{\{>\s*([\w-]+)\s*\}\}/g, (_, name) =>
    render(generated[name] ? generated[name]() : readPartial(name), ctx, depth + 1));
  return html.replace(/\{\{\s*([\w.]+)\s*\}\}/g, (m, key) => {
    const v = key.split(".").reduce((o, k) => (o == null ? undefined : o[k]), ctx);
    return v == null ? m : String(v);
  });
}

function parsePage(file) {
  const raw = fs.readFileSync(file, "utf8");
  const m = raw.match(/^\s*<!--page\s*([\s\S]*?)-->\s*/);
  if (!m) throw new Error(`${path.relative(ROOT, file)}: missing <!--page {...} --> front matter`);
  let fm;
  try { fm = JSON.parse(m[1]); } catch (e) { throw new Error(`${path.relative(ROOT, file)}: front matter is not valid JSON (${e.message})`); }
  return { fm, body: raw.slice(m[0].length) };
}

function crumbsHtml(crumbs, root) {
  if (!crumbs || !crumbs.length) return "";
  const items = [["Home", "index.html"], ...crumbs];
  return `<nav class="crumbs" aria-label="Breadcrumb"><ol>` + items.map(([label, href], i) =>
    i === items.length - 1 || !href ? `<li aria-current="page">${esc(label)}</li>` : `<li><a href="${root}${href}">${esc(label)}</a></li>`).join("") + `</ol></nav>`;
}

function faqSchema(body) {
  const qs = [...body.matchAll(/<summary>([\s\S]*?)<\/summary>\s*<div class="ans">([\s\S]*?)<\/div>/g)];
  if (!qs.length) return null;
  const strip = s => s.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
  return { "@context": "https://schema.org", "@type": "FAQPage", mainEntity: qs.map(([, q, a]) => ({ "@type": "Question", name: strip(q), acceptedAnswer: { "@type": "Answer", text: strip(a) } })) };
}

function businessSchema() {
  return {
    "@context": "https://schema.org", "@type": "HomeAndConstructionBusiness", "@id": cfg.domain + "/#business",
    name: cfg.name, url: cfg.domain + "/", telephone: cfg.phoneTel, email: cfg.email, priceRange: "$$",
    address: { "@type": "PostalAddress", addressLocality: "Pittsburgh", addressRegion: "PA", addressCountry: "US" },
    areaServed: cfg.areas.map(a => ({ "@type": "Place", name: `${a.name.replace(/ \(City\)/, "")}, PA` })),
    openingHours: ["Mo-Fr 07:00-19:00", "Sa 08:00-16:00"],
  };
}

// ---------- build ----------
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });
for (const f of walk(path.join(SRC, "assets"))) {
  const dest = path.join(OUT, "assets", path.relative(path.join(SRC, "assets"), f));
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(f, dest);
}

const pagesDir = path.join(SRC, "pages");
const pageFiles = walk(pagesDir).filter(f => f.endsWith(".html"));
const built = [];
const problems = [];

for (const file of pageFiles) {
  const rel = path.relative(pagesDir, file).split(path.sep).join("/");
  let page;
  try { page = parsePage(file); } catch (e) { problems.push(e.message); continue; }
  const { fm, body } = page;
  const depth = rel.split("/").length - 1;
  // 404.html is served at whatever URL was missing, so its links must be absolute
  const root = rel === "404.html" ? "/" : depth ? "../".repeat(depth) : "";
  const landing = fm.layout === "landing";
  const urlPath = rel === "index.html" ? "/" : "/" + rel.replace(/(^|\/)index\.html$/, "$1");
  const ctx = { ...cfg, root, year: new Date().getFullYear(), page: fm, crumbs: crumbsHtml(fm.crumbs, root), bookHref: landing ? "#book" : root + "book.html" };

  const schemas = [businessSchema()];
  if (fm.crumbs && fm.crumbs.length) schemas.push({
    "@context": "https://schema.org", "@type": "BreadcrumbList",
    itemListElement: [["Home", "index.html"], ...fm.crumbs].map(([name, href], i) => ({ "@type": "ListItem", position: i + 1, name, ...(href ? { item: cfg.domain + "/" + href.replace(/index\.html$/, "") } : {}) })),
  });
  if (fm.faqSchema) { const s = faqSchema(render(body, ctx)); if (s) schemas.push(s); }
  for (const s of [].concat(fm.schema || [])) schemas.push({ "@context": "https://schema.org", ...s });

  const extraCss = (fm.css || []).map(n => `<link rel="stylesheet" href="${root}assets/css/${n}.css">`).join("\n");
  const head = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>${esc(fm.title)}</title>
<meta name="description" content="${esc(fm.description || "")}">
${fm.noindex ? '<meta name="robots" content="noindex">' : `<link rel="canonical" href="${cfg.domain}${urlPath}">`}
<meta name="theme-color" content="#141414">
<meta property="og:type" content="website">
<meta property="og:site_name" content="${esc(cfg.name)}">
<meta property="og:title" content="${esc(fm.ogTitle || fm.title)}">
<meta property="og:description" content="${esc(fm.description || "")}">
<meta property="og:url" content="${cfg.domain}${urlPath}">
<link rel="icon" href="${root}assets/img/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="${root}assets/css/site.css">
${extraCss}
${schemas.map(s => `<script type="application/ld+json">${JSON.stringify(s)}</script>`).join("\n")}
</head>
<body class="${landing ? "is-landing " : ""}${esc(fm.bodyClass || "")}" data-root="${root}">
`;
  const shell = [
    "{{> sprite}}",
    PREVIEW ? `<div style="background:#2A2A2A;color:#F4F1EB;font:14px/1.4 var(--f-body);text-align:center;padding:8px 16px"><b style="color:#FFB81C">Design preview.</b> Phone, license, Google rating and reviews are placeholders, and booking forms don't send anything yet.</div>` : "",
    '<a href="#main" class="skip">Skip to content</a>',
    landing ? "{{> header-landing}}" : "{{> util}}\n{{> header}}",
    `<main id="main">\n${body}\n</main>`,
    landing ? "{{> footer-landing}}" : "{{> footer}}",
    "{{> mbar}}",
    `<script>window.SITE=${JSON.stringify({ bookingEndpoint: cfg.bookingEndpoint, phone: cfg.phone, phoneTel: cfg.phoneTel, zipServed: cfg.zipPrefixesServed, zipMaybe: cfg.zipPrefixesMaybe, zips: Object.fromEntries(cfg.areas.flatMap(a => a.zips.map(z => [z, a.name]))) })};</script>`,
    `<script src="${root}assets/js/site.js" defer></script>`,
  ].join("\n");
  let html = head + render(shell, ctx) + "\n</body>\n</html>\n";
  if (fm.bookService) html = html.replace(/<form data-booking /g, `<form data-booking data-service="${esc(fm.bookService)}" `);
  if (fm.bookService) html = html.replace(/<form class="qb" data-quickbook /g, `<form class="qb" data-quickbook data-service="${esc(fm.bookService)}" `);
  if (fm.nav) html = html.replace(new RegExp(`data-nav="${fm.nav}"`, "g"), `data-nav="${fm.nav}" aria-current="page"`);

  const leftover = [...new Set(html.match(/\{\{[^}]*\}\}/g) || [])];
  if (leftover.length) problems.push(`${rel}: unfilled tokens ${leftover.join(", ")}`);
  if (!fm.title) problems.push(`${rel}: missing "title"`);
  if (!fm.description && !fm.noindex) problems.push(`${rel}: missing "description"`);
  if ((html.match(/<h1[\s>]/g) || []).length !== 1) problems.push(`${rel}: should have exactly one <h1> (found ${(html.match(/<h1[\s>]/g) || []).length})`);

  const dest = path.join(OUT, rel);
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, html);
  built.push({ rel, urlPath, fm, html });
}

// ---------- link check ----------
const exists = new Set(walk(OUT).map(f => path.relative(OUT, f).split(path.sep).join("/")));
exists.add("sitemap.xml"); exists.add("robots.txt");
const missing = new Map();
for (const { rel, html } of built) {
  const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
  for (const [, url] of html.matchAll(/\s(?:href|src)="([^"]+)"/g)) {
    if (/^(https?:|mailto:|tel:|sms:|data:|javascript:)/.test(url)) continue;
    if (url.startsWith("#")) { if (url.length > 1 && !ids.has(url.slice(1)) && !url.startsWith("#i-")) problems.push(`${rel}: anchor ${url} has no matching id`); continue; }
    const target = path.posix.normalize(path.posix.join(path.posix.dirname(rel), url.split("#")[0].split("?")[0]));
    if (!exists.has(target)) { if (!missing.has(target)) missing.set(target, new Set()); missing.get(target).add(rel); }
  }
}
for (const [t, from] of missing) problems.push(`broken link → ${t} (from ${[...from].slice(0, 3).join(", ")}${from.size > 3 ? ` +${from.size - 3} more` : ""})`);

// ---------- sitemap + robots ----------
const indexable = built.filter(b => !b.fm.noindex).sort((a, b) => a.urlPath.localeCompare(b.urlPath));
fs.writeFileSync(path.join(OUT, "sitemap.xml"), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
  indexable.map(b => `  <url><loc>${cfg.domain}${b.urlPath}</loc></url>`).join("\n") + `\n</urlset>\n`);
fs.writeFileSync(path.join(OUT, "robots.txt"), `User-agent: *\nAllow: /\nSitemap: ${cfg.domain}/sitemap.xml\n`);

// ---------- launch checklist: placeholder business details ----------
const placeholders = [];
if (/555-01\d\d/.test(cfg.phone)) placeholders.push(`phone is a placeholder (${cfg.phone})`);
if (/000000/.test(cfg.license)) placeholders.push(`license is a placeholder (${cfg.license})`);
if (cfg.reviews.some(r => r.sample)) placeholders.push(`${cfg.reviews.filter(r => r.sample).length} sample reviews (replace with real Google reviews and remove "sample": true)`);
if (!cfg.bookingEndpoint) placeholders.push("bookingEndpoint is empty, so the booking form doesn't send anywhere");
if (cfg.googleReviewsUrl === "https://www.google.com/maps") placeholders.push("googleReviewsUrl is a placeholder");
if (cfg.ratingVerified !== true) placeholders.push(`rating "${cfg.rating}" / "${cfg.reviewCount}" not confirmed (set "ratingVerified": true once they match your Google profile)`);
const ownerNotes = built.reduce((n, b) => n + (fs.readFileSync(path.join(pagesDir, b.rel), "utf8").match(/<!--\s*OWNER/g) || []).length, 0);

console.log(`Built ${built.length} pages → ${path.relative(process.cwd(), OUT) || "."}/`);
if (problems.length) {
  console.log(`\n${problems.length} problem(s):`);
  for (const p of problems) console.log("  • " + p);
  if (STRICT) process.exit(1);
} else console.log("No problems found.");
if (placeholders.length) {
  console.log(`\nBefore launch (${placeholders.length}):`);
  for (const p of placeholders) console.log("  • " + p);
}
if (ownerNotes) console.log(`  • ${ownerNotes} <!-- OWNER --> notes in src/pages to review (grep -rn "OWNER" src/pages)`);
if (LAUNCH && (placeholders.length || problems.length)) process.exit(1);
