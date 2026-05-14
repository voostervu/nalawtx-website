#!/usr/bin/env python3
"""
Researcher runner — entry point for the weekly Researcher workflow.

This script:
    1. Reads the Topic Seed Ideas tab for evergreen topic concepts
    2. Reads the Published Index to avoid duplicates
    3. Reads the current Blog Topics queue (all statuses) to avoid duplicates
    4. Calls the Researcher agent (uses web search + curated inputs)
    5. Writes 3-5 new Queued topics to the Blog Topics tab
    6. Logs the run to the Generation Log tab

This runs on a SEPARATE schedule from the blog agent — typically
Saturday afternoons, so new topics are queued before Monday's blog generation.

This script has its own error handling — failures are logged and the workflow
will notify via the same failure notification system as the blog agent.
"""

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Make sibling scripts importable
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

import sheets
from researcher import research_topics


def main() -> int:
    print(f"[Researcher] Starting Researcher run at {datetime.now().isoformat()}")

    try:
        # Step 1 — load Topic Seed Ideas
        print("[Researcher] Step 1: loading Topic Seed Ideas...")
        topic_seeds = sheets.get_topic_seed_ideas()
        print(f"[Researcher]   {len(topic_seeds)} seed topics loaded")

        # Step 2 — load Published Index
        print("[Researcher] Step 2: loading Published Index...")
        published_index = sheets.get_published_index()
        print(f"[Researcher]   {len(published_index)} previously published posts loaded")

        # Step 3 — load current Blog Topics queue (all statuses)
        print("[Researcher] Step 3: loading current Blog Topics queue...")
        current_queue = sheets.get_all_blog_topics()
        print(f"[Researcher]   {len(current_queue)} topics currently in queue")

        # Step 4 — call Researcher
        print("[Researcher] Step 4: invoking Researcher agent (with web search)...")
        result = research_topics(
            topic_seeds=topic_seeds,
            published_index=published_index,
            current_queue=current_queue,
        )
        print(f"[Researcher]   Used {result['tokens_input']} input + {result['tokens_output']} output tokens")
        print(f"[Researcher]   Cost: ${result['cost_usd']:.4f}")
        print(f"[Researcher]   Returned {len(result['topics'])} topic proposals")

        # Step 5 — write new topics to Blog Topics tab
        print("[Researcher] Step 5: writing new topics to Blog Topics tab...")
        added_count = 0
        for topic in result["topics"]:
            try:
                sheets.append_blog_topic(
                    status="Queued",
                    topic=topic.get("topic", ""),
                    target_keyword=topic.get("target_keyword", ""),
                    priority=topic.get("priority", "Medium"),
                    notes=f"[Researcher] {topic.get('notes', '')} (source: {topic.get('source', 'unknown')})",
                )
                added_count += 1
                print(f"[Researcher]   ✅ Added: {topic.get('topic', '')[:80]}")
            except Exception as exc:
                print(f"[Researcher]   ⚠️  Failed to add topic: {exc}", file=sys.stderr)

        # Step 6 — log the run
        print("[Researcher] Step 6: logging to Generation Log...")
        sheets.log_generation(
            topic=f"[Researcher run] {added_count} new topics queued",
            status="Success",
            tokens_input=result["tokens_input"],
            tokens_output=result["tokens_output"],
            cost_usd=result["cost_usd"],
            notes=f"Researcher: {result['model']} | Added {added_count}/{len(result['topics'])} topics",
        )

        print(f"[Researcher] ✅ Run complete. {added_count} new topics queued.")
        return 0

    except Exception as exc:
        print(f"[Researcher] ❌ Run failed: {exc}", file=sys.stderr)
        traceback.print_exc()

        # Log the failure
        try:
            sheets.log_generation(
                topic="[Researcher run] FAILED",
                status="Failed",
                notes=f"{type(exc).__name__}: {exc}"[:500],
            )
        except Exception:
            print("[Researcher] (Also failed to log to Sheet — manual cleanup may be needed)", file=sys.stderr)

        return 1


if __name__ == "__main__":
    sys.exit(main())
