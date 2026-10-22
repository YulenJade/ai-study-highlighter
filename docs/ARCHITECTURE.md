# Architecture / 技术架构

## Current MVP
FastAPI upload -> PyMuPDF text search -> PDF annotations -> streaming download.
No database or external AI services. Processing happens in the application process.

## Security
This is a **local development demo only**. It lacks authentication, user isolation, rate limiting, antivirus scanning, and background processing. Do not expose directly to the public Internet. Set network and CPU/memory restrictions when testing untrusted PDFs. Do not commit copyrighted textbooks, notes, secrets, or user data.

## Planned
- OCR for image-only PDFs
- Embedding candidate retrieval followed by exact PDF coordinate verification
- Notion OAuth and per-user scopes
- Background queue, private storage, expiring downloads
- Signed payment webhooks and entitlements
