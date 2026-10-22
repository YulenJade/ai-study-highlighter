"""Local-only PDF highlighting MVP. Do not deploy publicly without authentication and resource controls."""
from io import BytesIO
import re

import fitz
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

app = FastAPI(title="AI Study Highlighter", version="0.1.0")
MAX_BYTES = 15 * 1024 * 1024
MAX_PAGES = 300
MAX_TERMS = 40


def extract_terms(notes: str) -> list[str]:
    """Each nonempty line is a literal search phrase (not semantic AI matching)."""
    terms = []
    for line in notes.splitlines():
        term = re.sub(r"^\s*(?:[-*•]|\d+[.)、])\s*", "", line).strip()
        if len(term) >= 2 and term not in terms:
            terms.append(term[:200])
    return terms[:MAX_TERMS]


def highlight_pdf(data: bytes, notes: str) -> tuple[bytes, int]:
    if not data.startswith(b"%PDF-"):
        raise ValueError("Not a PDF file")
    terms = extract_terms(notes)
    if not terms:
        raise ValueError("Provide at least one note phrase (2+ characters)")
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        if doc.page_count > MAX_PAGES:
            raise ValueError("PDF exceeds page limit")
        count = 0
        for page in doc:
            for term in terms:
                for rect in page.search_for(term, quads=True):
                    annot = page.add_highlight_annot(rect)
                    annot.update()
                    count += 1
        result = doc.tobytes(garbage=4, deflate=True)
        return result, count
    finally:
        doc.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/highlight")
async def highlight(pdf: UploadFile = File(...), notes: str = Form(...)):
    if not pdf.filename or not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a .pdf file")
    data = await pdf.read(MAX_BYTES + 1)
    await pdf.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="PDF too large")
    if len(notes) > 10_000:
        raise HTTPException(status_code=400, detail="Notes too long")
    try:
        output, matches = highlight_pdf(data, notes)
    except (ValueError, RuntimeError, fitz.FileDataError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(output),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="highlighted.pdf"',
            "X-Highlight-Matches": str(matches),
        },
    )
