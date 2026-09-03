const { chromium } = require('@playwright/test');
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launch({ channel: 'msedge' });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  page.on('pageerror', e => console.log('PAGEERROR', e.message));
  await page.goto('http://127.0.0.1:5678/crypto-strategy-lab-slides.html', { waitUntil: 'networkidle0' });
  await sleep(400);
  await page.keyboard.press('e'); await sleep(200);
  await page.click('[data-le="annotate"]'); await sleep(300);
  const info = await page.evaluate(() => {
    const el = document.querySelector('.slide.active .slide-title .subtitle');
    if (!el) return { found: false, activeSlides: document.querySelectorAll('.slide.active').length, bodyClass: document.body.className };
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    const topEl = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
    return { found: true, rect: [r.x, r.y, r.width, r.height], opacity: cs.opacity, visibility: cs.visibility, display: cs.display, topAtCenter: topEl ? topEl.tagName + '.' + topEl.className : null };
  });
  console.log(JSON.stringify(info, null, 2));
  await browser.close();
})();
