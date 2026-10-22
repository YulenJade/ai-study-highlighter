"""Opt-in Notion result writer. Server-owned integration; no credentials in browser."""
import os
import re
import httpx

NOTION_VERSION = "2022-06-28"
PAGE_ID = re.compile(r"^[0-9a-fA-F]{32}$")

def _rich(text):
    return [{"type": "text", "text": {"content": text[:1900]}}]

def result_blocks(summary: dict, book_title: str = "Textbook") -> list[dict]:
    best = summary.get("best_match")
    if not best:
        raise ValueError("No paragraph match to publish")
    return [
        {"object": "block", "type": "heading_3", "heading_3": {"rich_text": _rich("AI Study Highlighter · 教材重点")}},
        {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _rich(f"教材 / Book: {book_title[:150]} · 页码 / Page: {best['page']}")}},
        {"object": "block", "type": "quote", "quote": {"rich_text": _rich(best["text"])}},
        {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _rich("机器匹配，仅供复核 / Lexical match — verify against the original PDF.")}},
    ]

async def append_result(page_id: str, summary: dict, book_title: str = "Textbook") -> dict:
    token = os.getenv("NOTION_INTEGRATION_TOKEN", "").strip()
    if not token:
        raise ValueError("Notion integration is not configured")
    clean = page_id.replace("-", "")
    if not PAGE_ID.fullmatch(clean):
        raise ValueError("Invalid Notion page ID")
    blocks = result_blocks(summary, book_title)
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.patch(
            f"https://api.notion.com/v1/blocks/{clean}/children",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            json={"children": blocks},
        )
        response.raise_for_status()
        return {"page_id": clean, "blocks_added": len(blocks)}
