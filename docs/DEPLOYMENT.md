# Hosted demo / 演示部署

This project can be deployed as a **restricted demo**, not a production SaaS. It has no persistent storage and is not hardened against hostile PDF files. Use only non-sensitive sample PDFs.

## Render (manual deployment)
1. Open https://dashboard.render.com/ and connect the GitHub repository `YulenJade/ai-study-highlighter`.
2. Choose **New > Blueprint**, select this repository and review the `render.yaml` service.
3. Set the required secret environment variable `DEMO_ACCESS_TOKEN` to a strong random password (never commit it).
4. Deploy and wait for `/health` to return `{"status":"ok","version":"0.3.0"}`.
5. Open the assigned Render URL. Browser Basic Auth credentials: username `demo`, password = your `DEMO_ACCESS_TOKEN`.
6. Upload only a test PDF with no personal or copyrighted private materials.

The Render free plan and availability may change; check current platform terms. Cold starts and temporary unavailability are possible. **A Render account connection and deployment have not been performed by ChatGPT.**

## Other Docker host / 其他 Docker 平台
```bash
docker build -t ai-study-highlighter .
docker run --rm -p 127.0.0.1:8000:8000 -e DEMO_ACCESS_TOKEN=replace-with-a-strong-secret ai-study-highlighter
```
On a hosted deployment set `DEMO_ACCESS_TOKEN` using the platform secret manager. Never publish port 8000 directly without HTTPS and access controls. The Basic Auth token is a demo gate, not multi-user authentication or rate limiting.

## Before public launch / 正式上线前
- Add per-user authentication, quotas, rate limiting and concurrency controls.
- Add isolated PDF processing, CPU/time/memory limits and upload scanning.
- Add privacy and retention policies, security logging and abuse controls.
- Validate actual Chinese textbooks and improve handling of scanned PDFs.
