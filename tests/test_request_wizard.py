"""Contract tests for the client-side pilot request builder and its pages.

The builder must stay a local draft tool: fixed options only, no free text, no
upload, no network, no storage, and no claim that a request was submitted.
"""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "request.html"
SCRIPT = ROOT / "scripts" / "pilot_request.js"
GUIDE = ROOT / "report-guide.html"
FIRST = ROOT / "first-15-minutes.html"
TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "pilot_request.yml"


class RequestParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.inputs, self.tags = [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append(tag)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a":
            self.links.append(a.get("href", ""))
        if tag == "input":
            self.inputs.append(a)


def template_options():
    """Return {field: [allowed values]} from the public GitHub issue form."""
    text = TEMPLATE.read_text(encoding="utf-8")
    out, field, in_options = {}, None, False
    for line in text.splitlines():
        m = re.match(r"\s+id: (\w+)\s*$", line)
        if m and not line.strip().startswith("- "):
            field = m.group(1)
            out.setdefault(field, [])
            in_options = False
            continue
        if field and line.strip() == "options:":
            in_options = True
            continue
        if in_options:
            m = re.match(r"\s+- (.+?)\s*$", line)
            if m:
                out[field].append(m.group(1).strip())
            elif line.strip() and not line.strip().startswith("-"):
                in_options = False
    return {k: v for k, v in out.items() if v}


class RequestWizardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = REQUEST.read_text(encoding="utf-8")
        cls.js = SCRIPT.read_text(encoding="utf-8")
        cls.parsed = RequestParser()
        cls.parsed.feed(cls.html)

    def test_page_exists_and_is_wellformed(self):
        self.assertTrue(self.html.lower().startswith("<!doctype html>"))
        self.assertIn('name="viewport"', self.html)
        self.assertEqual(len(set(self.parsed.ids)), len(self.parsed.ids), "duplicate ids")

    def test_allowed_fields_only(self):
        for field in ("role", "environment", "input", "goal"):
            self.assertIn('name="%s"' % field, self.html)
        names = {a.get("name") for a in self.parsed.inputs if a.get("type") == "radio"}
        self.assertEqual(names, {"role", "environment", "input", "goal"})

    def test_options_match_public_issue_template(self):
        expected = template_options()
        for field in ("role", "environment", "input"):
            self.assertIn(field, expected, "issue template lost %s" % field)
            for option in expected[field]:
                self.assertIn(option.replace('"', "&quot;"), self.html,
                              "request page is missing template option: %s" % option)
                self.assertIn(option, self.js,
                              "builder allow-list is missing template option: %s" % option)

    def test_no_sensitive_inputs(self):
        self.assertNotIn('type="file"', self.html)
        self.assertNotIn('type="email"', self.html)
        self.assertNotIn('type="tel"', self.html)
        self.assertNotIn("<textarea", self.html)
        self.assertNotIn("<form", self.html)
        for word in ("password", "phone number", "your email"):
            self.assertNotIn(word, self.html.lower())

    def test_no_network_collection(self):
        for needle in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource"):
            self.assertNotIn(needle, self.html)
            self.assertNotIn(needle, self.js)

    def test_no_persistent_storage(self):
        for needle in ("localStorage", "sessionStorage", "document.cookie", "indexedDB"):
            self.assertNotIn(needle, self.html)
            self.assertNotIn(needle, self.js)

    def test_github_target_only(self):
        urls = re.findall(r"https?://[^\s\"'<]+", self.html)
        for url in urls:
            self.assertTrue(
                url.startswith("https://github.com/ODIN3797/robot-incident-analyzer-site/")
                or "odin3797.github.io/robot-incident-analyzer-site" in url,
                "unexpected external URL in request page: %s" % url)
        self.assertEqual(self.js.count("https://"), 1, "builder must hold one and only one base URL")
        self.assertIn(
            "https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new",
            self.js)
        self.assertIn("pilot_request.yml", self.js)
        self.assertNotIn("releases", self.js)

    def test_plain_github_link_survives_without_javascript(self):
        self.assertIn(
            "https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new?template=pilot_request.yml",
            self.parsed.links,
            "a JavaScript-free path to the public form must always be present")
        self.assertIn('id="pilot-github-fallback"', self.html)

    def test_no_false_submission(self):
        lowered = self.html.lower()
        for forbidden in ("application submitted", "request received", "thanks, we received",
                          "your request has been submitted", "you're in", "you are approved",
                          "access granted", "successfully submitted"):
            self.assertNotIn(forbidden, lowered)
        self.assertIn("nothing is submitted", lowered)
        self.assertIn("submitted only when", lowered)
        self.assertIn("prepared draft, not submitted", self.js)

    def test_manual_review_copy(self):
        lowered = self.html.lower()
        self.assertIn("does not guarantee approval", lowered)
        self.assertIn("manual review", lowered)
        self.assertIn("no payment", lowered)
        self.assertIn("private delivery is arranged separately", lowered)
        for forbidden in ("instant access", "immediately activated", "immediate download",
                          "guaranteed access", "free forever", "no approval needed"):
            self.assertNotIn(forbidden, lowered)

    def test_version_split_is_accurate(self):
        self.assertIn("0.7.58;", self.html)
        self.assertIn("separate 0.7.59 build", self.html)
        provenance = json.loads((ROOT / "demo" / "provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["analyzer_version"], "0.7.58")

    def test_paid_button_never_promised_here(self):
        self.assertNotIn('type="submit"', self.html)
        self.assertNotIn("buy", self.html.lower())
        self.assertIn("coming soon", self.html.lower())

    def test_provenance_and_report_unchanged(self):
        import hashlib
        provenance = json.loads((ROOT / "demo" / "provenance.json").read_text(encoding="utf-8"))
        report = (ROOT / "demo" / "report.html").read_bytes()
        self.assertEqual(provenance["report_html_sha256"], hashlib.sha256(report).hexdigest())
        self.assertTrue(provenance["public_preview_only"])
        self.assertIsNone(provenance["physical_fault_precision"])


class CompanionPageTests(unittest.TestCase):
    def test_report_guide_counts_match_provenance(self):
        provenance = json.loads((ROOT / "demo" / "provenance.json").read_text(encoding="utf-8"))
        guide = GUIDE.read_text(encoding="utf-8")
        self.assertIn("<b>%d</b>" % provenance["number_of_input_files"], guide)
        self.assertIn("<b>%d</b>" % provenance["candidate_event_count"], guide)
        self.assertIn("<b>%d</b>" % provenance["investigation_finding_count"], guide)
        self.assertIn(provenance["analyzer_version"], guide)
        self.assertIn("does not name a verified physical root cause", guide)
        self.assertIn("./demo/report.html", guide)
        self.assertIn("./request.html", guide)

    def test_first_15_minutes_is_honest(self):
        page = FIRST.read_text(encoding="utf-8")
        self.assertIn("suggested order", page.lower())
        self.assertIn("not a promise", page.lower())
        self.assertIn("requires github", page.lower())
        self.assertIn("does not prove the robot behaved correctly", page.lower())
        self.assertIn("./request.html", page)
        self.assertIn("./demo/report.html", page)

    def test_pages_link_back_into_the_funnel(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        start = (ROOT / "start.html").read_text(encoding="utf-8")
        for page in (home, start):
            self.assertIn("./request.html", page)
        self.assertIn("./report-guide.html", home)
        self.assertIn("./first-15-minutes.html", home)
        self.assertIn("./first-15-minutes.html", start)
        self.assertIn("./report-guide.html", start)

    def test_home_attributes_the_sample_to_the_real_engine_version(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        provenance = json.loads((ROOT / "demo" / "provenance.json").read_text(encoding="utf-8"))
        self.assertIn("Robot Incident Analyzer v%s</strong>" % provenance["analyzer_version"], home)
        self.assertIn("separate v0.7.59 build", home)


if __name__ == "__main__":
    unittest.main()
