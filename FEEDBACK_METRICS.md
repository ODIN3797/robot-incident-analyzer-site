# Pilot feedback metrics — offline, privacy-minimal summary

This tool converts **public GitHub pilot feedback form submissions** into aggregate usability counts. It does not contact GitHub automatically or upload robot data. Do not claim field-fault accuracy or confirmed business traction from this scorecard.

## 1. Get a local issue export

Run GitHub CLI only from a trusted machine with your own GitHub access, outside this repository or any public directory:

~~~bash
gh issue list --repo ODIN3797/robot-incident-analyzer-site \
  --state all --limit 500 \
  --json number,title,body,author \
  > /private/path/pilot_issues.json
~~~

The source file contains user-authored free text and GitHub handles. **Do not commit, publish, or share it.** Use a larger limit or paginated export if necessary: the summary only covers provided issues.

## 2. Generate the aggregate

~~~bash
python3 scripts/summarize_pilot_feedback.py \
  --input /private/path/pilot_issues.json \
  --output /private/path/pilot_aggregate.json
~~~

The tool refuses to overwrite output and has an 8 MB input cap. It accepts a JSON array of GitHub issues or an object containing an issues array. It counts only the issue form titled [Feedback] Engineer pilot review and one valid first response per GitHub login. Unknown, incomplete or tampered dropdown values are excluded.

The summary includes **only** fixed-category counts for attempted environment, task completion, time-to-first-report bucket and interest in future reuse. No issue numbers, author aliases, free-text answers, raw logs, source links, or screenshots are copied into it.

## Correct interpretation

- valid_distinct_github_accounts is a count of **account aliases**, not verified independent engineers.
- evidence_or_report_reached is **self-reported**, not observed task performance.
- five_account_feedback_target_reached reflects five valid account responses in the supplied export. It does not prove five independent engineers used the software.
- independent_engineer_count_verified, diagnostic precision/recall and measured time savings remain null.
- With zero issues the output accurately states zero feedback rather than invented progress.

For real field evaluation, use approved logs, separately collected incident labels and the provenance gates in the **private analyzer repository**. The public issue form must not request customer files.

## Developer checks

~~~bash
python3 -m unittest discover -s tests -v
~~~

Six synthetic tests cover zero data, duplicate accounts, invalid/dropdown injection, non-feedback issue filtering, privacy-safe output and no-overwrite behavior.
