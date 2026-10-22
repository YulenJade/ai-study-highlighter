import pytest

from app.course_bindings import resolve_textbook


def test_unassigned_pdf_is_not_guessed():
    rows = [{"url": "https://example.test/book", "教材名称": None,
             "所属课程": None, "原版PDF": '["pdf-id"]', "处理状态": "待上传"}]
    with pytest.raises(ValueError, match="No named PDF"):
        resolve_textbook("园林植物病虫害防治", rows)


def test_single_explicit_binding():
    rows = [{"url": "https://example.test/book", "教材名称": "园林植物病虫害防治",
             "所属课程": "园林植物病虫害防治", "原版PDF": '["pdf-id"]', "处理状态": "待处理"}]
    result = resolve_textbook("园林植物病虫害防治", rows)
    assert result.title == "园林植物病虫害防治"


def test_ambiguous_binding_requires_selection():
    row = {"url": "https://example.test/book", "教材名称": "病虫害教材",
           "所属课程": "园林植物病虫害防治", "原版PDF": '["pdf-id"]'}
    with pytest.raises(ValueError, match="Multiple textbooks"):
        resolve_textbook("园林植物病虫害防治", [row, row])
