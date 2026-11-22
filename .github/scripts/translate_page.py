#!/usr/bin/env python3
"""Translate practice pages or blog posts into Spanish and Vietnamese.

Usage: python .github/scripts/translate_page.py <slug> [<slug> ...] [--section blog] [--lang es] [--lang vi] [--force]

Reads practice/<slug>.html and writes <lang>/practice/<slug>.html. Only the words are
translated: the page's HTML, styling, links and schema structure are kept as they are.
Also keeps the three language versions pointing at each other (hreflang tags and the
EN / ES / VI switcher), adds the new pages to sitemap.xml, and links them from the
language's practice hub. Existing translations are skipped unless --force is given.
"""
import html
import json
import os
import pathlib
import re
import sys

SITE = "https://nalawtx.com"
ROOT = pathlib.Path(__file__).resolve().parents[2]
MODEL = os.environ.get("TRANSLATE_MODEL", os.environ.get("SENSITIVITY_MODEL", "claude-sonnet-4-6"))
LANGS = {
    "es": "Spanish as spoken by Mexican and Central American families in Houston (formal 'usted')",
    "vi": "Vietnamese as spoken by Vietnamese families in Houston (polite, natural, not word-for-word)",
}
INLINE = {"a", "strong", "em", "b", "i", "span", "br", "sup", "sub", "small", "u", "mark", "abbr", "code"}
TOKEN = re.compile(r"(<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>|<[^>]+>)", re.S | re.I)
META = re.compile(
    r'(<meta\s+(?:name|property)="(?:description|og:title|og:description|twitter:title|twitter:description)"\s+content=")([^"]*)(")',
    re.I,
)
NO_NAME = {"LegalService", "Organization", "Person", "Attorney", "LocalBusiness", "WebSite", "City", "PostalAddress", "State"}
MARKER = re.compile(r"\[\[\d+\]\]")
SECTION = "practice"  # folder the pages are in; "." for pages at the top of the site. Set from --section


def page_url(lang, slug):
    """Public address of a page: no .html, and a folder address for index pages."""
    parts = [SITE] + ([] if lang == "en" else [lang]) + ([] if SECTION == "." else [SECTION])
    base = "/".join(parts)
    return base + "/" if slug == "index" else f"{base}/{slug}"


def page_dir(lang):
    return os.path.normpath(SECTION if lang == "en" else f"{lang}/{SECTION}")


def tag_name(token):
    m = re.match(r"</?([a-zA-Z0-9]+)", token)
    return m.group(1).lower() if m else ""


def split_runs(text):
    """Return (tokens, runs): each run is a list of token indexes forming one translatable unit."""
    tokens = TOKEN.split(text)
    runs, current = [], []
    for i, tok in enumerate(tokens):
        is_tag = tok.startswith("<")
        if is_tag and (tok.startswith("<!--") or tag_name(tok) not in INLINE):
            if current:
                runs.append(current)
                current = []
        else:
            current.append(i)
    if current:
        runs.append(current)
    keep = []
    for run in runs:
        words = "".join(tokens[i] for i in run if not tokens[i].startswith("<"))
        if re.search(r"[A-Za-zÀ-ỹ]{2,}", html.unescape(words)):
            keep.append(run)
    return tokens, keep


def pack(tokens, run):
    """Turn a run into text with [[n]] markers standing in for its inline tags."""
    while run and not tokens[run[0]].strip():
        run = run[1:]
    while run and not tokens[run[-1]].strip():
        run = run[:-1]
    parts, tags = [], []
    for i in run:
        if tokens[i].startswith("<"):
            tags.append(tokens[i])
            parts.append(f"[[{len(tags)}]]")
        else:
            parts.append(tokens[i])
    return run, "".join(parts), tags


def unpack(translated, tags):
    return re.sub(r"\[\[(\d+)\]\]", lambda m: tags[int(m.group(1)) - 1], translated)


