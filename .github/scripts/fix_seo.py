#!/usr/bin/env python3
"""Keep every blog post's search tags and the sitemap in line with its real URL.

For each blog/<slug>.html this makes sure that:
  - the canonical tag points to https://nalawtx.com/blog/<slug>
  - the Article schema "mainEntityOfPage" points to the same URL
  - an og:url tag exists and points to the same URL
  - the post is listed in sitemap.xml
  - the post is listed in llms.txt (the file AI search engines read)
  - the post names an attorney as its author, in the schema and in a visible
    byline linked to the attorney's bio
  - internal audit notes (REVIEW markers and audit comments) are moved out of
    the public page into .github/audits/<slug>.md

Safe to run any number of times. Run with --dry-run to preview.
"""
import datetime
import html
import pathlib
import re
import sys

SITE = "https://nalawtx.com"
ROOT = pathlib.Path(__file__).resolve().parents[2]
BLOG = ROOT / "blog"
SITEMAP = ROOT / "sitemap.xml"
LLMS = ROOT / "llms.txt"
AUDITS = ROOT / ".github" / "audits"
DRY = "--dry-run" in sys.argv

# Attorney named as author on every post.
AUTHOR_NAME = "Vu Nguyen"
AUTHOR_TITLE = "Founder & Managing Partner"
AUTHOR_SLUG = "vu-nguyen"
AUTHOR_SCHEMA = (
    '"author": {\n'
    '    "@type": "Person",\n'
    f'    "name": "{AUTHOR_NAME}",\n'
    f'    "jobTitle": "{AUTHOR_TITLE}",\n'
    f'    "url": "{SITE}/attorneys/{AUTHOR_SLUG}",\n'
    '    "worksFor": {\n'
    '      "@type": "LegalService",\n'
    '      "name": "Nguyen & Associates Injury Law Firm",\n'
    f'      "url": "{SITE}"\n'
    "    }\n"
    "  }"
)
BYLINE = (
    '    <p class="post-byline" style="margin-top: 0.5rem; font-size: 0.95rem; color: var(--muted);">'
    f'By <a href="../attorneys/{AUTHOR_SLUG}.html" style="color: var(--body); border-bottom: 1px dotted currentColor;">'
    f"{AUTHOR_NAME}</a>, {html.escape(AUTHOR_TITLE)}</p>\n"
)


def add_author(text):
    """Name the attorney as author in the Article schema and in a visible byline."""
    new = re.sub(
        r'"author"\s*:\s*\{\s*"@type"\s*:\s*"Organization"[^{}]*\}',
        lambda m: AUTHOR_SCHEMA,
        text,
        count=1,
    )
    if 'class="post-byline"' not in new:
        new = re.sub(
            r'([ \t]*<p class="phead__lede">.*?</p>\n)',
            lambda m: m.group(1) + BYLINE,
            new,
            count=1,
            flags=re.S,
        )
    return new


NOTE = re.compile(r"<!--((?:(?!-->).)*?(?:REVIEW|AUDIT \(Phase)(?:(?!-->).)*?)-->", re.S)


def plain(fragment):
    fragment = re.sub(r"<[^>]*$", "", fragment)
    text = html.unescape(" ".join(re.sub(r"<[^>]+>", " ", fragment).split()))
    return text.replace(" .", ".").replace(" ,", ",").replace(" ?", "?")


