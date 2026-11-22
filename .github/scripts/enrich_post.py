#!/usr/bin/env python3
"""Add a "Quick answer" box and an FAQ (with FAQ schema) to blog posts.

Usage: python .github/scripts/enrich_post.py blog/<slug>.html [more.html ...]
       python .github/scripts/enrich_post.py --all        # every blog post that lacks them

The text is written by the model from the post's own content only, then checked here:
any statute number or dollar figure that is not in the post, or any promise-of-results
wording, makes the script skip that post rather than publish it.
"""
import html
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODEL = os.environ.get("ENRICH_MODEL", os.environ.get("SENSITIVITY_MODEL", "claude-sonnet-4-6"))
MARK = "<!-- quick-answer -->"
BANNED = re.compile(r"guarantee|we will win|you will win|best (?:lawyer|attorney|firm)|no\.? ?1\b|#1", re.I)


def plain(fragment):
    text = html.unescape(" ".join(re.sub(r"<[^>]+>", " ", fragment).split()))
    return text.replace(" .", ".").replace(" ,", ",").replace(" ?", "?")


def post_text(text):
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    start = text.find("</h1>")
    end = text.find("<!-- related-links -->")
    if end < 0:
        end = text.find('<section class="cta-band">')
    body = re.sub(r"<(script|style|nav|footer)\b.*?</\1>", " ", text[max(start, 0):end if end > 0 else len(text)], flags=re.S | re.I)
    return (plain(h1.group(1)) if h1 else ""), plain(body)[:24000]


def ask_model(headline, body):
    from anthropic import Anthropic

    prompt = (ROOT / ".github" / "prompts" / "enrich.md").read_text(encoding="utf-8")
    resp = Anthropic().messages.create(
        model=MODEL,
        max_tokens=2500,
        system=prompt,
        messages=[{"role": "user", "content": f"## Headline\n{headline}\n\n## Post text\n{body}\n\nReturn only the JSON object."}],
    )
    out = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    return json.loads(out[out.find("{"):out.rfind("}") + 1])


def check(data, body):
    """Return a reason to reject the model's output, or '' if it is usable."""
    qa = " ".join(str(data.get("quick_answer", "")).split())
    tk = [" ".join(str(t).split()) for t in data.get("takeaways") or []]
    faqs = [(" ".join(str(f.get("q", "")).split()), " ".join(str(f.get("a", "")).split())) for f in data.get("faqs") or []]
    if not qa or len(tk) < 2 or len(faqs) < 3 or any(not q or not a for q, a in faqs):
        return "incomplete output"
    everything = " ".join([qa] + tk + [q + " " + a for q, a in faqs])
    if BANNED.search(everything):
        return "promise or comparison wording"
    source = body.replace(",", "")
    for num in re.findall(r"§+\s*([\d.]+\d)", everything):
        if num not in source:
            return f"statute § {num} is not in the post"
    for money in re.findall(r"\$\s?([\d,]+)", everything):
        if money.replace(",", "") not in source:
            return f"dollar figure ${money} is not in the post"
    return ""


def render(data):
    e = lambda s: html.escape(" ".join(str(s).split()), quote=False)
    qa = (
        f"    {MARK}\n"
        '    <div class="qa" style="margin-bottom: var(--s-lg);">\n'
        f"      <p>{e(data['quick_answer'])}</p>\n"
        '      <ul style="margin: 0.75rem 0 0 1.25rem; line-height: 1.55; list-style: disc;">\n'
        + "".join(f"        <li>{e(t)}</li>\n" for t in data["takeaways"][:4])
        + "      </ul>\n    </div>\n\n"
    )
    faq = (
        "\n    <h2>Common questions</h2>\n"
        '    <div class="faq" style="margin-top: var(--s-md);">\n'
        + "".join(
            f"      <details><summary>{e(f['q'])}</summary><p>{e(f['a'])}</p></details>\n" for f in data["faqs"][:5]
        )
        + "    </div>\n"
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": " ".join(f["q"].split()),
             "acceptedAnswer": {"@type": "Answer", "text": " ".join(f["a"].split())}}
            for f in data["faqs"][:5]
        ],
    }
    script = '<script type="application/ld+json">\n' + json.dumps(schema, indent=2, ensure_ascii=False) + "\n</script>\n"
    return qa, faq, script


def insert(text, qa, faq, script):
    """Place the quick answer above the first body paragraph, the FAQ at the end of the article."""
    start = text.find("</h1>")
    m = re.search(r"\n[ \t]*<(?:p|h2)>", text[start:])
    if start < 0 or not m:
        return None
    at = start + m.start() + 1
    new = text[:at] + qa + text[at:]
    tail = re.search(r"\n[ \t]*</div>\s*</article>", new)
    if tail:
        new = new[:tail.start()] + "\n" + faq + new[tail.start():]
    else:
        anchor = "<!-- related-links -->" if "<!-- related-links -->" in new else '<section class="cta-band">'
        block = '<section class="section section--tight">\n  <div class="wrap" style="max-width: 820px;">' + faq + "  </div>\n</section>\n\n"
        new = new.replace(anchor, block + anchor, 1)
    if '"FAQPage"' not in text:
        new = re.sub(r"</head>", lambda m: script + m.group(0), new, count=1, flags=re.I)
    return new


def enrich(path, ask=ask_model):
    text = path.read_text(encoding="utf-8")
    if MARK in text:
        return "already has them"
    headline, body = post_text(text)
    try:
        data = ask(headline, body)
    except Exception as exc:
        return f"skipped ({type(exc).__name__}: {exc})"
    problem = check(data, body)
    if problem:
        return f"skipped ({problem})"
    new = insert(text, *render(data))
    if not new:
        return "skipped (could not find where to insert)"
    path.write_text(new, encoding="utf-8")
    return "added"


def main():
    if "--all" in sys.argv:
        paths = [p for p in sorted((ROOT / "blog").glob("*.html")) if p.name != "index.html"]
    else:
        paths = [ROOT / a for a in sys.argv[1:] if not a.startswith("--")]
    for path in paths:
        if not path.exists():
            print(f"[enrich] no such file: {path}")
            continue
        print(f"[enrich] {path.relative_to(ROOT)}: {enrich(path)}")


if __name__ == "__main__":
    main()
