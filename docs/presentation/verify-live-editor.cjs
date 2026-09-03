// End-to-end verification of the Live Slide Editor on the deck.
const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const DIR = __dirname;
const DECK = path.join(DIR, 'crypto-strategy-lab-slides.html');
const URL = 'http://127.0.0.1:5678/crypto-strategy-lab-slides.html';
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ channel: 'msedge' });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const errs = [];
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  const results = {};

  await page.goto(URL, { waitUntil: 'networkidle0' });
  await sleep(500);

  // 1) Editor UI present, not visible before edit mode
  results.ui_present = await page.evaluate(() =>
    !!document.querySelector('.le-toolbar') && !!document.querySelector('.le-anno') &&
    !!document.querySelector('.le-notes') && !!document.querySelector('.le-hint'));
  results.toolbar_hidden_initially = await page.evaluate(() =>
    getComputedStyle(document.querySelector('.le-toolbar')).display === 'none');

  // 2) Press E -> edit mode
  await page.keyboard.press('e');
  await sleep(300);
  results.editing = await page.evaluate(() => document.body.classList.contains('editing'));
  results.contenteditable = await page.evaluate(() =>
    document.querySelector('.slide').getAttribute('contenteditable') === 'true');
  results.toolbar_visible = await page.evaluate(() =>
    getComputedStyle(document.querySelector('.le-toolbar')).display !== 'none');

  // 3) Edit slide text (title slide h1)
  await page.evaluate(() => {
    const h1 = document.querySelector('.slide.active .slide-title h1');
    h1.textContent = 'Crypto Strategy Lab [EDITED]';
  });

  // 4) Edit speaker notes via notes panel
  await page.click('[data-le="notes"]');
  await sleep(200);
  await page.evaluate(() => {
    const ta = document.querySelector('[data-le="notes"]');
    ta.value = 'NOTE EDITED BY VERIFIER.';
    ta.dispatchEvent(new Event('input', { bubbles: true }));
  });
  results.notes_synced = await page.evaluate(() =>
    document.querySelector('.slide.active').getAttribute('data-notes') === 'NOTE EDITED BY VERIFIER.');

  // 5) Arrow keys must NOT navigate while typing in the notes textarea
  await page.focus('[data-le="notes"]');
  await page.keyboard.press('ArrowRight');
  await sleep(200);
  results.arrow_suppressed_in_notes = await page.evaluate(() =>
    document.querySelector('.slide.active').classList.contains('active') &&
    document.getElementById('counter').textContent.trim() === '1 / 26');

  // 6) Save -> POST /api/save writes the deck file
  const before = fs.statSync(DECK).size;
  await page.click('[data-le="save"]');
  await sleep(1200);
  results.save_status = await page.evaluate(() => document.querySelector('[data-le="status"]').textContent);
  const after = fs.readFileSync(DECK, 'latin1');
  results.file_changed = after.length !== before;
  results.text_persisted = after.includes('Crypto Strategy Lab [EDITED]');
  results.notes_persisted = after.includes('NOTE EDITED BY VERIFIER.');
  results.no_crlf_corruption = !after.includes('\r\r\n');
  results.editor_survives = after.includes('__makeSlideEditor');

  // 7) Reload -> edits persisted, no duplicate editor UI, edit mode off
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await sleep(500);
  results.reload_text = await page.evaluate(() =>
    document.querySelector('.slide .slide-title h1').textContent.includes('[EDITED]'));
  results.reload_notes = await page.evaluate(() =>
    document.querySelector('.slide').getAttribute('data-notes') === 'NOTE EDITED BY VERIFIER.');
  results.no_duplicate_ui = await page.evaluate(() =>
    document.querySelectorAll('.le-toolbar').length === 1 &&
    document.querySelectorAll('.le-anno').length === 1);
  results.edit_off_after_reload = await page.evaluate(() => !document.body.classList.contains('editing'));

  // 8) Annotate flow: E -> Annotate -> pin element -> instruction -> Add -> Apply
  await page.keyboard.press('e');
  await sleep(200);
  await page.click('[data-le="annotate"]');
  await sleep(200);
  results.annotating = await page.evaluate(() => document.body.classList.contains('le-annotating'));
  results.ce_off_in_annotate = await page.evaluate(() =>
    document.querySelector('.slide').getAttribute('contenteditable') === 'false');
  await page.click('.slide.active .slide-title .subtitle');
  await sleep(200);
  results.pinned = await page.evaluate(() => !!document.querySelector('[data-le-pin]'));
  await page.evaluate(() => {
    document.querySelector('[data-le="an-text"]').value = 'make this subtitle gold and italic';
  });
  await page.click('[data-le="an-add"]');
  await sleep(200);
  results.pending_count = await page.evaluate(() =>
    document.querySelector('[data-le="an-count"]').textContent);
  await page.click('[data-le="an-apply"]');
  await sleep(900);
  results.anno_status = await page.evaluate(() => document.querySelector('[data-le="status"]').textContent);
  results.marker_stamped = await page.evaluate(() =>
    document.querySelector('.slide.active .slide-title .subtitle').getAttribute('data-le-annot') === 'make this subtitle gold and italic');

  // 9) annotations.jsonl sidecar on disk
  const jsonlPath = path.join(DIR, 'annotations.jsonl');
  results.jsonl_exists = fs.existsSync(jsonlPath);
  if (results.jsonl_exists) {
    const jsonl = fs.readFileSync(jsonlPath, 'utf-8');
    results.jsonl_record = jsonl.includes('"instruction": "make this subtitle gold and italic"') && jsonl.includes('"slide": 1');
  }

  // 10) GET /api/annotations returns the record
  const resp = await page.evaluate(async () => (await fetch('/api/annotations')).json());
  results.api_annotations = Array.isArray(resp.annotations) && resp.annotations.length > 0;

  // 11) Print CSS hides editor UI
  results.print_css_hides_editor = await page.evaluate(() => {
    const css = [...document.styleSheets].flatMap(s => { try { return [...s.cssRules]; } catch { return []; } });
    return css.some(r => r.media && /print/.test(r.media.mediaText) && /\.le-toolbar/.test(r.cssText));
  });

  results.page_errors = errs;
  console.log(JSON.stringify(results, null, 2));

  const fails = Object.entries(results).filter(([k, v]) => v === false || (k === 'page_errors' && v.length));
  await browser.close();
  if (fails.length) { console.log('FAILURES:', fails.map(f => f[0]).join(', ')); process.exit(1); }
  console.log('ALL CHECKS PASSED');
})().catch(e => { console.error('FATAL', e); process.exit(2); });
