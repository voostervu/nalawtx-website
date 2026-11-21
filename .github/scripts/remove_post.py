#!/usr/bin/env python3
"""Take a blog post down cleanly.

Usage: python .github/scripts/remove_post.py <slug>

Deletes blog/<slug>.html and removes every reference to it: the blog index
card, "Keep reading" and "From our blog" cards, inline links (the link text is
kept), the sitemap entry, the llms.txt line and the audit notes file.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main():
    slug = sys.argv[1].strip().removesuffix(".html") if len(sys.argv) > 1 else ""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug) or slug == "index":
        sys.exit(f"Not a valid post slug: {slug!r}")
    post = ROOT / "blog" / f"{slug}.html"
    if not post.exists():
        sys.exit(f"No such post: blog/{slug}.html")

    post.unlink()
    print(f"deleted blog/{slug}.html")
    audit = ROOT / ".github" / "audits" / f"{slug}.md"
    if audit.exists():
        audit.unlink()
        print(f"deleted .github/audits/{slug}.md")

    link = rf'<a\b[^>]*href="[^"]*\b{re.escape(slug)}(?:\.html)?"[^>]*>(.*?)</a>'
    for page in sorted(ROOT.rglob("*.html")):
        if ".git" in page.parts:
            continue
        text = page.read_text(encoding="utf-8")
        if slug not in text:
            continue
        # A link that fills its own lines is a card: remove it whole.
        new = re.sub(rf"(?m)^[ \t]*{link}[ \t]*\n", "", text, flags=re.S)
        # Any other link sits inside a sentence: keep the words, drop the link.
        new = re.sub(link, lambda m: m.group(1), new, flags=re.S)
        if new != text:
            page.write_text(new, encoding="utf-8")
            print(f"removed links: {page.relative_to(ROOT)}")

    sitemap = ROOT / "sitemap.xml"
    text = sitemap.read_text(encoding="utf-8")
    new = re.sub(
        rf"[ \t]*<url>\s*<loc>[^<]*/blog/{re.escape(slug)}(?:\.html)?</loc>.*?</url>\n?", "", text, flags=re.S
    )
    if new != text:
        sitemap.write_text(new, encoding="utf-8")
        print("removed from sitemap.xml")

    llms = ROOT / "llms.txt"
    if llms.exists():
        lines = llms.read_text(encoding="utf-8").split("\n")
        kept = [l for l in lines if not re.search(rf"/blog/{re.escape(slug)}(?:\.html)?\)", l)]
        if len(kept) != len(lines):
            llms.write_text("\n".join(kept), encoding="utf-8")
            print("removed from llms.txt")


if __name__ == "__main__":
    main()
