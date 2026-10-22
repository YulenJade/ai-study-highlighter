import asyncio
import json

import httpx
import pytest

from app.notion_discovery import parse_course_bindings, resolve_course, discover_notes


COURSE_ID = "4005440836d581ca870af6443b71bc09"
BOOK_ID = "4015440836d5804380dfd3be8e7c2b2e"
NOTE_ID = "4005440836d58010bdb1f86b9a98fe23"


def test_config_rejects_missing_and_ambiguous():
    with pytest.raises(ValueError):
        parse_course_bindings("{}")
    with pytest.raises(ValueError):
        parse_course_bindings('{"园林苗圃学":{"course_page_id":"invalid","textbook_page_id":"invalid"}}')
    assert parse_course_bindings(json.dumps({
        "园林苗圃学": {"course_page_id": COURSE_ID, "textbook_page_id": BOOK_ID}
    }))["园林苗圃学"]["textbook_page_id"] == BOOK_ID


def test_ancestor_course_detection():
    bindings = parse_course_bindings(json.dumps({
        "园林苗圃学": {"course_page_id": COURSE_ID, "textbook_page_id": BOOK_ID}
    }))
    class Client:
        async def get(self, *args, **kwargs):
            raise AssertionError("Direct course parent should not require network")
    page = {"parent": {"type": "page_id", "page_id": COURSE_ID}}
    assert asyncio.run(resolve_course(page, Client(), {}, bindings)) == "园林苗圃学"


def test_discovery_only_returns_pages_in_bound_course(monkeypatch):
    monkeypatch.setenv("NOTION_INTEGRATION_TOKEN", "test-token")
    monkeypatch.setenv("NOTION_COURSE_BINDINGS_JSON", json.dumps({
        "园林苗圃学": {"course_page_id": COURSE_ID, "textbook_page_id": BOOK_ID}
    }))
    class MockClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            assert url.endswith("/search")
            return httpx.Response(200, json={"has_more": False, "results": [
                {"id": NOTE_ID, "object": "page", "parent": {"page_id": COURSE_ID},
                 "properties": {"title": {"type": "title", "title": [{"plain_text": "课堂笔记"}]}}},
                {"id": BOOK_ID, "object": "page", "parent": {"type": "workspace"}},
            ]}, request=httpx.Request("POST", url))
    monkeypatch.setattr("app.notion_discovery.httpx.AsyncClient", MockClient)
    result = asyncio.run(discover_notes())
    assert len(result["notes"]) == 1
    assert result["notes"][0]["course"] == "园林苗圃学"
    assert result["notion_write_enabled"] is False
