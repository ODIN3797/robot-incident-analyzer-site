"""Contract tests for guided-walkthrough discovery (home + reel landing).

The three-exercise walkthrough already exists; this layer only adds entry
points to it. These tests lock the two properties that matter:

* a visitor can actually reach the walkthrough from the homepage proof section
  and from the reel landing, without disturbing the existing CTA hierarchy;
* the honesty boundary does not move — the sample is genuine engine output from
  fictional recordings, an exercise is not a diagnosis, and a draft is not a
  submission.

Links and anchors are read from the real files rather than a hard-coded copy, so
regenerating the report or renaming an anchor fails the test instead of shipping
a dead link.
"""
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
START = ROOT / "start.html"
WALKTHROUGH = ROOT / "report-walkthrough.html"
REPORT = ROOT / "demo" / "report.html"
PROVENANCE = ROOT / "demo" / "provenance.json"

WALKTHROUGH_HREF = "./report-walkthrough.html"
REPORT_HREF = "./demo/report.html"
REQUEST_HREF = "./request.html"
PROVENANCE_HREF = "./demo/provenance.json"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "source", "track", "wbr"}


class Node:
    """A minimal element tree: enough to ask 'what is inside this element?'."""

    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        self.text = []

    # -- queries -----------------------------------------------------------
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

    def handle_startendtag(self, tag, attrs):  # <br/> and friends
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


class HomepageDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.page = parse(INDEX)
        self.proof = self.page.find(tag="section", element_id="proof")
        self.assertIsNotNone(self.proof, "index.html lost its #proof section")

    def test_home_proof_contains_direct_walkthrough_link(self):
        """#proof must carry its own link to the three-exercise walkthrough."""
        links = self.proof.anchors()
        hrefs = [a.attrs["href"] for a in links]
        self.assertIn(WALKTHROUGH_HREF, hrefs,
                      "no direct walkthrough link inside #proof")
        link = next(a for a in links if a.attrs["href"] == WALKTHROUGH_HREF)
        self.assertEqual(link.plain_text(), "Follow 3 guided evidence exercises")
        # A quiet text link, so the real report stays the section's main action.
        self.assertNotIn("button", link.classes)

    def test_home_primary_report_link_preserved(self):
        """The real report is still the first, primary action in #proof."""
        first = self.proof.anchors()[0]
        self.assertEqual(first.attrs["href"], REPORT_HREF)
        self.assertIn("button", first.classes)
        self.assertEqual(first.plain_text(), "Open the real HTML report ↗")
        hrefs = self.proof.hrefs()
        self.assertLess(hrefs.index(REPORT_HREF), hrefs.index(WALKTHROUGH_HREF))

    def test_home_provenance_link_preserved(self):
        """Provenance, reading guide and the limitation note survive unchanged."""
        hrefs = self.proof.hrefs()
        self.assertIn(PROVENANCE_HREF, hrefs)
        self.assertIn("./report-guide.html", hrefs)
        text = self.proof.plain_text()
        for phrase in ("19", "17", "v0.7.58", "Synthetic scenario only",
                       "not proven root causes"):
            self.assertIn(phrase, text)


class ReelLandingDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.page = parse(START)
        self.entries = self.page.find_all(tag="aside", cls="guided-entry")

    def test_start_has_one_guided_entry(self):
        """One compact guided entry sits outside the hero and links exactly once."""
        self.assertEqual(len(self.entries), 1,
                         f"expected one .guided-entry aside, found {len(self.entries)}")
        entry = self.entries[0]
        self.assertEqual(entry.hrefs(), [WALKTHROUGH_HREF])
        heroes = self.page.find_all(tag="section", cls="hero")
        self.assertTrue(heroes, "start.html lost its hero section")
        # The aside is a sibling after the hero, never nested inside it.
        self.assertFalse(any(entry in hero.walk() for hero in heroes),
                         "the guided entry must not live inside the hero")
        title = entry.attrs.get("aria-labelledby")
        self.assertEqual(title, "guided-entry-title")
        self.assertIsNotNone(self.page.find(element_id=title),
                             "aria-labelledby points at a missing id")
        heading = self.page.find(element_id=title)
        self.assertEqual(heading.tag, "h2")
        self.assertEqual(heading.plain_text(), "Not sure where to start?")
        text = entry.plain_text().lower()
        for phrase in ("fictional recordings", "docking", "navigation", "motion"):
            self.assertIn(phrase, text)

    def test_start_hero_ctas_unchanged(self):
        """The hero keeps exactly two CTAs, same order and same targets."""
        hero = self.page.find(tag="section", cls="hero")
        self.assertIsNotNone(hero, "start.html lost its hero section")
        actions = hero.find(tag="div", cls="actions")
        self.assertIsNotNone(actions, "the hero action group disappeared")
        self.assertEqual(actions.hrefs(), [REPORT_HREF, REQUEST_HREF],
                         "hero CTA hierarchy changed")
        self.assertEqual(len(actions.find_all(tag="a")), 2)
        # No new CTA was smuggled into the hero to reach the walkthrough.
        self.assertNotIn(WALKTHROUGH_HREF, hero.hrefs())


