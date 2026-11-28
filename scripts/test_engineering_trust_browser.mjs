// Engineering trust & limits smoke: the two new sections restate facts that
// already live in privacy.html / pilot-terms.html / provenance, so this checks
// only presentation and access — both pages at phone and desktop sizes, the
// limits readable before the request, the reel-landing hero CTAs still two and
// above the fold, keyboard reach, JavaScript-disabled rendering, no external
// request, no sideways scroll, no console error.
// Usage: npm install --no-save playwright
//        node scripts/test_engineering_trust_browser.mjs
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
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text());
  });
  return {context, page, external, errors};
};

const scrollState = page => page.evaluate(() => ({
  scrollWidth: document.documentElement.scrollWidth,
  clientWidth: document.documentElement.clientWidth,
}));

const trustMetrics = page => page.evaluate(() => {
  const trust = document.querySelector('section#trust');
  const cards = [...trust.querySelectorAll('.trust-card, article')];
  const grid = trust.querySelector('.trust-grid');
  const cardsPerRow = (() => {
    if (!grid || !cards.length) return cards.length;
    const firstTop = cards[0].getBoundingClientRect().top;
    return cards.filter(card => Math.abs(card.getBoundingClientRect().top - firstTop) < 2).length;
  })();
  const heading = trust.querySelector('h2');
  const labelledBy = trust.getAttribute('aria-labelledby');
  const links = [...trust.querySelectorAll('a')].map(a => ({
    href: a.getAttribute('href'),
    label: a.textContent.trim(),
    visible: a.offsetParent !== null,
  }));
  const hero = document.querySelector('section.hero');
  const heroActions = hero ? [...hero.querySelectorAll('.actions a')] : [];
  return {
    count: document.querySelectorAll('section#trust').length,
    text: trust.textContent.replace(/\s+/g, ' ').trim(),
    headingTag: heading?.tagName ?? '',
    headingText: heading?.textContent.trim() ?? '',
    labelledByMatches: !!heading && labelledBy === heading.id,
    cardCount: cards.length,
    cardsPerRow,
    links,
    buttons: trust.querySelectorAll('button').length,
    inputs: trust.querySelectorAll('input').length,
    scripts: trust.querySelectorAll('script').length,
    insideHero: !!hero && hero.contains(trust),
    heroHrefs: heroActions.map(a => a.getAttribute('href')),
    heroSecondBottom: heroActions[1] ? heroActions[1].getBoundingClientRect().bottom : null,
    viewportHeight: window.innerHeight,
    trustTop: trust.getBoundingClientRect().top + window.scrollY,
    requestTop: (document.querySelector('#request') || document.querySelector('#pilot'))
      ?.getBoundingClientRect().top + window.scrollY ?? null,
  };
});

