"""
Google Sheets I/O for the blog agent.

Reads the topic queue, writes status updates, logs generation events,
and feeds brand voice + published index back to other agents.

Authentication: uses a Google Cloud service account JSON credential
provided as the GOOGLE_CREDENTIALS_JSON environment variable.

The service account must be shared on the target Google Sheet as an Editor.
"""

import json
import os
from datetime import datetime
from typing import Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


SHEET_ID = os.environ["BLOG_AGENT_SHEET_ID"]  # set as GitHub secret

# Tab names — these must match exactly what the user creates in the Sheet
TAB_TOPICS = "Blog Topics"
TAB_LOG = "Generation Log"
TAB_PUBLISHED = "Published Index"
TAB_BRAND_VOICE = "Brand Voice Bank"
TAB_STATUTES = "Statute Reference"


def _client():
    """Build an authenticated Sheets API client."""
    creds_json = os.environ["GOOGLE_CREDENTIALS_JSON"]
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds).spreadsheets()


def _read_tab(tab_name: str) -> list[list[str]]:
    """Return all rows of a tab as a list of lists. Row 0 is the header row."""
    svc = _client()
    result = svc.values().get(
        spreadsheetId=SHEET_ID,
        range=tab_name,
    ).execute()
    return result.get("values", [])


def _update_cell(tab_name: str, row_idx: int, col_letter: str, value: str):
    """Update a single cell. row_idx is 1-indexed in spreadsheet terms."""
    svc = _client()
    svc.values().update(
        spreadsheetId=SHEET_ID,
        range=f"{tab_name}!{col_letter}{row_idx}",
        valueInputOption="USER_ENTERED",
        body={"values": [[value]]},
    ).execute()


def _append_row(tab_name: str, row: list):
    """Append a row to the bottom of a tab."""
    svc = _client()
    svc.values().append(
        spreadsheetId=SHEET_ID,
        range=tab_name,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def get_next_queued_topic() -> Optional[dict]:
    """
    Find the highest-priority Queued topic.
    Returns dict with topic, target_keyword, priority, notes, and the 1-indexed
    spreadsheet row for later status updates.
    Returns None if no Queued topics exist.

    Expected 'Blog Topics' tab columns (row 1 = headers):
      A: Status
      B: Topic
      C: Target Keyword
      D: Priority   (High / Medium / Low)
      E: Notes
      F: Date Generated
      G: Draft URL
      H: Date Published
      I: Published URL
    """
    rows = _read_tab(TAB_TOPICS)
    if not rows or len(rows) < 2:
        return None

    priority_order = {"High": 0, "Medium": 1, "Low": 2, "": 3}
    candidates = []
    for idx, row in enumerate(rows[1:], start=2):  # spreadsheet row 2+
        # Pad row to expected length
        padded = row + [""] * (9 - len(row))
        status = padded[0].strip()
        if status.lower() == "queued":
            candidates.append({
                "row_idx": idx,
                "topic": padded[1].strip(),
                "target_keyword": padded[2].strip(),
                "priority": padded[3].strip(),
                "notes": padded[4].strip(),
            })

    if not candidates:
        return None

    # Sort by priority, then by row index (FIFO within priority)
    candidates.sort(key=lambda c: (priority_order.get(c["priority"], 3), c["row_idx"]))
    return candidates[0]


def update_topic_status(
    row_idx: int,
    status: str,
    draft_url: Optional[str] = None,
    published_url: Optional[str] = None,
):
    """Update the status and metadata for a topic row."""
    _update_cell(TAB_TOPICS, row_idx, "A", status)

    if status.lower() in ("generating", "drafted", "draftedreviewneeded"):
        _update_cell(TAB_TOPICS, row_idx, "F", datetime.now().strftime("%Y-%m-%d"))
    if draft_url:
        _update_cell(TAB_TOPICS, row_idx, "G", draft_url)
    if status.lower() == "published":
        _update_cell(TAB_TOPICS, row_idx, "H", datetime.now().strftime("%Y-%m-%d"))
    if published_url:
        _update_cell(TAB_TOPICS, row_idx, "I", published_url)


def log_generation(
    topic: str,
    status: str,
    tokens_input: int = 0,
    tokens_output: int = 0,
    cost_usd: float = 0.0,
    notes: str = "",
):
    """Append a row to the Generation Log tab.

    Expected 'Generation Log' tab columns (row 1 = headers):
      A: Timestamp
      B: Topic
      C: Status   (Success / Failed)
      D: Tokens In
      E: Tokens Out
      F: Cost USD
      G: Notes
    """
    _append_row(TAB_LOG, [
        datetime.now().isoformat(timespec="seconds"),
        topic,
        status,
        tokens_input,
        tokens_output,
        f"${cost_usd:.4f}",
        notes,
    ])


def get_brand_voice_samples() -> list[str]:
    """
    Read approved brand voice samples for Editor/Writer agents to match.

    Expected 'Brand Voice Bank' tab columns (row 1 = headers):
      A: Sample Text
      B: Source (where it came from — consultation page, attorney bio, etc.)
      C: Notes
    """
    rows = _read_tab(TAB_BRAND_VOICE)
    if not rows or len(rows) < 2:
        return []
    return [row[0].strip() for row in rows[1:] if row and row[0].strip()]


def get_published_index() -> list[dict]:
    """
    Read the index of published posts to avoid duplication / contradictions.

    Expected 'Published Index' tab columns (row 1 = headers):
      A: Title
      B: Slug
      C: Date Published
      D: Target Keyword
      E: Key Claims (summary)
      F: Statutes Cited
    """
    rows = _read_tab(TAB_PUBLISHED)
    if not rows or len(rows) < 2:
        return []
    out = []
    for row in rows[1:]:
        padded = row + [""] * (6 - len(row))
        if padded[0].strip():
            out.append({
                "title": padded[0].strip(),
                "slug": padded[1].strip(),
                "date_published": padded[2].strip(),
                "target_keyword": padded[3].strip(),
                "key_claims": padded[4].strip(),
                "statutes_cited": padded[5].strip(),
            })
    return out


def append_to_published_index(
    title: str,
    slug: str,
    target_keyword: str,
    key_claims: str = "",
    statutes_cited: str = "",
):
    """Add a newly published post to the index (called after PR merge or manual publish)."""
    _append_row(TAB_PUBLISHED, [
        title,
        slug,
        datetime.now().strftime("%Y-%m-%d"),
        target_keyword,
        key_claims,
        statutes_cited,
    ])


def get_statute_references() -> list[dict]:
    """
    Read curated Texas statute reference list — ground truth for Citation agent.

    Expected 'Statute Reference' tab columns (row 1 = headers):
      A: Citation (e.g., "Texas CPRC § 16.003")
      B: Description
      C: Common Topic Tags (comma-separated)
    """
    rows = _read_tab(TAB_STATUTES)
    if not rows or len(rows) < 2:
        return []
    out = []
    for row in rows[1:]:
        padded = row + [""] * (3 - len(row))
        if padded[0].strip():
            out.append({
                "citation": padded[0].strip(),
                "description": padded[1].strip(),
                "tags": padded[2].strip(),
            })
    return out
