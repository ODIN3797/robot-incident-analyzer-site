"""Commercial self-service links fail closed until artifacts and payments are real."""
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ISSUE_BASE = "https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new?template="
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TRIAL_RE = re.compile(r"^/ODIN3797/robot-incident-analyzer-site/releases/download/v[0-9][^/]*/ria-windows-[^/]+-portable\.zip$")
BUY_RE = re.compile(r"^/checkout/buy/[A-Za-z0-9-]+$")
LS_HOST = re.compile(r"^[a-z0-9-]+\.lemonsqueezy\.com$")


def trial_url(url):
    if not isinstance(url, str):
        return False
    p = urlparse(url)
    return p.scheme == "https" and p.netloc == "github.com" and bool(TRIAL_RE.fullmatch(p.path)) and not p.query and not p.fragment


def checkout_url(url):
    if not isinstance(url, str):
        return False
    p = urlparse(url)
    return p.scheme == "https" and bool(LS_HOST.fullmatch(p.netloc)) and bool(BUY_RE.fullmatch(p.path)) and not p.query and not p.fragment


def config_checked(path=ROOT / "purchase-config.json"):
    cfg = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(cfg, dict) and set(cfg) == {
        "schema_version", "published_app_version", "trial", "paid"
    }
    assert cfg["schema_version"] == 1
    assert re.fullmatch(r"\d+\.\d+\.\d+", cfg["published_app_version"])
    trial = cfg["trial"]
    paid = cfg["paid"]
    assert isinstance(trial, dict) and set(trial) == {
        "mode", "public_download_url", "sha256", "automatic_14_day_expiration", "note"
    }
    assert isinstance(paid, dict) and set(paid) == {
        "mode", "provider", "checkout_url", "merchant_activated",
        "paid_license_activation_verified", "note"
    }
    assert trial["mode"] in ("manual_request", "public_download")
    assert paid["mode"] in ("inquiry", "live_checkout")
    assert paid["provider"] == "lemonsqueezy"
    assert type(trial["automatic_14_day_expiration"]) is bool
    assert type(paid["merchant_activated"]) is bool
    assert type(paid["paid_license_activation_verified"]) is bool
    assert isinstance(trial["note"], str) and 25 < len(trial["note"]) < 600
    assert isinstance(paid["note"], str) and 25 < len(paid["note"]) < 600
    if trial["mode"] == "manual_request":
        assert trial["public_download_url"] is None
        assert trial["sha256"] is None
        assert trial["automatic_14_day_expiration"] is False
    else:
        assert trial["automatic_14_day_expiration"] is True
        assert trial_url(trial["public_download_url"])
        assert isinstance(trial["sha256"], str) and HEX64.fullmatch(trial["sha256"])
    if paid["mode"] == "inquiry":
        assert paid["checkout_url"] is None
        assert paid["merchant_activated"] is False
        assert paid["paid_license_activation_verified"] is False
    else:
        assert paid["merchant_activated"] is True
        assert paid["paid_license_activation_verified"] is True
        assert checkout_url(paid["checkout_url"])
    return cfg


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.forms = []
        self.scripts = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a":
            self.links.append(a)
        if tag == "script":
            self.scripts.append(a)
        if tag == "form":
            self.forms.append(a)


class PurchasePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.page = (ROOT / "pricing.html").read_text(encoding="utf-8")
        cls.parser = LinkParser()
        cls.parser.feed(cls.page)

    def test_purchase_links_disabled_until_real_merchant_and_download(self):
        cfg = config_checked()
        self.assertEqual(cfg["trial"]["mode"], "manual_request")
        self.assertEqual(cfg["paid"]["mode"], "inquiry")
        self.assertIsNone(cfg["trial"]["public_download_url"])
        self.assertIsNone(cfg["paid"]["checkout_url"])
        self.assertFalse(cfg["trial"]["automatic_14_day_expiration"])
        self.assertFalse(cfg["paid"]["paid_license_activation_verified"])

    def test_no_broken_checkout_button_or_invented_asset(self):
        self.assertIn('id="trial-cta"', self.page)
        self.assertIn('id="paid-cta"', self.page)
        self.assertIn(ISSUE_BASE + "pilot_request.yml", self.page)
        self.assertIn(ISSUE_BASE + "commercial_inquiry.yml", self.page)
        self.assertIn("separate 14-day windows trial exe", self.page.lower())
        self.assertIn("not publicly downloadable", self.page.lower())
        self.assertIn("No payment will be taken", self.page)
        self.assertNotIn("stripe.com/checkout/session", self.page)
        self.assertNotIn('<form', self.page)
        self.assertNotIn('type="file"', self.page)
        self.assertFalse(self.parser.forms)
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)))
        self.assertEqual(self.parser.scripts, [{}])

    def test_checkout_activation_checks_exist_in_client(self):
        for phrase in (
            'p.mode==="live_checkout"',
            'p.merchant_activated===true',
            'p.paid_license_activation_verified===true',
            't.mode==="public_download"',
            't.automatic_14_day_expiration===true',
            'checkoutUrl(p.checkout_url)',
            'trialUrl(t.public_download_url)',
            'loadPurchaseLinks()',
        ):
            self.assertIn(phrase, self.page)

    def test_url_allowlist_rejects_fake_links_and_private_releases(self):
        for url in (
            "https://github.com/ODIN3797/Robot-Incident-Analyzer/releases/download/v0.7.59/private.zip",
            "https://evil.example/release.zip",
            "javascript:alert(1)",
            "https://github.com/ODIN3797/robot-incident-analyzer-site/releases/download/v0.7.59/hi.exe",
            "https://github.com/ODIN3797/robot-incident-analyzer-site/releases/download/v0.7.59/ria-windows-0.7.59-portable.zip?token=abc",
        ):
            self.assertFalse(trial_url(url))
        for url in (
            "http://ria.lemonsqueezy.com/checkout/buy/some-product",
            "https://ria.lemonsqueezy.com/checkout/?cart=secret",
            "https://ria.lemonsqueezy.com.evil.example/checkout/buy/xyz",
            "https://evil.example/checkout/buy/item",
            "https://ria.lemonsqueezy.com/checkout/buy/abc?test=1",
        ):
            self.assertFalse(checkout_url(url))
        self.assertTrue(trial_url(
            "https://github.com/ODIN3797/robot-incident-analyzer-site/releases/download/v0.8.0/ria-windows-0.8.0-portable.zip"))
        self.assertTrue(checkout_url(
            "https://ria.lemonsqueezy.com/checkout/buy/0123456a-bbbb-ccdd-eeee-ff99"))

    def test_homepage_has_purchase_navigation_and_no_fake_checkout(self):
        self.assertIn('href="./pricing.html"', self.home)
        self.assertIn("Direct downloads and paid orders are not live yet", self.home)
        self.assertIn("14-day", self.home.lower())
        self.assertIn("manual evaluation", self.home.lower())
        self.assertNotIn("lemonsqueezy.com/checkout/buy/", self.home)

    def test_public_pages_exist(self):
        for file in ("pricing.html", "privacy.html", "pilot-terms.html",
                     ".github/ISSUE_TEMPLATE/commercial_inquiry.yml",
                     "demo/report.html", "purchase-config.json"):
            self.assertTrue((ROOT / file).is_file(), file)


if __name__ == "__main__":
    unittest.main()
