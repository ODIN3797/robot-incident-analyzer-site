"""Contract tests for the public, non-uploading, fictional interactive landing page."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

SITE = Path(__file__).resolve().parents[1] / "index.html"

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.scripts, self.tabs = [], [], [], []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a":
            self.links.append(a.get("href", ""))
        if tag == "script":
            self.scripts.append(a)
        if a.get("role") == "tab":
            self.tabs.append(a)

class SiteChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = SITE.read_text(encoding="utf-8")
        cls.parsed = Parser()
        cls.parsed.feed(cls.html)

    def test_metadata_and_version(self):
        self.assertTrue(self.html.lower().startswith("<!doctype html>"))
        self.assertIn('name="viewport"', self.html)
        self.assertIn('property="og:title"', self.html)
        self.assertLess(len(self.html.encode()), 120_000)

    def test_windows_portable_onboarding_is_accurate(self):
        for text in ("V0.7.58", "ria-windows-0.7.58-portable.zip",
                     "RobotIncidentAnalyzer.exe", "Explore fictional demo",
                     "Exit session", "unsigned portable build",
                     "not publicly downloadable", "Python 3.10+"):
            self.assertIn(text.lower(), self.html.lower())
        self.assertNotIn("0.7.51", self.html)
        self.assertIn('data-platform="windows"', self.html)
        self.assertIn('data-platform="python"', self.html)
        self.assertIn('data-platform-panel="windows"', self.html)
        self.assertIn('data-platform-panel="python"', self.html)
        self.assertIn("selectPlatform(platform)", self.html)

    def test_no_broken_internal_nav_or_duplicate_ids(self):
        self.assertEqual(len(set(self.parsed.ids)), len(self.parsed.ids))
        for href in self.parsed.links:
            if href.startswith("#"):
                self.assertIn(href[1:], self.parsed.ids)

    def test_three_keyboard_selectable_scenarios(self):
        self.assertEqual(len(self.parsed.tabs), 3)
        self.assertIn("selectCase(index", self.html)
        self.assertIn("ArrowRight", self.html)
        self.assertIn("ArrowLeft", self.html)

    def test_preview_makes_no_real_fault_claim(self):
        for marker in ("SYNTHETIC DEMO", "fictional product walkthrough",
                       "not a genuine analyzer report", "not proof of physical cause"):
            self.assertIn(marker, self.html)

    def test_no_private_source_or_collection(self):
        self.assertNotIn("Robot-Incident-Analyzer/releases", self.html)
        self.assertNotIn('type="file"', self.html)
        self.assertNotIn("fetch(", self.html)
        self.assertNotIn("XMLHttpRequest", self.html)
        self.assertNotIn("<form", self.html)

    def test_approved_public_pilot_links(self):
        self.assertIn("https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new?template=pilot_request.yml", self.parsed.links)
        self.assertIn("./PILOT_GUIDE.md", self.parsed.links)

    def test_pilot_feedback_is_public_and_privacy_safe(self):
        link = "https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new?template=pilot_feedback.yml"
        self.assertIn(link, self.parsed.links)
        self.assertIn("Share pilot feedback", self.html)
        form = (SITE.parent / ".github/ISSUE_TEMPLATE/pilot_feedback.yml").read_text(encoding="utf-8")
        for marker in ("id: experience", "id: outcome", "id: first_report_time",
                       "id: friction", "id: privacy", "This is a public issue"):
            self.assertIn(marker.lower(), form.lower())
        self.assertIn("required: true", form)
        self.assertNotIn("type: upload", form)

    def test_self_contained_and_accessible(self):
        self.assertTrue(all("src" not in tag for tag in self.parsed.scripts))
        self.assertIn("prefers-reduced-motion", self.html)
        self.assertIn('role="tabpanel"', self.html)
        self.assertIn('role="tablist"', self.html)
        self.assertIn("aria-label", self.html)

    def test_public_pilot_form_collects_environment_safely(self):
        form = (SITE.parent / ".github/ISSUE_TEMPLATE/pilot_request.yml").read_text(encoding="utf-8")
        self.assertIn("id: environment", form)
        self.assertIn("Windows 10/11 (portable EXE", form)
        self.assertIn("Browser walkthrough only", form)
        self.assertIn("This is a **public issue**", form)

    def test_premium_components_present(self):
        for c in ("hero-visual", "hero-stats", "hero-plot", "trust-strip",
                  "problem-grid", "demo-body", "hero-alert"):
            self.assertIn(c, self.html)

if __name__ == "__main__":
    unittest.main()
