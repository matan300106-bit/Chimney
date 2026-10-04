// Render sheet HTML pages to PDF and PNG previews with headless Chromium.
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const cfg = JSON.parse(process.argv[2]);
(async () => {
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage();
  const pxw = Math.round(cfg.w / 25.4 * 96), pxh = Math.round(cfg.h / 25.4 * 96);
  await page.setViewportSize({ width: pxw, height: pxh });
  for (const j of cfg.jobs) {
    await page.goto('file://' + j.html, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    if (cfg.pdf) await page.pdf({ path: j.pdf, width: cfg.w + 'mm', height: cfg.h + 'mm', printBackground: true });
    if (cfg.png) await page.screenshot({ path: j.png, fullPage: false });
  }
  await browser.close();
})();
