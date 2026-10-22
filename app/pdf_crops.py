"""V0.7a: source-grounded, read-only PDF paragraph screenshots."""
from __future__ import annotations

from io import BytesIO

import fitz

from .paragraph_matcher import match_best_paragraph

MAX_RENDER_PIXELS = 5_000_000


def crop_candidate(pdf_bytes: bytes, notes: str, candidate_index: int,
                   scale: float = 1.7) -> tuple[dict, bytes]:
    """Recompute source candidates; never accept untrusted client rectangles."""
    if not isinstance(candidate_index, int) or not 0 <= candidate_index < 5:
        raise ValueError("Candidate index must be between 0 and 4")
    if not 1 <= scale <= 2:
        raise ValueError("Invalid image scale")
    summary, _ = match_best_paragraph(pdf_bytes, notes)
    candidates = summary["candidates"]
    if candidate_index >= len(candidates):
        raise ValueError("Candidate does not exist")
    candidate = candidates[candidate_index]
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = doc[candidate["page"] - 1]
        bounds = fitz.Rect(candidate["rect"])
        clip = fitz.Rect(bounds.x0 - 20, bounds.y0 - 18,
                         bounds.x1 + 20, bounds.y1 + 18) & page.rect
        if clip.is_empty or clip.width * clip.height * scale * scale > MAX_RENDER_PIXELS:
            raise ValueError("Invalid or oversized crop")
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip,
                              alpha=False)
        if pix.width * pix.height > MAX_RENDER_PIXELS:
            raise ValueError("Image too large")
        return {
            "page": candidate["page"],
            "text": candidate["text"],
            "score": candidate["score"],
            "candidate_index": candidate_index,
            "source": "actual_pdf_render",
            "requires_confirmation": True,
        }, pix.tobytes("png")
    finally:
        doc.close()
