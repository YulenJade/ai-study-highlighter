# AI Study Highlighter | AI 教材划重点

> Verified PDF passage highlighting from study notes. / 根据笔记定位 PDF 真实原文并生成高亮副本。

**V0.2: local prototype, not a hosted AI service. / V0.2：本地原型，尚非线上 AI 服务。**

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

## Preview / 预览
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

## Security / 安全
**Local development only. Do not expose to the Internet.** No authentication, user isolation, malware scanning, or rate limiting. PDF parsing consumes resources; file-size limits alone do not guarantee safety. Do not commit textbooks, personal notes, credentials or customer data. Only process PDFs you have the rights to use. / 仅用于本地开发，未经鉴权与安全加固不得公网开放。

## Docs / 文档
[PRD](docs/PRD.md) · [Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md)

## License / 许可
No software license is granted unless a LICENSE file is added; third-party textbooks remain owned by their respective rightsholders. / 仓库尚未包含 LICENSE 文件，不能仅凭 README 声明视为已授予 MIT 许可。
