# AI Study Highlighter | AI 教材划重点

> Verified PDF passage highlighting from study notes. / 根据笔记定位 PDF 真实原文并生成高亮副本。

**V0.7a deployed on Render (2026-10-22). Notion-linked course preview is experimental and currently returns HTTP 502 in live testing. / V0.7a 已部署 Render，Notion 课程联合预览真实测试仍返回 502，尚未验收。**

## Features / 功能
- Chinese and English **literal** text search in text-based PDFs / 支持文字型 PDF 的中英文原文搜索
- Preview matching page numbers, coordinates, categories and unmatched phrases / 预览页码、坐标、分类与未匹配词句
- Three highlight colors: `[重点]` yellow, `[定义]` green, `[补充]` blue / 三色高亮
- Export a separate annotated PDF / 导出带高亮标注的 PDF 副本
- Up to 15 MB, 300 pages, 40 phrases, 1000 matches / 限制文件、页数和匹配数量

**Not AI semantic matching:** notes must contain text actually present in the PDF. Image-only/scanned PDFs require OCR, which is not implemented. Chinese PDFs must contain extractable text; unusual encodings may fail. / 目前是原文匹配，不是语义理解；扫描版需要未来 OCR。

## Quick start / 启动
Python 3.11+:
```bash
git clone https://github.com/YulenJade/ai-study-highlighter.git
cd ai-study-highlighter
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Windows activation: `.venv\Scripts\activate`.

Visit `http://127.0.0.1:8000/docs` for interactive API documentation.

## Web UI / 网页界面

Run the server locally, then open **http://127.0.0.1:8000/**. Choose Chinese or English, upload a text-based PDF, paste one exact phrase per line, click Analyze, inspect matching pages and categories, then click Download. The generated PDF is also loaded into an embedded browser viewer where supported. / 启动本地服务后打开首页，选择语言、上传教材、输入笔记、预览匹配结果并下载高亮 PDF。

## API Preview / 接口预览
```bash
curl -X POST http://127.0.0.1:8000/preview \
  -F "pdf=@book.pdf" \
  -F $'notes=[重点] photosynthesis\n[定义] chlorophyll'
```
Returns JSON with `page_count`, `match_count`, `matched_pages`, `unmatched_terms`, `matches` (including `page`, `text`, `category`, `rect`) and `truncated`. Page numbering starts at 1. Coordinates are PDF page coordinates.

## Export / 导出
```bash
curl -X POST http://127.0.0.1:8000/highlight \
  -F "pdf=@book.pdf" \
  -F "notes=[定义] photosynthesis" \
  -o highlighted.pdf
```

## Deploy a private demo / 部署密码保护的演示版

Docker and Render Blueprint files are included. Follow [deployment instructions / 部署教程](docs/DEPLOYMENT.md). A hosted demo is live at **https://ai-study-highlighter-demo.onrender.com/**. Protected routes require the server-side `DEMO_ACCESS_TOKEN`; do not commit it. / Render 演示网站已上线，受保护接口需要服务器端密钥。

## Security / 安全
**Prototype deployment only, not production-ready for public multi-user uploads.** The hosted demo uses access protection, but user isolation, comprehensive malware scanning and rate limiting have not been fully validated. PDF parsing consumes resources; size limits alone do not guarantee safety. Do not commit textbooks, notes, credentials or customer data. Only process PDFs you have the rights to use. / 当前为受保护演示站，不具备完整多租户安全验收；请勿上传无权处理的教材或提交私密信息。

## Current status / 当前进度（2026-10-22）

- **Deployed / 已上线**: bilingual text-PDF workflow, literal matching, color-coded highlights, annotated PDF export, manual paragraph candidate/crop review UI.
- **Implemented, not live-verified / 已实现但未完成真实验收**: read-only Notion course discovery, course-bound PDF candidate preview and PNG crop endpoints. Mocked Notion → PDF → PNG integration tests passed.
- **Live blocker / 线上阻塞**: `GET /v07a/course/preview` returned **HTTP 502** during real Notion integration testing. Stage-specific error diagnostics were committed as `c76ce280`; confirm CI/deployment and retry before claiming this feature works.
- **Not implemented / 未完成**: Notion OAuth, unattended Notion write-back, native AI Meeting Notes full-text support, OCR, semantic AI matching, multi-user subscriptions.
- **Resume / 下次继续**: verify diagnostics deploy → reproduce 502 → inspect Notion integration permissions, note ancestry, textbook properties and signed PDF download → confirm genuine PNG crops. Keep Notion write-back disabled.
- **Links**: [Live demo / 演示网站](https://ai-study-highlighter-demo.onrender.com/) · [V0.7a PR](https://github.com/YulenJade/ai-study-highlighter/pull/10) · [Staging acceptance notes](docs/v07a-staging-acceptance.md).

## Docs / 文档
[PRD](docs/PRD.md) · [Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md)

## License / 许可
No software license is granted unless a LICENSE file is added; third-party textbooks remain owned by their respective rightsholders. / 仓库尚未包含 LICENSE 文件，不能仅凭 README 声明视为已授予 MIT 许可。