class WalkthroughDiscoveryScopeTests(unittest.TestCase):
    def test_real_walkthrough_exercises_exist(self):
        """The new link lands on the real three-exercise page."""
        page = parse(WALKTHROUGH)
        steps = [node.attrs["data-walk-step"]
                 for node in page.find_all(tag="section")
                 if "data-walk-step" in node.attrs]
        self.assertEqual(sorted(steps), ["1", "2", "3"])
        for number in ("1", "2", "3"):
            self.assertIsNotNone(page.find(element_id=f"step-{number}-title"))

    def test_walkthrough_evidence_links_resolve(self):
        """Every report anchor the walkthrough uses exists in the real report."""
        walk = parse(WALKTHROUGH)
        report_ids = {node.attrs["id"] for node in parse(REPORT).walk()
                      if node.attrs.get("id")}
        used = []
        for href in walk.hrefs():
            if href.startswith(REPORT_HREF + "#"):
                fragment = href.split("#", 1)[1]
                used.append(fragment)
                self.assertIn(fragment, report_ids,
                              f"walkthrough links to missing report anchor #{fragment}")
        self.assertTrue(used, "the walkthrough no longer links into the report")
        self.assertIn("event-E0010", used)
        self.assertIn("incident-I004", used)

    def test_fictional_and_no_diagnosis_copy(self):
        """Fictional inputs and the no-diagnosis boundary stay explicit everywhere."""
        proof = self.page_proof_text().lower()
        self.assertIn("fictional", proof)
        entry = parse(START).find(tag="aside", cls="guided-entry")
        entry_text = entry.plain_text().lower()
        for phrase in ("fictional recordings", "no diagnosis", "no submission"):
            self.assertIn(phrase, entry_text)
        body = WALKTHROUGH.read_text(encoding="utf-8").lower()
        for phrase in ("fictional", "nothing has been submitted",
                       "not an assessment result", "confirmed diagnosis"):
            self.assertIn(phrase, body)
        self.assertNotIn("diagnosis complete", body)
        self.assertNotIn("validated diagnosis", body)

    def page_proof_text(self):
        return parse(INDEX).find(tag="section", element_id="proof").plain_text()

    def test_no_tracking_or_new_collection(self):
        """Discovery adds navigation only: no storage, beacon or tracking params."""
        patterns = ("localstorage", "sessionstorage", "document.cookie",
                    "xmlhttprequest", "sendbeacon", "fetch(", "utm_",
                    "gtag(", "google-analytics", "navigator.connection")
        for path in (INDEX, START):
            body = path.read_text(encoding="utf-8").lower()
            for pattern in patterns:
                self.assertNotIn(pattern, body,
                                 f"{path.name} gained tracking/storage: {pattern}")
            for node in parse(path).find_all(tag="script"):
                self.assertNotIn("src", node.attrs,
                                 f"{path.name} gained an external script")
            for href in parse(path).hrefs():
                if href.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                self.assertNotIn("?", href,
                                 f"{path.name} internal link carries a query string: {href}")

    def test_provenance_sha_unchanged(self):
        """The published report is still byte-identical to its provenance hash."""
        provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        digest = hashlib.sha256(REPORT.read_bytes()).hexdigest()
        self.assertEqual(digest, provenance["report_html_sha256"])
        self.assertTrue(provenance["no_real_robot_data"])
        self.assertIsNone(provenance["physical_fault_precision"])
        self.assertIsNone(provenance["physical_fault_recall"])


if __name__ == "__main__":
    unittest.main()
