"""Scoped automatic Notion note discovery, read-only.

The public Notion search endpoint is NOT an AI Meeting Notes index. This
discovers only pages shared with the Render integration, then checks ancestry
against explicitly configured course page IDs.
"""
from __future__ import annotations

import json
import os
import httpx

from .notion_notes_readonly import _clean_id, NOTION_VERSION


def parse_course_bindings(raw: str) -> dict[str, dict]:
    try:
        config = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid NOTION_COURSE_BINDINGS_JSON") from exc
    if not isinstance(config, dict) or not config or len(config) > 30:
        raise ValueError("Configure 1 to 30 course bindings")
    result = {}
    for name, item in config.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(item, dict):
            raise ValueError("Invalid course binding")
        result[name] = {
            "course_page_id": _clean_id(item.get("course_page_id", "")),
            "textbook_page_id": _clean_id(item.get("textbook_page_id", "")),
        }
    if len({v["course_page_id"] for v in result.values()}) != len(result):
        raise ValueError("Duplicate course page IDs")
    return result


def _parent_id(page: dict) -> str | None:
    parent = page.get("parent") or {}
    raw = parent.get("page_id")
    if not raw:
        return None
    try:
        return _clean_id(raw)
    except ValueError:
        return None


async def resolve_course(page: dict, client: httpx.AsyncClient,
                         headers: dict, bindings: dict, depth: int = 8) -> str | None:
    by_id = {v["course_page_id"]: course for course, v in bindings.items()}
    visited = set()
    current = page
    for _ in range(depth):
        pid = _parent_id(current)
        if not pid or pid in visited:
            return None
        if pid in by_id:
            return by_id[pid]
        visited.add(pid)
        response = await client.get(f"https://api.notion.com/v1/pages/{pid}", headers=headers)
        if response.status_code in (403, 404):
            return None
        response.raise_for_status()
        current = response.json()
    return None


def _page_title(page: dict) -> str:
    for prop in (page.get("properties") or {}).values():
        if prop.get("type") == "title":
            return "".join(x.get("plain_text", "") for x in prop.get("title", []))[:160]
    return ""


async def discover_notes() -> dict:
    token = os.getenv("NOTION_INTEGRATION_TOKEN", "").strip()
    if not token:
        raise ValueError("Notion integration token is not configured")
    bindings = parse_course_bindings(os.getenv("NOTION_COURSE_BINDINGS_JSON", ""))
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION}
    results, cursor, scanned = [], None, 0
    async with httpx.AsyncClient(timeout=20) as client:
        # Bounded, manual discovery only; no scheduled polling or writes.
        for _ in range(5):
            params = {"page_size": 100, "filter": {"value": "page", "property": "object"}}
            if cursor:
                params["start_cursor"] = cursor
            response = await client.post("https://api.notion.com/v1/search",
                                         headers=headers, json=params)
            response.raise_for_status()
            body = response.json()
            for page in body.get("results", []):
                scanned += 1
                course = await resolve_course(page, client, headers, bindings)
                if course:
                    results.append({
                        "page_id": _clean_id(page["id"]),
                        "title": _page_title(page),
                        "course": course,
                        "textbook_page_id": bindings[course]["textbook_page_id"],
                        "last_edited_time": page.get("last_edited_time"),
                        "requires_confirmation": True,
                    })
            cursor = body.get("next_cursor") if body.get("has_more") else None
            if not cursor:
                break
    return {
        "pages_scanned": scanned, "notes": results,
        "incomplete": bool(cursor),
        "discovery_method": "shared_pages_under_configured_course_ancestors",
        "warning": "Candidates are not verified official AI Meeting Notes. Confirm note type and summary readability.",
        "notion_write_enabled": False,
    }
