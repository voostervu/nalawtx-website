#!/usr/bin/env python3
"""
Rebuild the card grid in blog/index.html from the post files on disk.

Safe to re-run. Only the contents of <div class="areas"> ... </div> are
replaced; everything else in index.html is left byte-for-byte alone.

Dates and eyebrows already present in index.html are preserved, so
re-running never rewrites history for posts that are already correct.

Usage:
    python .github/scripts/rebuild_blog_index.py [--dry-run]
"""

import argparse
import html
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BLOG_DIR = REPO_ROOT / "blog"
INDEX_PATH = BLOG_DIR / "index.html"

CHROME_TAGS = ("nav", "header", "footer", "script", "style", "aside")

MONTHS = (
    "January February March April May June July "
    "August September October November December"
).split()


# --------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------

def strip_chrome(doc: str) -> str:
    out = doc
    for tag in CHROME_TAGS:
        out = re.sub(
            rf"<{tag}\b[^>]*>.*?</{tag}>", " ", out,
            flags=re.IGNORECASE | re.DOTALL,
        )
    return out


def clean(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", "", fragment)
    text = html.unescape(text)
    return " ".join(text.split())


def extract_h1(doc: str, fallback: str) -> str:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.IGNORECASE | re.DOTALL)
    if m:
        text = clean(m.group(1))
        if text:
            return text
    return fallback


def extract_lede(doc: str) -> str:
    """First real prose paragraph of the article body."""
    body = strip_chrome(doc)

    h1 = re.search(r"</h1>", body, re.IGNORECASE)
    region = body[h1.end():] if h1 else body

    for para in re.findall(r"<p[^>]*>(.*?)</p>", region, re.IGNORECASE | re.DOTALL):
        text = clean(para)
        if len(text) < 50:
            continue
        # Real prose has sentence punctuation; link rows and label
        # strips do not.
        if not any(mark in text for mark in (".", "?", "!")):
            continue
        return text
    return ""


def extract_eyebrow(doc: str) -> str:
    patterns = (
        r'<span[^>]*class="[^"]*t-eyebrow[^"]*"[^>]*>(.*?)</span>',
        r'<p[^>]*class="[^"]*eyebrow[^"]*"[^>]*>(.*?)</p>',
    )
    body = strip_chrome(doc)
    for pattern in patterns:
        m = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
        if m:
            text = clean(m.group(1))
            if text:
                return text
    return ""


def extract_date(doc: str, path: Path) -> str:
    """Human date string. Tries the post's own markup, then the
    compliance audit stamp the pipeline embeds, then file mtime."""
    m = re.search(r'<time[^>]*datetime="(\d{4})-(\d{2})-(\d{2})', doc, re.IGNORECASE)
    if not m:
        m = re.search(r"Audit timestamp:\s*(\d{4})-(\d{2})-(\d{2})", doc)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{MONTHS[mo - 1]} {d}, {y}"

    stamp = datetime.fromtimestamp(path.stat().st_mtime)
    return f"{MONTHS[stamp.month - 1]} {stamp.day}, {stamp.year}"


def truncate(text: str, limit: int = 160) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 5].rsplit(" ", 1)[0] + "..."


# --------------------------------------------------------------------------
# existing index -> preserve what is already right
# --------------------------------------------------------------------------

def harvest_existing(index_html: str) -> dict:
    """slug -> {eyebrow, date} from the cards already in index.html."""
    known = {}
    card_re = re.compile(
        r'<a class="area"\s+href="([^"]+?)\.html".*?'
        r'class="t-eyebrow[^"]*"[^>]*>(.*?)</span>.*?'
        r'margin-top: var\(--s-sm\);">([^<]*?)</span>',
        re.IGNORECASE | re.DOTALL,
    )
    for slug, eyebrow, date in card_re.findall(index_html):
        known[slug] = {"eyebrow": clean(eyebrow), "date": clean(date)}
    return known


def sort_key(entry: dict):
    try:
        return datetime.strptime(entry["date"], "%B %d, %Y")
    except ValueError:
        return datetime.min


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

CARD = '''    <a class="area" href="{slug}.html" style="min-height: 280px;">
      <span class="t-eyebrow t-eyebrow--gold" style="font-size:0.72rem;">{eyebrow}</span>
      <h2 style="margin-top: var(--s-sm);">{h1}</h2>
      <p style="font-size: 0.94rem; flex-grow: 1;">{lede}</p>
      <span style="font-size: 0.82rem; color: var(--muted); margin-top: var(--s-sm);">{date}</span>
      <span class="area__arrow"><svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.5" fill="none"><path d="M7 17L17 7M9 7h8v8"/></svg></span>
    </a>
'''


def build(dry_run: bool = False) -> int:
    if not INDEX_PATH.exists():
        print(f"ERROR: {INDEX_PATH} not found", file=sys.stderr)
        return 1

    index_html = INDEX_PATH.read_text(encoding="utf-8")
    known = harvest_existing(index_html)
    print(f"Found {len(known)} existing cards to preserve metadata from.\n")

    entries = []
    for path in sorted(BLOG_DIR.glob("*.html")):
        if path.name == "index.html":
            continue

        slug = path.stem
        doc = path.read_text(encoding="utf-8")
        prior = known.get(slug, {})

        lede = extract_lede(doc)
        if not lede:
            print(f"  !  {slug}: no usable lede found, leaving excerpt empty")

        entries.append({
            "slug": slug,
            "h1": extract_h1(doc, fallback=slug.replace("-", " ").title()),
            "lede": truncate(lede),
            # prefer what the post itself declares; fall back to the
            # existing card so hand-tuned eyebrows survive
            "eyebrow": extract_eyebrow(doc) or prior.get("eyebrow") or "Texas law",
            # prefer the existing card's date: it is the published date
            # of record and must not drift
            "date": prior.get("date") or extract_date(doc, path),
        })

    entries.sort(key=sort_key, reverse=True)

    for e in entries:
        status = "carried" if e["slug"] in known else "NEW    "
        print(f"  {status}  {e['date']:<20}  {e['h1'][:58]}")

    grid = "".join(
        CARD.format(
            slug=e["slug"],
            eyebrow=html.escape(e["eyebrow"]),
            h1=html.escape(e["h1"]),
            lede=html.escape(e["lede"]),
            date=html.escape(e["date"]),
        )
        for e in entries
    )

    open_marker = '<div class="areas">'
    start = index_html.find(open_marker)
    if start == -1:
        print("ERROR: could not find the .areas container", file=sys.stderr)
        return 1
    content_start = start + len(open_marker)

    end = index_html.find("</div>", content_start)
    if end == -1:
        print("ERROR: unterminated .areas container", file=sys.stderr)
        return 1

    new_html = index_html[:content_start] + "\n" + grid + "    " + index_html[end:]

    print(f"\n{len(entries)} cards total.")

    if dry_run:
        print("Dry run: index.html not written.")
        return 0

    INDEX_PATH.write_text(new_html, encoding="utf-8")
    print(f"Wrote {INDEX_PATH}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.exit(build(dry_run=args.dry_run))
