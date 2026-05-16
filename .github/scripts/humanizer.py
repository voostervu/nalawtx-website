"""
Humanizer agent — Phase 2.5 of the blog pipeline.

Aggressive AI-tell removal pass that runs between Editor and Compliance.
Specifically focused on:
    - Em dash (—) and en dash (–) removal
    - AI vocabulary replacement
    - AI sentence pattern removal
    - Smart quote → straight quote conversion

Strategy: Two-stage cleanup
    1. AI pass: Claude rewrites with humanization prompt
    2. Deterministic safety net: Python regex catches any remaining em dashes,
       smart quotes, and other mechanical AI tells

The deterministic safety net is critical because even with a strong prompt,
em dashes occasionally slip through. The Python pass is a final guarantee.
"""

import os
import re
from pathlib import Path

from anthropic import Anthropic


HUMANIZER_MODEL = os.environ.get("HUMANIZER_MODEL", "claude-sonnet-4-6")

PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
}


def _load_prompt() -> str:
    """Load the humanizer prompt from its versioned location."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "humanizer.md"
    return prompt_path.read_text()


def _estimate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    p = PRICING.get(model, {"input": 3.00, "output": 15.00})
    return (tokens_input / 1_000_000) * p["input"] + (tokens_output / 1_000_000) * p["output"]


def _deterministic_cleanup(html: str) -> tuple[str, dict]:
    """
    Final mechanical cleanup pass. Catches anything the AI missed.

    Returns:
        (cleaned_html, stats_dict)
    """
    stats = {
        "em_dashes_removed": 0,
        "en_dashes_removed": 0,
        "smart_quotes_replaced": 0,
        "triple_ellipsis_replaced": 0,
    }

    # Count what we're about to remove (for logging)
    stats["em_dashes_removed"] = html.count("\u2014")  # —
    stats["en_dashes_removed"] = html.count("\u2013")  # –

    # Em dash replacement strategy:
    # 1. " — " (with spaces) → ". " (sentence break)
    # 2. "—" (no spaces) → ", " (mid-clause)
    # This catches the most common AI patterns conservatively.
    html = re.sub(r"\s+—\s+", ". ", html)  # spaced em dash → period
    html = re.sub(r"—", ", ", html)         # tight em dash → comma

    # En dash same treatment (less common but same tell)
    html = re.sub(r"\s+–\s+", ". ", html)
    html = re.sub(r"–", ", ", html)

    # Clean up doubled punctuation from substitution
    html = re.sub(r"\.\s+\.", ".", html)
    html = re.sub(r",\s+,", ",", html)
    html = re.sub(r"\.\s+,", ".", html)
    html = re.sub(r",\s+\.", ".", html)

    # Smart quotes → straight quotes
    smart_quote_pattern = re.compile(r"[\u201C\u201D\u2018\u2019]")
    stats["smart_quotes_replaced"] = len(smart_quote_pattern.findall(html))
    html = html.replace("\u201C", '"').replace("\u201D", '"')  # " "
    html = html.replace("\u2018", "'").replace("\u2019", "'")  # ' '

    # Triple ellipsis as Unicode character
    stats["triple_ellipsis_replaced"] = html.count("\u2026")  # …
    html = html.replace("\u2026", "...")

    return html, stats


def humanize(html_content: str, brand_voice_samples: list[str] | None = None) -> dict:
    """
    Humanize the HTML content via Claude + deterministic post-processing.

    Args:
        html_content: The HTML output from the Editor agent
        brand_voice_samples: Optional list of brand voice paragraphs for reference

    Returns:
        {
            "html": str,                # humanized HTML
            "tokens_input": int,
            "tokens_output": int,
            "cost_usd": float,
            "model": str,
            "deterministic_stats": dict, # what the safety net caught
        }
    """
    client = Anthropic()
    system_prompt = _load_prompt()

    # Build user message with optional brand voice
    user_parts = []

    if brand_voice_samples:
        voice_block = "\n\n".join(f"---\n{s}\n---" for s in brand_voice_samples[:3])
        user_parts.append(
            f"## Brand voice reference (the firm's actual writing samples)\n\n{voice_block}\n"
        )

    user_parts.append(
        "## Content to humanize\n\n"
        "Run your humanization pass on this HTML. Strip em dashes and AI vocabulary. "
        "Preserve all citations, links, and HTML structure. Return only the humanized HTML.\n\n"
        f"{html_content}"
    )

    user_message = "\n\n".join(user_parts)

    response = client.messages.create(
        model=HUMANIZER_MODEL,
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    humanized_html = response.content[0].text.strip()

    # Strip accidental markdown code fences if Claude added them
    if humanized_html.startswith("```"):
        first_newline = humanized_html.find("\n")
        if first_newline > 0:
            humanized_html = humanized_html[first_newline + 1:]
        if humanized_html.endswith("```"):
            humanized_html = humanized_html[:-3]
        humanized_html = humanized_html.strip()

    # Deterministic safety net pass — catches any em dashes the AI missed
    humanized_html, det_stats = _deterministic_cleanup(humanized_html)

    tokens_input = response.usage.input_tokens
    tokens_output = response.usage.output_tokens
    cost = _estimate_cost(HUMANIZER_MODEL, tokens_input, tokens_output)

    return {
        "html": humanized_html,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "cost_usd": cost,
        "model": HUMANIZER_MODEL,
        "deterministic_stats": det_stats,
    }
