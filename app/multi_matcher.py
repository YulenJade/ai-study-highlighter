"""V0.4 multi-note lexical paragraph matching, grounded in source PDF blocks.

No external AI or semantic model. Results must be reviewed before publishing.
"""
from __future__ import annotations

from collections import Counter
from io import BytesIO

import fitz

from .highlighter import COLORS, extract_items
from .paragraph_matcher import _extract_paragraphs, _terms, MAX_PAGES, MAX_PARAGRAPHS

MAX_ITEMS = 40
MIN_SCORE = 0.12


def match_multiple(pdf_bytes: bytes, notes: str, annotate: bool = False):
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Not a PDF file")
    if len(notes) > 10000:
        raise ValueError("Notes too long")
    items = extract_items(notes)
    if not items:
        raise ValueError("Provide separate note lines of 2-200 characters")
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
        indexed = [(p, Counter(_terms(p["text"]))) for p in paragraphs]
        results = []
        selected = set()
        for item in items[:MAX_ITEMS]:
            terms = Counter(_terms(item.text))
            total = sum(terms.values())
            ranked = []
            for i, (paragraph, counts) in enumerate(indexed):
                overlap = sum(min(n, counts.get(term, 0)) for term, n in terms.items())
                if overlap and total:
                    score = overlap / total
                    ranked.append((score, overlap, i, paragraph))
            ranked.sort(key=lambda x: (-x[0], -x[1], x[3]["page"], x[2]))
            best = next((x for x in ranked if x[0] >= MIN_SCORE and x[2] not in selected), None)
            result = {"note": item.text, "category": item.category, "matched": bool(best)}
            if best:
                score, _, idx, paragraph = best
                selected.add(idx)
                result.update({
                    "page": paragraph["page"], "text": paragraph["text"],
                    "rect": paragraph["rect"], "score": round(score, 4),
                })
                if annotate:
                    page = doc[paragraph["page"] - 1]
                    rect = paragraph["_rect"] & page.rect
                    if not rect.is_empty:
                        ann = page.add_highlight_annot(rect)
                        ann.set_colors(stroke=COLORS[item.category])
                        ann.update()
            results.append(result)
        output = doc.tobytes(garbage=4, deflate=True) if annotate else None
        return {
            "page_count": doc.page_count,
            "note_count": len(results),
            "match_count": sum(r["matched"] for r in results),
            "matched_pages": sorted({r["page"] for r in results if r["matched"]}),
            "results": results,
            "matching_method": "lexical_bigram_not_semantic_ai",
            "requires_confirmation": True,
            "truncated": len(paragraphs) >= MAX_PARAGRAPHS,
        }, output
    finally:
        doc.close()
