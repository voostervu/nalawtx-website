"""
Researcher agent — discovers blog topics from seed list + web search.

Reads its system prompt from prompts/researcher.md.
Has access to web search via Anthropic's web_search tool.
Returns 3-5 topic proposals as a list of dicts.

This agent is called by researcher_runner.py (a separate entry point from
the blog agent's CEO orchestrator). It runs weekly on a different schedule
than the blog generation pipeline.

Output is written directly to the "Blog Topics" Sheet tab as new Queued rows.
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic


RESEARCHER_MODEL = os.environ.get("RESEARCHER_MODEL", "claude-sonnet-4-6")

PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
}


def _load_prompt() -> str:
    """Load the researcher prompt from its versioned location."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "researcher.md"
    return prompt_path.read_text()


def _estimate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    p = PRICING.get(model, {"input": 3.00, "output": 15.00})
    return (tokens_input / 1_000_000) * p["input"] + (tokens_output / 1_000_000) * p["output"]


def research_topics(
    topic_seeds: list[dict],
    published_index: list[dict],
    current_queue: list[dict],
) -> dict:
    """
    Generate 3-5 new blog topic proposals.

    Args:
        topic_seeds: list of dicts from the Topic Seed Ideas Sheet tab
                     (fields: topic_concept, target_keyword, practice_area, priority)
        published_index: list of dicts of already-published posts
        current_queue: list of dicts of topics currently in the Blog Topics tab
                      (any status — Queued, Generating, Drafted, Published)

    Returns:
        {
            "topics": [<list of topic dicts>],
            "tokens_input": int,
            "tokens_output": int,
            "cost_usd": float,
            "model": str,
        }
    """
    client = Anthropic()
    system_prompt = _load_prompt()

    # Format inputs for the Researcher
    if topic_seeds:
        seed_lines = []
        for s in topic_seeds:
            line_parts = [f"- **{s.get('topic_concept', '')}**"]
            if s.get('target_keyword'):
                line_parts.append(f" (target: {s['target_keyword']})")
            if s.get('practice_area'):
                line_parts.append(f" [{s['practice_area']}]")
            if s.get('priority'):
                line_parts.append(f" — priority: {s['priority']}")
            seed_lines.append("".join(line_parts))
        seed_block = "\n".join(seed_lines)
    else:
        seed_block = "(no seed ideas — rely on web search and general PI knowledge)"

    if published_index:
        published_lines = [f"- {p['title']} (target: {p.get('target_keyword', '')})" for p in published_index]
        published_block = "\n".join(published_lines)
    else:
        published_block = "(no posts published yet)"

    if current_queue:
        queue_lines = [f"- {t['topic']} (status: {t.get('status', 'Queued')})" for t in current_queue]
        queue_block = "\n".join(queue_lines)
    else:
        queue_block = "(no topics in queue)"

    user_message = f"""Generate 3-5 new blog topic proposals for Nguyen & Associates' blog.

## Topic Seed Ideas (curated evergreen list)

{seed_block}

## Already Published — DO NOT duplicate

{published_block}

## Currently in Blog Topics queue — DO NOT duplicate

{queue_block}

## Instructions

Use web search to:
1. Check for recent Texas legal news, court rulings, or statute changes
2. Verify topic relevance and current search interest
3. Identify content gaps (topics competitors cover that we don't)

Return only a JSON array of 3-5 topic objects. No commentary, no markdown fences."""

    # Call the API with web search enabled
    response = client.messages.create(
        model=RESEARCHER_MODEL,
        max_tokens=4000,
        system=system_prompt,
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 5,  # cap web searches per run
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    # The response may contain multiple content blocks (text + tool_use + tool_result + final text)
    # Find the final text block which should contain the JSON
    final_text = ""
    for block in response.content:
        if hasattr(block, "type") and block.type == "text":
            final_text = block.text
    
    # If no text block found, fall back to first content
    if not final_text and response.content:
        final_text = getattr(response.content[0], "text", "")

    # Strip accidental markdown code fences
    text = final_text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline > 0:
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    
    # Parse JSON
    try:
        topics = json.loads(text)
    except json.JSONDecodeError as e:
        # Try to find JSON within the text (sometimes model wraps it in prose)
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            try:
                topics = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                raise ValueError(f"Researcher returned invalid JSON: {e}\n\nResponse text:\n{text[:500]}")
        else:
            raise ValueError(f"Researcher returned invalid JSON: {e}\n\nResponse text:\n{text[:500]}")

    # Validate structure
    if not isinstance(topics, list):
        raise ValueError(f"Researcher must return a JSON array, got: {type(topics).__name__}")
    if not (3 <= len(topics) <= 5):
        print(f"⚠️  Researcher returned {len(topics)} topics, expected 3-5. Proceeding anyway.")

    required_fields = {"topic", "target_keyword", "priority", "notes", "source"}
    for i, t in enumerate(topics):
        if not isinstance(t, dict):
            raise ValueError(f"Topic #{i} is not a dict: {t}")
        missing = required_fields - set(t.keys())
        if missing:
            # Auto-fill missing fields with sensible defaults
            for field in missing:
                if field == "priority":
                    t[field] = "Medium"
                elif field == "source":
                    t[field] = "web_search"
                else:
                    t[field] = ""

    tokens_input = response.usage.input_tokens
    tokens_output = response.usage.output_tokens
    cost = _estimate_cost(RESEARCHER_MODEL, tokens_input, tokens_output)

    return {
        "topics": topics,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "cost_usd": cost,
        "model": RESEARCHER_MODEL,
    }