def collect_schema(node, out):
    """Find translatable strings inside a JSON-LD object: (container, key) pairs."""
    if isinstance(node, list):
        for item in node:
            collect_schema(item, out)
    elif isinstance(node, dict):
        types = node.get("@type")
        types = set(types if isinstance(types, list) else [types])
        branded = bool(types & NO_NAME)
        for key, value in node.items():
            if isinstance(value, str):
                if key in ("headline", "text", "serviceType") or (key in ("name", "description") and not branded):
                    out.append((node, key))
            else:
                collect_schema(value, out)


def call_model(lang, items):
    from anthropic import Anthropic

    system = (
        f"You translate website text for a Houston, Texas personal injury law firm into {LANGS[lang]}.\n"
        "Rules:\n"
        "- Translate the meaning faithfully. Do not add, remove, soften or strengthen any legal statement.\n"
        "- Keep every [[n]] marker exactly as written and in a sensible place; they stand for formatting.\n"
        "- Keep unchanged: the firm name 'Nguyen & Associates', people's names, phone numbers, URLs, statute "
        "citations (for example 'Tex. Civ. Prac. & Rem. Code § 16.003'), case names, dollar figures, 'EN', 'ES', 'VI'.\n"
        "- Keep HTML entities such as &amp; and &rarr; as they are.\n"
        "- Return ONLY a JSON array of strings, the same length and order as the input array."
    )
    resp = Anthropic().messages.create(
        model=MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": json.dumps(items, ensure_ascii=False)}],
    )
    out = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    data = json.loads(out[out.find("["):out.rfind("]") + 1])
    if not isinstance(data, list) or len(data) != len(items):
        raise ValueError("translation came back with the wrong number of items")
    return [str(x) for x in data]


def translate_all(lang, items, translator):
    """Translate a list of strings in batches; fall back to the original on any failure."""
    result, kept_english = list(items), 0
    batch, size, batches = [], 0, []
    for idx, item in enumerate(items):
        if batch and (size + len(item) > 6000 or len(batch) >= 40):
            batches.append(batch)
            batch, size = [], 0
        batch.append(idx)
        size += len(item)
    if batch:
        batches.append(batch)
    for batch in batches:
        source = [items[i] for i in batch]
        translated = None
        for _ in range(2):
            try:
                translated = translator(lang, source)
                break
            except Exception as exc:
                print(f"[translate] batch failed ({type(exc).__name__}: {exc}); retrying")
        for i, src in zip(batch, translated or source):
            if translated is None or sorted(MARKER.findall(src)) != sorted(MARKER.findall(items[i])) or not src.strip():
                kept_english += 1
                continue
            result[i] = src
    return result, kept_english


def rewrite_links(token, lang, translated_paths):
    """Fix relative links for the page's new folder; point to translated pages where they exist."""
    def fix(m):
        attr, url = m.group(1), m.group(2)
        if re.match(r"(?:[a-z][a-z0-9+.-]*:|#|/|\?)", url, re.I) or not url:
            return m.group(0)
        path, sep, frag = url.partition("#")
        target = os.path.normpath(os.path.join(SECTION, path))
        if path.endswith("/"):
            target += "/"
        local = target + "index.html" if target.endswith("/") else target
        if f"{lang}/{local}" in translated_paths:
            target = f"{lang}/{target}"
        rel = os.path.relpath(target.rstrip("/"), page_dir(lang)) + ("/" if target.endswith("/") else "")
        return f'{attr}="{rel}{sep}{frag}"'

    return re.sub(r'\b(href|src)="([^"]*)"', fix, token)


def hreflang_block(slug, langs):
    lines = [f'<link rel="alternate" hreflang="en" href="{page_url("en", slug)}">']
    lines += [f'<link rel="alternate" hreflang="{l}" href="{page_url(l, slug)}">' for l in langs]
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{page_url("en", slug)}">')
    return "\n".join(lines)


