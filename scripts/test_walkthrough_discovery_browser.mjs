// Guided-walkthrough discovery smoke: the three-exercise walkthrough already
// exists, so this checks only that a real visitor can find and reach it from the
// homepage proof section and the reel landing — at phone and desktop sizes, with
// the hero CTA hierarchy intact, no external request, no sideways scroll and no
// console error. Also verifies the route works with JavaScript disabled.
// Usage: npm install --no-save playwright
//        node scripts/test_walkthrough_discovery_browser.mjs
import assert from 'node:assert/strict';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';

const INDEX = pathToFileURL(resolve(process.env.RIA_INDEX_HTML || 'index.html')).href;
const START = pathToFileURL(resolve(process.env.RIA_START_HTML || 'start.html')).href;
const browser = await chromium.launch({headless: true});

const openAt = async (width, height, {javaScriptEnabled = true} = {}) => {
  const context = await browser.newContext({
    viewport: {width, height}, deviceScaleFactor: 1,
    isMobile: width < 700, hasTouch: width < 700, javaScriptEnabled,
  });
  const page = await context.newPage();
  const external = [];
  const errors = [];
  page.on('request', request => {
    if (!request.url().startsWith('file:')) external.push(request.url());
  });
  page.on('pageerror', error => errors.push(error.message));
  return {context, page, external, errors};
};

const scrollState = page => page.evaluate(() => ({
  scrollWidth: document.documentElement.scrollWidth,
  clientWidth: document.documentElement.clientWidth,
}));

const startMetrics = page => page.evaluate(() => {
  const hero = document.querySelector('.hero');
  const actions = [...hero.querySelectorAll('.actions a')];
  const entry = document.querySelector('aside.guided-entry');
  const link = entry?.querySelector('a');
  const box = element => {
    const r = element.getBoundingClientRect();
    return {x: r.x, y: r.y + window.scrollY, w: r.width, h: r.height, bottom: r.bottom};
  };
  return {
    ctas: actions.map(a => ({
      href: a.getAttribute('href'), label: a.textContent.trim(), ...box(a),
    })),
    entryExists: !!entry,
    entryCount: document.querySelectorAll('aside.guided-entry').length,
    entryInsideHero: !!entry && hero.contains(entry),
    entryHref: link?.getAttribute('href') ?? null,
    entryLabel: link?.textContent.trim() ?? '',
    entryTitle: entry?.querySelector('h2')?.textContent.trim() ?? '',
    entryTitleId: entry?.querySelector('h2')?.id ?? '',
    entryLabelledBy: entry?.getAttribute('aria-labelledby') ?? '',
    entryText: entry?.textContent.replace(/\s+/g, ' ').trim() ?? '',
    entryBox: entry ? box(entry) : null,
    viewportHeight: window.innerHeight,
  };
});

const indexMetrics = page => page.evaluate(() => {
  const proof = document.querySelector('#proof');
  const links = [...proof.querySelectorAll('a')];
  const walk = links.find(a => a.getAttribute('href') === './report-walkthrough.html');
  return {
    hrefs: links.map(a => a.getAttribute('href')),
    walkthroughLabel: walk?.textContent.trim() ?? '',
    walkthroughVisible: !!walk && walk.offsetParent !== null,
    proofText: proof.textContent.replace(/\s+/g, ' ').trim(),
  };
});

const walkthroughState = page => page.evaluate(() => ({
  url: location.pathname.split('/').pop(),
  steps: document.querySelectorAll('[data-walk-step]').length,
  status: document.querySelector('#walk-status')?.textContent.trim() ?? '',
  completeHidden: document.querySelector('#walk-complete')?.hidden ?? null,
  externalScripts: [...document.querySelectorAll('script[src]')]
    .map(s => s.getAttribute('src')),
}));

