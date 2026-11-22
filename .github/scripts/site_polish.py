#!/usr/bin/env python3
"""Small, repeatable clean-ups across the site. Safe to run any number of times.

1. Links Texas statute citations to the official text on statutes.capitol.texas.gov
   (first mention of each section per page; blog posts, guides and practice pages).
2. Uses clean addresses (no .html) inside schema, to match the canonical tags.
3. Shortens page titles that run past 65 characters by trimming the brand suffix.
4. Shows a "Updated <date>" note in each blog post's byline.
"""
import datetime
import html
import pathlib
import re

SITE = "https://nalawtx.com"
ROOT = pathlib.Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", ".github", "node_modules"}

CODES = {
    "civil practice & remedies": "CP", "civil practice and remedies": "CP", "transportation": "TN",
    "insurance": "IN", "labor": "LA", "alcoholic beverage": "AL", "health & safety": "HS",
    "health and safety": "HS", "human resources": "HR", "business & commerce": "BC",
    "business and commerce": "BC", "penal": "PE", "government": "GV", "occupations": "OC",
    "property": "PR", "family": "FA",
}
CITE = re.compile(
    r"(?:Texas\s+|Tex\.\s+)?(Civil Practice (?:&amp;|&|and) Remedies|Transportation|Insurance|Labor|"
    r"Alcoholic Beverage|Health (?:&amp;|&|and) Safety|Human Resources|Business (?:&amp;|&|and) Commerce|"
    r"Penal|Government|Occupations|Property|Family)\s+Code\s+(?:§+|Section|Chapter|Ch\.)\s*(\d+(?:\.\d+)?)"
)
NO_LINK = ("a", "script", "style", "h1", "h2", "h3", "title", "head", "nav", "footer", "button")


def statute_url(code, number):
    abbr = CODES[html.unescape(code).lower()]
    chapter = number.split(".")[0]
    anchor = f"#{number}" if "." in number else ""
    return f"https://statutes.capitol.texas.gov/Docs/{abbr}/htm/{abbr}.{chapter}.htm{anchor}"


def link_statutes(text):
    seen = set(re.findall(r'href="(https://statutes\.capitol\.texas\.gov/[^"]+)"', text))
    parts = re.split(r"(<[^>]+>)", text)
    depth = {t: 0 for t in NO_LINK}
    out = []
    for part in parts:
        if part.startswith("<"):
            m = re.match(r"<(/?)([a-zA-Z0-9]+)", part)
            if m and m.group(2).lower() in depth and not part.endswith("/>"):
                depth[m.group(2).lower()] += -1 if m.group(1) else 1
            out.append(part)
            continue
        if any(v > 0 for v in depth.values()):
            out.append(part)
            continue

        def repl(m):
            url = statute_url(m.group(1), m.group(2))
            if url in seen:
                return m.group(0)
            seen.add(url)
            return f'<a href="{url}" target="_blank" rel="noopener">{m.group(0)}</a>'

        out.append(CITE.sub(repl, part))
    return "".join(out)


def clean_schema_urls(text):
    def fix_block(m):
        block = re.sub(rf'{re.escape(SITE)}/((?:[^"\s]*/)?)index\.html', rf"{SITE}/\1", m.group(0))
        return re.sub(rf'({re.escape(SITE)}/[^"\s]*?)\.html(?=["#?])', r"\1", block)

    return re.sub(r'<script type="application/ld\+json">.*?</script>', fix_block, text, flags=re.S)


def shorten_title(text):
    m = re.search(r"<title>([^<]*)</title>", text)
    if not m or len(html.unescape(m.group(1))) <= 65 or "|" not in m.group(1):
        return text
    head = m.group(1).rsplit("|", 1)[0].strip()
    brand = " | Nguyen &amp; Associates"
    new = head + brand if len(html.unescape(head + brand)) <= 65 else head
    return text.replace(m.group(0), f"<title>{new}</title>", 1)


def add_updated(text):
    if 'class="post-byline"' not in text or 'class="post-updated"' in text:
        return text
    m = re.search(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})', text) or re.search(
        r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', text
    )
    if not m:
        return text
    d = datetime.date.fromisoformat(m.group(1))
    note = f' <span class="post-updated">&middot; Updated {d.strftime("%B")} {d.day}, {d.year}</span>'
    return re.sub(r'(<p class="post-byline"[^>]*>.*?)(</p>)', lambda x: x.group(1) + note + x.group(2), text, count=1, flags=re.S)


def main():
    counts = {"statute links": 0, "schema addresses": 0, "titles": 0, "updated notes": 0}
    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        if SKIP_DIRS & set(rel.parts):
            continue
        text = path.read_text(encoding="utf-8")
        new = text
        if rel.parts[0] in ("blog", "guides", "practice") and rel.name != "index.html":
            step = link_statutes(new)
            counts["statute links"] += step != new
            new = step
        for name, fn in (("schema addresses", clean_schema_urls), ("titles", shorten_title)):
            step = fn(new)
            counts[name] += step != new
            new = step
        if rel.parts[0] == "blog":
            step = add_updated(new)
            counts["updated notes"] += step != new
            new = step
        if new != text:
            path.write_text(new, encoding="utf-8")
    print("Pages changed - " + ", ".join(f"{k}: {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
