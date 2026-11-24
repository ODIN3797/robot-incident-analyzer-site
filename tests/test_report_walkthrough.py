"""Contract tests for the guided report walkthrough.

The walkthrough may only describe what the published sample report actually
contains: real incident/event anchors, the recorded timestamps and observation
text of those rows, and the finding priorities the engine assigned. It is a
reading exercise, so it must not claim validation, storage or submission.
"""
from html.parser import HTMLParser
import hashlib
import html as html_module
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "report-walkthrough.html"
SCRIPT = ROOT / "scripts" / "report_walkthrough.js"
REPORT = ROOT / "demo" / "report.html"
PROVENANCE = ROOT / "demo" / "provenance.json"
GUIDE = ROOT / "report-guide.html"
FIRST = ROOT / "first-15-minutes.html"
START = ROOT / "start.html"
REQUEST = ROOT / "request.html"

# Learning order chosen for the page: easy status comparison, then sequence,
# then signal comparison. It is not the report's severity ranking.
EXERCISES = {
    1: ("I004", "Charging issue after successful docking", "HIGH",
        ["E0009", "E0010"], []),
    2: ("I003", "Navigation failure follows another anomaly", "HIGH",
        ["E0006", "E0007", "E0008"], []),
    3: ("I001", "Commanded velocity diverges from odometry", "MEDIUM",
        ["E0015"], ["E0014"]),
}


class Text(HTMLParser):
    """Collect ids, anchor hrefs and the visible text of a page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.hrefs, self._skip, self._parts = [], [], 0, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    @property
    def text(self):
        return re.sub(r"\s+", " ", html_module.unescape(" ".join(self._parts))).strip()


class EventRows(HTMLParser):
    """Read `<tr id="event-E00xx">` rows out of the generated report."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self._id, self._cells, self._cell = {}, None, None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tr":
            event_id = a.get("id", "")
            if event_id.startswith("event-"):
                self._id, self._cells, self._cell = event_id[6:], [], None
        elif tag == "td" and self._id:
            self._cell = []
            self._cells.append(self._cell)

    def handle_data(self, data):
        if self._id and self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag == "td":
            self._cell = None
        elif tag == "tr" and self._id:
            self.rows[self._id] = [" ".join("".join(c).split()) for c in self._cells]
            self._id, self._cells, self._cell = None, None, None


def read(path):
    return path.read_text(encoding="utf-8")


def finding_cards(report_html):
    """Return {title: (priority, [directly linked event ids])} from the queue."""
    cards = {}
    for match in re.finditer(
            r'<article class="investigation-card[^"]*">\s*<div class="finding-head">'
            r"<h3>(.*?)</h3><span class=\"severity-pill[^\"]*\">(\w+)</span></div>(.*?)</article>",
            report_html, re.S):
        title = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        evidence = re.findall(r'href="#event-(E\d{4})"', match.group(3))
        cards[html_module.unescape(title)] = (match.group(2), evidence)
    return cards


