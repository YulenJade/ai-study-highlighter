# V0.6 semantic matching (prototype / 试验版)

- Requires server-side `OPENAI_API_KEY`. Do not put secrets in the browser, GitHub, or this document.
- Requires explicit user consent before sending notes and PDF text to OpenAI's embedding endpoint.
- Model: `text-embedding-3-small`; ranks at most 120 text blocks, returns up to 5 candidates.
- Large PDF retrieval is **not exhaustive**: shortlist blends 80 lexical-ranked and 40 page-distributed blocks.
- Similarity is a cosine score, **not a probability of correctness**.
- The selected paragraph is recomputed server-side when downloading; it does not publish to Notion automatically.
- PDFs must contain extractable text; OCR, PDF storage, full-document vector indexing, and semantic multi-note publishing are not yet implemented.
- A second embedding request happens when downloading the selected highlight, which may incur extra charges.
- Keep the existing Basic Auth enabled. For production, add usage limits, rate limiting, persistent vector index, user-scoped permissions, and explicit privacy notice.
- Do not merge this prototype into main until CI and real Chinese textbook tests pass and the API cost/privacy choices are approved.
