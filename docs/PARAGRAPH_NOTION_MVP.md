# Paragraph + Notion MVP / 段落匹配与 Notion 集成路线

## What is implemented / 已实现
- Visit `/paragraph/workbench` for a bilingual PDF paragraph-matching prototype.
- The new `POST /paragraph/preview` accepts multipart `pdf` + `notes` and returns the highest-ranked **source-extracted text block**, page, coordinates, score, and up to five candidates.
- `POST /paragraph/highlight` adds a highlight over that one matching source block and returns a downloadable PDF. It does not invent or rewrite textbook passages.
- Use the copy button to paste the page and quotation into a Notion course page **manually**.
- Existing `/`, `/preview`, and `/highlight` behavior remains unchanged.

## Current limitations / 当前限制
- Lexical overlap, **not AI semantic matching**. Similar meanings using different words may not match.
- PyMuPDF PDF text blocks are not guaranteed to be semantic paragraphs. Some blocks include adjacent lines or omit columns. Review original text before relying on a highlight.
- Still limited to **15 MiB and 300 pages** on this preview route; no persistent personal library, user accounts, OCR or 200 MB direct upload yet.
- Notion OAuth and programmatic writeback are **not implemented**; a shared demo Basic Auth password is NOT per-user login. Do not configure an all-users Notion integration token on a shared demo.
- Never save a Notion token, OAuth secret, textbook, or personal data in the public repository. Avoid using public Notion file URLs as a substitute for private file storage.
- Existing Render Free instance cannot be relied on to persist uploaded files across deploys/restarts.

## Planned secure storage & Notion architecture / 后续安全方案
1. Independent accounts with Supabase Auth JWT validation, SQL RLS and ownership checks on every book/paragraph.
2. Store original files in an encrypted private R2 bucket (website-owned) or on users' Drive/OneDrive/WebDAV; store only owner-scoped reference, hash and searchable passage index in PostgreSQL. Check provider access and file version before reuse.
3. Up to 200 MB by multipart/streamed direct upload, quotas, timeouts, type validation, per-user limits and background processing; do not buffer entire books on Render Free.
4. Introduce Notion public OAuth integration with state/PKCE as applicable, minimum authorized capabilities, encrypted tokens, token revocation and user-selected destination pages. Never reuse the current global demo Basic Auth as identity.
5. Generate a PDF with confirmed source coordinates, store a private result, and write the book, page, matched excerpt and a time-limited authenticated link to the user's authorized Notion page.
6. Add Google/Microsoft OAuth, WebDAV credential encryption/SSRF protection, optional GitHub repository file adapter (not appropriate for ordinary >100 MiB files), OCR and semantic reranking.

## Tests / 测试
Run `python -m pytest -q`. For manual verification, upload a small selectable-text PDF and check that `/paragraph/preview` returns exactly one top paragraph, the text is present in the book, and `/paragraph/highlight` contains one annotation. A screenshot PDF will need OCR in a later release.
