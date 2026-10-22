# AI Study Highlighter | AI 教材划重点

V0.4 is a runnable **private, provisioned-account MVP**. Upload an entire textbook once, then select it from your own library on future visits. It is literal passage matching, not semantic AI or OCR.

## What works

- PDF, DOCX, PPTX, UTF-8 TXT and MD upload and text extraction.
- Default **100 MiB per book**, **1 GiB / 100 books per user**, up to 2,000 PDF pages/slides and 2 million extracted characters. Limits still apply to whole textbooks; large/scanned or pathological books may fail safely.
- A private library backed by **external PostgreSQL + private S3-compatible object storage**. Originals survive application restarts; extracted text is regenerated on demand. No textbook or metadata is persisted on Render's local disk.
- Browser-native HTTP Basic login with independent administrator-provisioned accounts, scrypt password hashes, owner-scoped reads/writes/deletes and CSRF protection. HTTPS is mandatory outside localhost.
- Original PDF preview/export, page coordinates, and `[重点]` yellow / `[定义]` green / `[补充]` blue annotations remain available. Other formats extract text, **not** annotated Office exports. DOCX sections are not print-layout pages; PPTX sections are slide numbers.
- Raw streamed request limits before multipart spooling, ZIP/XML checks, subprocess timeout and Linux resource limits, bounded processing concurrency, durable atomic quota reservations, and retryable deletion.

Scanned PDFs need OCR, which is not implemented. No model receives your text. DOCX extraction covers the main document paragraphs/tables, not headers, embedded attachments or images. PPTX extraction covers slide text, not speaker notes/images. Markdown is shown as text, never rendered as HTML.

## Run locally

Python 3.11+ on Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Open `http://127.0.0.1:8000/`. Without storage configuration, the UI explicitly offers **temporary processing only**, with no save/library controls. Do not expose this unauthenticated local mode publicly. `APP_ENV=production` or Render's `RENDER` flag makes startup fail unless all library/auth settings are present. Windows native execution is unsupported because parser limits use POSIX `resource`; use the Linux Docker image.

## Enable your private library

Follow [deployment and persistence setup](docs/DEPLOYMENT.md). Copy [`.env.example`](.env.example) as a reference; the app does not automatically load `.env`. Set environment variables in your shell or hosting dashboard.

Required: `LIBRARY_USERS`, `DATABASE_URL`, `S3_BUCKET`, AWS-compatible credentials and region; set `S3_ENDPOINT_URL` for compatible providers. Configure a **private bucket**, deny anonymous access, and grant the app credential only GetObject/PutObject/DeleteObject on `books/*`. Never put these secrets in browser code or GitHub.

Generate a distinct long random password for each person and hash it interactively:

```bash
python -m app.security
# Set LIBRARY_USERS to {"alice":"<salt:digest>","bob":"<salt:digest>"}
```

Use a password manager. Accounts are administrator-provisioned; there is no public registration, password reset, or OAuth yet. Account names are stable identities: do not recycle a removed username, because its existing library belongs to that identity. Remove its mapping to revoke access; restart/redeploy to apply secret changes. Browsers cache Basic credentials: use a private browser window and close it to sign out.

## API

Every authenticated mutation requires `X-Library-Request: 1`. Browser UI sends it automatically. No CORS access is enabled. Example (curl prompts for the password):

```bash
curl -u alice -H 'X-Library-Request: 1' -F 'file=@textbook.docx' https://YOUR_HOST/books
curl -u alice https://YOUR_HOST/books
curl -u alice https://YOUR_HOST/books/BOOK_ID/text
curl -u alice https://YOUR_HOST/books/BOOK_ID/original -o original.docx
curl -u alice -H 'X-Library-Request: 1' -F 'notes=[定义] photosynthesis' https://YOUR_HOST/books/BOOK_ID/preview
curl -u alice -H 'X-Library-Request: 1' -F 'notes=photosynthesis' https://YOUR_HOST/books/BOOK_ID/highlight -o highlighted.pdf
curl -u alice -H 'X-Library-Request: 1' -X DELETE https://YOUR_HOST/books/BOOK_ID
```

Temporary endpoints remain: `POST /extract` (`file`), `POST /preview` and `/highlight` (`pdf`, `notes`). Full schema: `/docs`. All routes except `/health` require login when accounts are configured. Unknown or another user's book returns 404. A saved PDF uses the same annotation engine as a temporary PDF.

## Quotas and failure recovery

`MAX_BOOK_MB` defaults to 100; `USER_QUOTA_MB` to 1024; `USER_BOOK_LIMIT` to 100. Values use MiB. The quota counts original file bytes, including pending uploads. Text/highlight outputs are temporary and never stored. Provider version history, backups and logs are outside this logical quota; configure their lifecycle separately.

An atomic conditional database update reserves bytes and one book slot before writing the object. Requests for the same account serialize remote writes/deletes using its database row. The book becomes `ready` only after object upload and metadata commit. No metadata rows or quota are silently discarded when storage success is ambiguous. On timeout/crash the entry can remain `pending`: refresh the library and delete that entry before uploading again. DELETE removes the object before releasing quota; failure retains the reservation for retry. Storage/database unavailability returns 503 rather than pretending that the book was saved. Restore metadata and objects together from backups.

## Security and operational limits

This is for a small group of **trusted, provisioned users**, not an anonymous public upload service. Two in-flight non-health requests and one parser per process are allowed; a bounded 240 requests/minute process-wide budget also limits authentication work. Busy requests return 429. Run one worker as configured. Add an upstream per-user/IP rate limiter before expanding access; these process-local limits are not a distributed rate limiter.

Parser children receive no database/S3/account secrets. They have a 45-second wall deadline, 35-second CPU limit, 768 MiB Linux address-space limit and output limits. Office archives have entry, expansion and XML entity restrictions, and no files are extracted to user-chosen paths. This reduces risk but **is not a kernel security sandbox or malware scanner**: children still share the container UID/network. Do not offer public self-signup until processing runs in separate no-network containers with malware scanning, a durable job queue and distributed abuse controls. Uploaded originals may contain active content when downloaded: opening them in Office remains the user's responsibility.

Render free memory, request duration, cold starts and provider quotas can prevent some 100 MiB/2,000-page books from completing. Limits are ceilings, not promised processing capacity. Move heavy jobs to an isolated worker/queue and choose adequate memory for broader use. Never increase limits blindly.

## Tests and deployment

`python -m pytest -q` covers original PDF behavior, all five formats, authentication, cross-user access, quota races, restart reuse, ambiguous writes, deletion failures, malformed input, parser timeouts and request size limits. Local metadata tests use SQLite **only as a test fixture**; production rejects SQLite. GitHub Actions also runs the library suite against PostgreSQL and a private Moto S3 test bucket, checks JavaScript syntax, and builds the non-root Docker image. No real cloud credentials are needed in CI.

[Deployment](docs/DEPLOYMENT.md) · [Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md)
