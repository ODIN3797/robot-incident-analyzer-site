"""Aggregate public pilot feedback issue-form responses without retaining identities.

Input: an operator-supplied GitHub issue JSON array, e.g. from gh issue list.
No network calls, no raw comment bodies, and no identifying issue/user fields in output.
Distinct GitHub account aliases are not verified independent human engineers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ISSUE_PREFIX = "[Feedback] Engineer pilot review"
MAX_BYTES = 8_000_000
FIELDS = {
    "Which experience did you try?": (
        "Public fictional browser walkthrough only",
        "Private Windows v0.7.53 portable EXE (fictional demo)",
        "Private Python v0.7.53 zipapp (fictional demo)",
        "Private pilot on permitted recording (no file sharing)",
        "I could not run the tool",
    ),
    "What could you complete?": (
        "Understand the purpose only",
        "Find the example incident",
        "Find the incident and inspect its evidence",
        "Export or open an HTML report",
        "Nothing — blocked by setup or UI",
    ),
    "Time from opening the local app to first report (optional)": (
        "Not measured / website only",
        "Under 2 minutes",
        "2 to 5 minutes",
        "5 to 15 minutes",
        "Over 15 minutes",
        "Could not complete",
    ),
    "Would you try this workflow for a future permitted incident?": (
        "Yes", "Maybe, after improvements", "No", "Not sure yet",
    ),
}
REQUIRED = (
    "Which experience did you try?",
    "What could you complete?",
    "Would you try this workflow for a future permitted incident?",
)
HEADING = re.compile(r"(?m)^### ([^\r\n]+)\s*$")
TIME_KEY = "Time from opening the local app to first report (optional)"


def _fields(body: str) -> dict[str, str] | None:
    """Read only fixed dropdown answers; never return textarea/free-form content."""
    if not isinstance(body, str) or len(body) > 100_000:
        return None
    matches = list(HEADING.finditer(body))
    parsed = {}
    for index, match in enumerate(matches):
        key = match.group(1).strip()
        if key not in FIELDS:
            continue
        if key in parsed:
            return None
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        value = body[match.end():end].strip()
        if value not in FIELDS[key] and not (key == TIME_KEY and value in ("", "No response")):
            return None
        parsed[key] = value
    if not all(key in parsed for key in REQUIRED):
        return None
    return parsed


def summarize(issues: list[dict]) -> dict:
    if not isinstance(issues, list) or len(issues) > 10000:
        raise ValueError("Expected a GitHub issues JSON array (maximum 10,000)")
    feedback = []
    for issue in issues:
        if not isinstance(issue, dict):
            raise ValueError("Issue items must be JSON objects")
        if issue.get("pull_request") or issue.get("isPullRequest") is True:
            continue
        if str(issue.get("title", "")).startswith(ISSUE_PREFIX):
            feedback.append(issue)
    feedback.sort(key=lambda issue: (
        issue.get("number") if type(issue.get("number")) is int else 10**15))
    valid = []
    seen = set()
    duplicate_count = 0
    invalid_count = 0
    for issue in feedback:
        author = issue.get("author") or issue.get("user")
        login = author.get("login") if isinstance(author, dict) else None
        if not isinstance(login, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", login):
            invalid_count += 1
            continue
        fields = _fields(issue.get("body", ""))
        if fields is None:
            invalid_count += 1
            continue
        key = login.casefold()
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        valid.append(fields)
    exp_key, outcome_key, retest_key = REQUIRED
    completed_evidence = sum(row[outcome_key] in (
        "Find the incident and inspect its evidence",
        "Export or open an HTML report",
    ) for row in valid)
    def count_options(key):
        return {label: sum(row.get(key) == label for row in valid) for label in FIELDS[key]}
    return {
        "schema_version": "1.0",
        "source": "operator-provided GitHub public issue export; not independently authenticated",
        "counts": {
            "exported_issues": len(issues),
            "feedback_issues": len(feedback),
            "valid_distinct_github_accounts": len(valid),
            "invalid_or_incomplete_feedback": invalid_count,
            "duplicate_account_submissions_excluded": duplicate_count,
            "evidence_or_report_reached": completed_evidence,
            "five_account_feedback_target_reached": len(valid) >= 5,
        },
        "experiences": count_options(exp_key),
        "task_outcomes": count_options(outcome_key),
        "first_report_time_buckets": count_options(TIME_KEY),
        "future_reuse_intent": count_options(retest_key),
        "independent_engineer_count_verified": None,
        "diagnostic_precision": None,
        "diagnostic_recall": None,
        "measured_time_savings": None,
        "limitations": [
            "GitHub account aliases are not proof of distinct humans or robotics engineering credentials.",
            "Dropdown choices are self-reported, not independently observed task completion.",
            "This report excludes free text, user identities, issue numbers, links and log contents.",
            "Counts cover only the provided export; incomplete pagination may omit submissions.",
            "This is usability feedback, not evidence of physical fault detection accuracy.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Local GitHub issue JSON export")
    parser.add_argument("--output", type=Path, required=True, help="Aggregate-only summary output")
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("Output exists; refusing to overwrite")
    if args.input.stat().st_size > MAX_BYTES:
        parser.error("Input exceeds safe size cap")
    with args.input.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and isinstance(payload.get("issues"), list):
        payload = payload["issues"]
    result = summarize(payload)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps(result["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
