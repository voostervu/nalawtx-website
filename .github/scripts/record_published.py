#!/usr/bin/env python3
"""Add a newly published post to the "Published Index" tab of the blog sheet.

Usage: python .github/scripts/record_published.py <slug> [topic]
       python .github/scripts/record_published.py <slug> --remove

The Writer reads that tab to link to older posts and to avoid repeating or
contradicting them. Skips the post if its slug is already listed.
Run with --print to show the row without touching the sheet, or --remove to
take a post's row out of the tab (used when a post is taken down).
"""
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
STATUTE = re.compile(
    r"(?:Tex(?:as|\.)\s+)?(?:Civil Practice (?:&|and) Remedies|Transportation|Insurance|Labor|"
    r"Alcoholic Beverage|Health (?:&|and) Safety|Human Resources|Business (?:&|and) Commerce|"
    r"Penal|Government|Occupations|Property|Family)\s+Code\s+(?:§+|Section|Chapter|Ch\.)\s*[\d.]+[A-Za-z]?"
    r"(?:\([a-z0-9]+\))*|49\s+C\.F\.R\.\s+(?:Part|§)\s*[\d.]+",
    re.I,
)


def plain(fragment):
    text = html.unescape(" ".join(re.sub(r"<[^>]+>", " ", fragment).split()))
    return text.replace(" .", ".").replace(" ,", ",").replace(" ?", "?")


def describe(slug):
    """Return the Published Index row for a post, without the keyword."""
    text = (ROOT / "blog" / f"{slug}.html").read_text(encoding="utf-8")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    desc = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', text, re.I)
    date = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', text)
    start = text.find("<h1")
    body = re.sub(r"<(script|style|footer|nav)\b.*?</\1>", " ", text[max(start, 0):], flags=re.S | re.I)
    cites = []
    for m in STATUTE.finditer(plain(body)):
        cite = re.sub(r"\s+", " ", m.group(0)).replace(" and ", " & ")
        cite = re.sub(r"^Tex(?:as|\.)\s+", "", cite, flags=re.I).rstrip(".")
        if cite.lower() not in [c.lower() for c in cites]:
            cites.append(cite)
    # Key claims: the post's summary plus its section headings.
    skip = ("related cases and articles", "got a question about your case", "keep reading")
    heads = [plain(h).rstrip(".") for h in re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.S)]
    heads = [h for h in heads if h and not h.lower().startswith(skip)]
    claims = html.unescape(desc.group(1)).strip() if desc else ""
    if heads:
        claims = (claims + " Covers: " + "; ".join(heads)).strip()
    if len(claims) > 900:
        claims = claims[:900].rsplit(";", 1)[0]
    return {
        "title": plain(h1.group(1)) if h1 else slug,
        "slug": slug,
        "date": date.group(1) if date else "",
        "claims": claims,
        "statutes": "; ".join(cites[:12]),
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args[0]):
        sys.exit("Usage: record_published.py <slug> [topic]")
    slug, topic = args[0], (args[1] if len(args) > 1 else "")
    if "--remove" in sys.argv:
        import sheets

        removed = sheets.remove_from_published_index(slug)
        print(f"[published-index] {'removed' if removed else 'not listed'}: {slug}")
        return
    if not (ROOT / "blog" / f"{slug}.html").exists():
        sys.exit(f"No such post: blog/{slug}.html")
    row = describe(slug)
    if "--print" in sys.argv:
        print(row)
        return

    import sheets

    if any(p["slug"] == slug for p in sheets.get_published_index()):
        print(f"[published-index] already listed: {slug}")
        return
    keyword = ""
    for t in sheets.get_all_blog_topics():
        if topic and t.get("topic", "").strip() == topic.strip():
            keyword = t.get("target_keyword", "")
            break
    sheets.append_to_published_index(
        title=row["title"],
        slug=slug,
        target_keyword=keyword,
        key_claims=row["claims"],
        statutes_cited=row["statutes"],
    )
    print(f"[published-index] added: {slug}")


if __name__ == "__main__":
    main()
