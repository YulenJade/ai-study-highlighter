# AI Study Highlighter | AI 教材划重点

> Match class notes to verifiable passages in PDF textbooks, then generate a highlighted copy.  
> 根据课堂笔记定位教材 PDF 中可核验的原文，并生成高亮副本。

**Status / 状态:** Early MVP development. Not deployed, not a paid service. / 早期原型开发中，尚未部署或提供收费服务。

## Features / 功能
- Upload a text-based PDF and paste study notes / 上传文字型 PDF、粘贴课堂笔记
- Exact text matching and page-level highlight / 精确文字匹配与原文高亮
- Download a new PDF without modifying the original / 下载独立高亮 PDF
- Planned: semantic retrieval, OCR, Notion OAuth, quizzes, billing / 规划：语义检索、OCR、Notion 授权、复习题、支付

## Quick start / 快速开始
Requires Python 3.11+.
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
On Windows use `.venv\Scripts\activate`. Visit http://127.0.0.1:8000/docs for API docs.

Example:
```bash
curl -X POST http://127.0.0.1:8000/highlight \
  -F "pdf=@your-textbook.pdf" \
  -F "notes=photosynthesis" \
  -o highlighted.pdf
```

**Limitations:** V0.1 uses literal matching, not AI understanding; scanned/image-only PDFs need OCR (not yet supported). For local development only; the upload API has no authentication, rate limiting, or production-grade malware scanning. Do not expose directly to the public Internet.

## Documentation / 文档
- [Product requirements / 产品需求](docs/PRD.md)
- [Architecture / 架构与安全](docs/ARCHITECTURE.md)
- [Roadmap / 路线图](docs/ROADMAP.md)

## Privacy & copyright / 隐私与版权
Only process files you have rights to use. Do not commit textbooks, private notes, API keys, tokens, or customer data. Uploaded PDFs are processed in memory in this demo and are not intentionally retained by the application. / 仅处理有权使用的文件；不要上传私人教材、笔记、密钥和用户数据到 GitHub。

## License
MIT (code only; no license granted to third-party textbook content).
