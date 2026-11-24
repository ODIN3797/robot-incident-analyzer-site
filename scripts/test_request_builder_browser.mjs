// Optional Chromium smoke for the client-side request builder.
// Needs Playwright: npm install --no-save playwright && npx playwright install chromium
// Run: node scripts/test_request_builder_browser.mjs
import assert from 'node:assert/strict';
import {mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';

const page_url = f => pathToFileURL(resolve(f)).href;
// Screenshots stay outside the repository by default.
const SHOT_DIR = process.env.RIA_SHOTS || resolve('..', 'ria-shots');
mkdirSync(SHOT_DIR, {recursive: true});
const browser = await chromium.launch({headless: true});
const page = await browser.newPage({viewport: {width: 1280, height: 900}});
const errors = [];
page.on('pageerror', e => errors.push(e.message));
const external = [];
page.on('request', r => { if (!r.url().startsWith('file:')) external.push(r.url()); });

try {
  page.setDefaultTimeout(15000);
  await page.goto(page_url('request.html'));

  assert.equal(await page.locator('#pilot-copy').isDisabled(), true, 'copy starts disabled');
  assert.equal(await page.locator('#pilot-github').isDisabled(), true, 'github starts disabled');

  await page.getByText('ROS / robot software engineer', {exact: true}).click();
  await page.getByText('Windows 10/11 — unsigned portable EXE, no Python needed').click();
  await page.getByText('ROS2 MCAP', {exact: true}).click();
  await page.getByText('Navigation incidents — commanded motion versus measured motion').last().click();
  assert.equal(await page.locator('#pilot-copy').isDisabled(), true, 'consent is still required');
  await page.locator('#pilot-consent').check();

  const draft = await page.locator('#pilot-draft').innerText();
  assert.match(draft, /prepared draft, not submitted/);
  assert.match(draft, /Robotics role: ROS \/ robot software engineer/);
  assert.match(draft, /Recording format: ROS2 MCAP/);
  assert.equal(await page.locator('#pilot-copy').isDisabled(), false);
  assert.equal(await page.locator('#pilot-github').isDisabled(), false);
  assert.equal(await page.locator('#pilot-status').getAttribute('data-tone'), 'ready');

  await page.screenshot({path: resolve(SHOT_DIR, 'ria-request-builder.png'), fullPage: true});

  const url = await page.evaluate(() => window.RIA_PILOT.buildPilotUrl({
    role: 'ROS / robot software engineer',
    environment: 'Windows 10/11 (portable EXE, no Python)',
    input: 'ROS2 MCAP',
    goal: 'Review navigation incidents with command vs odometry context'
  }));
  const parsed = new URL(url);
  assert.equal(parsed.host, 'github.com');
  assert.equal(parsed.pathname, '/ODIN3797/robot-incident-analyzer-site/issues/new');
  assert.equal(parsed.searchParams.get('template'), 'pilot_request.yml');
  assert.equal(parsed.searchParams.get('role'), 'ROS / robot software engineer');

  // Copy path: the status must never claim a submission.
  await page.locator('#pilot-copy').click();
  await page.waitForTimeout(400);
  const status = await page.locator('#pilot-status').innerText();
  assert.match(status, /copied|highlighted/i, 'copy or manual-select feedback appears');
  assert.doesNotMatch(status.toLowerCase(), /application submitted|request received/);

  // Unchecking the notice withdraws the draft again.
  await page.locator('#pilot-consent').uncheck();
  assert.equal(await page.locator('#pilot-copy').isDisabled(), true);

  await page.goto(page_url('report-guide.html'));
  await page.screenshot({path: resolve(SHOT_DIR, 'ria-report-guide.png')});
  await page.goto(page_url('index.html'));
  assert.equal(await page.locator('a[href="./request.html"]').count() > 0, true, 'home links the builder');
  assert.equal(await page.locator('a[href="./report-guide.html"]').count() > 0, true, 'home links the guide');

  assert.deepEqual(errors, [], 'no page errors');
  assert.deepEqual(external, [], 'the builder page must not load anything from the network');
  console.log('PASS request builder Chromium smoke: gating, draft, GitHub URL, copy status, no network');
} finally {
  await browser.close();
}