def strip_notes(path, text):
    """Move internal audit notes out of the page and into .github/audits/."""
    inline, blocks = [], []
    for m in NOTE.finditer(text):
        body = m.group(1).strip()
        if body == "/REVIEW":
            continue
        if "AUDIT (Phase" in body:
            blocks.append(body)
        else:
            context = plain(NOTE.sub("", text[m.end():m.end() + 400]))[:140]
            inline.append((body.replace("\u26a0\ufe0f", "").strip(), context))
    if not inline and not blocks:
        return text
    new = re.sub(r"(?m)^[ \t]*" + NOTE.pattern + r"[ \t]*\n", "", text, flags=re.S)
    new = NOTE.sub("", new)
    new = re.sub(r"\A(<!doctype html>)\s*", lambda m: m.group(1) + "\n", new, flags=re.I)
    out = [f"# Audit notes: blog/{path.name}", "", "Moved out of the published page automatically.", ""]
    out.append("## Passages marked for review")
    out.append("")
    for note, context in inline:
        out.append(f"- {note}")
        if context:
            out.append(f"  - Text that follows: {context}")
    if not inline:
        out.append("None.")
    for block in blocks:
        out += ["", "## Audit", "", "```", block, "```"]
    print(f"moved {len(inline)} review note(s) and {len(blocks)} audit block(s): blog/{path.name}")
    if not DRY:
        AUDITS.mkdir(parents=True, exist_ok=True)
        (AUDITS / f"{path.stem}.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    return new


def fix_post(path):
    url = f"{SITE}/blog/{path.stem}"
    text = path.read_text(encoding="utf-8")
    new = add_author(strip_notes(path, text))

    canonical = f'<link rel="canonical" href="{url}">'
    if re.search(r'<link\s+rel="canonical"[^>]*>', new, re.I):
        new = re.sub(r'<link\s+rel="canonical"[^>]*>', lambda m: canonical, new, count=1, flags=re.I)
    else:
        new = re.sub(r"</head>", lambda m: canonical + "\n</head>", new, count=1, flags=re.I)

    # mainEntityOfPage as a plain string ...
    new = re.sub(
        r'("mainEntityOfPage"\s*:\s*)"[^"]*"',
        lambda m: f'{m.group(1)}"{url}"',
        new,
    )
    # ... or as a WebPage object with an @id
    new = re.sub(
        r'("mainEntityOfPage"\s*:\s*\{[^{}]*?"@id"\s*:\s*)"[^"]*"',
        lambda m: f'{m.group(1)}"{url}"',
        new,
        flags=re.S,
    )

    og = f'<meta property="og:url" content="{url}">'
    if re.search(r'<meta\s+property="og:url"[^>]*>', new, re.I):
        new = re.sub(r'<meta\s+property="og:url"[^>]*>', lambda m: og, new, count=1, flags=re.I)
    else:
        new = new.replace(canonical, canonical + "\n" + og, 1)

    if new != text:
        print(f"fixed tags: blog/{path.name}")
        if not DRY:
            path.write_text(new, encoding="utf-8")

    m = re.search(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})', new) or re.search(
        r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', new
    )
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", new, re.S)
    desc = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', new, re.I)
    return {
        "url": url,
        "date": m.group(1) if m else datetime.date.today().isoformat(),
        "title": plain(h1.group(1)) if h1 else path.stem,
        "desc": html.unescape(desc.group(1)).strip() if desc else "",
    }


def update_llms(posts):
    """List every post in llms.txt, inside its Blog section."""
    if not LLMS.exists():
        return
    lines = LLMS.read_text(encoding="utf-8").split("\n")
    text = "\n".join(lines)
    start = next((i for i, l in enumerate(lines) if l.startswith("## Blog")), None)
    if start is None:
        return
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    last = max((i for i in range(start, end) if lines[i].startswith("- [")), default=start)
    added = []
    for p in posts:
        if p["url"] + ")" in text or p["url"] + ".html)" in text:
            continue
        title = p["title"].replace("[", "(").replace("]", ")")
        added.append(f"- [{title}]({p['url']})" + (f": {p['desc']}" if p["desc"] else ""))
        print(f"added to llms.txt: {p['url']}")
    if added and not DRY:
        lines[last + 1:last + 1] = added
        LLMS.write_text("\n".join(lines), encoding="utf-8")


def main():
    posts = [fix_post(p) for p in sorted(BLOG.glob("*.html")) if p.name != "index.html"]

    sitemap = SITEMAP.read_text(encoding="utf-8")
    listed = set(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sitemap))
    entries = ""
    for p in posts:
        url, date = p["url"], p["date"]
        if url in listed or url + ".html" in listed:
            continue
        print(f"added to sitemap: {url}")
        entries += (
            "  <url>\n"
            f"    <loc>{url}</loc>\n"
            f"    <lastmod>{date}</lastmod>\n"
            "    <changefreq>monthly</changefreq>\n"
            "    <priority>0.7</priority>\n"
            "  </url>\n"
        )
    if entries:
        idx = sitemap.rindex("</urlset>")
        sitemap = sitemap[:idx].rstrip("\n") + "\n" + entries + "\n" + sitemap[idx:]
        if not DRY:
            SITEMAP.write_text(sitemap, encoding="utf-8")

    update_llms(posts)
    print(f"Checked {len(posts)} posts.")


if __name__ == "__main__":
    main()
