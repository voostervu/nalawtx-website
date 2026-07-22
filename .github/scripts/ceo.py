def extract_lede_from_html(html_content: str, fallback: str = "") -> str:
    """Extract the first substantive article paragraph for the blog card excerpt.

    Two-stage defence against grabbing page chrome:
      1. Strip nav/header/footer/script/style blocks entirely.
      2. Only search after the <h1>, since the article body always follows it.
    """
    # Stage 1 - remove chrome that contains link text and CTAs
    body = html_content
    for tag in ("nav", "header", "footer", "script", "style", "aside"):
        body = re.sub(
            rf"<{tag}\b[^>]*>.*?</{tag}>",
            " ",
            body,
            flags=re.IGNORECASE | re.DOTALL,
        )

    # Stage 2 - start after the H1; the lede always follows the headline
    h1_match = re.search(r"</h1>", body, re.IGNORECASE)
    search_region = body[h1_match.end():] if h1_match else body

    paragraphs = re.findall(
        r"<p[^>]*>(.*?)</p>", search_region, re.IGNORECASE | re.DOTALL
    )

    for p in paragraphs:
        text = re.sub(r"<[^>]+>", "", p)
        text = html.unescape(text)
        # Collapse whitespace - nav remnants arrive as multi-line blobs
        text = " ".join(text.split())

        if len(text) < 50:
            continue

        # A real lede is prose: it contains sentence punctuation.
        # Stray link lists and label rows do not.
        if not any(mark in text for mark in (".", "?", "!")):
            continue

        return text

    return fallback
