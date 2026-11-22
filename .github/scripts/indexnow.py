#!/usr/bin/env python3
"""Tell Bing (and other IndexNow search engines) about new or changed pages.

Usage: python .github/scripts/indexnow.py            # submit every URL in sitemap.xml
       python .github/scripts/indexnow.py <url> ...  # submit specific URLs

ChatGPT and Copilot draw on Bing's index, so this gets new posts in front of them
sooner. The key below is public by design: it matches the key file at the site root.
"""
import json
import pathlib
import re
import sys
import urllib.request

HOST = "nalawtx.com"
KEY = "ff14c766c093599c747b6ad069948ad8"
ROOT = pathlib.Path(__file__).resolve().parents[2]


def main():
    urls = [a for a in sys.argv[1:] if a.startswith("https://")]
    if not urls:
        urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", (ROOT / "sitemap.xml").read_text(encoding="utf-8"))
    body = json.dumps({
        "host": HOST,
        "key": KEY,
        "keyLocation": f"https://{HOST}/{KEY}.txt",
        "urlList": urls,
    }).encode()
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"[indexnow] submitted {len(urls)} URL(s): HTTP {resp.status}")
    except Exception as exc:  # never fail a publish over this
        print(f"[indexnow] could not submit: {exc}")


if __name__ == "__main__":
    main()