try {
  for (const [width, height] of [[390, 844], [360, 740], [1280, 900]]) {
    // ---- reel landing: guided entry under the hero, hero CTAs untouched ----
    const landing = await openAt(width, height);
    await landing.page.goto(START);
    const start = await startMetrics(landing.page);
    const landingScroll = await scrollState(landing.page);

    assert.equal(start.entryCount, 1, `${width}px: exactly one guided entry`);
    assert.equal(start.entryExists, true, `${width}px: guided entry is rendered`);
    assert.equal(start.entryInsideHero, false, `${width}px: guided entry sits outside the hero`);
    assert.equal(start.entryHref, './report-walkthrough.html',
      `${width}px: guided entry opens the walkthrough`);
    assert.equal(start.entryLabel, 'Try the guided walkthrough');
    assert.equal(start.entryTitle, 'Not sure where to start?');
    assert.equal(start.entryLabelledBy, start.entryTitleId,
      `${width}px: aria-labelledby points at the visible heading`);
    for (const phrase of ['fictional recordings', 'No diagnosis', 'No submission']) {
      assert.ok(start.entryText.includes(phrase),
        `${width}px: guided entry keeps the "${phrase}" boundary`);
    }
    assert.deepEqual(start.ctas.map(c => c.href), ['./demo/report.html', './request.html'],
      `${width}px: hero keeps exactly two CTAs in order`);
    if (width === 390) {
      assert.ok(start.ctas[1].bottom <= 844,
        `second hero CTA stays above the fold (bottom ${start.ctas[1].bottom})`);
    }
    assert.equal(landingScroll.scrollWidth, landingScroll.clientWidth,
      `${width}px: reel landing has no sideways scroll`);
    assert.deepEqual(landing.external, [], `${width}px: reel landing makes no external request`);
    assert.deepEqual(landing.errors, [], `${width}px: reel landing has no JS error`);

    // ---- homepage: the proof section links straight to the walkthrough ----
    const home = await openAt(width, height);
    await home.page.goto(INDEX);
    const index = await indexMetrics(home.page);
    const homeScroll = await scrollState(home.page);

    assert.ok(index.hrefs.includes('./report-walkthrough.html'),
      `${width}px: #proof links to the walkthrough`);
    assert.equal(index.hrefs[0], './demo/report.html',
      `${width}px: the real report stays the first action in #proof`);
    assert.equal(index.walkthroughLabel, 'Follow 3 guided evidence exercises');
    assert.ok(index.walkthroughVisible, `${width}px: the walkthrough link is visible`);
    assert.ok(index.proofText.includes('Synthetic scenario only'),
      `${width}px: #proof keeps the limitation note`);
    assert.equal(homeScroll.scrollWidth, homeScroll.clientWidth,
      `${width}px: homepage has no sideways scroll`);
    assert.deepEqual(home.external, [], `${width}px: homepage makes no external request`);
    assert.deepEqual(home.errors, [], `${width}px: homepage has no JS error`);

    await home.context.close();
    await landing.context.close();
  }

  // ---- keyboard: Tab to the guided link, Enter to travel, real exercises land ----
  const keyboard = await openAt(1280, 900);
  await keyboard.page.goto(START);
  let reached = false;
  for (let i = 0; i < 12 && !reached; i += 1) {
    await keyboard.page.keyboard.press('Tab');
    reached = await keyboard.page.evaluate(() =>
      document.activeElement?.getAttribute?.('href') === './report-walkthrough.html');
  }
  assert.ok(reached, 'the guided link is reachable with Tab');
  await Promise.all([keyboard.page.waitForNavigation(), keyboard.page.keyboard.press('Enter')]);
  const arrival = await walkthroughState(keyboard.page);
  assert.equal(arrival.url, 'report-walkthrough.html');
  assert.equal(arrival.steps, 3, 'the landing link opens the real three-exercise page');
  assert.match(arrival.status, /nothing has been submitted/i);
  assert.equal(arrival.completeHidden, true, 'the completion panel stays hidden on arrival');
  assert.deepEqual(arrival.externalScripts, ['./scripts/report_walkthrough.js'],
    'only the first-party walkthrough script loads');
  assert.deepEqual(keyboard.external, [], 'the walkthrough makes no external request');
  assert.deepEqual(keyboard.errors, [], 'the walkthrough has no JS error');
  await keyboard.context.close();

  // ---- JavaScript disabled: the route is plain HTML and still works ----
  const noJs = await openAt(390, 844, {javaScriptEnabled: false});
  await noJs.page.goto(START);
  const plainStart = await startMetrics(noJs.page);
  assert.equal(plainStart.entryHref, './report-walkthrough.html',
    'guided link works without JavaScript');
  await Promise.all([
    noJs.page.waitForNavigation(),
    noJs.page.locator('aside.guided-entry a').click(),
  ]);
  const plainArrival = await noJs.page.evaluate(() => ({
    url: location.pathname.split('/').pop(),
    steps: document.querySelectorAll('[data-walk-step]').length,
  }));
  assert.equal(plainArrival.url, 'report-walkthrough.html');
  assert.equal(plainArrival.steps, 3, 'all three exercises stay readable without JavaScript');
  assert.deepEqual(noJs.external, [], 'no external request without JavaScript');
  await noJs.context.close();

  console.log('PASS walkthrough discovery: #proof + reel landing reach the real 3 exercises at 390/360/1280, hero CTAs intact, keyboard and no-JS routes work, 0 external requests, 0 JS errors');
} finally {
  await browser.close();
}
