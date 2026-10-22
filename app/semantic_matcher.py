"""Opt-in semantic retrieval using an embedding API; never silently call lexical matching AI.

Server-only API key. The PDF text is sent to the configured embedding provider.
"""
from __future__ import annotations

import math
import os

import fitz
import httpx

from .paragraph_matcher import _extract_paragraphs, _terms, MAX_PAGES

MAX_SEMANTIC_BLOCKS = 120
MAX_CANDIDATES = 5
EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
MODEL = "text-embedding-3-small"


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("Invalid embedding dimensions")
    norm = math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(x*x for x in b))
    return sum(x*y for x, y in zip(a, b)) / norm if norm else 0.0


def _shortlist(paragraphs: list[dict], notes: str) -> list[dict]:
    """Combine lexical recall with coverage across the entire PDF.

    A long textbook cannot be exhaustively embedded per request under this
    cost limit. Reserve 40 slots for evenly distributed paragraphs so sections
    with no shared terms still have some chance of being retrieved.
    """
    if len(paragraphs) <= MAX_SEMANTIC_BLOCKS:
        return paragraphs
    query = set(_terms(notes))
    ranked = sorted(enumerate(paragraphs), key=lambda pair:
                    (-len(query.intersection(_terms(pair[1]["text"]))), pair[0]))
    lexical_slots = MAX_SEMANTIC_BLOCKS - 40
    selected = {i for i, _ in ranked[:lexical_slots]}
    total = len(paragraphs)
    for n in range(40):
        index = round((n + 0.5) * total / 40 - 0.5)
        selected.add(min(total - 1, max(0, index)))
    if len(selected) < MAX_SEMANTIC_BLOCKS:
        for i, _ in ranked:
            selected.add(i)
            if len(selected) == MAX_SEMANTIC_BLOCKS:
                break
    return [paragraphs[i] for i in sorted(selected)][:MAX_SEMANTIC_BLOCKS]


async def _embeddings(texts: list[str]) -> list[list[float]]:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Semantic matching is not configured (OPENAI_API_KEY missing)")
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            EMBEDDINGS_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": MODEL, "input": texts, "encoding_format": "float"},
        )
        response.raise_for_status()
        payload = response.json()
    vectors = payload["data"]
    if len(vectors) != len(texts):
        raise RuntimeError("Embedding count mismatch")
    vectors = sorted(vectors, key=lambda item: item["index"])
    return [item["embedding"] for item in vectors]


async def semantic_candidates(pdf_bytes: bytes, notes: str) -> dict:
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Not a PDF file")
    if not notes.strip() or len(notes) > 10000:
        raise ValueError("Notes must contain 1-10000 characters")
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
        count = len(paragraphs)
        shortlist = _shortlist(paragraphs, notes)
        if not shortlist:
            return {"candidates": [], "matching_method": "openai_embeddings",
                    "requires_confirmation": True, "paragraph_count": count}
        vectors = await _embeddings([notes[:3000]] + [p["text"][:1500] for p in shortlist])
        query, passages = vectors[0], vectors[1:]
        ranked = sorted(zip(shortlist, passages), key=lambda item:
                        -cosine(query, item[1]))
        candidates = []
        for p, vector in ranked[:MAX_CANDIDATES]:
            score = cosine(query, vector)
            candidates.append({"page": p["page"], "text": p["text"],
                               "rect": p["rect"], "similarity": round(score, 4),
                               "candidate_id": len(candidates)})
        return {"candidates": candidates, "matching_method": "openai_embeddings",
                "requires_confirmation": True, "paragraph_count": count,
                "shortlisted_count": len(shortlist),
                "shortlist_truncated": count > MAX_SEMANTIC_BLOCKS,
                "similarity_is_not_probability": True}
    finally:
        doc.close()


def highlight_selected(pdf_bytes: bytes, candidate: dict) -> bytes:
    """Highlight a server-recomputed candidate; do not trust client-supplied rectangles."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = doc[candidate["page"] - 1]
        rect = fitz.Rect(candidate["rect"]) & page.rect
        if rect.is_empty:
            raise ValueError("Invalid candidate rectangle")
        ann = page.add_highlight_annot(rect)
        ann.set_colors(stroke=(1.0, 0.84, 0.20))
        ann.update()
        return doc.tobytes(garbage=4, deflate=True)
    finally:
        doc.close()
