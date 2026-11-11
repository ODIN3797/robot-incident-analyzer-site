"""Evidence and privacy contracts for the manual early-access product site."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs).get("href", ""))


class EarlyAccessLaunchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = (ROOT / "index.html").read_text("utf-8")
        cls.parser = Parser()
        cls.parser.feed(cls.home)

    def test_real_report_is_exactly_attested_built_in_synthetic_output(self):
        provenance = json.loads((ROOT / "demo" / "provenance.json").read_text("utf-8"))
        report = (ROOT / "demo" / "report.html").read_bytes()
        self.assertEqual(provenance["source_commit"], "4fd7db5a25105db942af160314d655a93b9b0bcb")
        self.assertEqual(provenance["analyzer_version"], "0.7.58")
        self.assertEqual(provenance["kind"], "GENUINE_RIA_ENGINE_REPORT_FROM_BUILT_IN_FICTIONAL_DATA")
        self.assertTrue(provenance["public_preview_only"])
        self.assertTrue(provenance["no_real_robot_data"])
        self.assertEqual(provenance["number_of_input_files"], 3)
        self.assertEqual(provenance["candidate_event_count"], 19)
        self.assertEqual(provenance["investigation_finding_count"], 17)
        self.assertFalse(provenance["physical_fault_root_cause_verified"])
        self.assertIsNone(provenance["physical_fault_precision"])
        self.assertIsNone(provenance["physical_fault_recall"])
        self.assertEqual(provenance["report_html_sha256"], hashlib.sha256(report).hexdigest())
        self.assertGreater(len(report), 40_000)
        self.assertIn(b"FICTIONAL DEMO", report)
        self.assertIn(b"not", report.lower())
        self.assertNotIn(b"ghp_", report)
        self.assertNotIn(b"private-user-images.githubusercontent.com", report)

    def test_html_has_actual_preview_link_and_trust_safeguards(self):
        for link in ("./demo/report.html", "./demo/provenance.json",
                     "./pilot-terms.html", "./privacy.html"):
            self.assertIn(link, self.parser.links)
            self.assertTrue((ROOT / link).is_file())
        for phrase in ("REAL ENGINE OUTPUT", "FICTIONAL INPUTS",
                       "not a mockup", "No customer data",
                       "14-day", "no charge", "commercial",
                       "no self-service checkout", "public"):
            self.assertIn(phrase.lower(), self.home.lower())
        self.assertNotIn("Stripe(", self.home)
        self.assertNotIn("checkout.stripe.com", self.home)
        self.assertNotIn('type="file"', self.home)
        self.assertNotIn('<form', self.home)
        self.assertNotIn('fetch(', self.home)
        self.assertNotIn("XMLHttpRequest", self.home)

    def test_public_team_inquiry_does_not_request_secrets_or_payments(self):
        form = (ROOT / ".github" / "ISSUE_TEMPLATE" / "commercial_inquiry.yml").read_text()
        self.assertIn("type: dropdown", form)
        for field in ("id: role", "id: team_size", "id: interest", "id: format", "id: privacy"):
            self.assertIn(field, form)
        self.assertIn("required: true", form)
        self.assertNotIn("type: upload", form)
        self.assertNotIn("type: input", form)
        self.assertNotIn("email address", form.lower())
        self.assertIn(
            "https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new?template=commercial_inquiry.yml",
            self.parser.links
        )

    def test_data_practices_and_manual_pilot_are_visible(self):
        notice = (ROOT / "privacy.html").read_text()
        terms = (ROOT / "pilot-terms.html").read_text()
        for text in (notice, terms):
            self.assertIn("<html", text)
            self.assertIn("November 12, 2026", text)
            self.assertIn("GitHub", notice)
        for phrase in ("no telemetry collection", "customer logs", "public"):
            self.assertIn(phrase, notice.lower())
        self.assertIn("no-charge", terms)
        self.assertIn("manual", terms.lower())
        self.assertIn("not a", terms.lower())


if __name__ == "__main__":
    unittest.main()
