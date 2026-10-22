import httpx
import pytest

from app.notion_notes_readonly import extract_summary_blocks, inspect_configured_note


def test_extracts_only_standard_text_blocks():
    blocks = [
        {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "课堂重点"}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "根系保护"}]}},
        {"type": "child_page", "child_page": {"title": "Raw transcript"}},
    ]
    assert extract_summary_blocks(blocks) == ["课堂重点", "根系保护"]


@pytest.mark.asyncio
async def test_missing_config_is_rejected(monkeypatch):
    monkeypatch.delenv("NOTION_TEST_NOTE_PAGE_ID", raising=False)
    with pytest.raises(ValueError, match="Configure"):
        await inspect_configured_note()


@pytest.mark.asyncio
async def test_readonly_probe_does_not_write(monkeypatch):
    monkeypatch.setenv("NOTION_INTEGRATION_TOKEN", "test-token")
    monkeypatch.setenv("NOTION_TEST_NOTE_PAGE_ID", "4005440836d58010bdb1f86b9a98fe23")
    calls = []
    class MockClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, **kwargs):
            calls.append(("GET", url))
            if "/pages/" in url:
                return httpx.Response(200, json={"last_edited_time": "2026-10-22T12:00:00Z"},
                                      request=httpx.Request("GET", url))
            return httpx.Response(200, json={"has_more": False, "results": [
                {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "课堂重点"}]}}
            ]}, request=httpx.Request("GET", url))
    monkeypatch.setattr("app.notion_notes_readonly.httpx.AsyncClient", MockClient)
    result = await inspect_configured_note()
    assert result["summary_preview"] == ["课堂重点"]
    assert result["notion_write_enabled"] is False
    assert len(calls) == 2 and all(method == "GET" for method, _ in calls)
