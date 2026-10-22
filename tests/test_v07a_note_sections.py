import pytest

from app.v07a_note_sections import extract_matching_notes


def block(kind, text):
    return {"type": kind, kind: {"rich_text": [{"plain_text": text}]}}


def test_only_classroom_record_is_used():
    blocks = [
        block("heading_2", "测试说明"),
        block("paragraph", "这是测试元数据，不应参与匹配"),
        block("heading_2", "模拟课堂记录（供关键词匹配）"),
        block("numbered_list_item", "春季浇水与施肥管理"),
        block("numbered_list_item", "苗圃病虫害巡查"),
        block("heading_2", "测试核对清单"),
        block("to_do", "自动扫描能发现本页面"),
    ]
    assert extract_matching_notes(blocks) == "春季浇水与施肥管理\n苗圃病虫害巡查"


def test_unknown_ai_notes_layout_requires_review():
    with pytest.raises(ValueError, match="No recognized"):
        extract_matching_notes([block("paragraph", "原始转录可能非常长")])
