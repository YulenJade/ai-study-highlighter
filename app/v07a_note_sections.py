"""Extract only explicitly scoped note content for PDF matching.

Avoid matching test instructions, metadata, task checklists, and result placeholders.
This is a deterministic read-only parser, not a claim to parse native AI Meeting Notes.
"""
from __future__ import annotations


def _plain(block: dict) -> str:
    kind = block.get("type", "")
    payload = block.get(kind) or {}
    return "".join(x.get("plain_text", "") for x in payload.get("rich_text", []))


def extract_matching_notes(blocks: list[dict], max_chars: int = 8000) -> str:
    """Prefer the simulated classroom-record section; fall back to standard prose.

    The fallback deliberately excludes checklist items, headings, and metadata.
    """
    section, found, lines = False, False, []
    for block in blocks:
        kind = block.get("type", "")
        text = _plain(block).strip()
        if kind.startswith("heading_"):
            if "模拟课堂记录" in text or "课堂重点" in text:
                section, found = True, True
            elif section:
                break
            continue
        if not section or kind not in {"paragraph", "numbered_list_item", "bulleted_list_item"}:
            continue
        if text:
            lines.append(text)
    if not found:
        # No recognized section: avoid pretending to understand unknown layouts.
        raise ValueError("No recognized classroom-note section; manual review required")
    notes = "\n".join(lines)
    if not notes.strip() or len(notes) > max_chars:
        raise ValueError("No usable classroom note content")
    return notes
