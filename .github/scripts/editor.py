"""
Editor agent — polishes Writer output to remove AI-isms and tighten voice.

Reads its system prompt from prompts/editor.md (versioned, like the Writer).
Takes the Writer's HTML draft + brand voice samples as input.
Returns polished HTML.

The Editor is called by ceo.py between Writer output and file save. If the
Editor fails (API error, timeout), ceo.py falls back to publishing the
Writer's draft unedited — graceful degradation.
"""

import os
from pathlib import Path

from anthropic import Anthropic


# Model to use. Override via env var to A/B test new models without code changes.
EDITOR_MODEL = os.environ.get("EDITOR_MODEL", "claude-sonnet-4-6")

# Approximate per-million-token pricing for cost estimation.
PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
}


def _load_prompt() -> str:
    """Load the editor prompt from its versioned location."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "editor.md"
    return prompt_path.read_text()


def _estimate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    p = PRICING.get(model, {"input": 3.00, "output": 15.00})
    return (tokens_input / 1_000_000) * p["input"] + (tokens_output / 1_000_000) * p["output"]


def edit_post(
    writer_html: str,
    brand_voice_samples: list[str],
) -> dict:
    """
    Edit/polish a Writer-generated post.

    Args:
        writer_html: the complete HTML output from the Writer agent
        brand_voice_samples: list of brand voice samples for reference

    Returns:
        {
            "html": str,             # polished HTML
            "tokens_input": int,
            "tokens_output": int,
            "cost_usd": float,
            "model": str,
        }
    """
    client = Anthropic()  # uses ANTHROPIC_API_KEY env var
    system_prompt = _load_prompt()

    brand_voice_block = (
        "\n\n---\n\n".join(brand_voice_samples)
        if brand_voice_samples
        else "(no samples available — use the brand voice description in the system prompt)"
    )

    user_message = f"""Polish this blog post draft from the Writer agent.

## Brand voice samples (use these as your editorial reference)

{brand_voice_block}

## Writer's draft (HTML — edit this)

{writer_html}

Return the complete edited HTML. No explanations, no markdown fences, no commentary."""

    response = client.messages.create(
        model=EDITOR_MODEL,
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
    cost = _estimate_cost(EDITOR_MODEL, tokens_input, tokens_output)

    return {
        "html": html,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "cost_usd": cost,
        "model": EDITOR_MODEL,
    }
