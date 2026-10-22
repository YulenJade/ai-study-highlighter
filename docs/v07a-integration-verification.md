# V0.7a integration verification · 2026-10-22

## Verified
- Two existing official Notion AI meeting-note pages under 园林植物病虫害防治 were readable through the connected Notion tool. The pages include structured AI summaries and, in at least one case, long raw transcripts.
- The textbook data source currently returned exactly one row. Its 教材名称 and 所属课程 are both null; 原版PDF has a file reference; 处理状态 is 待上传.
- Therefore **no course-bound PDF can be selected safely yet**. Do not infer the course from the PDF filename, notes, or page ancestry.
- The connector used by this chat is **not the Render application's NOTION_INTEGRATION_TOKEN**. Its ability to read AI Meeting Notes does not establish that Render can read those pages.

## Next steps
1. In the Notion 教材资料库, fill 教材名称 and 所属课程 for the PDF record and verify it is the intended textbook. If multiple PDFs belong to a course, add an explicit active/default selection rather than guessing.
2. Share a test AI Meeting Notes page with the server's Notion integration. Verify read-only access to the page's summary blocks through Notion's official API; exclude transcript and audio by default.
3. Add a server-side Notion adapter to query authorized note pages and textbook rows. Only after this works, connect the read-only workbench to these adapters.
4. Require manual review of the real cropped source PDF paragraph. No automatic Notion writes in V0.7a.
5. Run end-to-end test on a deliberately authorized note and textbook before merge or deployment.

## Source privacy
Do not copy real classroom notes, meeting transcripts, or private PDF URLs into GitHub tests or logs.
