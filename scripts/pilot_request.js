/* RIA pilot request builder — client-side only.
 *
 * This file never uploads, stores or transmits anything. It formats the
 * visitor's own selection into a draft text and into a GitHub issue-form URL
 * that the visitor chooses to open. The allowed values below mirror
 * .github/ISSUE_TEMPLATE/pilot_request.yml; tests/test_request_wizard.py
 * fails if the two drift apart.
 */
(function (root) {
  'use strict';

  var ISSUE_BASE = 'https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new';
  var TEMPLATE = 'pilot_request.yml';

  var FIELDS = {
    role: [
      'ROS / robot software engineer',
      'AMR / AGV integration engineer',
      'Robotics researcher or student',
      'Other'
    ],
    environment: [
      'Windows 10/11 (portable EXE, no Python)',
      'Linux (Python 3.10+ zipapp)',
      'macOS (Python 3.10+ zipapp)',
      'Windows (Python 3.10+ zipapp)',
      'Browser walkthrough only (no private executable)'
    ],
    input: [
      'ROS2 MCAP',
      'ROS2 DB3',
      'ROS1 BAG',
      'CSV telemetry',
      'Just the synthetic demo first'
    ],
    goal: [
      'Review navigation incidents with command vs odometry context',
      'Investigate localization jumps or position discontinuities',
      'Check power and battery telemetry around an unexpected stop',
      'Review a general robot incident chronology',
      'Understand the workflow on the synthetic sample first'
    ]
  };

  var CLOSING = 'I understand that a GitHub submission is public, that access is reviewed manually, and that I will not post private logs, contact details, or confidential information.';

  function assertAllowed(field, value) {
    if (!Object.prototype.hasOwnProperty.call(FIELDS, field)) {
      throw new Error('Unknown request field: ' + field);
    }
    if (FIELDS[field].indexOf(value) === -1) {
      throw new Error('Value not allowed for ' + field + ': ' + value);
    }
  }

  function assertNoUnknown(selection) {
    if (!selection || typeof selection !== 'object') {
      throw new Error('A selection object is required');
    }
    Object.keys(selection).forEach(function (key) {
      if (!Object.prototype.hasOwnProperty.call(FIELDS, key)) {
        throw new Error('Unknown request field: ' + key);
      }
    });
  }

  function isComplete(selection, consent) {
    if (!selection) return false;
    for (var field in FIELDS) {
      if (!Object.prototype.hasOwnProperty.call(FIELDS, field)) continue;
      if (FIELDS[field].indexOf(selection[field]) === -1) return false;
    }
    return consent === true;
  }

  /* Only the three dropdown answers travel in the URL. The goal sentence is
   * kept in the copied draft because GitHub does not reliably carry textarea
   * prefill across its issue forms. Nothing is submitted from here. */
  function buildPilotUrl(selection) {
    assertNoUnknown(selection);
    assertAllowed('role', selection && selection.role);
    assertAllowed('environment', selection && selection.environment);
    assertAllowed('input', selection && selection.input);
    var params = [
      'template=' + encodeURIComponent(TEMPLATE),
      'role=' + encodeURIComponent(selection.role),
      'environment=' + encodeURIComponent(selection.environment),
      'input=' + encodeURIComponent(selection.input)
    ];
    return ISSUE_BASE + '?' + params.join('&');
  }

  function buildDraft(selection) {
    assertNoUnknown(selection);
    assertAllowed('role', selection && selection.role);
    assertAllowed('environment', selection && selection.environment);
    assertAllowed('input', selection && selection.input);
    assertAllowed('goal', selection && selection.goal);
    return [
      'RIA pilot request — prepared draft, not submitted',
      '',
      'Robotics role: ' + selection.role,
      'Preferred pilot environment: ' + selection.environment,
      'Recording format: ' + selection.input,
      'Investigation goal: ' + selection.goal,
      '',
      'The public sample report uses wholly fictional input data.',
      CLOSING
    ].join('\n');
  }

  var api = {
    ISSUE_BASE: ISSUE_BASE,
    TEMPLATE: TEMPLATE,
    FIELDS: FIELDS,
    CLOSING: CLOSING,
    isComplete: isComplete,
    buildPilotUrl: buildPilotUrl,
    buildDraft: buildDraft
  };
  root.RIA_PILOT = api;
  if (typeof module === 'object' && module.exports) module.exports = api;

  if (typeof document === 'undefined') return;

  function ready(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  }

  ready(function () {
    var builder = document.getElementById('pilot-builder');
    if (!builder) return;
    var draftEl = document.getElementById('pilot-draft');
    var statusEl = document.getElementById('pilot-status');
    var copyBtn = document.getElementById('pilot-copy');
    var githubBtn = document.getElementById('pilot-github');
    var consent = document.getElementById('pilot-consent');
    var fallback = document.getElementById('pilot-github-fallback');

    function selection() {
      var out = {};
      Object.keys(FIELDS).forEach(function (field) {
        var checked = builder.querySelector('input[name="' + field + '"]:checked');
        if (checked) out[field] = checked.value;
      });
      return out;
    }

    function setStatus(text, tone) {
      if (!statusEl) return;
      statusEl.textContent = text;
      statusEl.setAttribute('data-tone', tone || 'neutral');
    }

    function refresh() {
      var chosen = selection();
      var complete = isComplete(chosen, !!(consent && consent.checked));
      if (copyBtn) copyBtn.disabled = !complete;
      if (githubBtn) githubBtn.disabled = !complete;
      if (draftEl) {
        draftEl.textContent = complete
          ? buildDraft(chosen)
          : 'Choose all four options and confirm the public-submission notice to generate your draft.';
      }
      if (complete) setStatus('Draft ready. It stays in this browser until you copy it or open GitHub.', 'ready');
      else setStatus('Nothing has been sent. This page has no server and stores nothing.', 'neutral');
    }

    builder.addEventListener('change', refresh);

    if (copyBtn) copyBtn.addEventListener('click', function () {
      var chosen = selection();
      if (!isComplete(chosen, !!(consent && consent.checked))) return;
      var text = buildDraft(chosen);
      function done() { setStatus('Draft copied. Nothing has been submitted — GitHub submission is still yours to make.', 'ready'); }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, fallbackSelect);
      } else {
        fallbackSelect();
      }
      function fallbackSelect() {
        var range = document.createRange();
        range.selectNodeContents(draftEl);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        setStatus('Select the highlighted draft and copy it with your keyboard. Nothing has been submitted.', 'ready');
      }
    });

    if (githubBtn) githubBtn.addEventListener('click', function () {
      var chosen = selection();
      if (!isComplete(chosen, !!(consent && consent.checked))) return;
      var url = buildPilotUrl(chosen);
      var win = window.open(url, '_blank', 'noopener');
      if (!win && fallback) fallback.focus();
      setStatus('GitHub opened in a new tab. Your request is submitted only when you post the issue there.', 'pending');
    });

    if (fallback) fallback.addEventListener('click', function () {
      setStatus('Opening the empty public form. Paste your copied draft into the matching fields.', 'pending');
    });

    refresh();
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
