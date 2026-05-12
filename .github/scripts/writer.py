"""
Writer agent — generates a blog post HTML matching the firm's template.

Reads its system prompt from prompts/writer.md (versioned, Upgrade C).
Receives topic + brand voice samples + published index from CEO.
Returns complete HTML for one blog post.
"""

import os
from pathlib import Path

from anthropic import Anthropic


# Model to use. Override via env var to A/B test new models without code changes.
WRITER_MODEL = os.environ.get("WRITER_MODEL", "claude-sonnet-4-6-20250901")

# Approximate per-million-token pricing for cost estimation. Update when needed.
# (Phase 1.5 will pull live pricing from Anthropic's API metadata.)
PRICING = {
    "claude-sonnet-4-6-20250901": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
}


def _load_prompt() -> str:
    """Load the writer prompt from its versioned location."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "writer.md"
    return prompt_path.read_text()


def _estimate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    p = PRICING.get(model, {"input": 3.00, "output": 15.00})
    return (tokens_input / 1_000_000) * p["input"] + (tokens_output / 1_000_000) * p["output"]


def write_post(
    topic: str,
    target_keyword: str,
    notes: str,
    todays_date: str,
    brand_voice_samples: list[str],
    published_index: list[dict],
) -> dict:
    """
    Generate one blog post.

    Returns:
        {
            "html": str,             # the complete HTML file
            "tokens_input": int,
            "tokens_output": int,
            "cost_usd": float,
            "model": str,
        }
    """
    client = Anthropic()  # uses ANTHROPIC_API_KEY env var
    system_prompt = _load_prompt()

    # Compose the user message — the dynamic context the prompt expects
    brand_voice_block = "\n\n---\n\n".join(brand_voice_samples) if brand_voice_samples else "(no samples yet — write in the brand voice described in the system prompt)"

    if published_index:
        published_lines = [
            f"- {p['title']} (slug: {p['slug']}, target: {p['target_keyword']})"
            for p in published_index
        ]
        published_block = "\n".join(published_lines)
    else:
        published_block = "(no published posts yet)"

    user_message = f"""Write a blog post for nalawtx.com.

## Topic
{topic}

## Target SEO keyword
{target_keyword}

## Editorial notes
{notes if notes else "(none)"}

## Today's date
{todays_date}

## Brand voice samples — match this voice
{brand_voice_block}

## Already-published posts — do not duplicate these
{published_block}

Return only the complete HTML file. No explanations, no markdown fences."""

    response = client.messages.create(
        model=WRITER_MODEL,
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    html = response.content[0].text

    # Strip accidental markdown code fences if the model added them despite instructions
    if html.startswith("```"):
        first_newline = html.find("\n")
        if first_newline > 0:
            html = html[first_newline + 1:]
        if html.endswith("```"):
            html = html[:-3]
        html = html.strip()

    tokens_input = response.usage.input_tokens
    tokens_output = response.usage.output_tokens
    cost = _estimate_cost(WRITER_MODEL, tokens_input, tokens_output)

    return {
        "html": html,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "cost_usd": cost,
        "model": WRITER_MODEL,
    }