try {
  for (const [width, height] of [[390, 844], [360, 740], [1280, 900]]) {
    // ---- homepage ----
    const home = await openAt(width, height);
    await home.page.goto(INDEX);
    const index = await trustMetrics(home.page);
    const homeScroll = await scrollState(home.page);

    assert.equal(index.count, 1, `${width}px: exactly one #trust on the homepage`);
    assert.equal(index.headingTag, 'H2', `${width}px: the trust heading is an h2`);
    assert.equal(index.headingText, 'Know what RIA can — and cannot — tell you.');
    assert.ok(index.labelledByMatches, `${width}px: aria-labelledby points at the heading`);
    assert.equal(index.cardCount, 4, `${width}px: four trust cards`);
    assert.equal(index.cardsPerRow, width < 700 ? 1 : 2,
      `${width}px: trust cards use ${width < 700 ? 1 : 2} column(s)`);
    for (const phrase of ['What RIA provides', 'What RIA cannot verify',
      'Where your data goes', 'How evaluation access works',
      'does not prove that a robot operated normally',
      'log-upload endpoint', 'GitHub', 'Coming Soon']) {
      assert.ok(index.text.includes(phrase), `${width}px: #trust keeps "${phrase}"`);
    }
    assert.equal(index.buttons, 0, `${width}px: #trust adds no button`);
    assert.equal(index.inputs, 0, `${width}px: #trust adds no input`);
    assert.equal(index.scripts, 0, `${width}px: #trust adds no script`);
    for (const link of index.links) {
      assert.ok(link.visible, `${width}px: trust link "${link.label}" is visible`);
    }
    assert.ok(index.links.some(link => link.href === './privacy.html'),
      `${width}px: privacy link present`);
    assert.ok(index.requestTop === null || index.trustTop < index.requestTop,
      `${width}px: limits come before the pilot request`);
    assert.equal(homeScroll.scrollWidth, homeScroll.clientWidth,
      `${width}px: homepage has no sideways scroll`);
    assert.deepEqual(home.external, [], `${width}px: homepage makes no external request`);
    assert.deepEqual(home.errors, [], `${width}px: homepage has no console/JS error`);

    // ---- reel landing ----
    const landing = await openAt(width, height);
    await landing.page.goto(START);
    const start = await trustMetrics(landing.page);
    const landingScroll = await scrollState(landing.page);

    assert.equal(start.count, 1, `${width}px: exactly one #trust on the reel landing`);
    assert.equal(start.headingText, 'Before you try RIA');
    assert.ok(start.labelledByMatches, `${width}px: landing aria-labelledby resolves`);
    assert.equal(start.cardCount, 3, `${width}px: three compact trust cards`);
    for (const phrase of ['Evidence, not a diagnosis',
      'Local analysis, with clear boundaries', 'Manual evaluation access',
      'does not prove normal operation', 'no robot-log upload endpoint']) {
      assert.ok(start.text.includes(phrase), `${width}px: landing #trust keeps "${phrase}"`);
    }
    assert.deepEqual(start.heroHrefs, ['./demo/report.html', './request.html'],
      `${width}px: hero keeps exactly two CTAs in order`);
    assert.equal(start.insideHero, false, `${width}px: #trust sits outside the hero`);
    if (width < 700) {
      assert.ok(start.heroSecondBottom <= height,
        `${width}px: second hero CTA stays above the fold (bottom ${start.heroSecondBottom})`);
    }
    assert.ok(start.requestTop !== null && start.trustTop < start.requestTop,
      `${width}px: landing shows limits before the request steps`);
    assert.equal(landingScroll.scrollWidth, landingScroll.clientWidth,
      `${width}px: reel landing has no sideways scroll`);
    assert.deepEqual(landing.external, [], `${width}px: reel landing makes no external request`);
    assert.deepEqual(landing.errors, [], `${width}px: reel landing has no console/JS error`);

    await home.context.close();
    await landing.context.close();
  }

  // ---- keyboard: Tab reaches the privacy link inside #trust, Enter opens it ----
  const keyboard = await openAt(1280, 900);
  await keyboard.page.goto(START);
  const tabbed = await keyboard.page.evaluate(async () => {
    const trust = document.querySelector('section#trust');
    const link = trust.querySelector('a[href="./privacy.html"]');
    link.focus();
    return {
      focusedHref: document.activeElement?.getAttribute?.('href') ?? null,
      outline: getComputedStyle(link).outlineStyle,
    };
  });
  assert.equal(tabbed.focusedHref, './privacy.html', 'trust link accepts keyboard focus');
  await Promise.all([keyboard.page.waitForNavigation(), keyboard.page.keyboard.press('Enter')]);
  const arrival = await keyboard.page.evaluate(() => ({
    url: location.pathname.split('/').pop(),
    title: document.title,
  }));
  assert.equal(arrival.url, 'privacy.html', 'Enter on the trust link opens the notice');
  assert.deepEqual(keyboard.external, [], 'the trust link route makes no external request');
  await keyboard.context.close();

  // ---- JavaScript disabled: the limits stay readable, hero CTAs intact ----
  const noJs = await openAt(390, 844, {javaScriptEnabled: false});
  await noJs.page.goto(START);
  const plain = await trustMetrics(noJs.page);
  assert.equal(plain.cardCount, 3, 'trust cards render without JavaScript');
  assert.ok(plain.text.includes('Manual evaluation access'),
    'limits stay readable without JavaScript');
  assert.deepEqual(plain.heroHrefs, ['./demo/report.html', './request.html'],
    'hero CTAs survive without JavaScript');
  assert.deepEqual(noJs.external, [], 'no external request without JavaScript');
  await noJs.context.close();

  console.log('PASS engineering trust: #trust on home (4 cards) and reel landing (3 cards) at 390/360/1280, limits before the request, hero CTAs intact and above the fold, keyboard route to privacy, no-JS readable, 0 external requests, 0 console errors');
} finally {
  await browser.close();
}
