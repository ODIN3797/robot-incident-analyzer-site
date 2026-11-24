"""Contract tests for the reel-first mobile landing (start.html).

The landing has one job: a visitor arriving from a short video should learn
what RIA is and pick one of two next actions without scrolling past an essay.
These tests lock the CTA hierarchy, the mobile-first layout rules, and the
honesty boundaries that must survive any copy change: AI reels are fictional,
the sample report is real engine output from fictional data, a draft is not a
submission, and only a public GitHub issue can actually request access.
"""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
START = ROOT / "start.html"
TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "pilot_request.yml"
ISSUE_FORM = (
    "https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new"
    "?template=pilot_request.yml"
)


class HeroParser(HTMLParser):
    """Collect the anchors inside <section class="hero"> .actions and the h1 text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.hero_links = []          # anchors inside .hero .actions
        self.hero_hrefs_anywhere = []  # anchors anywhere inside .hero
        self.all_hrefs = []
        self.h1_text = []
        self._in_hero = False
        self._in_actions = 0
        self._in_h1 = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "section" and "hero" in (a.get("class") or "").split():
            self._in_hero = True
        if self._in_hero and tag == "div" and "actions" in (a.get("class") or "").split():
            self._in_actions += 1
        if self._in_hero and tag == "h1":
            self._in_h1 = True
        if tag == "a" and "href" in a:
            self.all_hrefs.append(a["href"])
            if self._in_hero:
                self.hero_hrefs_anywhere.append(a["href"])
                if self._in_actions:
                    self.hero_links.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "section":
            self._in_hero = False
        if tag == "div" and self._in_actions:
            self._in_actions -= 1
        if tag == "h1":
            self._in_h1 = False

    def handle_data(self, data):
        if self._in_h1:
            self.h1_text.append(data)


def parse_start():
    html = START.read_text(encoding="utf-8")
    parser = HeroParser()
    parser.feed(html)
    return html, parser


class StartMobileLandingTest(unittest.TestCase):
    def setUp(self):
        self.html, self.parsed = parse_start()
        self.lower = self.html.lower()

    # ---- CTA hierarchy -------------------------------------------------
    def test_hero_has_exactly_two_ctas(self):
        self.assertEqual(len(self.parsed.hero_links), 2,
                         "the hero must offer exactly two primary actions")

    def test_primary_cta_opens_the_sample_report(self):
        self.assertEqual(self.parsed.hero_links[0], "./demo/report.html")

    def test_secondary_cta_opens_the_request_builder(self):
        self.assertEqual(self.parsed.hero_links[1], "./request.html")

    def test_third_hero_request_button_is_gone(self):
        self.assertNotIn("#request", self.parsed.hero_links,
                         "the duplicated 'request an evaluation' button must not compete with the two CTAs")
        self.assertNotIn("request an evaluation ↓", self.lower)

    def test_hero_has_one_heading_that_names_the_product_job(self):
        heading = " ".join(" ".join(self.parsed.h1_text).split()).lower()
        self.assertIn("follow the logs", heading)
        self.assertEqual(self.lower.count("<h1>"), 1)

    # ---- Honest framing -------------------------------------------------
    def test_ai_reels_and_real_engine_output_are_distinguished(self):
        self.assertIn("fictional comedy", self.lower)
        self.assertIn("genuine ria engine output generated from fictional data", self.lower)
        self.assertIn("not a verified field diagnosis", self.lower)

    def test_public_github_submission_is_disclosed_in_the_hero(self):
        self.assertIn("a github account is required to submit a public request", self.lower)

    def test_draft_and_submission_are_separated(self):
        self.assertIn("nothing is submitted from the request builder", self.lower)
        self.assertIn("approval is not guaranteed", self.lower)

    def test_manual_pilot_path_is_still_available(self):
        self.assertIn(ISSUE_FORM, self.html)
        self.assertTrue(TEMPLATE.is_file(), "the public issue form must exist")

    def test_funnel_guide_links_are_retained(self):
        for href in ("./report-guide.html", "./first-15-minutes.html", "./request.html"):
            self.assertIn(href, self.parsed.all_hrefs)

    # ---- No collection, no false commerce ------------------------------
    def test_no_new_data_collection(self):
        for banned in ("<form", "<input", "type=\"file\"", "fetch(", "xmlhttprequest",
                       "sendbeacon", "localstorage", "document.cookie", "<script"):
            self.assertNotIn(banned, self.lower)

    def test_no_false_commercial_or_accuracy_claims(self):
        for banned in ("buy now", "add to cart", "instant download", "start free trial",
                       "guaranteed approval", "certified accuracy", "detection accuracy of",
                       "money-back", "stripe", "$"):
            self.assertNotIn(banned, self.lower)

    # ---- Mobile-first layout rules ------------------------------------
    def test_viewport_and_mobile_rules_are_present(self):
        self.assertIn('name="viewport" content="width=device-width,initial-scale=1"',
                      self.html)
        self.assertIn("clamp(", self.html)
        # The base rules are the mobile ones; desktop tweaks live in a min-width query.
        self.assertIn("@media(min-width:700px)", self.html)
        self.assertIsNone(re.search(r"@media\(max-width:430px\)", self.html))

    def test_tap_targets_and_gaps_meet_mobile_minimums(self):
        base_btn = re.search(r"\.btn\{([^}]*)\}", self.html)
        self.assertIsNotNone(base_btn)
        min_height = re.search(r"min-height:(\d+)px", base_btn.group(1))
        self.assertIsNotNone(min_height, "buttons need an explicit minimum height")
        self.assertGreaterEqual(int(min_height.group(1)), 48)
        actions = re.search(r"\.actions\{([^}]*)\}", self.html)
        gap = re.search(r"gap:(\d+)px", actions.group(1))
        self.assertGreaterEqual(int(gap.group(1)), 10)
        self.assertLessEqual(int(gap.group(1)), 12)

    def test_layout_cannot_scroll_sideways(self):
        self.assertIn("box-sizing:border-box", self.html.replace(" ", ""))
        self.assertIn("calc(100% - 32px)", self.html)
        self.assertIn("overflow-wrap:break-word", self.html)


if __name__ == "__main__":
    unittest.main()
