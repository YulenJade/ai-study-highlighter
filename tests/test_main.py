from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from app.main import app, extract_terms

client = TestClient(app)


def make_pdf():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "photosynthesis converts light")
    data = doc.tobytes()
    doc.close()
    return data


def make_chinese_pdf():
    """Use a bundled CJK font available on GitHub Ubuntu runners."""
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    ]
    font_path = next((p for p in candidates if Path(p).exists()), None)
    if font_path is None:
        return None
    doc = fitz.open()
    page = doc.new_page()
    font = fitz.Font(fontfile=font_path)
    page.insert_text((72, 72), "植物光合作用", fontname="cjk", fontfile=font_path, fontsize=16)
    data = doc.tobytes()
    doc.close()
    return data


def test_terms():
    assert extract_terms("- photosynthesis\n2. chlorophyll") == ["photosynthesis", "chlorophyll"]


def test_health():
    assert client.get("/health").json()["version"] == "0.2.0"


def test_highlight():
    response = client.post("/highlight", files={"pdf": ("book.pdf", make_pdf(), "application/pdf")}, data={"notes": "photosynthesis"})
    assert response.status_code == 200
    assert response.headers["x-highlight-matches"] == "1"
    assert response.headers["x-matched-pages"] == "1"
    doc = fitz.open(stream=response.content, filetype="pdf")
    assert len(list(doc[0].annots())) == 1
    doc.close()


def test_preview_and_categories():
    response = client.post("/preview", files={"pdf": ("book.pdf", make_pdf(), "application/pdf")},
                           data={"notes": "[定义] photosynthesis\n[补充] absent"})
    assert response.status_code == 200
    body = response.json()
    assert body["matched_pages"] == [1]
    assert body["match_count"] == 1
    assert body["matches"][0]["category"] == "definition"
    assert body["matches"][0]["rect"]
    assert body["unmatched_terms"] == ["absent"]


def test_annotation_color():
    response = client.post("/highlight", files={"pdf": ("book.pdf", make_pdf(), "application/pdf")},
                           data={"notes": "[定义] photosynthesis"})
    assert response.status_code == 200
    doc = fitz.open(stream=response.content, filetype="pdf")
    annot = next(doc[0].annots())
    assert len(annot.colors["stroke"]) == 3
    assert abs(annot.colors["stroke"][1] - 0.82) < 0.01
    doc.close()


def test_invalid_pdf():
    response = client.post("/highlight", files={"pdf": ("bad.pdf", b"not pdf", "application/pdf")},
                           data={"notes": "photosynthesis"})
    assert response.status_code == 422


def test_empty_notes():
    response = client.post("/preview", files={"pdf": ("book.pdf", make_pdf(), "application/pdf")},
                           data={"notes": "x"})
    assert response.status_code == 422


def test_chinese_pdf_when_font_available():
    import pytest
    pdf = make_chinese_pdf()
    if pdf is None:
        pytest.skip("CJK font unavailable")
    response = client.post("/preview", files={"pdf": ("cn.pdf", pdf, "application/pdf")},
                           data={"notes": "[重点] 植物光合作用"})
    assert response.status_code == 200
    assert response.json()["match_count"] >= 1