def set_head(text, slug, page_lang, langs):
    """Canonical, og:url, hreflang and the EN / ES / VI switcher for one version of the page."""
    own = page_url(page_lang, slug)
    text = re.sub(r'<link rel="alternate" hreflang="[^"]*" href="[^"]*">\n?', "", text)
    text = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{own}">\n{hreflang_block(slug, langs)}', text, count=1)
    text = re.sub(r'(<meta property="og:url" content=")[^"]*(")', rf"\g<1>{own}\g<2>", text)
    text = re.sub(r'<html lang="[^"]*"', f'<html lang="{page_lang}"', text, count=1)
    here = page_dir(page_lang)
    for code in ["en"] + list(LANGS):
        there = page_dir(code)
        exists = code == "en" or code in langs
        href = os.path.relpath(f"{there}/{slug}.html" if exists else (f"{code}/index.html"), here)
        active = ' class="active"' if code == page_lang else ""
        text = re.sub(rf'<a href="[^"]*"(?: class="active")?>{code.upper()}</a>', f'<a href="{href}"{active}>{code.upper()}</a>', text)
    return text


def translate_page(slug, lang, translator, translated_paths):
    source = (ROOT / SECTION / f"{slug}.html").read_text(encoding="utf-8")
    tokens, runs = split_runs(source)
    items, slots = [], []
    for run in runs:
        run, text, tags = pack(tokens, run)
        if not run:
            continue
        items.append(text)
        slots.append(("run", run, tags))
    metas = list(META.finditer(source))
    for m in metas:
        items.append(m.group(2))
        slots.append(("meta", m.group(0), None))
    schema_blocks = []
    for i, tok in enumerate(tokens):
        if tok.lower().startswith('<script type="application/ld+json">'):
            inner = tok[tok.find(">") + 1:tok.rfind("</script>")]
            try:
                data = json.loads(inner)
            except ValueError:
                continue
            found = []
            collect_schema(data, found)
            schema_blocks.append((i, data))
            for node, key in found:
                items.append(node[key])
                slots.append(("schema", node, key))

    translated, kept = translate_all(lang, items, translator)

    meta_map, done = {}, set()  # done: tokens whose links are already rewritten
    for (kind, a, b), new in zip(slots, translated):
        if kind == "run":
            lead = re.match(r"\s*", tokens[a[0]]).group(0) if not tokens[a[0]].startswith("<") else ""
            trail = re.search(r"\s*$", tokens[a[-1]]).group(0) if not tokens[a[-1]].startswith("<") else ""
            tags = [rewrite_links(tag, lang, translated_paths) for tag in b]
            tokens[a[0]] = lead + unpack(new.strip(), tags) + trail
            done.add(a[0])
            for i in a[1:]:
                tokens[i] = ""
        elif kind == "meta":
            meta_map[a] = new
        else:
            a[b] = html.unescape(new)  # schema is JSON, so no HTML entities
    for i, data in schema_blocks:
        text = json.dumps(data, indent=2, ensure_ascii=False)
        text = re.sub(re.escape(page_url("en", slug)) + r'(?=")', lambda m: page_url(lang, slug), text)
        text = re.sub(rf'"{re.escape(SITE)}/practice/"', f'"{SITE}/{lang}/practice/"', text)
        text = re.sub(rf'"item": "{re.escape(SITE)}/"', f'"item": "{SITE}/{lang}/"', text)
        tokens[i] = '<script type="application/ld+json">\n' + text + "\n</script>"
    def relink(i, tok):
        if i in done or not tok.startswith("<") or tok.startswith(("<!--", "<style")):
            return tok
        if tok.lower().startswith("<script"):  # only the opening tag of a script can hold a link
            end = tok.find(">") + 1
            return rewrite_links(tok[:end], lang, translated_paths) + tok[end:]
        return rewrite_links(tok, lang, translated_paths)

    tokens = [relink(i, t) for i, t in enumerate(tokens)]
    out = "".join(tokens)
    out = META.sub(lambda m: m.group(1) + html.escape(html.unescape(meta_map.get(m.group(0), m.group(2))), quote=True) + m.group(3), out)
    return out, len(items), kept


