"""Local-only development API; do not expose publicly without security controls."""
from io import BytesIO
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .highlighter import analyze_pdf, extract_items

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
