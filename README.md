# Robot Incident Analyzer — public landing page

**This is the public early-access product website**, not the private analyzer source repository. The live homepage is https://odin3797.github.io/robot-incident-analyzer-site/.

The intended Pages address is https://odin3797.github.io/robot-incident-analyzer-site/ — accessible only **after** Pages is enabled and deployed.

- `index.html`: standalone public marketing page and interactive **fictional** incident explorer.
- `pricing.html` and `purchase-config.json`: clear 14-day evaluation and paid team-license flows, with fail-closed support for future **verified** public Windows download and Lemon Squeezy checkout. Currently manual inquiries only; no functioning self-serve payment or installer download.
- `SELF_SERVICE_COMMERCE_ROLLOUT.md`: exact business/merchant, signed trial entitlement, release asset, license activation and verification gates.
- `demo/report.html`: **actual RIA-engine-generated** standalone HTML report created from three **fictional** inputs, not field data; 19 observations and 17 findings on the reproducible v0.7.59 build.
- `demo/provenance.json`: source SHA, report SHA-256, analyzer version, explicit synthetic-only and withheld field precision/recall.
- `privacy.html` and `pilot-terms.html`: public static preview data practices and manually approved evaluation scope.
- `.github/ISSUE_TEMPLATE/commercial_inquiry.yml`: privacy-safe team inquiry (not a payment or purchase).
- `PILOT_GUIDE.md`: product limitations, pilot access, first-time user tasks.
- `.github/ISSUE_TEMPLATE/pilot_request.yml`: nonconfidential private pilot access requests.
- `.github/ISSUE_TEMPLATE/pilot_feedback.yml`: structured, privacy-safe pilot usability feedback (preview or local app).

**No binary, proprietary data, private source, API tokens or customer logs belong in this repository.** The public walkthrough is a visual illustration, not a validated physical-fault detection result.

## Pages deployment

Repository owner: go to **Settings → Pages → Build and deployment → Source: Deploy from a branch**, select **main**, **/(root)** and Save. Then check the URL above without signing in. Creating the repository as Public does not automatically enable Pages.

## Product distribution

The private analyzer release **v0.7.59** includes both a Python zipapp (.pyz) and a **Windows portable EXE ZIP** (no Python installation required). The EXE was built and smoke-tested through release CI. This public site hosts **neither** package: access is reviewed manually through the public pilot request, and the analyzer binaries remain in the private repository. It is an unsigned portable EXE, not an MSI installer. No Linux-native executable or public download is offered. See [PILOT_GUIDE.md](PILOT_GUIDE.md) for steps and limitations.

## Feedback and outreach

Invite ROS engineers to test the public fictional walkthrough first. Use the public issue form for nonconfidential feedback. Never upload raw recordings to a public issue. Publish outreach only after verifying the live site.

**v0.7.59 note:** Private Windows and Python pilot packages are distinct from the new *internal-QA-only* Windows 14-day trial edition. The trial QA build has first-use expiry checks and a paid-key UI, but is not shipped or merchant-activated. The website's download and buy buttons remain **manual request links** until authenticated distribution and end-to-end commerce gates pass.

## Pilot feedback metrics (offline)

After receiving public feedback forms, run the local, aggregate-only [pilot feedback summary guide](FEEDBACK_METRICS.md) and its standard-library script. The input issue export contains usernames and free text: keep that export private and never commit it. Aggregate counts are not evidence of independent engineer identity, physical-fault accuracy or proven time savings.

## Launch state (manual early access, not a completed commercial sale)

The homepage now offers **two clearly different experiences**:
1. A *free, ungated* look at a real RIA report created by the actual private analyzer engine exclusively from built-in fictional ROS/telemetry data. There is no upload, no customer data, no source code exposed, no false precision figure.
2. A manual invitation to a **no-charge 14-day engineer evaluation** (initial goal: five independent users) or a commercial inquiry for a future scoped paid onboarding/team license. The public GitHub issue forms are **not** contracts, purchases, or private communications.

The v0.7.59 Python zipapp and Windows portable EXE were independently built as versioned assets in a **private GitHub Release**. Never suggest that public issue creation grants access to that repository or its source. A manually approved evaluator needs an independently agreed private, **binary-only** distribution route and SHA-256 verification. There is **no working public checkout, license enforcement, automated approvals, payment processor, production support SLA, validated field fault precision or confirmed paying customer**. The [download & pricing page](pricing.html) shows honest current status and will only change to direct links after its strict configuration gates and actual external provider setup are verified.

The authentic demo report was built and source-hash-attested by the private repository automation in `scripts/build_public_preview.py`; public contents were copied from its dedicated `artifact/fictional-public-preview` branch. Do not manually invent/alter incident counts or rewrite that generated HTML; regenerate from the actual RIA engine and update `demo/provenance.json` after changing the analysis.

### Manual distribution and privacy safety
The public forms intentionally ask only for role, OS, recording format and general problem description. They must not collect customer logs, emails, employer names, production robot identifiers or confidential details. Direct private agreements and actual invoicing must be handled off this public repo.
