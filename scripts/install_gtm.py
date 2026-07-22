#!/usr/bin/env python3
"""Install a Google Tag Manager container across static HTML pages.

Usage:
  python3 scripts/install_gtm.py GTM-XXXXXXX
  python3 scripts/install_gtm.py GTM-XXXXXXX --check

The script is idempotent. It inserts:
- the standard GTM head script immediately after <head>
- the GTM noscript iframe immediately after <body...>

When --check is used, it reports which HTML files are missing GTM without
changing anything.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {".git", "node_modules"}
HEAD_MARKER = "<!-- Google Tag Manager -->"
BODY_MARKER = "<!-- Google Tag Manager (noscript) -->"


def iter_html_files(root: Path):
    for path in root.rglob("*.html"):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        yield path


def build_head_snippet(gtm_id: str) -> str:
    return (
        f"{HEAD_MARKER}\n"
        "<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':\n"
        "new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],\n"
        "j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=\n"
        f"'https://www.googletagmanager.com/gtm.js?id={gtm_id}'+dl;f.parentNode.insertBefore(j,f);\n"
        f"}})(window,document,'script','dataLayer','{gtm_id}');</script>\n"
        "<!-- End Google Tag Manager -->"
    )


def build_body_snippet(gtm_id: str) -> str:
    return (
        f"{BODY_MARKER}\n"
        f'<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={gtm_id}"\n'
        'height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>\n'
        "<!-- End Google Tag Manager (noscript) -->"
    )


def install_gtm(html: str, gtm_id: str) -> tuple[str, bool]:
    changed = False

    if HEAD_MARKER not in html:
        html, count = re.subn(r"(<head[^>]*>)", r"\1\n" + build_head_snippet(gtm_id), html, count=1, flags=re.IGNORECASE)
        changed = changed or count > 0

    if BODY_MARKER not in html:
        html, count = re.subn(r"(<body[^>]*>)", r"\1\n" + build_body_snippet(gtm_id), html, count=1, flags=re.IGNORECASE)
        changed = changed or count > 0

    return html, changed


def has_gtm(html: str) -> bool:
    return HEAD_MARKER in html and BODY_MARKER in html


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("gtm_id", help="Google Tag Manager container ID, like GTM-ABC1234")
    parser.add_argument("--check", action="store_true", help="Only report whether HTML files already contain GTM")
    args = parser.parse_args()

    html_files = list(iter_html_files(ROOT))
    missing = []
    changed_files = []

    for path in html_files:
        original = path.read_text(encoding="utf-8")
        if args.check:
            if not has_gtm(original):
                missing.append(path)
            continue

        updated, changed = install_gtm(original, args.gtm_id)
        if changed:
            path.write_text(updated, encoding="utf-8")
            changed_files.append(path)

    if args.check:
        if missing:
            print("Missing GTM:")
            for path in missing:
                print(path.relative_to(ROOT))
            return 1
        print(f"All {len(html_files)} HTML files already include GTM markers.")
        return 0

    print(f"Updated {len(changed_files)} HTML files with {args.gtm_id}.")
    for path in changed_files[:20]:
        print(path.relative_to(ROOT))
    if len(changed_files) > 20:
        print(f"... and {len(changed_files) - 20} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
