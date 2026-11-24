// Mobile-reel landing smoke: a visitor arriving from a short video must see the
// product's job and exactly two actions without scrolling, on real Chromium at
// phone sizes, with no external request and no sideways scroll.
// Usage: npm install --no-save playwright
//        node scripts/test_start_mobile_browser.mjs
import assert from 'node:assert/strict';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';

const START = pathToFileURL(resolve(process.env.RIA_START_HTML || 'start.html')).href;
const browser = await chromium.launch({headless: true});

const openAt = async (width, height) => {
  const context = await browser.newContext({
    viewport: {width, height}, deviceScaleFactor: 1, isMobile: true, hasTouch: true,
  });
  const page = await context.newPage();
  const external = [];
  const errors = [];
  page.on('request', request => {
    if (!request.url().startsWith('file:')) external.push(request.url());
  });
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(START);
  return {context, page, external, errors};
};

const measure = page => page.evaluate(() => {
  const hero = document.querySelector('.hero');
  const actions = [...hero.querySelectorAll('.actions a')];
  const box = element => {
    const r = element.getBoundingClientRect();
    return {x: r.x, y: r.y + window.scrollY, w: r.width, h: r.height};
  };
  const hint = hero.querySelector('.hint a');
  return {
    heroTitle: hero.querySelector('h1')?.textContent?.trim() ?? '',
    ctas: actions.map(a => ({href: a.getAttribute('href'), label: a.textContent.trim(), ...box(a)})),
    heroActionsLinks: actions.length,
    heroAllLinks: hero.querySelectorAll('a').length,
    hintInActions: !!hint && !!hero.querySelector('.actions')?.contains(hint),
    hintHref: hint?.getAttribute('href') ?? null,
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    pageHeight: document.documentElement.scrollHeight,
    viewportHeight: window.innerHeight,
  };
});

try {
  // ---- 390x844 (iPhone-class): both CTAs must sit above the fold ----
  const phone = await openAt(390, 844);
  const metrics = await measure(phone.page);

  assert.equal(metrics.heroActionsLinks, 2, 'hero keeps exactly two primary actions');
  assert.equal(metrics.ctas[0].href, './demo/report.html', 'primary CTA opens the sample report');
  assert.equal(metrics.ctas[1].href, './request.html', 'secondary CTA opens the request builder');
  assert.equal(metrics.hintInActions, false, 'the guide link stays a text link, not a third button');
  assert.equal(metrics.hintHref, './report-guide.html');
  assert.ok(/follow the logs/i.test(metrics.heroTitle), 'the heading states the product job');

  const primary = metrics.ctas[0];
  const secondary = metrics.ctas[1];
  assert.ok(primary.y < secondary.y, 'the sample report is offered first');
  assert.ok(primary.h >= 48 && secondary.h >= 48, 'both tap targets are at least 48px tall');
  assert.ok(secondary.y - (primary.y + primary.h) >= 10,
    'the CTAs are separated by at least 10px');
  assert.ok(secondary.y + secondary.h <= 844,
    'both CTAs fit in the first mobile view at 390x844 (secondary ends at ' +
    Math.round(secondary.y + secondary.h) + ')');
  assert.equal(metrics.scrollWidth, metrics.clientWidth, 'no horizontal scroll at 390px');
  assert.deepEqual(phone.errors, [], 'no page errors');

  // ---- 360x740 (small Android): no sideways scroll, nothing clipped ----
  const small = await openAt(360, 740);
  const smallMetrics = await measure(small.page);
  assert.equal(smallMetrics.scrollWidth, smallMetrics.clientWidth,
    'no horizontal scroll at 360px');
  assert.ok(smallMetrics.ctas.every(c => c.x >= 0 && c.x + c.w <= 360),
    'both CTAs sit inside a 360px viewport');
  assert.ok(smallMetrics.ctas[1].y + smallMetrics.ctas[1].h <= 740,
    'at 360x740 the second CTA still ends inside the first view (' +
    Math.round(smallMetrics.ctas[1].y + smallMetrics.ctas[1].h) + ')');

  // ---- Desktop sanity: the same two actions, still no third button ----
  const wide = await openAt(1280, 900);
  const wideMetrics = await measure(wide.page);
  assert.equal(wideMetrics.heroActionsLinks, 2);

  // ---- No page may load anything from the network ----
  assert.deepEqual(phone.external, [], 'the landing makes no external request');
  assert.deepEqual(small.external, [], 'the small-screen landing makes no external request');
  assert.deepEqual(wide.external, [], 'the desktop landing makes no external request');

  console.log('PASS mobile reel landing: 2 CTAs above the fold at 390x844 and 360x740, ' +
    'no sideways scroll, no external request');
  console.log(JSON.stringify({
    phone390: {title: metrics.heroTitle,
      ctas: metrics.ctas.map(c => ({href: c.href, y: Math.round(c.y), h: Math.round(c.h)})),
      secondCtaBottom: Math.round(secondary.y + secondary.h)},
    small360: {secondCtaBottom: Math.round(smallMetrics.ctas[1].y + smallMetrics.ctas[1].h)},
    externalRequests: phone.external.length + small.external.length + wide.external.length,
  }));
} finally {
  await browser.close();
}
