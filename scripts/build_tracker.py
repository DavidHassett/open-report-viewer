#!/usr/bin/env python3
"""
Builds a small SVG "open reports" tracker image from the currently open
GitHub Issues in this repository, and writes it to assets/tracker.svg.

No external dependencies (uses only Python's standard library) so it runs
in GitHub Actions with zero pip installs.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

# --- Configuration -----------------------------------------------------

REPO = "DavidHassett/open-report-viewer"
OUTPUT_PATH = "assets/tracker.svg"
MAX_ROWS = 15  # cap how many rows are drawn; extra reports are summarised

# --- Fetch open issues ---------------------------------------------------

def fetch_open_issues(repo: str):
    """Pull all open issues (excluding pull requests) via the GitHub API."""
    token = os.environ.get("GITHUB_TOKEN", "")
    issues = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/issues?state=open&per_page=100&page={page}"
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github+json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req) as resp:
            batch = json.loads(resp.read().decode())
        if not batch:
            break
        for item in batch:
            if "pull_request" in item:
                continue  # skip PRs, the issues endpoint includes them
            issues.append(item)
        page += 1
    return issues


def format_date(iso_string: str) -> str:
    dt = datetime.strptime(iso_string, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return dt.strftime("%d %b %Y")


def days_open(iso_string: str) -> int:
    dt = datetime.strptime(iso_string, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def truncate(text: str, max_len: int = 46) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "\u2026"


# --- Build SVG ------------------------------------------------------------

def build_svg(issues):
    # Oldest-first, so the longest-outstanding reports surface at the top
    issues_sorted = sorted(issues, key=lambda i: i["created_at"])

    row_height = 22
    header_height = 34
    footer_height = 22 if len(issues_sorted) > MAX_ROWS else 0
    shown = issues_sorted[:MAX_ROWS]
    width = 480
    height = header_height + row_height * max(len(shown), 1) + footer_height + 10

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Segoe UI, Arial, sans-serif">'
    )
    parts.append(f'<rect width="{width}" height="{height}" fill="#ffffff" stroke="#d0d7de" rx="6"/>')

    # Header
    parts.append(
        f'<text x="14" y="22" font-size="14" font-weight="700" fill="#24292f">'
        f'Open Reports ({len(issues_sorted)})</text>'
    )
    parts.append(f'<line x1="0" y1="{header_height}" x2="{width}" y2="{header_height}" stroke="#d0d7de"/>')

    if not shown:
        parts.append(
            f'<text x="14" y="{header_height + 20}" font-size="12" fill="#57606a">'
            f'No open reports \U0001F389</text>'
        )
    else:
        for idx, issue in enumerate(shown):
            y = header_height + row_height * idx + 16
            title = truncate(escape_xml(issue["title"]))
            opened = format_date(issue["created_at"])
            age = days_open(issue["created_at"])
            row_fill = "#f6f8fa" if idx % 2 == 0 else "#ffffff"
            parts.append(f'<rect x="0" y="{header_height + row_height * idx}" width="{width}" height="{row_height}" fill="{row_fill}"/>')
            parts.append(f'<text x="14" y="{y}" font-size="12" fill="#24292f">{title}</text>')
            parts.append(f'<text x="{width - 14}" y="{y}" font-size="11" fill="#57606a" text-anchor="end">{opened} \u00b7 {age}d</text>')

    if footer_height:
        remaining = len(issues_sorted) - MAX_ROWS
        y = header_height + row_height * len(shown) + 16
        parts.append(
            f'<text x="14" y="{y}" font-size="11" fill="#57606a" font-style="italic">'
            f'+ {remaining} more open\u2026</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    issues = fetch_open_issues(REPO)
    svg = build_svg(issues)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {OUTPUT_PATH} with {len(issues)} open issue(s).")


if __name__ == "__main__":
    main()
