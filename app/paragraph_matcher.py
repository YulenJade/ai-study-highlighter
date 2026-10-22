"""Paragraph-level matching backed by the PDF's own text and coordinates.

This is lexical ranking, not a semantic AI model. A result is always sourced from
the uploaded PDF, and its quads are verified with PyMuPDF before annotation.
"""
from __future__ import annotations

import re
from collections import Counter
from io import BytesIO

import fitz

MAX_PAGES = 300
MAX_PARAGRAPHS = 12000
MAX_NOTE_CHARS = 10000
MAX_TOP_CANDIDATES = 5

def _terms(text: str) -> list[str]:
    """Mixed English/CJK indexing without external embeddings."""
    tokens = re.findall(r"[a-zA-Z0-9]{3,}|[\u3400-\u9fff]+", text.lower())
    output = []
    for token in tokens:
        if re.fullmatch(r"[\u3400-\u9fff]+", token):
            output.extend(token[i:i + 2] for i in range(len(token) - 1))
            if len(token) == 1:
                output.append(token)
        else:
            output.append(token)
    return output

def _extract_paragraphs(doc: fitz.Document) -> list[dict]:
    paragraphs = []
    for page_num, page in enumerate(doc, 1):
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            if block.get("type") != 0:
                continue
            lines = block.get("lines", [])
            spans = [span for line in lines for span in line.get("spans", []) if span.get("text", "").strip()]
            if not spans:
                continue
            text = " ".join(span["text"].strip() for span in spans).strip()
            if len(text) < 8:
                continue
            rects = [fitz.Rect(span["bbox"]) for span in spans]
            rect = fitz.Rect(rects[0])
            for r in rects[1:]:
                rect.include_rect(r)
            paragraphs.append({
                "page": page_num,
                "text": text[:3000],
                "rect": [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)],
                "_rect": rect,
            })
            if len(paragraphs) >= MAX_PARAGRAPHS:
                return paragraphs
    return paragraphs

def match_best_paragraph(pdf_bytes: bytes, notes: str, annotate: bool = False) -> tuple[dict, bytes | None]:
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Not a PDF file")
    if not notes.strip() or len(notes) > MAX_NOTE_CHARS:
        raise ValueError("Notes must contain between 1 and 10000 characters")
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError("Cannot open PDF") from exc
    try:
        if doc.needs_pass:
            raise ValueError("Password-protected PDF is not supported")
        if doc.page_count > MAX_PAGES:
            raise ValueError("PDF exceeds page limit")
        paragraphs = _extract_paragraphs(doc)
        note_counts = Counter(_terms(notes))
        if not note_counts:
            raise ValueError("No searchable note words")
        scored = []
        for p in paragraphs:
            para_counts = Counter(_terms(p["text"]))
            overlap = sum(min(count, para_counts.get(term, 0)) for term, count in note_counts.items())
            if not overlap:
                continue
            # Recall for the notes, with modest preference for denser paragraphs.
            score = overlap / max(1, sum(note_counts.values()))
            score *= 0.75 + 0.25 * min(1.0, overlap / max(1, sum(para_counts.values())) * 5)
            scored.append((score, p))
        scored.sort(key=lambda x: (-x[0], x[1]["page"]))
        best = scored[0] if scored else None
        candidates = [{
            "page": p["page"],
            "text": p["text"],
            "rect": p["rect"],
            "score": round(score, 4),
        } for score, p in scored[:MAX_TOP_CANDIDATES]]
        output = None
        if annotate and best is not None:
            _, paragraph = best
            page = doc[paragraph["page"] - 1]
            rectangle = paragraph["_rect"] & page.rect
            if not rectangle.is_empty:
                annotation = page.add_highlight_annot(rectangle)
                annotation.set_colors(stroke=(1.0, 0.84, 0.20))
                annotation.update()
            output = doc.tobytes(garbage=4, deflate=True)
        elif annotate:
            output = doc.tobytes(garbage=4, deflate=True)
        summary = {
            "page_count": doc.page_count,
            "paragraph_count": len(paragraphs),
            "match_count": 1 if best else 0,
            "matched_pages": [best[1]["page"]] if best else [],
            "best_match": candidates[0] if candidates else None,
            "candidates": candidates,
            "matching_method": "lexical_overlap_not_semantic_ai",
            "requires_confirmation": True,
            "truncated": len(paragraphs) >= MAX_PARAGRAPHS,
        }
        return summary, output
    finally:
        doc.close()
