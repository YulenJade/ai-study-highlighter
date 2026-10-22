"""Local-only development API; do not expose publicly without security controls."""
from io import BytesIO
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .highlighter import analyze_pdf, extract_items
from .paragraph_matcher import match_best_paragraph
from .multi_matcher import match_multiple
from .notion_export import append_result

app = FastAPI(title="AI Study Highlighter", version="0.3.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
MAX_BYTES = 15 * 1024 * 1024
MAX_NOTES = 10_000


@app.middleware("http")
async def demo_access_guard(request: Request, call_next):
    """Require HTTP Basic authentication when DEMO_ACCESS_TOKEN is configured."""
    if request.url.path == "/health":
        return await call_next(request)
    token = os.environ.get("DEMO_ACCESS_TOKEN", "")
    if token:
        from base64 import b64decode
        authorization = request.headers.get("authorization", "")
        valid = False
        if authorization.startswith("Basic "):
            try:
                raw = b64decode(authorization[6:], validate=True).decode("utf-8")
                username, password = raw.split(":", 1)
                valid = secrets.compare_digest(username, "demo") and secrets.compare_digest(password, token)
            except (ValueError, UnicodeError):
                valid = False
        if not valid:
            return JSONResponse({"detail": "Authentication required"}, status_code=401,
                                headers={"WWW-Authenticate": 'Basic realm="AI Study Highlighter demo"'})
    return await call_next(request)



def extract_terms(notes: str) -> list[str]:
    """Backward-compatible V0.1 helper."""
    return [item.text for item in extract_items(notes)]


def highlight_pdf(data: bytes, notes: str) -> tuple[bytes, int]:
    summary, output = analyze_pdf(data, notes, annotate=True)
    assert output is not None
    return output, summary["match_count"]


async def read_input(pdf: UploadFile, notes: str) -> bytes:
    if not pdf.filename or not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a .pdf file")
    if len(notes) > MAX_NOTES:
        raise HTTPException(status_code=400, detail="Notes too long")
    data = await pdf.read(MAX_BYTES + 1)
    await pdf.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="PDF too large")
    return data


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html", headers={"Cache-Control": "no-store"})


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.3.0"}


@app.post("/preview")
async def preview(pdf: UploadFile = File(...), notes: str = Form(...)):
    data = await read_input(pdf, notes)
    try:
        summary, _ = analyze_pdf(data, notes)
        return summary
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/highlight")
async def highlight(pdf: UploadFile = File(...), notes: str = Form(...)):
    data = await read_input(pdf, notes)
    try:
        summary, output = analyze_pdf(data, notes, annotate=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    assert output is not None
    return StreamingResponse(
        BytesIO(output),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="highlighted.pdf"',
            "X-Highlight-Matches": str(summary["match_count"]),
            "X-Matched-Pages": ",".join(map(str, summary["matched_pages"])),
        },
    )


@app.post("/paragraph/preview")
async def paragraph_preview(pdf: UploadFile = File(...), notes: str = Form(...)):
    """Rank source-extracted PDF text blocks and return one best paragraph."""
    data = await read_input(pdf, notes)
    try:
        summary, _ = match_best_paragraph(data, notes)
        return summary
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/paragraph/highlight")
async def paragraph_highlight(pdf: UploadFile = File(...), notes: str = Form(...)):
    """Highlight the top-ranked source paragraph (review the preview first)."""
    data = await read_input(pdf, notes)
    try:
        summary, output = match_best_paragraph(data, notes, annotate=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    assert output is not None
    return StreamingResponse(
        BytesIO(output), media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="paragraph-highlighted.pdf"',
            "X-Highlight-Matches": str(summary["match_count"]),
            "X-Matched-Pages": ",".join(map(str, summary["matched_pages"])),
        },
    )

@app.post("/notion/publish")
async def notion_publish(pdf: UploadFile = File(...), notes: str = Form(...),
                         page_id: str = Form(...), book_title: str = Form("Textbook")):
    """Explicitly publish the verified best paragraph to an authorized Notion page."""
    if not os.getenv("DEMO_ACCESS_TOKEN"):
        raise HTTPException(status_code=503, detail="Configure demo authentication before enabling Notion publishing")
    data = await read_input(pdf, notes)
    try:
        summary, _ = match_best_paragraph(data, notes)
        if not summary["best_match"]:
            raise HTTPException(status_code=422, detail="No matching paragraph")
        return await append_result(page_id, summary, book_title)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=502, detail="Notion publish failed; check integration permission") from None


@app.get("/paragraph/workbench", include_in_schema=False)
def paragraph_workbench():
    return FileResponse(STATIC_DIR / "paragraph.html", media_type="text/html", headers={"Cache-Control": "no-store"})


@app.post("/multi/preview")
async def multi_preview(pdf: UploadFile = File(...), notes: str = Form(...)):
    """Preview independently ranked source paragraphs for each note line."""
    data = await read_input(pdf, notes)
    try:
        summary, _ = match_multiple(data, notes)
        return summary
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/multi/highlight")
async def multi_highlight(pdf: UploadFile = File(...), notes: str = Form(...)):
    """Return a PDF with category-colored, source-grounded paragraph highlights."""
    data = await read_input(pdf, notes)
    try:
        summary, output = match_multiple(data, notes, annotate=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    assert output is not None
    return StreamingResponse(
        BytesIO(output), media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="multi-highlighted.pdf"',
            "X-Highlight-Matches": str(summary["match_count"]),
            "X-Matched-Pages": ",".join(map(str, summary["matched_pages"])),
        },
    )
