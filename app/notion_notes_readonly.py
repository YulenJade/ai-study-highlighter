"""Read-only Notion AI notes access probe for a single explicitly configured page.

Never assume the chat connector and the Render integration share permissions.
"""
from __future__ import annotations

import os
import re
import httpx

NOTION_VERSION = "2022-06-28"
ID_RE = re.compile(r"^[0-9a-fA-F]{32}$")


def _clean_id(raw: str) -> str:
    value = raw.replace("-", "")
    if not ID_RE.fullmatch(value):
        raise ValueError("Invalid configured Notion page ID")
    return value


def _plain(rich_text: list) -> str:
    return "".join(part.get("plain_text", "") for part in rich_text if isinstance(part, dict))


def extract_summary_blocks(blocks: list[dict], limit: int = 25) -> list[str]:
    """Extract summary-like rich text, never traverse transcript child blocks."""
    lines = []
    for block in blocks:
        kind = block.get("type")
        if kind not in {"paragraph", "heading_1", "heading_2", "heading_3",
                        "bulleted_list_item", "numbered_list_item", "to_do", "quote"}:
            continue
        text = _plain(block.get(kind, {}).get("rich_text", []))
        if text.strip():
            lines.append(text[:500])
        if len(lines) >= limit:
            break
    return lines


async def inspect_configured_note() -> dict:
    token = os.getenv("NOTION_INTEGRATION_TOKEN", "").strip()
    configured = os.getenv("NOTION_TEST_NOTE_PAGE_ID", "").strip()
    if not token or not configured:
        raise ValueError("Configure NOTION_INTEGRATION_TOKEN and NOTION_TEST_NOTE_PAGE_ID")
    page_id = _clean_id(configured)
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION}
    async with httpx.AsyncClient(timeout=15) as client:
        page_response = await client.get(f"https://api.notion.com/v1/pages/{page_id}", headers=headers)
        page_response.raise_for_status()
        blocks_response = await client.get(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            params={"page_size": 100}, headers=headers)
        blocks_response.raise_for_status()
    page = page_response.json()
    blocks = blocks_response.json()
    if blocks.get("has_more"):
        return {"accessible": True, "complete": False,
                "reason": "Page contains more than 100 top-level blocks; inspection is incomplete",
                "note_page_id": page_id, "notion_write_enabled": False}
    lines = extract_summary_blocks(blocks.get("results", []))
    return {"accessible": True, "complete": True, "note_page_id": page_id,
            "last_edited_time": page.get("last_edited_time"),
            "summary_line_count": len(lines),
            "summary_preview": lines[:10],
            "notion_write_enabled": False,
            "caveat": "Only top-level standard blocks; official AI note summary may be nested or inaccessible"}
