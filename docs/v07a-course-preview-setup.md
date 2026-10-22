# V0.7a course-bound preview: deployment checklist

**Status:** independent draft branch, not deployed. Never commit environment variables containing credentials.

Server environment variables:
- `NOTION_INTEGRATION_TOKEN`: existing server secret (do not change).
- `DEMO_ACCESS_TOKEN`: existing Basic Auth secret (required).
- `NOTION_TEST_NOTE_PAGE_ID`: ID of an authorized **园林苗圃学** official AI note page, explicitly shared with the Render integration.
- `NOTION_TEST_TEXTBOOK_PAGE_ID=4015440836d5804380dfd3be8e7c2b2e`
- `NOTION_TEST_COURSE=园林苗圃学`

Authenticated GET `/v07a/course/preview` reads the configured note and textbook metadata, validates the course and textbook title, downloads the short-lived Notion PDF file with a 15MB cap, then computes lexical PDF source candidates. The response is **read-only** and contains no PDF signed URLs or secrets.

Limitations:
- Notion official AI note content may be nested in child blocks and not exposed by the public API. This version reads only top-level standard text blocks and rejects missing content.
- It does not generate screenshot PNGs from the remote PDF in the same request; `/v07a/crop` still accepts a user-uploaded PDF. Server-side cached review sessions and remote crop endpoint are pending.
- It is not yet a semantic matcher. The course's PDF is a nursery care plan, not necessarily a textbook chapter.
- Notion's file signed URL expires. Re-fetch the textbook page before each request.
- Do not enable or merge until a real authorized note is selected, tests pass, and Render's own token is verified.
