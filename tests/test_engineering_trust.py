"""Contract tests for the engineering trust & limits sections (home + reel landing).

The same facts already exist, correctly worded, in privacy.html, pilot-terms.html,
pricing.html, purchase-config.json and demo/provenance.json - they were simply
scattered across pages. This layer moves them next to the evaluation request
without inventing anything.

So these tests do not check that "some text is present": they read the source of
each claim and fail when a new trust sentence would outrun the file it comes from
(for example, if privacy.html ever gains a log-upload form, or purchase-config
stops being fail-closed).
"""
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
START = ROOT / "start.html"
PRIVACY = ROOT / "privacy.html"
PILOT_TERMS = ROOT / "pilot-terms.html"
PRICING = ROOT / "pricing.html"
PROVENANCE = ROOT / "demo" / "provenance.json"
REPORT = ROOT / "demo" / "report.html"
PURCHASE_CONFIG = ROOT / "purchase-config.json"
PILOT_TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "pilot_request.yml"

REPORT_HREF = "./demo/report.html"
REQUEST_HREF = "./request.html"
PRIVACY_HREF = "./privacy.html"
PILOT_SCOPE_HREF = "./pilot-terms.html"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "source", "track", "wbr"}


class Node:
    """Minimal element tree - only what these assertions need."""

    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        self.text = []

    @property
    def classes(self):
        return (self.attrs.get("class") or "").split()

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def find_all(self, tag=None, cls=None, element_id=None):
        return [node for node in self.walk()
                if (tag is None or node.tag == tag)
                and (cls is None or cls in node.classes)
                and (element_id is None or node.attrs.get("id") == element_id)]

    def find(self, **kwargs):
        matches = self.find_all(**kwargs)
        return matches[0] if matches else None

    def anchors(self):
        return [a for a in self.find_all(tag="a") if a.attrs.get("href")]

    def hrefs(self):
        return [a.attrs["href"] for a in self.anchors()]

    def plain_text(self):
        parts = []

        def collect(node):
            parts.extend(node.text)
            for child in node.children:
                if child.tag in ("script", "style"):
                    continue
                collect(child)

        collect(self)
        return " ".join(" ".join(parts).split())


class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {})
        self.stack = [self.root]
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, dict(attrs)))

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if not self._skip:
            self.stack[-1].text.append(data)


def parse(path):
    parser = TreeParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser.root


def section_order(page, ids):
    """Return the document order of the given section ids."""
    order = []
    for node in page.walk():
        if node.tag == "section" and node.attrs.get("id") in ids:
            order.append(node.attrs["id"])
    return order


class TrustPlacementTests(unittest.TestCase):
    def setUp(self):
        self.index = parse(INDEX)
        self.start = parse(START)

    def test_home_has_one_trust_section(self):
        sections = self.index.find_all(tag="section", element_id="trust")
        self.assertEqual(len(sections), 1,
                         f"expected exactly one section#trust on the homepage, found {len(sections)}")
        section = sections[0]
        heading_id = section.attrs.get("aria-labelledby")
        heading = self.index.find(element_id=heading_id)
        self.assertIsNotNone(heading, "homepage #trust aria-labelledby points at a missing id")
        self.assertEqual(heading.tag, "h2")
        self.assertEqual(heading.plain_text(),
                         "Know what RIA can — and cannot — tell you.")

    def test_start_has_one_trust_section(self):
        sections = self.start.find_all(tag="section", element_id="trust")
        self.assertEqual(len(sections), 1,
                         f"expected exactly one section#trust on the reel landing, found {len(sections)}")
        heading = self.start.find(element_id=sections[0].attrs.get("aria-labelledby"))
        self.assertIsNotNone(heading)
        self.assertEqual(heading.tag, "h2")
        self.assertEqual(heading.plain_text(), "Before you try RIA")

    def test_trust_sits_before_the_request_and_after_how_it_works(self):
        order = section_order(self.index, {"how", "trust", "early-access", "pilot"})
        self.assertIn("trust", order)
        self.assertIn("pilot", order)
        self.assertLess(order.index("how"), order.index("trust"),
                        "the limits section should follow 'How it works'")
        self.assertLess(order.index("trust"), order.index("pilot"),
                        "the limits section must come before the pilot request section")
        start_order = section_order(self.start, {"trust", "request"})
        self.assertLess(start_order.index("trust"), start_order.index("request"),
                        "the reel landing must show limits before the request steps")

    def test_start_hero_ctas_unchanged(self):
        hero = self.start.find(tag="section", cls="hero")
        self.assertIsNotNone(hero, "start.html lost its hero section")
        actions = hero.find(tag="div", cls="actions")
        self.assertIsNotNone(actions, "the hero action group disappeared")
        self.assertEqual(actions.hrefs(), [REPORT_HREF, REQUEST_HREF],
                         "hero CTA hierarchy changed")
        self.assertEqual(len(actions.find_all(tag="a")), 2)
        # The trust section must live outside the hero.
        trust = self.start.find(tag="section", element_id="trust")
        self.assertFalse(any(trust in node.walk() for node in [hero]),
                         "the trust section must not live inside the hero")