def incident_meta(report_html):
    """Return {incident id: first timestamp string in its meta line}."""
    out = {}
    for match in re.finditer(
            r'<article class="incident-row[^"]*" id="incident-(I\d{3})">(.*?)</article>',
            report_html, re.S):
        meta = re.search(r'<div class="incident-meta">(.*?)</div>', match.group(2), re.S)
        if meta:
            stamp = re.search(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z", meta.group(1))
            if stamp:
                out[match.group(1)] = stamp.group(0)
    return out


class ReportWalkthroughTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = read(PAGE)
        cls.js = read(SCRIPT)
        cls.parsed = Text()
        cls.parsed.feed(cls.html)
        cls.text = cls.parsed.text
        cls.report_html = read(REPORT)
        cls.report_text = Text()
        cls.report_text.feed(cls.report_html)
        cls.rows = EventRows()
        cls.rows.feed(cls.report_html)
        cls.cards = finding_cards(cls.report_html)
        cls.incidents = incident_meta(cls.report_html)
        cls.steps = re.findall(r'data-walk-step="(\d)"', cls.html)
        cls.provenance = json.loads(read(PROVENANCE))

    # --- what the page is allowed to claim -------------------------------

    def test_three_exercises_only(self):
        self.assertEqual(self.steps, ["1", "2", "3"])
        self.assertEqual(self.html.count("data-walk-step="), 3)
        self.assertEqual(self.html.count("data-review-check="), 3)
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_page_is_wellformed_and_ids_are_unique(self):
        self.assertTrue(self.html.lower().startswith("<!doctype html>"))
        self.assertIn('name="viewport"', self.html)
        self.assertEqual(len(set(self.parsed.ids)), len(self.parsed.ids))
        for anchor in ("walk-progress", "walk-status", "walk-prev", "walk-next",
                       "walk-complete", "walk-step-count"):
            self.assertIn(anchor, self.parsed.ids)

    def test_every_link_is_local_and_resolves(self):
        for href in self.parsed.hrefs:
            self.assertFalse(href.startswith(("http:", "https:", "//", "/")),
                             "walkthrough must stay on relative links: %s" % href)
            path, _, fragment = href.partition("#")
            target = (PAGE.parent / path).resolve() if path else PAGE
            self.assertTrue(target.is_file(), "broken link: %s" % href)
            if fragment and target.suffix.lower() == ".html":
                dest = Text()
                dest.feed(read(target))
                self.assertIn(fragment, dest.ids, "broken anchor: %s" % href)

    def test_real_incident_anchors_and_windows(self):
        for number, (incident, _, _, _, _) in EXERCISES.items():
            self.assertIn('id="incident-%s"' % incident, self.report_html,
                          "report lost incident %s" % incident)
            self.assertIn(incident, self.incidents)
            self.assertIn(self.incidents[incident], self.text,
                          "exercise %d must quote the recorded incident timestamp" % number)

    def test_real_event_anchors(self):
        cited = [e for _, _, _, direct, context in EXERCISES.values()
                 for e in direct + context]
        for event_id in cited:
            self.assertIn('id="event-%s"' % event_id, self.report_html)
            self.assertIn("./demo/report.html#event-%s" % event_id, self.parsed.hrefs,
                          "walkthrough must link the real row for %s" % event_id)

    def test_cited_events_match_the_reported_row(self):
        for number, (_, _, _, direct, context) in EXERCISES.items():
            for event_id in direct + context:
                row = self.rows.rows.get(event_id)
                self.assertIsNotNone(row, "missing row %s" % event_id)
                stamp, severity, code, observation = row[1], row[2], row[3], row[4]
                for value, label in ((stamp, "timestamp"), (severity, "severity"),
                                     (code, "code"), (observation, "observation")):
                    self.assertIn(value, self.text,
                                  "exercise %d %s for %s is not what the report says"
                                  % (number, label, event_id))

    def test_finding_titles_and_priorities_match_report(self):
        for _, title, priority, _, _ in EXERCISES.values():
            self.assertIn(title, self.cards, "report lost finding: %s" % title)
            self.assertEqual(self.cards[title][0], priority)
            self.assertIn(title, self.text)
        for title, (priority, _) in self.cards.items():
            if title in self.text:
                self.assertIn(priority, self.text)

    def test_direct_evidence_matches_the_report_links(self):
        for number, (_, title, _, direct, context) in EXERCISES.items():
            priority, evidence = self.cards[title]
            self.assertEqual(sorted(evidence), sorted(direct),
                             "%s no longer links these evidence rows" % title)
            for event_id in context:
                self.assertNotIn(event_id, evidence,
                                 "%s must stay outside %s's direct evidence"
                                 % (event_id, title))
            linked = [href for href in self.parsed.hrefs
                      if href.startswith("./demo/report.html#event-")]
            for event_id in direct:
                self.assertIn("./demo/report.html#event-%s" % event_id, linked)
            self.assertEqual(self.html.count('href="./demo/report.html#incident-%s"'
                                             % EXERCISES[number][0]), 1)

    def test_adjacent_context_is_not_sold_as_cause(self):
        self.assertIn("Adjacent context", self.text)
        self.assertIn("not proof", self.text)
        for claim in ("E0014 caused", "root cause is", "the cause was",
                      "proves the cause", "because of E0014"):
            self.assertNotIn(claim.lower(), self.text.lower())
        # The page's E0014 sentence must carry both a "not proof" and a
        # "context" qualifier rather than reading as the finding's evidence.
        sentence = re.search(r"Adjacent context:.{0,700}?correction\.”(.*?)</p>", self.html, re.S)
        self.assertIsNotNone(sentence)
        qualifier = html_module.unescape(re.sub(r"<[^>]+>", "", sentence.group(1)))
        self.assertIn("not proof", qualifier)
        self.assertIn("does not list it as direct evidence", qualifier)

    def test_fictional_inputs_are_disclosed(self):
        lowered = self.text.lower()
        self.assertIn("wholly fictional inputs", lowered)
        self.assertIn("v0.7.58", self.text)
        self.assertIn("not a test of real-world fault-detection accuracy", lowered)
        self.assertIn("confirmed diagnosis", lowered)
        self.assertEqual(self.provenance["analyzer_version"], "0.7.58")
        self.assertTrue(self.provenance["no_real_robot_data"])

    def test_no_field_accuracy_or_commercial_claims(self):
        lowered = self.text.lower()
        for forbidden in ("high accuracy", "proven accuracy", "accuracy rate",
                          "field precision", "field recall", "precision of",
                          "recall of", "guaranteed", "guarantee", "instant access",
                          "buy", "checkout", "download now", "free forever",
                          "immediately activated"):
            self.assertNotIn(forbidden, lowered)
        self.assertIn("does not establish real-world detection accuracy", lowered)

    def test_no_network_storage_or_collection(self):
        for needle in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket",
                       "EventSource", "localStorage", "sessionStorage",
                       "document.cookie", "indexedDB", "navigator.send"):
            self.assertNotIn(needle, self.html)
            self.assertNotIn(needle, self.js)
        for needle in ("<form", 'type="file"', 'type="email"', 'type="tel"',
                       "<textarea", "<iframe"):
            self.assertNotIn(needle, self.html)
        # The walkthrough reads the report in another tab; it never embeds or
        # fetches it, so a click cannot be turned into a request.
        self.assertNotIn("demo/report.html", self.js)
        self.assertIn('src="./scripts/report_walkthrough.js"', self.html)

    def test_no_false_completion(self):
        self.assertIn("Nothing has been submitted.", self.html)
        self.assertIn("Nothing has been submitted.", self.js)
        for forbidden in ("Validated", "Diagnosis complete", "Evaluation complete",
                          "You passed", "Access granted", "Request approved",
                          "approved for the pilot", "application submitted",
                          "request received"):
            self.assertNotIn(forbidden.lower(), self.text.lower())
        self.assertIn("All three exercises marked reviewed.", self.html)
        self.assertIn("not an assessment result", self.text.lower())

    def test_marking_reviewed_is_self_reported_and_reversible(self):
        self.assertIn("Your checklist reflects your own review", self.html)
        self.assertIn("reviewed.delete(index)", self.js)
        self.assertIn("next.disabled = current === steps.length - 1", self.js)
        self.assertIn('id="walk-prev" disabled', self.html)
        self.assertNotIn("if (!reviewed", self.js)
        self.assertIn("Reloading this page clears the three checkboxes", self.html)

    def test_works_without_javascript(self):
        for step in range(1, 4):
            match = re.search(r'<section[^>]*data-walk-step="%d"[^>]*>' % step, self.html)
            self.assertIsNotNone(match)
            self.assertNotIn("hidden", match.group(0))
        self.assertIn("0 of 3 exercises marked reviewed. Nothing has been submitted.",
                      self.text)
        self.assertIn("Previous exercise", self.html)

    # --- the rest of the public funnel stays intact ----------------------

    def test_immutable_report_and_provenance(self):
        digest = hashlib.sha256(REPORT.read_bytes()).hexdigest()
        self.assertEqual(self.provenance["report_html_sha256"], digest)
        self.assertEqual(self.provenance["candidate_event_count"], 19)
        self.assertEqual(self.provenance["investigation_finding_count"], 17)
        self.assertIsNone(self.provenance["physical_fault_precision"])
        self.assertIsNone(self.provenance["physical_fault_recall"])

    def test_existing_funnel_unchanged(self):
        start = read(START)
        hero = re.search(r'<div class="actions">(.*?)</div>', start, re.S)
        self.assertIsNotNone(hero)
        self.assertEqual(hero.group(1).count("<a class=\"btn"), 2)
        self.assertIn('href="./demo/report.html"', hero.group(1))
        self.assertIn('href="./request.html"', hero.group(1))
        request = read(REQUEST)
        self.assertIn('id="pilot-github-fallback"', request)
        self.assertIn("https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new"
                      "?template=pilot_request.yml", request)
        for page in (read(GUIDE), read(FIRST)):
            self.assertIn("./report-walkthrough.html", page)
            self.assertIn("./demo/report.html", page)
            self.assertIn("./request.html", page)


if __name__ == "__main__":
    unittest.main()
