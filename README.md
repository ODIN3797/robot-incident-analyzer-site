# Robot Incident Analyzer — public landing page

**This is the public website only**, not the private analyzer source repository.

The intended Pages address is https://odin3797.github.io/robot-incident-analyzer-site/ — accessible only **after** Pages is enabled and deployed.

- `index.html`: standalone public marketing page and interactive **fictional** incident explorer.
- `PILOT_GUIDE.md`: product limitations, pilot access, first-time user tasks.
- `.github/ISSUE_TEMPLATE/pilot_request.yml`: nonconfidential private pilot access requests.
- `.github/ISSUE_TEMPLATE/pilot_feedback.yml`: structured, privacy-safe pilot usability feedback (preview or local app).

**No binary, proprietary data, private source, API tokens or customer logs belong in this repository.** The public walkthrough is a visual illustration, not a validated physical-fault detection result.

## Pages deployment

Repository owner: go to **Settings → Pages → Build and deployment → Source: Deploy from a branch**, select **main**, **/(root)** and Save. Then check the URL above without signing in. Creating the repository as Public does not automatically enable Pages.

## Product distribution

The private analyzer release **v0.7.53** includes both a Python zipapp (.pyz) and a **Windows portable EXE ZIP** (no Python installation required). The EXE was built and smoke-tested through release CI. This public site hosts **neither** package: access is reviewed manually through the public pilot request, and the analyzer binaries remain in the private repository. It is an unsigned portable EXE, not an MSI installer. No Linux-native executable or public download is offered. See [PILOT_GUIDE.md](PILOT_GUIDE.md) for steps and limitations.

## Feedback and outreach

Invite ROS engineers to test the public fictional walkthrough first. Use the public issue form for nonconfidential feedback. Never upload raw recordings to a public issue. Publish outreach only after verifying the live site.
