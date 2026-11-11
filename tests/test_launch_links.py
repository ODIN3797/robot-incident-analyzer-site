"""Regression coverage for offline link audit and deployed static SHA check."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.check_launch_links import (
    PUBLIC_BASE, validate_live, validate_local,
)


class LaunchLinkSmokeTests(unittest.TestCase):
    def test_existing_public_site_has_complete_local_navigation(self):
        result = validate_local()
        self.assertGreaterEqual(result["html_pages"], 4)
        self.assertGreater(result["links_checked"], 10)
        self.assertEqual(result["issue_forms"], [
            "commercial_inquiry.yml", "pilot_feedback.yml", "pilot_request.yml"
        ])

    def test_detects_missing_relative_link_and_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text(
                '<html><a href="./gone.html">missing</a></html>', encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "Broken"):
                validate_local(root)
            (root / "index.html").write_text(
                '<html><a href="../../secret.txt">outside</a></html>', encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "escaping"):
                validate_local(root)

    def test_live_verification_uses_three_exact_public_urls(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "index.html").read_bytes()
        report = (root / "demo/report.html").read_bytes()
        provenance = (root / "demo/provenance.json").read_bytes()
        urls = {
            PUBLIC_BASE: html,
            PUBLIC_BASE + "demo/report.html": report,
            PUBLIC_BASE + "demo/provenance.json": provenance,
        }
        calls = []
        def mock_fetch(url):
            calls.append(url)
            return urls[url]
        result = validate_live(root, fetch=mock_fetch)
        self.assertTrue(result["deployed_report_verified"])
        self.assertEqual(calls, list(urls))
        def tampered(url):
            if url.endswith("report.html"):
                return report + b"<!-- tampered -->"
            return urls[url]
        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_live(root, fetch=tampered)

    def test_rejects_stale_deployed_provenance(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "index.html").read_bytes()
        report = (root / "demo/report.html").read_bytes()
        old = json.loads((root / "demo/provenance.json").read_text())
        old["source_commit"] = "0" * 40
        def stale(url):
            if url == PUBLIC_BASE:
                return html
            if url.endswith("report.html"):
                return report
            return json.dumps(old).encode()
        with self.assertRaisesRegex(ValueError, "provenance differs"):
            validate_live(root, fetch=stale)


if __name__ == "__main__":
    unittest.main()
