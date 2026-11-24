// Unit tests for the browser-only request builder logic.
// Run: node --test scripts/test_pilot_request.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const RIA = require('./pilot_request.js');

const selection = {
  role: 'ROS / robot software engineer',
  environment: 'Windows 10/11 (portable EXE, no Python)',
  input: 'ROS2 MCAP',
  goal: 'Review navigation incidents with command vs odometry context'
};

test('every option list is a non-empty allow-list', () => {
  for (const field of ['role', 'environment', 'input', 'goal']) {
    assert.ok(Array.isArray(RIA.FIELDS[field]), field + ' must be an array');
    assert.ok(RIA.FIELDS[field].length >= 2, field + ' needs real choices');
  }
});

test('isComplete requires all four answers and the public notice', () => {
  assert.equal(RIA.isComplete(selection, true), true);
  assert.equal(RIA.isComplete(selection, false), false);
  assert.equal(RIA.isComplete({...selection, goal: undefined}, true), false);
  assert.equal(RIA.isComplete({...selection, role: 'CTO'}, true), false);
});

test('URL only ever targets the public issue form', () => {
  const url = RIA.buildPilotUrl(selection);
  assert.ok(url.startsWith('https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new?'), url);
  const params = new URL(url).searchParams;
  assert.equal(params.get('template'), 'pilot_request.yml');
  assert.equal(params.get('role'), selection.role);
  assert.equal(params.get('environment'), selection.environment);
  assert.equal(params.get('input'), selection.input);
  assert.equal(params.has('feedback'), false, 'free text must never be prefilled');
  assert.equal(params.has('body'), false);
});

test('values outside the allow-list are rejected', () => {
  assert.throws(() => RIA.buildPilotUrl({...selection, role: 'someone@example.com'}), /not allowed/);
  assert.throws(() => RIA.buildPilotUrl({...selection, environment: '<script>'}), /not allowed/);
  assert.throws(() => RIA.buildDraft({...selection, input: 'secrets.zip'}), /not allowed/);
  assert.throws(() => RIA.buildPilotUrl({...selection, extra: 'x'}), /not allowed|Unknown/);
});

test('draft text states that nothing was submitted', () => {
  const draft = RIA.buildDraft(selection);
  assert.match(draft, /prepared draft, not submitted/);
  assert.match(draft, /Robotics role: ROS \/ robot software engineer/);
  assert.match(draft, /Preferred pilot environment: Windows 10\/11/);
  assert.match(draft, /Recording format: ROS2 MCAP/);
  assert.match(draft, /Investigation goal: Review navigation/);
  assert.match(draft, /public/);
  assert.doesNotMatch(draft, /application submitted|request received|approved for access/i);
});

test('draft never contains contact or upload fields', () => {
  const draft = RIA.buildDraft(selection);
  for (const needle of ['email', 'phone', 'password', '@', 'attachment']) {
    assert.equal(draft.toLowerCase().includes(needle), false, needle + ' must not appear');
  }
});

test('goal choices stay short privacy-safe sentences', () => {
  for (const goal of RIA.FIELDS.goal) {
    assert.ok(goal.length <= 90, 'goal too long: ' + goal);
    assert.doesNotMatch(goal, /company|customer|client name|http/i);
  }
});

test('the builder declares no network, storage or submission API', () => {
  const source = require('node:fs').readFileSync(new URL('./pilot_request.js', import.meta.url), 'utf8');
  for (const needle of ['fetch(', 'XMLHttpRequest', 'sendBeacon', 'localStorage', 'sessionStorage', 'document.cookie']) {
    assert.equal(source.includes(needle), false, needle + ' must not be used');
  }
  assert.equal((source.match(/https:\/\//g) || []).length, 1, 'one and only one base URL');
});
