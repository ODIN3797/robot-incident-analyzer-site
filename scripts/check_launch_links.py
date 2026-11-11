"""Check public launch links and verify that deployed demo matches local provenance.

Offline mode is used by PR CI. --live fetches only the three static GitHub Pages
URLs; no customer data, GitHub authentication, or private repository access.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BASE = "https://odin3797.github.io/robot-incident-analyzer-site/"
ALLOWED_ISSUE_TEMPLATES = {
    "pilot_request.yml", "pilot_feedback.yml", "commercial_inquiry.yml",
}


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.ids: list[str] = []
        self.base_tags = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "a" and "href" in attributes:
            self.links.append(attributes["href"])
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if tag == "base":
            self.base_tags += 1


def validate_local(root: Path = ROOT) -> dict:
    """Fail closed on broken local links, duplicate anchors and forged reports."""
    root = Path(root).resolve()
    pages = sorted(root.rglob("*.html"))
    pages = [p for p in pages if ".git" not in p.relative_to(root).parts]
    if not pages or not (root / "index.html").is_file():
        raise ValueError("Missing public homepage")
    checked = 0
    issues = set()
    for page in pages:
        parsed = Links()
        parsed.feed(page.read_text(encoding="utf-8"))
        if parsed.base_tags or len(set(parsed.ids)) != len(parsed.ids):
            raise ValueError(f"Unsafe base URL or duplicate IDs: {page.relative_to(root)}")
        for href in parsed.links:
            if href.startswith(("mailto:", "tel:", "javascript:", "data:")):
                raise ValueError(f"Unsupported public site URL: {href}")
            parts = urlsplit(href)
            if parts.scheme or parts.netloc:
                if (parts.scheme != "https" or
                    parts.netloc != "github.com" or
                    parts.path != "/ODIN3797/robot-incident-analyzer-site/issues/new" or
                    not parts.query.startswith("template=")):
                    # External links that are not GitHub issue forms are outside this check.
                    continue
                template = parts.query.removeprefix("template=")
                if template not in ALLOWED_ISSUE_TEMPLATES:
                    raise ValueError(f"Unexpected issue template: {href}")
                issues.add(template)
                target = root / ".github" / "ISSUE_TEMPLATE" / template
                if not target.is_file():
                    raise ValueError(f"Missing issue form: {template}")
                checked += 1
                continue
            if href.startswith("//") or href.startswith("/"):
                raise ValueError(f"Root-relative or protocol-relative link: {href}")
            relative = unquote(parts.path)
            if relative:
                target = (page.parent / relative).resolve()
                if not target.is_relative_to(root) or not target.is_file():
                    raise ValueError(f"Broken or escaping internal link in {page.name}: {href}")
            else:
                target = page
            if parts.fragment:
                anchor = unquote(parts.fragment)
                if target.suffix.lower() == ".html":
                    dest = Links()
                    dest.feed(target.read_text(encoding="utf-8"))
                    if anchor not in dest.ids:
                        raise ValueError(f"Broken anchor in {page.name}: {href}")
            checked += 1
    if issues != ALLOWED_ISSUE_TEMPLATES:
        raise ValueError(f"Missing public CTA issue forms: {ALLOWED_ISSUE_TEMPLATES - issues}")
    provenance = json.loads((root / "demo/provenance.json").read_text("utf-8"))
    report = (root / "demo/report.html").read_bytes()
    digest = hashlib.sha256(report).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}", provenance.get("report_html_sha256", "")):
        raise ValueError("Malformed report SHA-256")
    if digest != provenance["report_html_sha256"]:
        raise ValueError("Public report does not match provenance SHA-256")
    if not (provenance.get("public_preview_only") is True and
            provenance.get("no_real_robot_data") is True and
            provenance.get("physical_fault_root_cause_verified") is False and
            provenance.get("physical_fault_precision") is None and
            provenance.get("physical_fault_recall") is None and
            b"FICTIONAL DEMO" in report):
        raise ValueError("Fictional-only report and unverified-accuracy safeguards missing")
    return {"html_pages": len(pages), "links_checked": checked,
            "issue_forms": sorted(issues), "report_sha256": digest}


def fetch_bytes(url: str, *, attempts: int = 3, pause: float = 4.0) -> bytes:
    if not url.startswith(PUBLIC_BASE):
        raise ValueError("Only the fixed public GitHub Pages site is permitted")
    for attempt in range(attempts):
        try:
            with urlopen(Request(url, headers={"User-Agent": "RIA-public-link-smoke/1.0"}),
                         timeout=15) as response:
                if response.status != 200 or response.url != url:
                    raise ValueError(f"Unexpected status or redirect for {url}")
                body = response.read(2_000_001)
                if len(body) > 2_000_000:
                    raise ValueError("Unexpectedly large public artifact")
                return body
        except (OSError, ValueError):
            if attempt + 1 == attempts:
                raise
            time.sleep(pause)
    raise RuntimeError("Unreachable")


def validate_live(root: Path = ROOT, *, fetch=fetch_bytes) -> dict:
    local = validate_local(root)
    home = fetch(PUBLIC_BASE)
    report = fetch(PUBLIC_BASE + "demo/report.html")
    remote_provenance = json.loads(fetch(PUBLIC_BASE + "demo/provenance.json"))
    expected = json.loads((Path(root) / "demo/provenance.json").read_text("utf-8"))
    if "Open the real HTML report" not in home.decode("utf-8"):
        raise ValueError("Deployed homepage lacks real-report CTA")
    if remote_provenance != expected:
        raise ValueError("Deployed provenance differs from repository")
    if hashlib.sha256(report).hexdigest() != expected["report_html_sha256"]:
        raise ValueError("Deployed HTML does not match published provenance")
    return {"deployment": PUBLIC_BASE, **local, "deployed_report_verified": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true",
                        help="Verify the exact deployed GitHub Pages files via HTTPS")
    args = parser.parse_args(argv)
    print(json.dumps(validate_live() if args.live else validate_local(), sort_keys=True))


if __name__ == "__main__":
    main()
