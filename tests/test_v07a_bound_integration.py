"""End-to-end mocked Notion API → actual generated PDF → actual PNG crop.

No live credentials, no network, no Notion writes.
"""
import asyncio
import json

import fitz
import httpx

from app.v07a_course_preview import inspect_bound_course


NOTE_ID = "4015440836d5817cbd6df5c01fc8d876"
BOOK_ID = "4015440836d5804380dfd3be8e7c2b2e"
COURSE_ID = "4005440836d58138b8eee61483667132"
FOLDER_ID = "4005440836d581949082c8e78ebb0cfd"


def make_pdf():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 80), "Nursery irrigation and fertilization management", fontsize=12)
    page.insert_text((50, 110), "Watering and pruning improve seedling growth", fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


def test_bound_course_preview_and_png(monkeypatch):
    monkeypatch.setenv("NOTION_INTEGRATION_TOKEN", "fake-test-token")
    monkeypatch.setenv("NOTION_TEST_NOTE_PAGE_ID", NOTE_ID)
    monkeypatch.setenv("NOTION_TEST_TEXTBOOK_PAGE_ID", BOOK_ID)
    monkeypatch.setenv("NOTION_TEST_COURSE", "园林苗圃学")
    monkeypatch.setenv("NOTION_COURSE_BINDINGS_JSON", json.dumps({"园林苗圃学": {"course_page_id": COURSE_ID, "textbook_page_id": BOOK_ID}}))
    pdf = make_pdf()
    file_url = "https://secure.notion-static.com/example.pdf"
    calls = []

    def handler(request):
        calls.append((request.method, str(request.url)))
        path = request.url.path
        if path.endswith(NOTE_ID) and "/pages/" in path:
            return httpx.Response(200, json={"id": NOTE_ID, "parent": {"page_id": FOLDER_ID}, "last_edited_time": "2026-10-22T00:00:00Z"})
        if path.endswith(FOLDER_ID) and "/pages/" in path:
            return httpx.Response(200, json={"id": FOLDER_ID, "parent": {"page_id": COURSE_ID}})
        if path.endswith(BOOK_ID) and "/pages/" in path:
            return httpx.Response(200, json={"properties": {
                "教材名称": {"title": [{"plain_text": "重庆市某苗圃苗木管护计划"}]},
                "所属课程": {"select": {"name": "园林苗圃学"}},
                "原版PDF": {"files": [{"file": {"url": file_url}}]},
            }})
        if path.endswith("/children"):
            return httpx.Response(200, json={"has_more": False, "results": [
                {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "模拟课堂记录（供关键词匹配）"}]}},
                {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Watering and pruning improve seedling growth"}]}},
                {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "测试核对清单"}]}},
                {"type": "to_do", "to_do": {"rich_text": [{"plain_text": "Do not match this checklist"}]}}
            ]})
        if str(request.url) == file_url:
            return httpx.Response(200, content=pdf)
        return httpx.Response(404)

    real_client = httpx.AsyncClient
    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("app.v07a_course_preview.httpx.AsyncClient", client_factory)
    preview = asyncio.run(inspect_bound_course())
    assert preview["course"] == "园林苗圃学"
    assert preview["pdf_page_count"] == 1
    assert preview["candidates"]
    assert preview["notion_write_enabled"] is False
    result, png = asyncio.run(inspect_bound_course(candidate_index=0))
    assert result["selected_candidate"]["page"] == 1
    assert png.startswith(bytes.fromhex("89504e470d0a1a0a"))
    assert all(method == "GET" for method, _ in calls)


def test_bound_course_rejects_wrong_course_binding(monkeypatch):
    monkeypatch.setenv("NOTION_INTEGRATION_TOKEN", "fake-test-token")
    monkeypatch.setenv("NOTION_TEST_NOTE_PAGE_ID", NOTE_ID)
    monkeypatch.setenv("NOTION_TEST_TEXTBOOK_PAGE_ID", BOOK_ID)
    monkeypatch.setenv("NOTION_TEST_COURSE", "园林苗圃学")
    monkeypatch.setenv("NOTION_COURSE_BINDINGS_JSON", json.dumps({
        "园林植物病虫害防治": {"course_page_id": COURSE_ID, "textbook_page_id": BOOK_ID}
    }))
    import pytest
    with pytest.raises(ValueError, match="course and textbook"):
        asyncio.run(inspect_bound_course())
