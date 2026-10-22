# V0.7 · Notion AI Meeting Notes → Course PDF → Review → Original Note Backfill

Status: **DESIGN ONLY**, isolated from production. No Notion pages modified and no automation activated.

## User story
After Notion's official AI Meeting Notes generates notes, show an opt-in “是否标记课本” action **in the surrounding course-note workflow**, not inside Notion's proprietary AI editor. User selects "Yes", the app reads only an authorized note, resolves its course-bound PDF, extracts highlights, proposes source-grounded matches, renders **actual PDF image crops**, and after manual review appends results to the **original note page**.

## Existing workspace integration
- Control center page: `4015440836d58176bdeec58c4750d22f`.
- Textbooks data source: `collection://06837269-cc68-4557-960c-3f2721e7f0e3`. Existing columns: `教材名称`, `所属课程`, `原版PDF`, `教材版本`, `处理状态`, `标注版PDF`. Course selection values currently include 植物生理学, 园林苗圃学, 园林植物病虫害防治, 其他; extend for additional courses after validation.
- Tasks data source: `collection://16364195-0250-46f0-afa0-dc7f32e4280f`. Existing: `任务名称`, `笔记链接`, `课程`, `教材名称`, `处理状态`, `匹配置信度`, `页码`, `最后处理时间`. States: 待处理, 匹配中, 待核对, 已完成, 失败.
- Do not assume that Notion's built-in AI notes have an automatic completion webhook or that meeting transcripts are accessible. Verify accessible note summary text with read-only access and explicit user approval. If inaccessible, fall back to pasting selected note content in the workbench.

## Interaction and flow
1. User finishes an official Notion AI note. The page template has a “📘 是否标记课本” section with a link to an authenticated review workbench. Native buttons cannot be inserted into Notion's AI Meeting Notes composer itself. Alternative: checkbox field on an ordinary course-notes database page, polled only after user opts in.
2. Workbench receives explicit `note_page_id` and course identifier. Server verifies Notion page access and parent/course mapping; never trust arbitrary user-provided page ID as authorization. Show source note preview and a checkbox consenting to analysis.
3. Find exactly one active textbook for the course in the textbook data source. If zero/multiple, ask user to bind/select a textbook; do not guess. Resolve a **server-side immutable snapshot** of PDF bytes by content hash, course ID, and textbook version. Notion file URLs may expire. Store PDF privately; do not expose PDFs in the public GitHub repository.
4. Extract headings, definitions, summaries, and explicit emphasis from accessible AI notes. Do not invent teacher-emphasized exam topics. Source snippets and original block IDs must be retained. Limit count/length and allow the user to remove items.
5. Use V0.6 candidate matching; return top candidates and page number. Cosine similarity is **not calibrated confidence**. On long books, lexical+sample shortlist is not exhaustive; clearly show incomplete search and allow page-range refinement. Require review for every item.
6. PDF crop: PyMuPDF `page.get_pixmap(matrix=fitz.Matrix(2,2), clip=expanded_rect, alpha=False)`; clip rectangle to page bounds, add a small contextual margin, produce PNG; keep PDF page index (1-based) and optional printed page number separately. Never fabricate screenshots from text.
7. Review cards: note highlight, actual PDF crop, candidate text, page number, match score, alternate-candidate selector, approve/reject. Clicking “确认回填” explicitly confirms selected cards and destination.
8. Upload approved images using Notion's supported file upload flow, then append a heading “📚 教材原文对照”, each highlight's source text + page + image + provenance to the **same original note page**, leaving existing AI summary untouched. Confirm permissions and file limits first. If the target is a read-only AI-generated child block, append to its writable containing page instead, with user approval.
9. Idempotency: key `note_page_id + note_last_edited_at + textbook_sha256 + highlight_id + candidate_id`. Persist job state and uploaded image IDs; retries must not duplicate images or note sections. Write a job receipt and recover from partial failures.
10. Track job statuses in task data source and secure DB; no automatic Notion write before explicit user approval.

## Suggested API contracts (not yet implemented)
- `GET /v07/courses` — accessible course/textbook bindings (authenticated)
- `POST /v07/notes/inspect` — note_page_id, consent; read note and propose extracted highlights
- `POST /v07/jobs` — note_page_id, course_id, textbook_id, selected_note_block_ids; prepare candidates
- `GET /v07/jobs/{id}` — review cards with candidate IDs and signed crop preview URLs
- `POST /v07/jobs/{id}/approve` — selected candidate IDs, confirmed=true; idempotent enqueue
- `GET /v07/jobs/{id}/status` — state, error code, Notion destination URL

## Privacy, authorization and operational gates
- Single-user demo authentication remains mandatory; server-side Notion token only.
- Do not store meeting audio/transcript unless separately authorized; prefer AI-generated summary.
- OpenAI embedding request requires separate informed consent; never send all source PDFs by default.
- Course PDFs and screenshots in private object storage with scoped short-lived links and deletion controls.
- Never print keys, transcripts, private notes, signed URLs or PDF bytes to logs.
- Guard against malicious PDFs, oversized rendering, upload failures, rate limits, and note updates during processing.
- Test PDF crop bounds, multiple candidates, incorrect course binding, stale review, Notion permission denial, idempotent retries, image upload and exact destination.
- Do not merge/deploy until V0.6 is verified and a real AI Meeting Notes page is accessible to the integration.

## Release stages
- **V0.7a**: read-only Notion note inspection, course→PDF binding, crop generation, local review; no Notion writes.
- **V0.7b**: explicitly confirmed image uploads and original-page backfill with idempotency.
- **V0.7c**: optional polling/Notion database checkbox trigger if supported; not an assumed AI-completion webhook.

## Acceptance criteria
- One opt-in click starts analysis without manual copy/paste **when** official note text is API-accessible.
- Each approved card includes a screenshot derived from the exact bound PDF page and passage, plus page citation.
- No unapproved or low-quality match is written.
- Repeating the same confirmation does not create duplicate Notion content.
- The original AI-generated notes remain unchanged; output is appended below.
