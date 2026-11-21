#!/usr/bin/env python3
"""Add structured data (schema) to indexable pages that have none.

Adds a page node (AboutPage, ContactPage, CollectionPage or WebPage) tied to the
firm's main LegalService entry, a BreadcrumbList, and for hub pages an ItemList
of the pages they link to. Pages that already have schema, and noindex pages,
are left alone. Safe to run any number of times.
"""
import html
import json
import os
import pathlib
import re

SITE = "https://nalawtx.com"
ORG = {"@id": f"{SITE}/#org"}
ROOT = pathlib.Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", ".github", "node_modules"}
HUB_NAMES = {
    "attorneys": "Attorneys", "blog": "Blog", "guides": "Guides", "intersections": "Intersections",
    "locations": "Areas We Serve", "practice": "Practice Areas",
}


def text_of(fragment):
    return html.unescape(" ".join(re.sub(r"<[^>]+>", " ", fragment).split()))


def clean_url(rel):
    rel = rel.as_posix()
    if rel == "index.html":
        return f"{SITE}/"
    if rel.endswith("/index.html"):
        return f"{SITE}/{rel[:-len('index.html')]}"
    return f"{SITE}/{rel[:-len('.html')]}"


def page_name(text, fallback):
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    title = re.search(r"<title>([^<]*)</title>", text)
    name = text_of(h1.group(1)) if h1 and text_of(h1.group(1)) else (text_of(title.group(1)).split(" | ")[0] if title else fallback)
    return name.rstrip(".")


def build(path, text):
    rel = path.relative_to(ROOT)
    url = clean_url(rel)
    title = re.search(r"<title>([^<]*)</title>", text)
    desc = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', text, re.I)
    name = text_of(title.group(1)).split(" | ")[0] if title else page_name(text, rel.stem)
    is_hub = rel.name == "index.html" and len(rel.parts) > 1
    kind = "CollectionPage" if is_hub else {"about.html": "AboutPage", "contact.html": "ContactPage"}.get(rel.as_posix(), "WebPage")

    page = {
        "@context": "https://schema.org",
        "@type": kind,
        "name": name,
        "url": url,
        "inLanguage": "en-US",
        "isPartOf": {"@type": "WebSite", "name": "Nguyen & Associates Injury Law Firm", "url": f"{SITE}/"},
        "about": ORG,
        "publisher": ORG,
    }
    if desc:
        page["description"] = html.unescape(desc.group(1)).strip()
    if kind == "ContactPage":
        page["mainEntity"] = ORG

    crumbs = [("Home", f"{SITE}/")]
    if is_hub:
        crumbs.append((HUB_NAMES.get(rel.parts[0], name), url))
    else:
        crumbs.append((name, url))
    blocks = [page, {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(crumbs, 1)
        ],
    }]

    # The blog hub changes every week, so it gets no fixed list of posts.
    if is_hub and rel.parts[0] != "blog":
        seen, items = set(), []
        for href in re.findall(r'href="([^"#?]+\.html)"', text):
            if href.startswith(("http:", "https:", "/")):
                continue
            target = pathlib.Path(os.path.normpath(path.parent / href))
            if target.parent != path.parent or target.name == "index.html" or target in seen or not target.exists():
                continue
            seen.add(target)
            items.append({
                "@type": "ListItem",
                "position": len(items) + 1,
                "name": page_name(target.read_text(encoding="utf-8"), target.stem),
                "url": clean_url(target.relative_to(ROOT)),
            })
        if items:
            blocks.append({"@context": "https://schema.org", "@type": "ItemList", "name": name, "itemListElement": items})
    return blocks


def main():
    done = 0
    for path in sorted(ROOT.rglob("*.html")):
        if SKIP_DIRS & set(path.relative_to(ROOT).parts):
            continue
        text = path.read_text(encoding="utf-8")
        if "application/ld+json" in text or re.search(r'name="robots"[^>]*noindex', text, re.I):
            continue
        if not re.search(r"</head>", text, re.I):
            continue
        scripts = "".join(
            '<script type="application/ld+json">\n' + json.dumps(b, indent=2, ensure_ascii=False) + "\n</script>\n"
            for b in build(path, text)
        )
        path.write_text(re.sub(r"</head>", lambda m: scripts + m.group(0), text, count=1, flags=re.I), encoding="utf-8")
        print(f"added schema: {path.relative_to(ROOT)}")
        done += 1
    print(f"Added schema to {done} pages.")


if __name__ == "__main__":
    main()
