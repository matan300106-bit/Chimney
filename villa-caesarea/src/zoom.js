// usage: node zoom.js sheet.html out.png x y w h [scale]   (x,y,w,h in mm)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const [html, out, x, y, w, h, sc] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch(); 
  const s = parseFloat(sc || '3');
  const p = await b.newPage({ deviceScaleFactor: s, viewport: { width: 3180, height: 2246 } });
  await p.goto('file://' + html); await p.evaluate(() => document.fonts.ready);
  const k = 96 / 25.4;
  await p.screenshot({ path: out, clip: { x: x * k, y: y * k, width: w * k, height: h * k } });
  await b.close();
})();
