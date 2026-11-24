// Guided report walkthrough smoke: real Chromium, session-only checkmarks,
// evidence links that actually open the reported row, and no network at all.
// Usage: npm install --no-save playwright
//        node scripts/test_report_walkthrough_browser.mjs
import assert from 'node:assert/strict';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';

const PAGE = pathToFileURL(resolve(process.env.RIA_WALKTHROUGH_HTML || 'report-walkthrough.html')).href;
const browser = await chromium.launch({headless: true});

const watch = page => {
  const external = [];
  const errors = [];
  page.on('request', request => {
    if (!request.url().startsWith('file:')) external.push(request.url());
  });
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') errors.push('console: ' + message.text());
  });
  return {external, errors};
};

const state = page => page.evaluate(() => {
  const status = document.getElementById('walk-status');
  const progress = document.getElementById('walk-progress');
  const counter = document.getElementById('walk-step-count');
  const complete = document.getElementById('walk-complete');
  const steps = [...document.querySelectorAll('[data-walk-step]')];
  return {
    status: status?.textContent?.trim() ?? '',
    value: Number(progress?.value ?? -1),
    max: Number(progress?.getAttribute('max') ?? -1),
    counter: counter?.textContent?.trim() ?? '',
    completeHidden: complete ? complete.hidden : null,
    completeText: complete?.textContent?.replace(/\s+/g, ' ').trim() ?? '',
    visible: steps.map(section => !section.hidden),
    checked: [...document.querySelectorAll('[data-review-check]')].map(box => box.checked),
    prevDisabled: document.getElementById('walk-prev')?.disabled ?? null,
    nextDisabled: document.getElementById('walk-next')?.disabled ?? null,
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    buttons: [...document.querySelectorAll('.controls button')].map(button => {
      const r = button.getBoundingClientRect();
      return {h: r.height, x: r.x, right: r.right};
    }),
  };
});

