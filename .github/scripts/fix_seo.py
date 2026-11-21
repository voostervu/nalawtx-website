#!/usr/bin/env python3
"""Keep every blog post's search tags and the sitemap in line with its real URL.

For each blog/<slug>.html this makes sure that:
  - the canonical tag points to https://nalawtx.com/blog/<slug>
  - the Article schema "mainEntityOfPage" points to the same URL
  - an og:url tag exists and points to the same URL
  - the post is listed in sitemap.xml

Safe to run any number of times. Run with --dry-run to preview.
"""
import datetime
import pathlib
import re
import sys

SITE = "https://nalawtx.com"
ROOT = pathlib.Path(__file__).resolve().parents[2]
BLOG = ROOT / "blog"
SITEMAP = ROOT / "sitemap.xml"
DRY = "--dry-run" in sys.argv


def fix_post(path):
    url = f"{SITE}/blog/{path.stem}"
    text = path.read_text(encoding="utf-8")
    new = text

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
    return url, (m.group(1) if m else datetime.date.today().isoformat())


def main():
    posts = [fix_post(p) for p in sorted(BLOG.glob("*.html")) if p.name != "index.html"]

    sitemap = SITEMAP.read_text(encoding="utf-8")
    listed = set(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sitemap))
    entries = ""
    for url, date in posts:
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

    print(f"Checked {len(posts)} posts.")


if __name__ == "__main__":
    main()
