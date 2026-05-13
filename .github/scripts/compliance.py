"""
Compliance + Citation agent — final safety pass on Editor output.

Two-in-one audit:
1. Texas Bar 7.02/7.04 compliance scan
2. Citation verification against approved Statute Reference list

Adds an audit summary HTML comment at the top of the post + inline
HTML comment flags for human-review items.

Like the Editor, this agent is fail-tolerant — if the API call fails,
ceo.py falls back to the Editor's output unchanged. The audit just doesn't
run for that post.
"""

import os
from pathlib import Path

from anthropic import Anthropic


COMPLIANCE_MODEL = os.environ.get("COMPLIANCE_MODEL", "claude-sonnet-4-6")

PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
}


def _load_prompt() -> str:
    """Load the compliance prompt from its versioned location."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "compliance.md"
    return prompt_path.read_text()


def _estimate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    p = PRICING.get(model, {"input": 3.00, "output": 15.00})
    return (tokens_input / 1_000_000) * p["input"] + (tokens_output / 1_000_000) * p["output"]


def audit_post(
    edited_html: str,
    statute_references: list[dict],
) -> dict:
    """
    Run compliance + citation audit on the Editor's output.

    Args:
        edited_html: the polished HTML from the Editor agent
        statute_references: list of dicts with 'citation', 'description', 'tags'
                           (from Statute Reference Sheet)

    Returns:
        {
            "html": str,             # audited HTML (with audit summary comment)
            "tokens_input": int,
            "tokens_output": int,
            "cost_usd": float,
            "model": str,
        }
    """
    client = Anthropic()  # uses ANTHROPIC_API_KEY env var
    system_prompt = _load_prompt()

    if statute_references:
        statute_lines = []
        for ref in statute_references:
            line = f"- **{ref['citation']}** — {ref['description']}"
            if ref.get('tags'):
                line += f" (topics: {ref['tags']})"
            statute_lines.append(line)
        statute_block = "\n".join(statute_lines)
    else:
        statute_block = "(no approved citations on file — flag all citations as unverified)"

    user_message = f"""Audit this blog post draft for Texas Bar compliance and citation accuracy.

## Approved statute citations (verify all citations in the post against this list)

{statute_block}

## Post HTML (audit this)

{edited_html}

Return the complete HTML with the audit summary comment at the top. No explanations outside the audit comment. No markdown fences."""

    response = client.messages.create(
        model=COMPLIANCE_MODEL,
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    html = response.content[0].text

    # Strip accidental markdown code fences if the model added them
    if html.startswith("```"):
        first_newline = html.find("\n")
        if first_newline > 0:
            html = html[first_newline + 1:]
        if html.endswith("```"):
            html = html[:-3]
        html = html.strip()

    tokens_input = response.usage.input_tokens
    tokens_output = response.usage.output_tokens
    cost = _estimate_cost(COMPLIANCE_MODEL, tokens_input, tokens_output)

    return {
        "html": html,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "cost_usd": cost,
        "model": COMPLIANCE_MODEL,
    }
