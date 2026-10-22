"""Safe course-to-PDF selection for V0.7a (no Notion writes)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextbookBinding:
    page_url: str
    course: str
    title: str
    pdf_reference: str


def resolve_textbook(course: str, rows: list[dict]) -> TextbookBinding:
    """Only use explicit course names and nonempty PDF references.

    This intentionally refuses guessing based on note titles or PDF filenames.
    """
    if not course or not course.strip():
        raise ValueError("Course name is required")
    candidates = []
    for row in rows:
        if row.get("所属课程") != course:
            continue
        if row.get("处理状态") == "已归档":
            continue
        title = (row.get("教材名称") or "").strip()
        pdf_ref = row.get("原版PDF")
        if title and pdf_ref:
            candidates.append(TextbookBinding(
                page_url=row.get("url") or "",
                course=course, title=title, pdf_reference=pdf_ref))
    if not candidates:
        raise ValueError("No named PDF textbook is explicitly bound to this course")
    if len(candidates) != 1:
        raise ValueError("Multiple textbooks are bound; select one explicitly")
    return candidates[0]
