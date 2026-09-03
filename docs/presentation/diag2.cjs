const { chromium } = require('@playwright/test');
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launch({ channel: 'msedge' });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.goto('http://127.0.0.1:5678/crypto-strategy-lab-slides.html', { waitUntil: 'networkidle0' });
  await sleep(400);
  const dump = await page.evaluate(() => {
    const s = document.querySelector('.slide.active');
    return { html: s.innerHTML.slice(0, 500), cls: s.className, notes: (s.getAttribute('data-notes') || '').slice(0, 60) };
  });
  console.log(JSON.stringify(dump, null, 2));
  await browser.close();
})();
