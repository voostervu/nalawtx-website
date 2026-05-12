"""
Shared utilities for the blog agent.

Provides:
- slugify()              — URL-safe kebab-case from a title
- read_time()            — minute estimate from HTML body
- extract_meta()         — pull title, description, eyebrow from generated HTML
- update_blog_index()    — regenerate /blog/index.html to include new post
"""

import re
from pathlib import Path
from html.parser import HTMLParser


def slugify(text: str, max_length: int = 60) -> str:
    """Turn a title into a URL-safe kebab-case slug.

    Examples:
        "What to Do After a Texas Car Wreck" -> "what-to-do-after-a-texas-car-wreck"
        "Houston's Top 5 Intersections!"     -> "houstons-top-5-intersections"
    """
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)        # drop punctuation
    s = re.sub(r"[-\s]+", "-", s)          # whitespace to dash
    s = s.strip("-")
    if len(s) > max_length:
        # Trim at the last whole word boundary
        s = s[:max_length].rsplit("-", 1)[0]
    return s


def read_time(html: str) -> int:
    """Estimate read time in minutes from rendered HTML body.

    Strips tags, counts words, divides by 225. Floor at 3 min.
    """
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    word_count = len(text.split())
    minutes = max(3, round(word_count / 225))
    return minutes


class _MetaExtractor(HTMLParser):
    """Pull <title>, description, eyebrow, h1 from generated HTML."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.canonical = ""
        self.eyebrow_text = ""
        self.h1 = ""
        self.lede = ""

        self._in_title = False
        self._in_eyebrow = False
        self._in_h1 = False
        self._in_lede = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            if attrs_dict.get("name") == "description":
                self.description = attrs_dict.get("content", "")
        elif tag == "link":
            if attrs_dict.get("rel") == "canonical":
                self.canonical = attrs_dict.get("href", "")
        elif tag == "span" and "t-eyebrow" in attrs_dict.get("class", ""):
            self._in_eyebrow = True
        elif tag == "h1":
            self._in_h1 = True
        elif tag == "p" and "phead__lede" in attrs_dict.get("class", ""):
            self._in_lede = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "span":
            self._in_eyebrow = False
        elif tag == "h1":
            self._in_h1 = False
        elif tag == "p":
            self._in_lede = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._in_eyebrow and not self.eyebrow_text:
            self.eyebrow_text += data
        elif self._in_h1:
            self.h1 += data
        elif self._in_lede:
            self.lede += data


def extract_meta(html: str) -> dict:
    """Pull post metadata from generated HTML for the blog index card."""
    parser = _MetaExtractor()
    parser.feed(html)
    return {
        "title": parser.title.strip(),
        "description": parser.description.strip(),
        "canonical": parser.canonical.strip(),
        "eyebrow": parser.eyebrow_text.strip(),
        "h1": parser.h1.strip(),
        "lede": parser.lede.strip(),
    }


def update_blog_index(
    repo_root: Path,
    new_slug: str,
    h1: str,
    lede: str,
    eyebrow: str,
    publish_date_human: str,  # "April 12, 2026"
):
    """
    Insert a new card at the top of /blog/index.html's .areas grid.

    Idempotent: if a card with the same slug already exists, this is a no-op.
    """
    index_path = repo_root / "blog" / "index.html"
    html = index_path.read_text()

    # Idempotency check
    if f'href="{new_slug}.html"' in html:
        return

    # Build the new card. Truncate lede to ~155 chars for the excerpt.
    excerpt = lede if len(lede) <= 160 else (lede[:155].rsplit(" ", 1)[0] + "...")

    card = f'''    <a class="area" href="{new_slug}.html" style="min-height: 280px;">
      <span class="t-eyebrow t-eyebrow--gold" style="font-size:0.72rem;">{eyebrow}</span>
      <h2 style="margin-top: var(--s-sm);">{h1}</h2>
      <p style="font-size: 0.94rem; flex-grow: 1;">{excerpt}</p>
      <span style="font-size: 0.82rem; color: var(--muted); margin-top: var(--s-sm);">{publish_date_human}</span>
      <span class="area__arrow"><svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="1.5" fill="none"><path d="M7 17L17 7M9 7h8v8"/></svg></span>
    </a>
'''

    # Insert immediately after the opening <div class="areas"> tag
    marker = '<div class="areas">'
    insert_pos = html.find(marker)
    if insert_pos == -1:
        raise ValueError("Could not find '.areas' container in blog/index.html")
    insert_pos += len(marker) + 1  # past the newline after the marker

    new_html = html[:insert_pos] + card + html[insert_pos:]
    index_path.write_text(new_html)


def format_human_date(iso_date: str) -> str:
    """Convert '2026-05-11' to 'May 11, 2026'."""
    from datetime import datetime
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%B %-d, %Y")
