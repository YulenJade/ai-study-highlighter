"""Private study library; external persistence is mandatory on hosted instances."""
from contextlib import asynccontextmanager
from io import BytesIO
import os
from pathlib import Path
import secrets
import threading
import time

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .highlighter import analyze_pdf, extract_items
from .library import configured_library
from .processing import process
from .security import accounts, authenticate

MAX_BYTES = int(os.getenv('MAX_BOOK_MB', '100')) * 1024 * 1024
MAX_NOTES = 10_000
STATIC_DIR = Path(__file__).resolve().parent / 'static'


@asynccontextmanager
async def lifespan(app):
    provisioned = accounts()
    library = configured_library()
    if (os.getenv('RENDER') or os.getenv('APP_ENV') == 'production') and (not provisioned or not library):
        raise RuntimeError('Hosted mode requires LIBRARY_USERS, PostgreSQL and private S3 storage')
    if library:
        if not provisioned:
            raise RuntimeError('Library requires independent user accounts')
        await run_in_threadpool(library.initialize, provisioned)
    app.state.library = library
    yield
    if library:
        library.engine.dispose()


app = FastAPI(title='AI Study Highlighter', version='0.4.0', lifespan=lifespan,
              docs_url=None, redoc_url=None)
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


class RequestLimits:
    """Cap raw request bytes before multipart spooling, including chunked bodies."""
    def __init__(self, application):
        self.app = application
        self.slots = threading.BoundedSemaphore(2)
        self.lock = threading.Lock()
        self.window, self.attempts = 0, 0

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        if scope['path'] == '/health':
            return await self.app(scope, receive, send)
        # Global bounded auth budget prevents unbounded scrypt work or an IP map.
        with self.lock:
            now = int(time.monotonic() // 60)
            if now != self.window:
                self.window, self.attempts = now, 0
            self.attempts += 1
            limited = self.attempts > 240
        if limited or not self.slots.acquire(blocking=False):
            return await JSONResponse({'detail': 'Busy; retry later'}, 429,
                                      headers={'Retry-After': '60'})(scope, receive, send)
        try:
            try:
                length = int(headers.get(b'content-length', b'0'))
                if length < 0:
                    raise ValueError()
            except ValueError:
                return await JSONResponse({'detail': 'Invalid content length'}, 400)(scope, receive, send)
            maximum = MAX_BYTES + 1024 * 1024
            if length > maximum:
                return await JSONResponse({'detail': 'Request too large'}, 413)(scope, receive, send)
            total = 0
            async def bounded_receive():
                nonlocal total
                import asyncio
                message = await asyncio.wait_for(receive(), timeout=30)
                total += len(message.get('body', b''))
                if total > maximum:
                    raise HTTPException(413, 'Request too large')
                return message
            await self.app(scope, bounded_receive, send)
        finally:
            self.slots.release()


@app.middleware('http')
async def access_guard(request: Request, call_next):
    if request.url.path == '/health':
        return await call_next(request)
    provisioned = accounts()
    header = request.headers.get('authorization', '')
    user = await run_in_threadpool(authenticate, header) if provisioned else None
    if provisioned and not user:
        return JSONResponse({'detail': 'Authentication required'}, 401,
                            headers={'WWW-Authenticate': 'Basic realm="Private study library", charset="UTF-8"'})
    if not provisioned and os.getenv('DEMO_ACCESS_TOKEN'):
        from base64 import b64decode
        try:
            raw = b64decode(header[6:], validate=True).decode() if header.startswith('Basic ') else ''
            username, password = raw.split(':', 1)
            valid = secrets.compare_digest(username, 'demo') and secrets.compare_digest(password, os.environ['DEMO_ACCESS_TOKEN'])
        except (ValueError, UnicodeError):
            valid = False
        if not valid:
            return JSONResponse({'detail': 'Authentication required'}, 401,
                                headers={'WWW-Authenticate': 'Basic realm="Demo"'})
    request.state.user = user
    if provisioned and request.method in {'POST', 'DELETE', 'PUT', 'PATCH'}:
        if request.headers.get('x-library-request') != '1':
            return JSONResponse({'detail': 'X-Library-Request: 1 required'}, 403)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers.setdefault('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; frame-src blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
    return response


# Outermost middleware: capacity is checked before authentication and body parsing.
app.add_middleware(RequestLimits)


def extract_terms(notes: str) -> list[str]:
    return [item.text for item in extract_items(notes)]


def highlight_pdf(data: bytes, notes: str) -> tuple[bytes, int]:
    summary, output = analyze_pdf(data, notes, annotate=True)
    return output, summary['match_count']


async def read_input(file: UploadFile, notes=''):
    try:
        extension = Path(file.filename or '').suffix.lower().lstrip('.')
        if extension not in {'pdf', 'docx', 'pptx', 'txt', 'md'}:
            raise HTTPException(400, 'Supported formats: PDF, DOCX, PPTX, TXT, MD')
        if len(notes) > MAX_NOTES:
            raise HTTPException(400, 'Notes too long')
        data = await file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, 'Book too large')
        if not data:
            raise HTTPException(422, 'Empty file')
        return extension, data
    finally:
        await file.close()


@app.get('/', include_in_schema=False)
def homepage():
    return FileResponse(STATIC_DIR / 'index.html', media_type='text/html')


@app.get('/docs', include_in_schema=False)
def api_docs():
    nonce = secrets.token_urlsafe(24)
    html = get_swagger_ui_html(openapi_url='/openapi.json', title='Study library API').body.decode()
    html = html.replace('<script', f'<script nonce="{nonce}"')
    return HTMLResponse(html, headers={'Content-Security-Policy':
        f"default-src 'self'; script-src 'nonce-{nonce}'; style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"})


@app.get('/health')
def health():
    return {'status': 'ok', 'version': '0.4.0'}


@app.get('/config')
def config(request: Request):
    return {'max_book_bytes': MAX_BYTES, 'library_enabled': bool(getattr(app.state, 'library', None)),
            'user': request.state.user}


def library_for(request):
    library = getattr(app.state, 'library', None)
    if not library or not request.state.user:
        raise HTTPException(503, 'Private library is not configured; temporary processing only')
    return library


@app.get('/books')
def list_books(request: Request):
    return library_for(request).listing(request.state.user)


@app.post('/books', status_code=201)
async def upload_book(request: Request, file: UploadFile = File(...)):
    library = library_for(request)
    extension, data = await read_input(file)
    await run_in_threadpool(process, data, extension)
    return await run_in_threadpool(library.save, request.state.user,
                                   Path(file.filename or 'book').name, extension, data)


@app.delete('/books/{book_id}', status_code=204)
def delete_book(request: Request, book_id: str):
    library_for(request).remove(request.state.user, book_id)


@app.get('/books/{book_id}/text')
def book_text(request: Request, book_id: str):
    row, data = library_for(request).read(request.state.user, book_id)
    summary, _ = process(data, row['extension'])
    return summary


@app.get('/books/{book_id}/original')
def book_original(request: Request, book_id: str):
    row, data = library_for(request).read(request.state.user, book_id)
    return StreamingResponse(BytesIO(data), media_type='application/octet-stream',
                             headers={'Content-Disposition': f'attachment; filename="book.{row["extension"]}"'})


@app.post('/extract')
async def extract_file(file: UploadFile = File(...)):
    extension, data = await read_input(file)
    summary, _ = await run_in_threadpool(process, data, extension)
    return summary


def export_response(summary, output):
    return StreamingResponse(BytesIO(output), media_type='application/pdf', headers={
        'Content-Disposition': 'attachment; filename="highlighted.pdf"',
        'X-Highlight-Matches': str(summary['match_count']),
        'X-Matched-Pages': ','.join(map(str, summary['matched_pages']))})


@app.post('/preview')
async def preview(pdf: UploadFile = File(...), notes: str = Form(...)):
    extension, data = await read_input(pdf, notes)
    if extension != 'pdf':
        raise HTTPException(400, 'PDF required for highlights; use /extract for other formats')
    summary, _ = await run_in_threadpool(process, data, 'pdf', 'preview', notes)
    return summary


@app.post('/highlight')
async def highlight(pdf: UploadFile = File(...), notes: str = Form(...)):
    extension, data = await read_input(pdf, notes)
    if extension != 'pdf':
        raise HTTPException(400, 'PDF required for annotation')
    summary, output = await run_in_threadpool(process, data, 'pdf', 'highlight', notes)
    return export_response(summary, output)


@app.post('/books/{book_id}/{action}')
def analyze_book(request: Request, book_id: str, action: str, notes: str = Form(...)):
    if action not in {'preview', 'highlight'}:
        raise HTTPException(404, 'Unknown operation')
    if len(notes) > MAX_NOTES:
        raise HTTPException(400, 'Notes too long')
    row, data = library_for(request).read(request.state.user, book_id)
    if row['extension'] != 'pdf':
        raise HTTPException(400, 'Only PDF supports annotation; use extracted text for other formats')
    summary, output = process(data, 'pdf', action, notes)
    return summary if action == 'preview' else export_response(summary, output)
