#!/usr/bin/env python3
"""
CEO orchestrator — runs the full blog generation pipeline.

Pipeline:
    Writer → Editor → Humanizer → Compliance → save HTML → update blog index

Each step is fail-tolerant: if a later step crashes, we fall back to the previous
step's output. Better to ship slightly-less-polished content than nothing.

Outputs to GITHUB_OUTPUT (for use by the workflow):
    slug    - the URL-safe slug
    topic   - the topic title (for commit message)
    title   - same as topic, formatted for display
"""

import os
import sys
import traceback
from pathlib import Path

# Make sibling scripts importable
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

import sheets
import utils
from writer import write_post
from editor import edit_post
from humanizer import humanize
from compliance import compliance_audit


REPO_ROOT = Path(__file__).resolve().parents[2]


def set_github_output(key: str, value: str):
    """Write a key=value pair to GITHUB_OUTPUT for the workflow to consume."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a") as f:
            # Escape multiline values
            if "\n" in value:
                f.write(f"{key}<<EOF\n{value}\nEOF\n")
            else:
                f.write(f"{key}={value}\n")


def main() -> int:
    print("[CEO] Starting blog generation pipeline")

    # Step 1 — get next topic from queue
    print("[CEO] Step 1: fetching next queued topic from Sheet...")
    topic_row = sheets.get_next_queued_topic()
    if not topic_row:
        print("[CEO] No queued topics. Exiting cleanly.")
        return 0

    topic = topic_row["topic"]
    target_keyword = topic_row["target_keyword"]
    row_idx = topic_row["row_idx"]
    print(f"[CEO]   Selected: {topic}")

    # Mark as Generating
    sheets.update_topic_status(row_idx, "Generating")

    try:
        # Step 2 — load brand voice + published index for Writer
        print("[CEO] Step 2: loading brand voice and published index...")
        brand_voice = sheets.get_brand_voice_samples()
        published = sheets.get_published_index()
        statutes = sheets.get_statute_references()
        print(f"[CEO]   {len(brand_voice)} voice samples, {len(published)} previously published, {len(statutes)} statutes")

        # Step 3 — Writer
        print("[CEO] Step 3: Writer is drafting...")
        writer_result = write_post(
            topic=topic,
            target_keyword=target_keyword,
            brand_voice_samples=brand_voice,
            published_index=published,
        )
        current_html = writer_result["html"]
        slug = writer_result["slug"]
        title = writer_result["title"]
        total_tokens_in = writer_result["tokens_input"]
        total_tokens_out = writer_result["tokens_output"]
        total_cost = writer_result["cost_usd"]
        print(f"[CEO]   Writer: ${writer_result['cost_usd']:.4f}")

        # Step 4 — Editor
        print("[CEO] Step 4: Editor is polishing...")
        try:
            editor_result = edit_post(
                html_content=current_html,
                brand_voice_samples=brand_voice,
            )
            current_html = editor_result["html"]
            total_tokens_in += editor_result["tokens_input"]
            total_tokens_out += editor_result["tokens_output"]
            total_cost += editor_result["cost_usd"]
            print(f"[CEO]   Editor: ${editor_result['cost_usd']:.4f}")
        except Exception as exc:
            print(f"[CEO]   ⚠️  Editor failed: {exc}. Continuing with Writer output.", file=sys.stderr)

        # Step 4.5 — Humanizer (NEW)
        print("[CEO] Step 4.5: Humanizer is removing AI tells...")
        try:
            humanizer_result = humanize(
                html_content=current_html,
                brand_voice_samples=brand_voice,
            )
            current_html = humanizer_result["html"]
            total_tokens_in += humanizer_result["tokens_input"]
            total_tokens_out += humanizer_result["tokens_output"]
            total_cost += humanizer_result["cost_usd"]
            
            det_stats = humanizer_result["deterministic_stats"]
            print(f"[CEO]   Humanizer: ${humanizer_result['cost_usd']:.4f}")
            print(f"[CEO]   Safety net caught: {det_stats['em_dashes_removed']} em dashes, "
                  f"{det_stats['en_dashes_removed']} en dashes, "
                  f"{det_stats['smart_quotes_replaced']} smart quotes")
        except Exception as exc:
            print(f"[CEO]   ⚠️  Humanizer failed: {exc}. Continuing with Editor output.", file=sys.stderr)

        # Step 5 — Compliance + Citation
        print("[CEO] Step 5: Compliance is auditing...")
        try:
            compliance_result = compliance_audit(
                html_content=current_html,
                statute_references=statutes,
            )
            current_html = compliance_result["html"]
            total_tokens_in += compliance_result["tokens_input"]
            total_tokens_out += compliance_result["tokens_output"]
            total_cost += compliance_result["cost_usd"]
            print(f"[CEO]   Compliance: ${compliance_result['cost_usd']:.4f}")
            print(f"[CEO]   Audit status: {compliance_result.get('summary_status', 'unknown')}")
        except Exception as exc:
            print(f"[CEO]   ⚠️  Compliance failed: {exc}. Continuing with humanized output.", file=sys.stderr)

        # Step 6 — save HTML to blog folder
        print("[CEO] Step 6: writing post to blog folder...")
        blog_dir = REPO_ROOT / "blog"
        blog_dir.mkdir(exist_ok=True)
        post_path = blog_dir / f"{slug}.html"
        post_path.write_text(current_html, encoding="utf-8")
        print(f"[CEO]   Saved to: {post_path}")

        # Step 7 — update blog/index.html
        print("[CEO] Step 7: updating blog index...")
        try:
            utils.update_blog_index(blog_dir, title, slug)
        except Exception as exc:
            print(f"[CEO]   ⚠️  Blog index update failed: {exc}. Post saved but index not refreshed.", file=sys.stderr)

        # Step 8 — log to Sheet
        print("[CEO] Step 8: logging to Generation Log...")
        sheets.log_generation(
            topic=topic,
            status="Success",
            tokens_input=total_tokens_in,
            tokens_output=total_tokens_out,
            cost_usd=total_cost,
            notes=f"Slug: {slug} | Pipeline: Writer→Editor→Humanizer→Compliance",
        )

        # Step 9 — update Sheet status
        published_url = f"https://nalawtx.com/blog/{slug}"
        sheets.update_topic_status(row_idx, "Drafted", draft_url=published_url)

        # Step 10 — write outputs for workflow
        set_github_output("slug", slug)
        set_github_output("topic", topic)
        set_github_output("title", title)

        print(f"[CEO] ✅ Pipeline complete. Total cost: ${total_cost:.4f}")
        print(f"[CEO]    Tokens: {total_tokens_in} in, {total_tokens_out} out")
        return 0

    except Exception as exc:
        print(f"[CEO] ❌ Pipeline failed: {exc}", file=sys.stderr)
        traceback.print_exc()

        # Mark topic as Queued again so it'll be picked up next run
        try:
            sheets.update_topic_status(row_idx, "Queued")
        except Exception:
            pass

        # Log the failure
        try:
            sheets.log_generation(
                topic=topic,
                status="Failed",
                notes=f"{type(exc).__name__}: {exc}"[:500],
            )
        except Exception:
            pass

        return 1


if __name__ == "__main__":
    sys.exit(main())
