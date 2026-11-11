"""Synthetic test cases: never use actual user information or robot recordings."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.summarize_pilot_feedback import summarize

BODY = """### Which experience did you try?

Public fictional browser walkthrough only

### What could you complete?

Find the incident and inspect its evidence

### Time from opening the local app to first report (optional)

Not measured / website only

### What evidence did you expect to see?

SECRET_PRIVATE_CUSTOMER_LOG

### Would you try this workflow for a future permitted incident?

Yes
"""


def entry(number, author, body=BODY):
    return {"number": number, "title": "[Feedback] Engineer pilot review",
            "author": {"login": author}, "body": body}


class FeedbackSummaryTests(unittest.TestCase):
    def test_empty_export_is_zero_not_100_percent(self):
        result = summarize([])
        self.assertEqual(result["counts"]["valid_distinct_github_accounts"], 0)
        self.assertFalse(result["counts"]["five_account_feedback_target_reached"])
        self.assertIsNone(result["diagnostic_precision"])

    def test_dedup_filters_and_private_text_removed(self):
        cases = [entry(2, "eng1"), entry(1, "eng1"), entry(3, "eng2"),
                 {**entry(4, "bot"), "pull_request": {"url": "none"}},
                 {**entry(5, "other"), "title": "Unrelated issue"},
                 entry(6, "broken", "### What could you complete?\n\nNo response")]
        result = summarize(cases)
        counts = result["counts"]
        self.assertEqual(counts["feedback_issues"], 4)
        self.assertEqual(counts["valid_distinct_github_accounts"], 2)
        self.assertEqual(counts["duplicate_account_submissions_excluded"], 1)
        self.assertEqual(counts["invalid_or_incomplete_feedback"], 1)
        self.assertEqual(counts["evidence_or_report_reached"], 2)
        serialized = json.dumps(result)
        for sensitive in ("SECRET_PRIVATE_CUSTOMER_LOG", "eng1", "eng2", "broken"):
            self.assertNotIn(sensitive, serialized)

    def test_target_only_at_five_distinct_valid_accounts(self):
        result = summarize([entry(n, f"engineer{n}") for n in range(1, 6)])
        self.assertTrue(result["counts"]["five_account_feedback_target_reached"])
        self.assertIsNone(result["independent_engineer_count_verified"])

    def test_repeated_or_malformed_dropdown_values_excluded(self):
        spoofed = BODY + "\n### What could you complete?\n\nExport or open an HTML report\n"
        malformed = BODY.replace("Yes", "Yes\nFake analytics here")
        result = summarize([entry(1, "e1", spoofed), entry(2, "e2", malformed)])
        self.assertEqual(result["counts"]["valid_distinct_github_accounts"], 0)
        self.assertEqual(result["counts"]["invalid_or_incomplete_feedback"], 2)

    def test_cli_creates_only_safe_aggregate_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "raw_issues.json"
            output = Path(tmp) / "aggregate.json"
            source.write_text(json.dumps([entry(1, "eng1")]), encoding="utf-8")
            cmd = [sys.executable, str(ROOT / "scripts/summarize_pilot_feedback.py"),
                   "--input", str(source), "--output", str(output)]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            aggregate = output.read_text(encoding="utf-8")
            self.assertEqual(json.loads(aggregate)["counts"]["valid_distinct_github_accounts"], 1)
            self.assertNotIn("SECRET_PRIVATE_CUSTOMER_LOG", aggregate)
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)

    def test_invalid_list_rejected(self):
        with self.assertRaises(ValueError):
            summarize({"foo": "bar"})


if __name__ == "__main__":
    unittest.main()