class TrustClaimSourceTests(unittest.TestCase):
    """Every claim is checked against the file that is allowed to make it."""

    def setUp(self):
        self.index = parse(INDEX)
        self.start = parse(START)
        self.home_trust = self.index.find(tag="section", element_id="trust").plain_text()
        self.start_trust = self.start.find(tag="section", element_id="trust").plain_text()
        self.both = f"{self.home_trust} {self.start_trust}".lower()

    def test_no_verified_root_cause_claim(self):
        provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        self.assertFalse(provenance["physical_fault_root_cause_verified"])
        self.assertIn("does not establish confirmed physical root causes", self.both)
        self.assertIn("does not prove that a robot operated normally", self.both)
        self.assertIn("not a safety controller", self.both)
        for banned in ("proven root cause", "confirmed root cause is provided",
                       "diagnosis complete", "safety certified"):
            self.assertNotIn(banned, self.both)

    def test_no_field_accuracy_claim(self):
        provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        self.assertIsNone(provenance["physical_fault_precision"])
        self.assertIsNone(provenance["physical_fault_recall"])
        self.assertIn("independently validated field-fault detection accuracy", self.both)
        for banned in ("precision of 9", "recall of 9", "% accuracy",
                       "guaranteed detection"):
            self.assertNotIn(banned, self.both)

    def test_privacy_claim_matches_notice(self):
        privacy = parse(PRIVACY)
        privacy_text = PRIVACY.read_text(encoding="utf-8").lower()
        # The notices must still say what the homepage now repeats.
        self.assertIn("does not ask you to upload", privacy_text)
        self.assertIn("github hosts the website", privacy_text)
        self.assertIn("your github identity", privacy_text)
        # And the site must still have no upload path at all.
        self.assertEqual(privacy.find_all(tag="form"), [],
                         "privacy.html gained a form")
        for page in (INDEX, START):
            body = page.read_text(encoding="utf-8").lower()
            self.assertNotIn('type="file"', body,
                             f"{page.name} gained a file input")
        self.assertIn("does not provide a log-upload endpoint", self.home_trust.lower())
        self.assertIn("no robot-log upload endpoint", self.start_trust.lower())

    def test_local_pilot_matches_terms(self):
        terms = PILOT_TERMS.read_text(encoding="utf-8").lower()
        self.assertIn("manually approved 14-day no-charge pilot", terms)
        self.assertIn("approved local recordings", terms)
        self.assertIn("pilot approval and binary-only delivery are manual", terms)
        self.assertIn("does not offer an instant executable download", terms)
        self.assertIn("run locally", self.home_trust.lower())
        self.assertIn("approved evaluation packages run locally", self.start_trust.lower())
        self.assertIn("private delivery", self.start_trust.lower())

    def test_public_issue_disclosed(self):
        template = PILOT_TEMPLATE.read_text(encoding="utf-8").lower()
        self.assertIn("public issue", template)
        self.assertIn("no public binary download", template)
        self.assertIn("public github issue", self.home_trust.lower())
        self.assertIn("public github request", self.start_trust.lower())
        self.assertIn("github identity", self.home_trust.lower())
        # No claim that anything is submitted from the site itself.
        self.assertIn("never post customer logs", self.home_trust.lower())

    def test_no_checkout_or_download_claim(self):
        config = json.loads(PURCHASE_CONFIG.read_text(encoding="utf-8"))
        self.assertIsNone(config["trial"]["public_download_url"])
        self.assertFalse(config["trial"]["automatic_14_day_expiration"])
        self.assertIsNone(config["paid"]["checkout_url"])
        self.assertFalse(config["paid"]["merchant_activated"])
        self.assertFalse(config["paid"]["paid_license_activation_verified"])
        pricing = parse(PRICING)
        payment_block = [node for node in pricing.find_all(tag="button")
                         if "disabled" in node.attrs]
        self.assertTrue(payment_block, "pricing.html lost its fail-closed buy button")
        self.assertIn("coming soon", self.home_trust.lower())
        self.assertIn("no immediate public executable download", self.home_trust.lower())
        self.assertIn("no immediate public download", self.start_trust.lower())

    def test_no_new_scripts_or_storage(self):
        patterns = ("localstorage", "sessionstorage", "document.cookie",
                    "xmlhttprequest", "sendbeacon", "fetch(", "utm_", "gtag(",
                    "google-analytics")
        for path in (INDEX, START):
            body = path.read_text(encoding="utf-8").lower()
            for pattern in patterns:
                self.assertNotIn(pattern, body,
                                 f"{path.name} gained tracking/storage: {pattern}")
        # The trust sections themselves carry no interactive control.
        for path in (INDEX, START):
            section = parse(path).find(tag="section", element_id="trust")
            self.assertIsNotNone(section, f"{path.name} lost section#trust")
            self.assertEqual(section.find_all(tag="script"), [],
                             "the trust section must not add script")
            self.assertEqual(section.find_all(tag="button"), [],
                             "the trust section must not add buttons")
            self.assertEqual(section.find_all(tag="input"), [],
                             "the trust section must not add inputs")

    def test_trust_links_resolve(self):
        home_hrefs = self.index.find(tag="section", element_id="trust").hrefs()
        for href in (PRIVACY_HREF, PILOT_SCOPE_HREF, REPORT_HREF):
            self.assertIn(href, home_hrefs)
        start_hrefs = self.start.find(tag="section", element_id="trust").hrefs()
        for href in (PRIVACY_HREF, PILOT_SCOPE_HREF):
            self.assertIn(href, start_hrefs)
        for href in set(home_hrefs) | set(start_hrefs):
            if href.startswith(("http://", "https://", "#")):
                continue
            target = (ROOT / href.split("#", 1)[0].lstrip("./")).resolve()
            self.assertTrue(target.exists(), f"trust link points at a missing file: {href}")

    def test_immutable_report_provenance(self):
        provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        digest = hashlib.sha256(REPORT.read_bytes()).hexdigest()
        self.assertEqual(digest, provenance["report_html_sha256"])
        self.assertEqual(
            provenance["report_html_sha256"],
            "73c3edc74f67687415d215dd0b4a45ea14f84374757a06de8f325f3092ee2818")
        self.assertTrue(provenance["no_real_robot_data"])
        self.assertTrue(provenance["public_preview_only"])


if __name__ == "__main__":
    unittest.main()
