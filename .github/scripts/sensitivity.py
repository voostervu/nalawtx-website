"""
Topical Sensitivity Agent — Phase 5 of the blog pipeline.

Checks recent Houston/Texas news to determine if publishing this post today
would be tone-deaf given current events.

Returns one of three statuses:
    SAFE    — no concerns, post can auto-merge normally
    CAUTION — minor concern, log it but allow auto-merge
    HOLD    — clear concern, leave PR open for human review

Uses Anthropic's web_search tool to check recent news.
"""

import json
import os
import re
from pathlib import Path

from anthropic import Anthropic


SENSITIVITY_MODEL = os.environ.get("SENSITIVITY_MODEL", "claude-sonnet-4-6")

PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-7": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
}


def _load_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "sensitivity.md"
    return prompt_path.read_text()


def _estimate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    p = PRICING.get(model, {"input": 3.00, "output": 15.00})
    return (tokens_input / 1_000_000) * p["input"] + (tokens_output / 1_000_000) * p["output"]


def _extract_text_blocks(response_content) -> str:
    """Extract concatenated text from response content blocks (text + tool_use + tool_result + final text)."""
    final_text = ""
    for block in response_content:
        if hasattr(block, "type") and block.type == "text":
            final_text = block.text  # last text block wins
    return final_text


def _parse_sensitivity_json(text: str) -> dict:
    """Parse the JSON output from the sensitivity agent."""
    text = text.strip()
    
    # Strip markdown code fences if present
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline > 0:
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from within prose
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        # Default to SAFE if can't parse — fail open, not closed
        return {
            "status": "SAFE",
            "reasoning": "Sensitivity agent returned unparseable output. Defaulting to SAFE.",
            "relevant_events": [],
            "search_queries_used": [],
        }


def check_sensitivity(post_topic: str, post_html: str) -> dict:
    """
    Check the sensitivity of publishing this post today.
    
    Args:
        post_topic: the topic title (e.g., "What to do after a car accident")
        post_html: the full HTML of the post (for context about content)
    
    Returns:
        {
            "status": "SAFE" | "CAUTION" | "HOLD",
            "reasoning": str,
            "relevant_events": list[str],
            "search_queries_used": list[str],
            "tokens_input": int,
            "tokens_output": int,
            "cost_usd": float,
            "model": str,
            "audit_comment": str,  # HTML comment to embed in post
        }
    """
    client = Anthropic()
    system_prompt = _load_prompt()
    
    # Truncate post HTML to first 4000 chars for context (don't need full text)
    post_excerpt = post_html[:4000]
    if len(post_html) > 4000:
        post_excerpt += "\n...[truncated]"
    
    user_message = f"""Check whether publishing this blog post TODAY would be tone-deaf given recent Houston/Texas news.

## Post topic
{post_topic}

## Post excerpt (first 4000 chars for context)
{post_excerpt}

Search for recent Houston/Texas news related to this topic. Determine if publishing now would be tone-deaf.

Return only the JSON object as specified in your system prompt."""
    
    response = client.messages.create(
        model=SENSITIVITY_MODEL,
        max_tokens=2000,
        system=system_prompt,
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 5,
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )
    
    final_text = _extract_text_blocks(response.content)
    parsed = _parse_sensitivity_json(final_text)
    
    # Normalize status
    status = parsed.get("status", "SAFE").upper().strip()
    if status not in ("SAFE", "CAUTION", "HOLD"):
        status = "SAFE"
    
    reasoning = parsed.get("reasoning", "")
    relevant_events = parsed.get("relevant_events", []) or []
    search_queries = parsed.get("search_queries_used", []) or []
    
    # Build audit comment to embed in HTML
    audit_lines = [
        "TOPICAL SENSITIVITY AUDIT (Phase 5)",
        "=" * 50,
        f"Status: {status}",
        f"Reasoning: {reasoning}",
    ]
    if relevant_events:
        audit_lines.append("Relevant recent events:")
        for event in relevant_events:
            audit_lines.append(f"  - {event}")
    if search_queries:
        audit_lines.append("Search queries used:")
        for q in search_queries:
            audit_lines.append(f"  - {q}")
    
    audit_comment = "<!--\n" + "\n".join(audit_lines) + "\n-->"
    
    tokens_input = response.usage.input_tokens
    tokens_output = response.usage.output_tokens
    cost = _estimate_cost(SENSITIVITY_MODEL, tokens_input, tokens_output)
    
    return {
        "status": status,
        "reasoning": reasoning,
        "relevant_events": relevant_events,
        "search_queries_used": search_queries,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "cost_usd": cost,
        "model": SENSITIVITY_MODEL,
        "audit_comment": audit_comment,
    }


def embed_audit_comment(html: str, audit_comment: str) -> str:
    """Insert the sensitivity audit comment near the top of the HTML, after any existing audit comments."""
    # Find the last existing HTML comment near the top, insert after it
    # Otherwise, insert right after <!doctype html> or at the very start
    
    # Pattern: find <!doctype html> or <!DOCTYPE html>
    doctype_match = re.search(r"<!doctype\s+html[^>]*>", html, re.IGNORECASE)
    if doctype_match:
        insert_pos = doctype_match.end()
        # Skip past any existing audit comments right after doctype
        comment_pattern = re.compile(r"\s*<!--[^>]*?-->\s*", re.DOTALL)
        while True:
            remaining = html[insert_pos:]
            m = comment_pattern.match(remaining)
            if m:
                insert_pos += m.end()
            else:
                break
        return html[:insert_pos] + "\n" + audit_comment + "\n" + html[insert_pos:]
    
    # No doctype — just prepend
    return audit_comment + "\n" + html
