#!/usr/bin/env python3
"""
Post the newest blog article to the firm's Google Business Profile.

One post per run. Picks the most recent English post in blog/ (by its
article:published_time) that has not been posted yet, turns its headline
and opening paragraph into a Google post with a "Learn more" button that
links to the article, and records the slug in .github/gbp_posted.json so
it is never posted twice.

Only text that already passed the blog pipeline (compliance, sensitivity,
fact check) is used. Nothing new is written by AI here.

Environment:
    GBP_CLIENT_ID, GBP_CLIENT_SECRET, GBP_REFRESH_TOKEN   OAuth (see gbp_auth.py)
    GBP_ACCOUNT_ID, GBP_LOCATION_ID                       numeric IDs (see gbp_auth.py)
    GBP_IMAGE_URL     optional public photo URL to attach to every post
    DRY_RUN=1         print the post instead of publishing it

Usage:
    python .github/scripts/gbp_post.py [--dry-run] [--slug SLUG]
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rebuild_blog_index import extract_h1, extract_lede  # noqa: E402

SITE = "https://nalawtx.com"
ROOT = Path(__file__).resolve().parents[2]
BLOG = ROOT / "blog"
STATE = ROOT / ".github" / "gbp_posted.json"
MAX_SUMMARY = 1500  # Google's limit for a post's text
FOOTER = "Nguyen & Associates Injury Law Firm · Houston, Texas · Responsible attorney: Vu Nguyen"
# Google rejects posts that contain phone numbers.
PHONE = re.compile(r"\(?\b\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")


def published(doc: str) -> str:
    m = re.search(r'article:published_time"\s+content="([^"]+)"', doc)
    return m.group(1) if m else ""


def load_state() -> list:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return []


def pick_post(done: set, slug: str = ""):
    posts = []
    for path in BLOG.glob("*.html"):
        if path.name == "index.html":
            continue
        doc = path.read_text(encoding="utf-8")
        posts.append((published(doc), path.stem, doc))
    if slug:
        posts = [p for p in posts if p[1] == slug]
    posts = [p for p in posts if p[1] not in done and p[0]]
    if not posts:
        return None
    return max(posts)  # newest by published date


def build_summary(doc: str, slug: str) -> str:
    title = extract_h1(doc, slug.replace("-", " ").title())
    lede = PHONE.sub("", extract_lede(doc)).strip()
    room = MAX_SUMMARY - len(title) - len(FOOTER) - 6
    if len(lede) > room:
        lede = lede[: room - 3].rsplit(" ", 1)[0] + "..."
    return f"{title}\n\n{lede}\n\n{FOOTER}"


def access_token() -> str:
    data = urllib.parse.urlencode({
        "client_id": os.environ["GBP_CLIENT_ID"],
        "client_secret": os.environ["GBP_CLIENT_SECRET"],
        "refresh_token": os.environ["GBP_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=30) as r:
        return json.load(r)["access_token"]


def create_post(body: dict) -> dict:
    url = (
        "https://mybusiness.googleapis.com/v4/accounts/"
        f"{os.environ['GBP_ACCOUNT_ID']}/locations/{os.environ['GBP_LOCATION_ID']}/localPosts"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {access_token()}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        sys.exit(f"[gbp] Google rejected the post ({exc.code}): {exc.read().decode()[:800]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--slug", default="", help="post this article instead of the newest")
    args = ap.parse_args()
    dry = args.dry_run or os.environ.get("DRY_RUN", "") in ("1", "true", "yes")

    state = load_state()
    choice = pick_post({s["slug"] for s in state}, args.slug)
    if not choice:
        print("[gbp] Nothing new to post.")
        return 0
    date, slug, doc = choice

    body = {
        "languageCode": "en-US",
        "topicType": "STANDARD",
        "summary": build_summary(doc, slug),
        "callToAction": {"actionType": "LEARN_MORE", "url": f"{SITE}/blog/{slug}"},
    }
    image = os.environ.get("GBP_IMAGE_URL", "").strip()
    if image:
        body["media"] = [{"mediaFormat": "PHOTO", "sourceUrl": image}]

    print(f"[gbp] Article: blog/{slug}.html (published {date})")
    print(json.dumps(body, indent=2, ensure_ascii=False))
    if dry:
        print("[gbp] Dry run: nothing was posted.")
        return 0

    result = create_post(body)
    state.append({"slug": slug, "post": result.get("name", ""), "url": result.get("searchUrl", "")})
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"[gbp] Posted: {result.get('searchUrl') or result.get('name')}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"posted={slug}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
