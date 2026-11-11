# Robot Incident Analyzer — Engineer Pilot (v0.7.57)

Robot Incident Analyzer is an **experimental offline engineering triage tool** for authorized ROS 1 BAG, ROS 2 MCAP/DB3 and telemetry CSV recordings. It groups candidate incidents, highlights time-aligned evidence and produces local HTML reports. **It does not verify physical root causes or make safety decisions.**

## Public preview (no installation)

The website's interactive three-case explorer is a **fictional illustration**, not analyzer output or a detection benchmark. The public page accepts no log uploads.

## Get private access

The source repository, Windows EXE and Python zipapp are in a **private** GitHub release. Request access through the [public pilot request issue](https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new?template=pilot_request.yml) (GitHub account required). Approval is manual and not guaranteed.

**Do not post customer names, contact information, proprietary robot logs, serial numbers, tokens or employer details in a public issue.**

## Windows: portable EXE, no Python installation

1. With approved access, obtain `ria-windows-0.7.57-portable.zip` from the private v0.7.57 release and verify its accompanying SHA-256 checksum.
2. Extract the **entire** `RobotIncidentAnalyzer` directory. Do not copy only the EXE.
3. Double-click `RobotIncidentAnalyzer.exe`; it opens a local browser at `127.0.0.1`.
4. Select **Explore fictional demo** for a first test on generated non-customer data.
5. Review incidents and evidence in the local workbench. Reports are saved to `%LOCALAPPDATA%\\RobotIncidentAnalyzer\\reports`.
6. Select **Exit session** inside the local page to stop the server.

The EXE is an **unsigned portable build**, not an MSI installer. SmartScreen may warn; do not circumvent organizational security policies. Verify the source and checksum before running. The localhost GUI includes a per-session token and origin checks, but untrusted log files are not sandboxed.

## Linux, macOS or Windows: Python zipapp

1. With approved access, download `ria-pilot-kit-0.7.57.zip` from the private release.
2. Unzip it and read `README-FIRST.txt`. Install Python **3.10+** if needed; the packaged sample requires no ROS or pip installation.
3. In the extracted folder run:

```bash
python3 robot-incident-analyzer-0.7.57.pyz analyze samples --output report
```

Use `python` instead of `python3` if appropriate. Open `report/report.html` and inspect candidate incidents and missing-signal warnings. CLI users can also run `python3 robot-incident-analyzer-0.7.57.pyz gui` to open the local workbench.

## 15-minute first-user evaluation

1. Explain what this product does after viewing the page for 60 seconds.
2. Use the fictional website explorer; distinguish an observation from a proven cause.
3. Run the local demo with your chosen pilot package and identify its first incident window.
4. Name the evidence you would need to investigate a real event, and what's missing.
5. Identify one confusing step or missing feature and whether you would try a permitted recording later.

Record OS, how long the first report took, what worked, what blocked you and whether the candidate findings were understandable. **No proprietary recording is required for this first round.**

## Share usability feedback (no logs)

After trying the website walkthrough or local pilot, use the [public feedback form](https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new?template=pilot_feedback.yml). Choose which environment you tried, whether you found a candidate incident and its evidence, the time to your first report (if measured), one missing signal and your biggest point of confusion. No real recording, error logs, customer names or sensitive screenshots are necessary.

The first business validation target is **five independent robotics engineers** completing the preview and structured feedback. A form being available is not evidence that five testers participated.

## Claims and limitations

- Local processing does not mean inputs are safe: only open recordings you are permitted to use and trust. Review report contents before sharing them.
- ROS 1 lz4 and some compressed MCAP types may need optional dependencies; the tool reports incomplete coverage.
- Windows releases may trigger SmartScreen, and portable executables can be reverse engineered.
- Public simulation and synthetic tests have been performed, but **independently verified real-field diagnostic precision, recall and time saved have not been established**.

**New in v0.7.57:** On permitted telemetry CSVs, an operator can explicitly map 0/1 validity columns in the local analyzer config (for example, `"validity_flags": {"ultra_front_valid": {"invalid": 0}}`). Each invalid recorded run becomes a bounded INFO signal-quality observation in HTML/JSON. Missing or unrecognized values remain unknown. **A validity bit is not independently confirmed equipment failure.** The public fictional walkthrough is not this analysis engine.
