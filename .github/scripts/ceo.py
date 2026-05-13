#!/usr/bin/env python3
"""
CEO Orchestrator — Phase 2 (Writer + Editor).

The supervisor agent. This is the entry point GitHub Actions calls.

Phase 2 pipeline:
    1. Get next Queued topic from Google Sheet
    2. If none, log and exit gracefully
    3. Mark topic as "Generating"
    4. Read brand voice samples + published index for Writer context
    5. Call Writer agent
    6. Call Editor agent (polishes voice, removes AI-isms). Falls back to
       Writer's output if Editor fails.
    7. Save HTML to blog/{slug}.html
    8. Regenerate blog/index.html to include the new post
    9. Log generation event (combined tokens, cost for Writer + Editor)
   10. Update topic status to "Drafted" with the file path

The GitHub Actions workflow handles git operations (branch, commit, PR)
AFTER this script exits successfully. This script only writes files.
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
import utils
from writer import write_post
from editor import edit_post


REPO_ROOT = Path(os.environ.get("GITHUB_WORKSPACE", Path(__file__).parent.parent.parent))


def main() -> int:
    print(f"[CEO] Starting Phase 2 pipeline at {datetime.now().isoformat()}")
    print(f"[CEO] Repo root: {REPO_ROOT}")

    # Step 1 — get next topic
    print("[CEO] Step 1: fetching next Queued topic from Sheet...")
    topic_row = sheets.get_next_queued_topic()
    if not topic_row:
        print("[CEO] No Queued topics found. Nothing to do. Exiting gracefully.")
        return 0

    topic = topic_row["topic"]
    target_keyword = topic_row["target_keyword"]
    notes = topic_row["notes"]
    priority = topic_row["priority"]
    row_idx = topic_row["row_idx"]

    print(f"[CEO] Picked topic (priority {priority or 'unset'}): {topic}")

    # Step 2 — mark as generating
    print("[CEO] Step 2: marking topic as 'Generating'...")
    sheets.update_topic_status(row_idx, "Generating")

    try:
        # Step 3 — gather context
        print("[CEO] Step 3: loading brand voice samples + published index...")
        brand_voice_samples = sheets.get_brand_voice_samples()
        published_index = sheets.get_published_index()
        print(f"[CEO]   {len(brand_voice_samples)} brand voice samples loaded")
        print(f"[CEO]   {len(published_index)} previously published posts in index")

        # Step 4 — invoke Writer
        print("[CEO] Step 4: invoking Writer agent...")
        todays_date = datetime.now().strftime("%Y-%m-%d")
        result = write_post(
            topic=topic,
            target_keyword=target_keyword,
            notes=notes,
            todays_date=todays_date,
            brand_voice_samples=brand_voice_samples,
            published_index=published_index,
        )
        print(f"[CEO]   Writer used {result['tokens_input']} input + {result['tokens_output']} output tokens")
        print(f"[CEO]   Writer cost: ${result['cost_usd']:.4f}")

        # Step 4.5 — invoke Editor agent to polish Writer's output
        print("[CEO] Step 4.5: invoking Editor agent...")
        editor_html = result["html"]
        editor_tokens_in = 0
        editor_tokens_out = 0
        editor_cost = 0.0
        try:
            editor_result = edit_post(
                writer_html=result["html"],
                brand_voice_samples=brand_voice_samples,
            )
            editor_html = editor_result["html"]
            editor_tokens_in = editor_result["tokens_input"]
            editor_tokens_out = editor_result["tokens_output"]
            editor_cost = editor_result["cost_usd"]
            print(f"[CEO]   Editor used {editor_tokens_in} input + {editor_tokens_out} output tokens")
            print(f"[CEO]   Editor cost: ${editor_cost:.4f}")
        except Exception as editor_exc:
            print(f"[CEO]   ⚠️  Editor failed: {editor_exc}", file=sys.stderr)
            print(f"[CEO]   Falling back to Writer's unedited draft.", file=sys.stderr)

        # Combine cost tracking
        total_tokens_in = result["tokens_input"] + editor_tokens_in
        total_tokens_out = result["tokens_output"] + editor_tokens_out
        total_cost = result["cost_usd"] + editor_cost
        print(f"[CEO]   Combined cost: ${total_cost:.4f}")

        # Use the Editor's HTML going forward (or Writer's if Editor failed)
        result["html"] = editor_html

        # Step 5 — derive slug + extract meta from generated HTML
        meta = utils.extract_meta(result["html"])
        slug = utils.slugify(meta["h1"] or topic)
        print(f"[CEO] Step 5: generated post slug = {slug}")

        # Step 6 — write the HTML file
        blog_dir = REPO_ROOT / "blog"
        blog_dir.mkdir(exist_ok=True)
        out_path = blog_dir / f"{slug}.html"
        out_path.write_text(result["html"])
        print(f"[CEO] Step 6: wrote {out_path.relative_to(REPO_ROOT)}")

        # Step 7 — regenerate blog index
        publish_date_human = utils.format_human_date(todays_date)
        utils.update_blog_index(
            repo_root=REPO_ROOT,
            new_slug=slug,
            h1=meta["h1"],
            lede=meta["lede"],
            eyebrow=meta["eyebrow"] or "Notes from the firm · 5 min read",
            publish_date_human=publish_date_human,
        )
        print(f"[CEO] Step 7: updated blog/index.html to include new post")

        # Step 8 — log success (combined Writer + Editor stats)
        print("[CEO] Step 8: logging to Generation Log...")
        sheets.log_generation(
            topic=topic,
            status="Success",
            tokens_input=total_tokens_in,
            tokens_output=total_tokens_out,
            cost_usd=total_cost,
            notes=f"Writer: {result['model']} (${result['cost_usd']:.4f}) | Editor: ${editor_cost:.4f} | Slug: {slug}",
        )

        # Step 9 — update topic row
        draft_url = f"https://github.com/voostervu/nalawtx-website/blob/blog-agent/{slug}/blog/{slug}.html"
        sheets.update_topic_status(row_idx, "Drafted", draft_url=draft_url)
        print(f"[CEO] Step 9: topic row marked Drafted")

        # Emit the slug for GitHub Actions to use in branch naming
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"slug={slug}\n")
                f.write(f"title={meta['h1']}\n")
                f.write(f"topic={topic}\n")

        print(f"[CEO] ✅ Pipeline complete. Post draft at blog/{slug}.html")
        return 0

    except Exception as exc:
        print(f"[CEO] ❌ Pipeline failed: {exc}", file=sys.stderr)
        traceback.print_exc()

        # Roll back the topic status so it's retried next run
        try:
            sheets.update_topic_status(row_idx, "Queued")
            sheets.log_generation(
                topic=topic,
                status="Failed",
                notes=f"{type(exc).__name__}: {exc}"[:500],
            )
        except Exception:
            print("[CEO] (Also failed to update Sheet status — manual cleanup may be needed)", file=sys.stderr)

        return 1


if __name__ == "__main__":
    sys.exit(main())
