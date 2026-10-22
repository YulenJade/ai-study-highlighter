"""Verified literal PDF matches with page metadata and colored annotations."""
from dataclasses import dataclass
import re

import fitz

MAX_PAGES = 2000
MAX_TERMS = 40
MAX_MATCHES = 1000

COLORS = {
    "key": (1.0, 0.84, 0.20),
    "definition": (0.36, 0.82, 0.48),
    "extra": (0.42, 0.68, 1.0),
}
LABELS = {"key": "重点", "definition": "定义", "extra": "补充"}
PREFIXES = {
    "定义": "definition", "definition": "definition",
    "补充": "extra", "extra": "extra",
    "重点": "key", "key": "key",
}


@dataclass(frozen=True)
class Term:
    text: str
    category: str


def extract_items(notes: str) -> list[Term]:
    """One exact phrase per line; optional [重点]/[定义]/[补充] prefix."""
    items: list[Term] = []
    for raw in notes.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)、])\s*", "", raw).strip()
        category = "key"
        m = re.match(r"^\[(重点|定义|补充|key|definition|extra)\]\s*", line, re.I)
        if m:
            category = PREFIXES[m.group(1).lower()]
            line = line[m.end():].strip()
        if 2 <= len(line) <= 200:
            item = Term(line, category)
            if item not in items:
                items.append(item)
        if len(items) >= MAX_TERMS:
            break
    return items


def analyze_pdf(data: bytes, notes: str, annotate: bool = False) -> tuple[dict, bytes | None]:
    if not data.startswith(b"%PDF-"):
        raise ValueError("Not a PDF file")
    items = extract_items(notes)
    if not items:
        raise ValueError("Provide one or more phrases of 2-200 characters")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError("Cannot open PDF") from exc
    try:
        if doc.needs_pass:
            raise ValueError("Password-protected PDF is not supported")
        if doc.page_count > MAX_PAGES:
            raise ValueError("PDF exceeds page limit")
        matches: list[dict] = []
        truncated = False
        for page_index, page in enumerate(doc):
            for item in items:
                # search_for uses PDF text extraction; no hallucinated passages.
                quads = page.search_for(item.text, quads=True)
                for quad in quads:
                    if len(matches) >= MAX_MATCHES:
                        truncated = True
                        break
                    rect = quad.rect
                    matches.append({
                        "page": page_index + 1,
                        "text": item.text,
                        "category": item.category,
                        "label": LABELS[item.category],
                        "rect": [round(rect.x0, 2), round(rect.y0, 2),
                                 round(rect.x1, 2), round(rect.y1, 2)],
                    })
                    if annotate:
                        annotation = page.add_highlight_annot(quad)
                        annotation.set_colors(stroke=COLORS[item.category])
                        annotation.update()
                if truncated:
                    break
            if truncated:
                break
        summary = {
            "page_count": doc.page_count,
            "match_count": len(matches),
            "matched_pages": sorted({m["page"] for m in matches}),
            "unmatched_terms": [item.text for item in items
                                if not any(m["text"] == item.text for m in matches)],
            "truncated": truncated,
            "matches": matches,
        }
        output = doc.tobytes(garbage=4, deflate=True) if annotate else None
        return summary, output
    finally:
        doc.close()
