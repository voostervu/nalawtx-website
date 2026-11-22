#!/usr/bin/env python3
"""Build llms-full.txt: the full text of the firm's guides, practice pages and blog
posts in one plain-text file, for AI search engines that read it. Safe to re-run."""
import html
import pathlib
import re

SITE = "https://nalawtx.com"
ROOT = pathlib.Path(__file__).resolve().parents[2]
SECTIONS = [("Guides", "guides"), ("Practice areas", "practice"), ("Blog", "blog")]
BLOCK = re.compile(r"<(h2|h3|p|li)\b[^>]*>(.*?)</\1>", re.S | re.I)


def plain(fragment):
    text = html.unescape(" ".join(re.sub(r"<[^>]+>", " ", fragment).split()))
    return text.replace(" .", ".").replace(" ,", ",").replace(" ?", "?")


def page_text(path):
    text = path.read_text(encoding="utf-8")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    start = text.find("</h1>")
    end = text.find("<!-- related-links -->")
    if end < 0:
        end = text.find('<section class="cta-band">')
    body = text[start if start >= 0 else 0:end if end > 0 else len(text)]
    body = re.sub(r"<(script|style|nav|footer|form)\b.*?</\1>", " ", body, flags=re.S | re.I)
    lines = []
    for tag, inner in BLOCK.findall(body):
        t = plain(inner)
        if len(t) < 3:
            continue
        tag = tag.lower()
        lines.append(f"\n### {t}" if tag == "h2" else f"\n#### {t}" if tag == "h3" else f"- {t}" if tag == "li" else t)
    return (plain(h1.group(1)) if h1 else path.stem), "\n".join(lines).strip()


def main():
    out = [
        "# Nguyen & Associates Injury Law Firm: full text",
        "",
        "> Houston, Texas personal injury law firm. This file holds the full text of the firm's",
        "> guides, practice-area pages and blog posts. General information, not legal advice.",
        "> Phone: (713) 842-9442. Site: https://nalawtx.com/",
    ]
    count = 0
    for title, folder in SECTIONS:
        out += ["", f"# {title}"]
        for path in sorted((ROOT / folder).glob("*.html")):
            if path.name == "index.html":
                continue
            name, body = page_text(path)
            if len(body) < 400:
                continue
            out += ["", f"## {name}", f"Source: {SITE}/{folder}/{path.stem}", "", body]
            count += 1
    (ROOT / "llms-full.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"llms-full.txt: {count} pages")


if __name__ == "__main__":
    main()