def update_sitemap(urls):
    path = ROOT / "sitemap.xml"
    text = path.read_text(encoding="utf-8")
    import datetime
    today = datetime.date.today().isoformat()
    add = "".join(
        f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>\n"
        for u in urls if f"<loc>{u}</loc>" not in text
    )
    if add:
        idx = text.rindex("</urlset>")
        path.write_text(text[:idx].rstrip("\n") + "\n" + add + "\n" + text[idx:], encoding="utf-8")


def repoint(lang):
    """Point links on this language's pages at translated pages wherever one now exists."""
    for page in (ROOT / lang).rglob("*.html"):
        here = page.parent.relative_to(ROOT).as_posix()

        def fix(m):
            url = m.group(1)
            if re.match(r"(?:[a-z][a-z0-9+.-]*:|#|/|\?)", url, re.I) or not url:
                return m.group(0)
            path, sep, frag = url.partition("#")
            target = os.path.normpath(os.path.join(here, path))
            if target.startswith(("..", "es/", "vi/")) or not target.endswith(".html"):
                return m.group(0)
            if not (ROOT / lang / target).exists():
                return m.group(0)
            return f'href="{os.path.relpath(f"{lang}/{target}", here)}{sep}{frag}"'

        text = page.read_text(encoding="utf-8")
        # every link inside an <a> tag, except the EN / ES / VI language switcher
        new = re.sub(
            r'(<a\b[^>]*?\b)href="([^"]*)"(?![^>]*>(?:EN|ES|VI)</a>)',
            lambda m: m.group(1) + fix(re.match(r'href="([^"]*)"', m.group(0)[len(m.group(1)):])),
            text,
        )
        if new != text:
            page.write_text(new, encoding="utf-8")


def main(translator=call_model):
    global SECTION
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--section" and i + 1 < len(args):
            SECTION = args[i + 1]
            del args[i:i + 2]
            break
    langs = [args[i + 1] for i, a in enumerate(args) if a == "--lang" and i + 1 < len(args)] or list(LANGS)
    slugs = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--lang")]
    force = "--force" in args
    slugs = [s for s in slugs if (ROOT / SECTION / f"{s}.html").exists()]
    # every page that will exist in each language once this run finishes
    translated_paths = set()
    for lang in LANGS:
        for p in (ROOT / lang).rglob("*.html"):
            translated_paths.add(p.relative_to(ROOT).as_posix())
        if lang in langs:
            translated_paths.update(os.path.normpath(f"{lang}/{SECTION}/{s}.html") for s in slugs)
    new_urls = []
    for slug in slugs:
        for lang in langs:
            dest = ROOT / lang / SECTION / f"{slug}.html"
            if dest.exists() and not force:
                print(f"[translate] {lang}/{SECTION}/{slug}.html: already exists")
                continue
            out, total, kept = translate_page(slug, lang, translator, translated_paths)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(out, encoding="utf-8")
            new_urls.append(page_url(lang, slug))
            print(f"[translate] {lang}/{SECTION}/{slug}.html: {total} text blocks, {kept} left in English")
        have = [l for l in LANGS if (ROOT / l / SECTION / f"{slug}.html").exists()]
        for page_lang in ["en"] + have:
            p = ROOT / (SECTION if page_lang == "en" else f"{page_lang}/{SECTION}") / f"{slug}.html"
            p.write_text(set_head(p.read_text(encoding="utf-8"), slug, page_lang, have), encoding="utf-8")
        for lang in have:  # link the translated page from that language's practice hub
            hub = ROOT / lang / "practice" / "index.html"
            if hub.exists():
                t = hub.read_text(encoding="utf-8")
                hub.write_text(t.replace(f'href="../../practice/{slug}.html"', f'href="{slug}.html"'), encoding="utf-8")
    for lang in LANGS:
        repoint(lang)
    update_sitemap(new_urls)


if __name__ == "__main__":
    main()
