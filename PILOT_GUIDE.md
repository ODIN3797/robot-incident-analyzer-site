# Robot Incident Analyzer — Engineer Pilot

Robot Incident Analyzer is an **experimental offline engineering triage tool** for ROS1/ROS2 BAG, MCAP, DB3 and telemetry CSV recordings. It groups candidate incidents and presents time-aligned signals in a local HTML report. **It does not diagnose verified physical root causes** and is not safety-certified.

## See the preview

Open the website's interactive 3-case explorer. The curves and values are fictional illustrations; this preview does **not** upload or analyze your log.

## Request private pilot access

The analyzer and GitHub source repository are private. To request access, open the [pilot request form](https://github.com/ODIN3797/robot-incident-analyzer-site/issues/new?template=pilot_request.yml). A GitHub account is required. Do not post confidential data, full logs, customer names, robot serial numbers or personal email addresses in a public issue.

If access is approved, you will receive private instructions for the release. The current v0.7.51 pilot package is a Python 3.10+ zipapp, not a Windows installer or a Linux native binary.

## Supported workflows (private tool)

- Read authorized ROS1 BAG, ROS2 MCAP/DB3 or telemetry CSVs; review warnings about unsupported messages.
- Inspect candidate events such as command-vs-odometry shortfall, sensor consistency and diagnostic-state issues.
- Review incident timelines and evidence context; export HTML reports for permitted audiences.

## 15-minute usability study

1. Describe the tool's purpose after 60 seconds on the landing page.
2. Open each fictional scenario and explain why the observation does not prove root cause.
3. Identify which evidence you would expect in your robot's incident log.
4. Identify anything unclear about the pilot download, data handling or report.
5. Tell us whether the workflow could fit your existing debug process.

No raw customer data is required for the first feedback round. Real-world diagnostic precision and time saved have **not** been established.
