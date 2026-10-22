from app.v07a_course_preview import _title, _select, _file_url
import pytest


def test_notion_textbook_property_parsing():
    assert _title({"title": [{"plain_text": "重庆市某苗圃苗木管护计划"}]}) == "重庆市某苗圃苗木管护计划"
    assert _select({"select": {"name": "园林苗圃学"}}) == "园林苗圃学"
    assert _file_url({"files": [{"file": {"url": "https://secure.notion-static.com/example.pdf"}}]}) == "https://secure.notion-static.com/example.pdf"


def test_pdf_binding_rejects_ambiguous_files():
    with pytest.raises(ValueError):
        _file_url({"files": []})
    with pytest.raises(ValueError):
        _file_url({"files": [{"external": {"url": "http://unsafe.test/file.pdf"}}]})
