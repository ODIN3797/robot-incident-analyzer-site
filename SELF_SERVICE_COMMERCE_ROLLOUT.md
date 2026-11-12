# Self-service 14-day download and paid checkout: rollout gates

**Status (2026-11-12): NOT ACTIVE.** The pricing page is real, the public
fictional-data report is usable, and GitHub forms accept non-confidential
requests. However no public Windows ZIP, 14-day local entitlement, live payment
merchant, or paid-license activation is currently deployed. Do not call the
request form a download or a purchase.

## Proposed provider: Lemon Squeezy (merchant of record)

Reasons: official Republic of Korea payout support, a hosted shareable
checkout URL, receipt/digital file delivery, built-in software license key
generation, and a separate License API. The seller must pass its own activation
/KYC/KYB approval. Check tax and business-registration implications locally.

Official sources:
- https://docs.lemonsqueezy.com/help/getting-started/supported-countries
- https://docs.lemonsqueezy.com/help/products/sharing-products
- https://docs.lemonsqueezy.com/help/licensing/generating-license-keys
- https://docs.lemonsqueezy.com/guides/tutorials/license-keys
- https://docs.lemonsqueezy.com/help/products/free-trials

**Important:** Lemon Squeezy's hosted **subscription** free trial is not
automatically a no-card, standalone Windows ZIP trial. Standalone software
needs a real local/backend entitlement policy and lifecycle; a download or a
site banner does not start or enforce a trustworthy 14-day clock.

## Rollout checklist

### A. Free 14-day Windows evaluation (public download)

- [ ] Decide whether users require email/login and how to handle 1-device
      per-trial identities and privacy. Keep raw logs local.
- [ ] Implement and review 14-day expiry inside the client or signed
      entitlement provider. Never store a shared signing secret inside
      a PyInstaller executable. Local system-clock timestamps alone are
      **not tamper-resistant** (reinstall and clock rollback).
- [ ] Build a **separately versioned, intentionally distributable** Windows
      trial artifact. Validate it on a clean Windows 10/11 VM with a
      reliable expiration test and no-hardware fictional demo.
- [ ] Publish only the compiled ZIP and its SHA-256 to an accessible
      binary-distribution endpoint. The regular private GitHub release
      cannot be downloaded anonymously. Avoid public uploads of the Python
      zipapp because it contains extractable Python sources.
- [ ] Verify the exact public URL returns the ZIP with correct bytes and
      checksum, then set in \`purchase-config.json\`:
      \`trial.mode=public_download\`,
      \`trial.automatic_14_day_expiration=true\`,
      \`trial.public_download_url=<verified GitHub public ZIP URL>\`,
      \`trial.sha256=<verified release SHA256>\`.
      The public URL allowlist currently targets **this public site's**
      GitHub Releases, which need a release artifact uploaded separately.
- [ ] Verify click-through, Windows SmartScreen disclosure, checksum,
      first use, expiration boundary, no internet during offline log
      analysis, and how expired trials are upgraded.

### B. Paid license

- [ ] Finish Korean business/seller onboarding and activate store.
- [ ] Define commercial product variant, tax/legal text, refunds,
      seat/activation allowance, renewal terms and a non-misleading
      price. Do not infer price from software engineering cost alone.
- [ ] Configure file/receipt delivery and customer license keys.
- [ ] Add product-scoped license activation/validation to **client or secure
      backend**. Validate store/product/variant and subscription state,
      device activation limits and revocations. Never treat checkout
      redirect, a locally typed code, or a GitHub issue as payment proof.
- [ ] Decide acceptable activation network connectivity and how offline
      analysis will behave during network failure. License activation may
      connect to Lemon Squeezy; no private robot logs are needed for it.
- [ ] Test **test-mode** purchase → receipt/key → activation → unlock →
      renew/expire/refund → revoke. Then a controlled **live-mode**
      small-value order with refund/accounting verification.
- [ ] Only then set \`paid.mode=live_checkout\`,
      \`paid.provider=lemonsqueezy\`,
      \`paid.merchant_activated=true\`,
      \`paid.paid_license_activation_verified=true\`,
      \`paid.checkout_url=<actual share URL>\`.
      Accepted checkout URLs are HTTPS \`*.lemonsqueezy.com/checkout/buy/...\`
      only. Do not use a one-time \`/checkout/?cart=...\` URL.

### C. Site verification

\`\`\`bash
python3 -m unittest discover -s tests -v
python3 scripts/check_launch_links.py
\`\`\`

\`test_purchase_flow.py\` checks the activation configuration,
rejects untrusted/malformed checkout/download URLs, and makes the
current manual-only state explicit. \`scripts/check_launch_links.py\`
checks the public links and the genuine fictional report provenance.

After an actual public asset or checkout is configured, extend CI with
release-asset SHA/HTTP verification and an end-to-end paid fulfillment
test. Current configuration intentionally does **not** enable a buy
button or imply a self-service download works.

## Risks that need deliberate owner choice

The existing standalone Python \`.pyz\` contains readable Python
sources. The unsigned Windows PyInstaller ZIP is also
reverse-engineerable and not a robust license-secret store. Public
distribution requires an intentionally hardened/appropriate licensing
decision; keeping the main repo private is insufficient to prevent
reverse engineering.

There is no backend, merchant account connection, license key
verification implementation or product license entitlement in the
public website repository. Static GitHub Pages cannot privately issue
trusted paid entitlements. Any backend webhook verifier must keep
merchant credentials outside the public site.
