"""V0.7a single-course, read-only Notion → PDF match preview.

All IDs are server configured. Never accept arbitrary Notion page IDs or PDF URLs
from browser input. Files are downloaded on demand; no signed URL is persisted.
"""
from __future__ import annotations

import os
import httpx
from urllib.parse import urlparse

from .notion_notes_readonly import _clean_id, extract_summary_blocks, NOTION_VERSION
from .paragraph_matcher import match_best_paragraph
from .pdf_crops import crop_candidate
from .v07a_note_sections import extract_matching_notes

PDF_MAX_BYTES = 15 * 1024 * 1024


def _title(prop: dict) -> str:
    return "".join(x.get("plain_text", x.get("text", {}).get("content", ""))
                   for x in prop.get("title", []) or prop.get("rich_text", []))


def _select(prop: dict) -> str:
    return (prop.get("select") or {}).get("name", "")


def _file_url(prop: dict) -> str:
    files = prop.get("files") or []
    if len(files) != 1:
        raise ValueError("Textbook must have exactly one PDF")
    item = files[0]
    url = (item.get("file") or item.get("external") or {}).get("url", "")
    if not url.startswith("https://"):
        raise ValueError("Invalid textbook file URL")
    return url


async def inspect_bound_course(candidate_index: int | None = None) -> dict | tuple[dict, bytes]:
    token = os.getenv("NOTION_INTEGRATION_TOKEN", "").strip()
    note_id = _clean_id(os.getenv("NOTION_TEST_NOTE_PAGE_ID", ""))
    textbook_id = _clean_id(os.getenv("NOTION_TEST_TEXTBOOK_PAGE_ID", ""))
    expected_course = os.getenv("NOTION_TEST_COURSE", "").strip()
    if not token or not expected_course:
        raise ValueError("Configure integration token and expected course")
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION}
    async with httpx.AsyncClient(timeout=25, follow_redirects=False) as client:
        note_page = await client.get(f"https://api.notion.com/v1/pages/{note_id}", headers=headers)
        note_page.raise_for_status()
        textbook = await client.get(f"https://api.notion.com/v1/pages/{textbook_id}", headers=headers)
        textbook.raise_for_status()
        props = textbook.json().get("properties", {})
        title = _title(props.get("教材名称", {}))
        course = _select(props.get("所属课程", {}))
        if not title or course != expected_course:
            raise ValueError("Textbook title or course binding does not match")
        url = _file_url(props.get("原版PDF", {}))
        note_blocks = await client.get(f"https://api.notion.com/v1/blocks/{note_id}/children",
                                       params={"page_size": 100}, headers=headers)
        note_blocks.raise_for_status()
        body = note_blocks.json()
        if body.get("has_more"):
            raise ValueError("Note has more than 100 blocks; review incomplete")
        notes_text = extract_matching_notes(body.get("results", []))
        # The URL is a short-lived Notion-signed URL from a trusted Notion API
        # response. Never accept arbitrary client-supplied URLs.
        if urlparse(url).hostname not in {"secure.notion-static.com",
                                            "prod-files-secure-apne1.s3.ap-northeast-1.amazonaws.com",
                                            "prod-files-secure.s3.us-west-2.amazonaws.com"}:
            raise ValueError("PDF host is not on the approved Notion file host list")
        async with client.stream("GET", url) as pdf_response:
            pdf_response.raise_for_status()
            parts = []
            size = 0
            async for part in pdf_response.aiter_bytes():
                size += len(part)
                if size > PDF_MAX_BYTES:
                    raise ValueError("PDF exceeds 15MB")
                parts.append(part)
            pdf = b"".join(parts)
    if not pdf.startswith(b"%PDF-"):
        raise ValueError("Not a PDF file")
    summary, _ = match_best_paragraph(pdf, notes_text)
    result = {
        "note_page_id": note_id,
        "textbook_page_id": textbook_id,
        "course": course,
        "textbook": title,
        "note_last_edited_time": note_page.json().get("last_edited_time"),
        "note_summary_lines": len(notes_text.splitlines()),
        "pdf_page_count": summary["page_count"],
        "candidates": summary["candidates"],
        "matching_method": summary["matching_method"],
        "requires_confirmation": True,
        "notion_write_enabled": False,
        "warning": "Read-only preview. Full AI Meeting Notes may not be exposed as top-level blocks.",
    }
    if candidate_index is None:
        return result
    meta, png = crop_candidate(pdf, notes_text, candidate_index)
    return {**result, "selected_candidate": meta}, png
