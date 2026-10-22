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


def multi_result_blocks(summary: dict, book_title: str, selected_indices: list[int]) -> list[dict]:
    """Build Notion blocks only for explicitly selected, source-backed matches."""
    results = summary.get("results", [])
    if not selected_indices or len(selected_indices) > 40:
        raise ValueError("Select between 1 and 40 matching paragraphs")
    if len(set(selected_indices)) != len(selected_indices):
        raise ValueError("Duplicate selection")
    if any(type(i) is not int or i < 0 or i >= len(results) for i in selected_indices):
        raise ValueError("Invalid selected index")
    selected = [results[i] for i in selected_indices]
    if any(not r.get("matched") for r in selected):
        raise ValueError("Cannot publish an unmatched paragraph")
    blocks = [
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": _rich("AI Study Highlighter · 已确认教材重点")}},
        {"object": "block", "type": "paragraph",
         "paragraph": {"rich_text": _rich("教材 / Book: " + book_title[:150])}},
    ]
    for r in selected:
        blocks.extend([
            {"object": "block", "type": "heading_3",
             "heading_3": {"rich_text": _rich(f"第 {r['page']} 页 · {r['category']}")}},
            {"object": "block", "type": "paragraph",
             "paragraph": {"rich_text": _rich("课堂笔记 / Note: " + r["note"])}},
            {"object": "block", "type": "quote",
             "quote": {"rich_text": _rich(r["text"])}},
        ])
    blocks.append({"object": "block", "type": "paragraph",
                   "paragraph": {"rich_text": _rich("逐条人工确认后发布；匹配方法为词语重合，并非语义 AI。")}})
    return blocks


async def append_multi_result(page_id: str, summary: dict, book_title: str,
                              selected_indices: list[int]) -> dict:
    token = os.getenv("NOTION_INTEGRATION_TOKEN", "").strip()
    if not token:
        raise ValueError("Notion integration is not configured")
    clean = page_id.replace("-", "")
    if not PAGE_ID.fullmatch(clean):
        raise ValueError("Invalid Notion page ID")
    blocks = multi_result_blocks(summary, book_title, selected_indices)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.patch(
            f"https://api.notion.com/v1/blocks/{clean}/children",
            headers={"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION,
                     "Content-Type": "application/json"},
            json={"children": blocks},
        )
        response.raise_for_status()
    return {"page_id": clean, "blocks_added": len(blocks),
            "highlights_added": len(selected_indices)}
