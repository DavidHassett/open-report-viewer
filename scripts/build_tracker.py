#!/usr/bin/env python3
"""
Builds a small PNG "open reports" tracker image from the currently open
GitHub Issues in this repository, and writes it to assets/tracker.png.

Uses Pillow for rendering (installed as a step in the GitHub Actions
workflow) since PNG has universal support in email clients like Outlook,
unlike SVG.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont

# --- Configuration -----------------------------------------------------

REPO = "DavidHassett/open-report-viewer"
OUTPUT_PATH = "assets/tracker.png"
MAX_ROWS = 15  # cap how many rows are drawn; extra reports are summarised

WIDTH = 480
ROW_HEIGHT = 26
HEADER_HEIGHT = 40
PADDING = 14

COLOR_BG = (255, 255, 255)
COLOR_BORDER = (208, 215, 222)
COLOR_HEADER_TEXT = (36, 41, 47)
COLOR_ROW_TEXT = (36, 41, 47)
COLOR_MUTED_TEXT = (87, 96, 105)
COLOR_ROW_ALT = (246, 248, 250)

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


def truncate(draw, text: str, font, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + "\u2026", font=font) > max_width:
        text = text[:-1]
    return text + "\u2026"


def load_font(size: int, bold: bool = False):
    candidates = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        if bold
        else ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


# --- Build PNG ------------------------------------------------------------

def build_image(issues):
    # Oldest-first, so the longest-outstanding reports surface at the top
    issues_sorted = sorted(issues, key=lambda i: i["created_at"])
    shown = issues_sorted[:MAX_ROWS]
    remaining = len(issues_sorted) - len(shown)

    footer_height = 24 if remaining > 0 else 0
    height = HEADER_HEIGHT + ROW_HEIGHT * max(len(shown), 1) + footer_height + 10

    img = Image.new("RGB", (WIDTH, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    header_font = load_font(15, bold=True)
    row_font = load_font(13)
    meta_font = load_font(11)

    # Border
    draw.rectangle([0, 0, WIDTH - 1, height - 1], outline=COLOR_BORDER)

    # Header
    draw.text((PADDING, 12), f"Open Reports ({len(issues_sorted)})", font=header_font, fill=COLOR_HEADER_TEXT)
    draw.line([(0, HEADER_HEIGHT), (WIDTH, HEADER_HEIGHT)], fill=COLOR_BORDER)

    if not shown:
        draw.text((PADDING, HEADER_HEIGHT + 10), "No open reports", font=row_font, fill=COLOR_MUTED_TEXT)
    else:
        for idx, issue in enumerate(shown):
            y_top = HEADER_HEIGHT + ROW_HEIGHT * idx
            if idx % 2 == 0:
                draw.rectangle([0, y_top, WIDTH, y_top + ROW_HEIGHT], fill=COLOR_ROW_ALT)

            opened = format_date(issue["created_at"])
            age = days_open(issue["created_at"])
            meta_text = f"{opened} \u00b7 {age}d"
            meta_width = draw.textlength(meta_text, font=meta_font)

            title = truncate(draw, issue["title"], row_font, WIDTH - PADDING * 2 - meta_width - 12)
            text_y = y_top + (ROW_HEIGHT - 14) // 2

            draw.text((PADDING, text_y), title, font=row_font, fill=COLOR_ROW_TEXT)
            draw.text((WIDTH - PADDING - meta_width, text_y + 1), meta_text, font=meta_font, fill=COLOR_MUTED_TEXT)

    if footer_height:
        y_top = HEADER_HEIGHT + ROW_HEIGHT * len(shown)
        draw.text(
            (PADDING, y_top + 5),
            f"+ {remaining} more open\u2026",
            font=meta_font,
            fill=COLOR_MUTED_TEXT,
        )

    return img


def main():
    issues = fetch_open_issues(REPO)
    img = build_image(issues)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    img.save(OUTPUT_PATH, format="PNG")
    print(f"Wrote {OUTPUT_PATH} with {len(issues)} open issue(s).")


if __name__ == "__main__":
    main()
