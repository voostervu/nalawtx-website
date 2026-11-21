#!/usr/bin/env python3
"""Fact-check a blog post's claims about new laws and court rulings.

Usage: python .github/scripts/factcheck.py blog/<slug>.html [--no-audit]

Uses web search to check every time-sensitive legal claim in the post, then
sets a status:

    PASS  - every claim confirmed (or the post makes none)
    WARN  - a side claim could not be confirmed, or the check could not run
    HOLD  - a claim is contradicted, or the post's main claim could not be
            confirmed. The workflow does not publish a HOLD post.

Results are appended to .github/audits/<slug>.md and written to the GitHub
Actions step outputs (status, summary).
"""
import html
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODEL = os.environ.get("FACTCHECK_MODEL", os.environ.get("SENSITIVITY_MODEL", "claude-sonnet-4-6"))
VERDICTS = ("CONFIRMED", "CONTRADICTED", "UNCONFIRMED")


def post_text(path):
    text = path.read_text(encoding="utf-8")
    title = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    start = text.find("<h1")
    body = text[start if start >= 0 else 0:]
    body = re.sub(r"<(script|style|footer|nav)\b.*?</\1>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    body = html.unescape(" ".join(re.sub(r"<[^>]+>", " ", body).split()))
    headline = html.unescape(" ".join(re.sub(r"<[^>]+>", " ", title.group(1)).split())) if title else path.stem
    return headline, body[:24000]


def parse_json(text):
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the fact-check reply")
    return json.loads(text[start:end + 1])


def ask_model(headline, body):
    from anthropic import Anthropic

    prompt = (ROOT / ".github" / "prompts" / "factcheck.md").read_text(encoding="utf-8")
    response = Anthropic().messages.create(
        model=MODEL,
        max_tokens=4000,
        system=prompt,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
        messages=[{
            "role": "user",
            "content": (
                "Fact-check the time-sensitive legal claims in this blog post.\n\n"
                f"## Headline\n{headline}\n\n## Post text\n{body}\n\n"
                "Return only the JSON object described in your instructions."
            ),
        }],
    )
    final = ""
    for block in response.content:
        if getattr(block, "type", "") == "text":
            final = block.text
    return parse_json(final)


def decide(result):
    """Turn the list of checked claims into PASS, WARN or HOLD."""
    claims = []
    for c in result.get("claims") or []:
        verdict = str(c.get("verdict", "")).upper().strip()
        claims.append({
            "claim": " ".join(str(c.get("claim", "")).split()),
            "central": bool(c.get("central")),
            "verdict": verdict if verdict in VERDICTS else "UNCONFIRMED",
            "evidence": " ".join(str(c.get("evidence", "")).split()),
            "source": str(c.get("source", "")).strip(),
        })
    if any(c["verdict"] == "CONTRADICTED" for c in claims):
        status = "HOLD"
    elif any(c["verdict"] == "UNCONFIRMED" and c["central"] for c in claims):
        status = "HOLD"
    elif any(c["verdict"] == "UNCONFIRMED" for c in claims):
        status = "WARN"
    else:
        status = "PASS"
    return status, claims


def write_audit(slug, status, claims, summary):
    lines = ["", "## Fact check (new laws and rulings)", "", f"Status: {status}", ""]
    if summary:
        lines += [summary, ""]
    for c in claims:
        if c["verdict"] == "CONFIRMED":
            lines.append(f"- Confirmed: {c['claim']}")
        else:
            lines.append(f"- REVIEW: fact check {c['verdict']}: {c['claim']} ({c['evidence']})")
        if c["source"]:
            lines.append(f"  - Source: {c['source']}")
    if not claims:
        lines.append("No time-sensitive legal claims found.")
    audits = ROOT / ".github" / "audits"
    audits.mkdir(parents=True, exist_ok=True)
    path = audits / f"{slug}.md"
    head = path.read_text(encoding="utf-8") if path.exists() else f"# Audit notes: blog/{slug}.html\n"
    head = head.split("\n## Fact check (new laws and rulings)")[0].rstrip("\n")
    path.write_text(head + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def set_output(name, value):
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={' '.join(str(value).split())}\n")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("Usage: factcheck.py blog/<slug>.html [--no-audit]")
    path = ROOT / args[0]
    if not path.exists():
        sys.exit(f"No such post: {args[0]}")

    try:
        headline, body = post_text(path)
        result = ask_model(headline, body)
        status, claims = decide(result)
        summary = " ".join(str(result.get("summary", "")).split())
    except Exception as exc:  # the check itself failed: publish, but say so
        print(f"[factcheck] could not run: {exc}", file=sys.stderr)
        status, claims = "WARN", []
        summary = f"The fact check could not run ({type(exc).__name__}). This post was not fact-checked."
        claims.append({"claim": "post was not fact-checked", "central": False, "verdict": "UNCONFIRMED",
                       "evidence": "fact check did not run", "source": ""})

    print(f"[factcheck] status: {status}")
    print(f"[factcheck] {summary}")
    for c in claims:
        print(f"[factcheck]   {c['verdict']:<12} {'(central) ' if c['central'] else ''}{c['claim']} | {c['evidence']} {c['source']}")
    if "--no-audit" not in sys.argv:
        write_audit(path.stem, status, claims, summary)
    set_output("status", status)
    set_output("summary", summary[:400])


if __name__ == "__main__":
    main()
