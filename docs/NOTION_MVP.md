# Notion integration MVP / Notion 集成基础版

> Development branch feature. **Not a multi-tenant SaaS**. The existing 15 MB upload / 300-page limit still applies. No persistent book library or 200 MB uploads yet.

## 中文

本阶段提供：`POST /paragraph/preview`（返回最相关的 PDF 原文文本块及页码）、`POST /paragraph/highlight`（生成仅标注该文本块的 PDF）、`POST /notion/publish`（用户明确提交后，把原文与页码写入指定 Notion 页面）。

匹配算法目前是**词汇重叠排序，不是语义 AI**。扫描版 PDF 尚不支持 OCR。文本块不一定等同于语义段落，务必人工核对结果。没有把整本书持久存储在 Render 免费实例，也不支持多用户独立 OAuth。

### Notion 设置

1. 在 Notion 创建自己的 Integration，授予需要的内容写入权限。
2. 在目标 Notion 课程页面通过 Connections 将该 Integration 加入允许访问的页面。
3. 在 Render 服务环境变量设置 `NOTION_INTEGRATION_TOKEN`。**不要将 Token 写进 GitHub、Notion 页面或聊天记录。**
4. 保留 `DEMO_ACCESS_TOKEN` 强口令保护。接口 `/notion/publish` 在缺少该保护时拒绝服务。
5. 使用页面 ID 调用发布接口（multipart form fields: `pdf`, `notes`, `page_id`, optional `book_title`）。发布前请先预览并人工确认；发布操作会向 Notion 页面追加四个 blocks。

该方案只适用于**单个受信任的演示账号**。面向公开用户之前必须实现各用户独立 OAuth、会话、授权范围隔离、CSRF 防护、滥用限制、可撤销连接及持久化存储。

## English

This development MVP exposes `POST /paragraph/preview`, `POST /paragraph/highlight`, and an explicitly triggered `POST /notion/publish` for a Notion page shared with a server-owned integration.

Matching is **lexical overlap, not semantic AI**. OCR, 200 MB uploads, persistent personal libraries, Google Drive / OneDrive / WebDAV OAuth and per-user Notion OAuth are **not yet implemented**. Results are PDF-derived and should be reviewed before publication.

Create a Notion integration with content update access, connect it to a target page, and set its secret in the server environment as `NOTION_INTEGRATION_TOKEN`. Keep `DEMO_ACCESS_TOKEN` enabled. Never commit credentials. Publishing appends four blocks to the selected page. This single-operator demo must not be offered as a public multi-user integration.

## API example

```bash
curl -u demo:'YOUR_DEMO_PASSWORD' \
  -F 'pdf=@book.pdf' -F 'notes=photosynthesis light energy' \
  https://YOUR_RENDER_HOST/paragraph/preview

curl -u demo:'YOUR_DEMO_PASSWORD' \
  -F 'pdf=@book.pdf' -F 'notes=photosynthesis light energy' \
  -F 'page_id=YOUR_NOTION_PAGE_ID' -F 'book_title=Botany' \
  https://YOUR_RENDER_HOST/notion/publish
```