try {
  const context = await browser.newContext({
    viewport: {width: 390, height: 844}, deviceScaleFactor: 1, isMobile: true, hasTouch: true,
  });
  const page = await context.newPage();
  const {external, errors} = watch(page);
  await page.goto(PAGE);

  // ---- initial: one exercise shown, nothing marked, Previous inert ----------
  const first = await state(page);
  assert.deepEqual(first.visible, [true, false, false], 'only exercise 1 is shown');
  assert.equal(first.value, 0);
  assert.equal(first.max, 3);
  assert.equal(first.counter, '1');
  assert.ok(first.status.startsWith('0 of 3'), 'status starts at 0 of 3: ' + first.status);
  assert.ok(first.status.includes('Nothing has been submitted.'));
  assert.equal(first.prevDisabled, true, 'Previous is inert on the first exercise');
  assert.equal(first.nextDisabled, false, 'Next is never locked behind a review check');
  assert.equal(first.completeHidden, true);

  // ---- Next works without marking anything reviewed ------------------------
  await page.click('#walk-next');
  const second = await state(page);
  assert.deepEqual(second.visible, [false, true, false]);
  assert.equal(second.counter, '2');
  assert.equal(second.value, 0, 'moving between exercises does not mark anything reviewed');
  assert.equal(second.prevDisabled, false);

  await page.click('#walk-next');
  const third = await state(page);
  assert.deepEqual(third.visible, [false, false, true]);
  assert.equal(third.counter, '3');
  assert.equal(third.nextDisabled, true, 'Next stops at the last exercise');
  assert.equal(third.completeHidden, true, 'no completion notice before any review check');

  // ---- Marking each exercise counts up; 3 of 3 reveals the honest finish ---
  await page.click('#walk-prev');
  await page.click('#walk-prev');
  assert.equal((await state(page)).counter, '1', 'Previous walks back to exercise 1');
  await page.locator('[data-review-check="1"]').check();
  const one = await state(page);
  assert.equal(one.value, 1);
  assert.ok(one.status.startsWith('1 of 3'), one.status);

  await page.click('#walk-next');
  await page.locator('[data-review-check="2"]').check();
  await page.click('#walk-next');
  await page.locator('[data-review-check="3"]').check();
  const all = await state(page);
  assert.equal(all.value, 3);
  assert.ok(all.status.startsWith('3 of 3'), all.status);
  assert.equal(all.completeHidden, false, 'finish block appears at 3 of 3');
  assert.ok(all.completeText.includes('All three exercises marked reviewed.'));
  assert.ok(all.completeText.includes('Nothing has been submitted.'));
  for (const claim of ['Validated', 'Diagnosis complete', 'Evaluation complete', 'Access granted']) {
    assert.ok(!all.completeText.includes(claim), 'finish copy must not claim : ' + claim);
  }

  // ---- Unchecking takes it back: the count is the visitor's own record ----
  await page.click('#walk-prev');
  await page.locator('[data-review-check="2"]').uncheck();
  const undone = await state(page);
  assert.equal(undone.value, 2);
  assert.equal(undone.completeHidden, true, 'finish block hides again when a check is cleared');

  // ---- Reload: nothing persisted anywhere --------------------------------
  await page.reload();
  const reset = await state(page);
  assert.deepEqual(reset.checked, [false, false, false]);
  assert.equal(reset.value, 0);
  assert.deepEqual(reset.visible, [true, false, false]);
  const storage = await page.evaluate(() => ({
    local: window.localStorage.length,
    session: window.sessionStorage.length,
    cookie: document.cookie,
  }));
  assert.deepEqual(storage, {local: 0, session: 0, cookie: ''});

  // ---- The evidence link really opens the reported row -------------------
  const popupPromise = context.waitForEvent('page');
  await page.click('a[href="./demo/report.html#event-E0010"]');
  const popup = await popupPromise;
  const popupWatch = watch(popup);
  await popup.waitForLoadState('load');
  await popup.waitForFunction(() => {
    const row = document.getElementById('event-E0010');
    return !!row && row.getBoundingClientRect().height > 0;
  }, null, {timeout: 15000});
  const opened = await popup.evaluate(() => {
    const row = document.getElementById('event-E0010');
    const fold = row?.closest('details');
    return {
      url: location.hash,
      cells: [...row.querySelectorAll('td')].map(td => td.textContent.trim()),
      foldOpen: fold ? fold.open : null,
      text: row.textContent.replace(/\s+/g, ' ').trim(),
    };
  });
  assert.equal(opened.url, '#event-E0010', 'the popup keeps the evidence anchor');
  assert.equal(opened.foldOpen, true, 'the folded event log opens for the anchored row');
  assert.equal(opened.cells[1], '2026-10-10T10:00:47.000Z');
  assert.ok(opened.text.includes('CHARGING'));
  assert.ok(opened.text.includes('Charging current is 0 A after docking.'));
  await popup.close();

  // ---- Same layout rules at small and desktop widths ---------------------
  for (const [width, height] of [[360, 740], [1280, 900]]) {
    const sized = await browser.newContext({viewport: {width, height}});
    const sizedPage = await sized.newPage();
    const sizedWatch = watch(sizedPage);
    await sizedPage.goto(PAGE);
    const layout = await state(sizedPage);
    assert.equal(layout.scrollWidth, layout.clientWidth,
      'no horizontal scroll at ' + width + 'px');
    assert.ok(layout.buttons.every(b => b.h >= 44),
      'step buttons stay at least 44px tall at ' + width + 'px');
    assert.ok(layout.buttons.every(b => b.x >= 0 && b.right <= width),
      'step buttons stay inside a ' + width + 'px viewport');
    assert.deepEqual(sizedWatch.errors, [], 'no page errors at ' + width + 'px');
    assert.deepEqual(sizedWatch.external, [], 'no external request at ' + width + 'px');
    await sized.close();
  }

  // ---- JavaScript disabled: every exercise stays readable ---------------
  const noJs = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 844}});
  const plain = await noJs.newPage();
  await plain.goto(PAGE);
  const staticPage = await plain.evaluate(() => ({
    steps: [...document.querySelectorAll('[data-walk-step]')].map(s => !s.hidden),
    links: [...document.querySelectorAll('[data-walk-step] a')].map(a => a.getAttribute('href')),
    status: document.getElementById('walk-status')?.textContent?.trim() ?? '',
  }));
  assert.deepEqual(staticPage.steps, [true, true, true],
    'without JavaScript all three exercises are readable');
  assert.ok(staticPage.links.includes('./demo/report.html#event-E0015'));
  assert.ok(staticPage.status.includes('Nothing has been submitted.'));
  await noJs.close();

  assert.deepEqual(external, [], 'the walkthrough makes no external request');
  assert.deepEqual(errors, [], 'no page errors or console errors');
  console.log('PASS guided walkthrough Chromium: session-only 3-step review, honest finish copy, ' +
    'real report anchors open the folded row, no storage, no network');
  console.log(JSON.stringify({
    initial: {status: first.status, visible: first.visible},
    allReviewed: {value: all.value, completeHidden: all.completeHidden},
    afterUncheck: {value: undone.value, completeHidden: undone.completeHidden},
    reportAnchor: {hash: opened.url, foldOpen: opened.foldOpen, timestamp: opened.cells[1]},
    externalRequests: external.length,
  }));
} finally {
  await browser.close();
}
