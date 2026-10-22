# V0.7a staging acceptance checklist — 2026-10-22

## Confirmed
- GitHub Actions for commit `b18b3df464ca3806ca7ff37e1aeee7ca4f9fa7b4`: both checks passed.
- Automated integration test mocks Notion pages and blocks, serves an actual PyMuPDF-generated PDF, and checks that the PNG output begins with the correct PNG signature.
- The test note is under the real course tree: `4015440836d5817cbd6df5c01fc8d876` → 笔记 → `4005440836d58138b8eee61483667132` (园林苗圃学).
- The textbook entry `4015440836d5804380dfd3be8e7c2b2e` is tagged 园林苗圃学. Source PDF has 7 pages.
- The Render service `srv-dbcu8ct9fdbs73fbk48g` currently deploys from `main`, not this branch.

## Required staging variables (values only, no secrets)
```text
NOTION_TEST_NOTE_PAGE_ID=4015440836d5817cbd6df5c01fc8d876
NOTION_TEST_TEXTBOOK_PAGE_ID=4015440836d5804380dfd3be8e7c2b2e
NOTION_TEST_COURSE=园林苗圃学
NOTION_COURSE_BINDINGS_JSON={"园林苗圃学":{"course_page_id":"4005440836d58138b8eee61483667132","textbook_page_id":"4015440836d5804380dfd3be8e7c2b2e"}}
```

Additionally configure `NOTION_INTEGRATION_TOKEN` and `DEMO_ACCESS_TOKEN` in the staging service's secret environment variables, never in GitHub, docs or logs. The Notion integration must have read access to both pages and their parent course tree.

## Acceptance steps
1. Deploy `feat/v07a-crop-review` to an isolated, authenticated staging service. Do not change production `main`.
2. GET `/health` should return 200.
3. With demo Basic Auth, GET `/v07a/notion/discover` and verify the test page appears under 园林苗圃学; note that Notion search may omit pages not directly shared with the integration.
4. GET `/v07a/course/preview` and verify `pdf_page_count=7`, `notion_write_enabled=false`, and actual candidate source excerpts.
5. GET `/v07a/course/crop/0` and verify HTTP 200, Content-Type image/png, PNG magic bytes, page header and visible PDF source text.
6. Check that no requests write to Notion, no credentials/signed PDF URLs appear in logs, and no unauthorized access succeeds.
7. Inspect candidates manually. Do not claim automated correctness solely from nonzero lexical scores.

## Current limitations
- No real Render-to-Notion end-to-end test yet.
- Native Notion AI Meeting Notes content may not be exposed as standard blocks.
- Course preview currently verifies the textbook course property but does not yet verify the note's ancestry; do not enable arbitrary note IDs or publish based on this alone.
- No automatic write-back to Notion.
