"""Safe MVP tests for source-grounded paragraph matching."""
from io import BytesIO
import fitz
from fastapi.testclient import TestClient
from app.main import app
from app.paragraph_matcher import match_best_paragraph

client = TestClient(app)

def pdf_fixture():
    d = fitz.open()
    p = d.new_page()
    p.insert_text((72, 80), "Photosynthesis converts light into chemical energy.")
    p.insert_text((72, 170), "Soil moisture and nutrients affect plant growth.")
    value = d.tobytes()
    d.close()
    return value

def test_ranks_one_relevant_original_paragraph():
    result, annotated = match_best_paragraph(pdf_fixture(), "photosynthesis chemical energy", annotate=True)
    assert result["match_count"] == 1
    assert result["matched_pages"] == [1]
    assert "Photosynthesis" in result["best_match"]["text"]
    assert result["matching_method"] == "lexical_overlap_not_semantic_ai"
    d = fitz.open(stream=annotated, filetype="pdf")
    assert len(list(d[0].annots())) == 1
    d.close()

def test_no_overlap_does_not_invent_highlight():
    result, annotated = match_best_paragraph(pdf_fixture(), "astronaut spaceships", annotate=True)
    assert result["match_count"] == 0
    assert result["best_match"] is None
    d = fitz.open(stream=annotated, filetype="pdf")
    assert list(d[0].annots() or []) == []
    d.close()

def test_new_endpoints_and_existing_one():
    params = {"pdf": ("example.pdf", pdf_fixture(), "application/pdf")}
    res = client.post("/paragraph/preview", files=params, data={"notes": "photosynthesis chemical energy"})
    assert res.status_code == 200
    assert res.json()["match_count"] == 1
    res = client.post("/paragraph/highlight", files=params, data={"notes": "photosynthesis chemical energy"})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/pdf")
    assert res.headers["x-highlight-matches"] == "1"
    assert client.post("/preview", files=params, data={"notes": "Photosynthesis"}).status_code == 200

def test_reject_invalid_input():
    assert client.post("/paragraph/preview", files={"pdf": ("bad.pdf", b"bad", "application/pdf")}, data={"notes": "test"}).status_code == 422
    assert client.post("/paragraph/preview", files={"pdf": ("book.pdf", pdf_fixture(), "application/pdf")}, data={"notes": "   "}).status_code == 422
