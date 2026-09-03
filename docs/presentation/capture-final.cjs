// FINAL capture: element-screenshot of <main> for each tab (clean, no nav chrome).
const { chromium } = require('@playwright/test');
const path = require('path');
const fs = require('fs');
const OUT = path.join(__dirname, 'img');
fs.mkdirSync(OUT, { recursive: true });

async function shotMain(page, name) {
  const main = page.locator('main').first();
  await main.screenshot({ path: path.join(OUT, name + '.png') });
  console.log(' saved', name + '.png', fs.statSync(path.join(OUT, name + '.png')).size);
}

(async () => {
  const browser = await chromium.launch({ channel: 'msedge' });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 2 });

  // 1. Market — 4 charts
  await page.goto('http://localhost:5173/market', { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(4000);
  await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim() === '4'); b?.click(); });
  await page.waitForTimeout(9000);
  await shotMain(page, 'tab-market');

  // 2. Strategies — saved list
  await page.goto('http://localhost:5173/strategies', { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3500);
  await shotMain(page, 'tab-strategies');

  // 3. Backtests — run a real backtest, capture result
  await page.goto('http://localhost:5173/backtests', { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3000);
  await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(x => /run backtest/i.test(x.textContent)); b?.click(); });
  for (let i = 0; i < 40; i++) {
    await page.waitForTimeout(1500);
    const ok = await page.evaluate(() => /win rate/i.test(document.body.innerText) && !/No backend result loaded/.test(document.body.innerText));
    if (ok) break;
  }
  await page.waitForTimeout(2000);
  await shotMain(page, 'tab-backtests');

  // 4. Leaderboard
  await page.goto('http://localhost:5173/leaderboard', { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(4500);
  await shotMain(page, 'tab-leaderboard');

  // 5. News
  await page.goto('http://localhost:5173/news', { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(4500);
  await shotMain(page, 'tab-news');

  // 6. Operations
  await page.goto('http://localhost:5173/operations', { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3500);
  await shotMain(page, 'tab-operations');

  // 7. Strategies wizard — Combine step, Weighted 60/40
  await page.goto('http://localhost:5173/strategies/new', { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  await page.evaluate(() => {
    for (const w of ['Moving Average', 'RSI']) {
      const row = [...document.querySelectorAll('*')].find(n => n.children.length && n.textContent.trim().startsWith(w));
      row?.click();
    }
  });
  await page.waitForTimeout(600);
  await page.evaluate(() => { [...document.querySelectorAll('button')].find(b => /continue to configure/i.test(b.textContent) && !b.disabled)?.click(); });
  await page.waitForTimeout(1200);
  await page.evaluate(() => { [...document.querySelectorAll('button')].find(b => /continue/i.test(b.textContent) && !b.disabled)?.click(); });
  await page.waitForTimeout(1200);
  await page.locator('button:has-text("Weighted")').first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(1000);
  await page.evaluate(() => {
    const sliders = [...document.querySelectorAll('input[type="range"]')];
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    [60, 40].forEach((v, i) => { const s = sliders[i]; if (!s) return; setter.call(s, v); s.dispatchEvent(new Event('input', { bubbles: true })); s.dispatchEvent(new Event('change', { bubbles: true })); });
  });
  await page.waitForTimeout(1200);
  await shotMain(page, 'tab-combine-weighted');

  await browser.close();
  console.log('ALL DONE');
})();
