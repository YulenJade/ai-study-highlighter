# V0.7a automatic discovery setup (read-only)

A new `GET /v07a/notion/discover` endpoint and workbench button list shared Notion pages whose **ancestor** is one of the explicitly configured course pages. It does not write to Notion, fetch raw transcripts, run in the background, or certify that a page is an official AI Meeting Note.

Configure the existing `NOTION_INTEGRATION_TOKEN` and `DEMO_ACCESS_TOKEN`, plus `NOTION_COURSE_BINDINGS_JSON` as a JSON object:

```json
{
  "园林苗圃学": {
    "course_page_id": "<actual Notion course root page ID>",
    "textbook_page_id": "4015440836d5804380dfd3be8e7c2b2e"
  }
}
```

Use the actual course root page ID from Notion. The textbook page ID above is verified for 重庆市某苗圃苗木管护计划. Do not substitute the textbook ID for the course root.

Security and limits:
- Scans at most 500 shared pages per request, and at most eight ancestor levels.
- Returns only course-matched page IDs, titles, timestamps and textbook IDs.
- Requires demo Basic Auth, which must be configured; otherwise the endpoint refuses service.
- Does not imply Render's token has the same access as ChatGPT's connected Notion account.
- Notion search API does not identify official AI Meeting Notes. User review and actual summary-block validation are required before using a candidate for matching.
- `/v07a/course/preview` is a separate opt-in preview with configured note ID. Fully automatic discovery-to-crop is not wired yet.

Do not merge/deploy without verifying a real authorized course page and test coverage.
