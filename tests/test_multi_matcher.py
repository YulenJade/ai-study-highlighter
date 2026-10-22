"""V0.4 multi-note API regression tests."""
import fitz
from fastapi.testclient import TestClient
from app.main import app


def sample_pdf():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Photosynthesis converts light energy into chemical energy.")
    page.insert_text((72, 120), "Roots absorb water and nutrients from soil.")
    page.insert_text((72, 170), "Pruning removes damaged and crossing branches.")
    data = doc.tobytes()
    doc.close()
    return data


def test_multiple_notes_find_distinct_source_blocks():
    client = TestClient(app)
    response = client.post("/multi/preview",
        files={"pdf": ("sample.pdf", sample_pdf(), "application/pdf")},
        data={"notes": "[重点] photosynthesis light energy\n[定义] roots absorb water"})
    assert response.status_code == 200
    result = response.json()
    assert result["note_count"] == 2
    assert result["match_count"] == 2
    assert result["requires_confirmation"] is True
    assert "Photosynthesis" in result["results"][0]["text"]
    assert "Roots" in result["results"][1]["text"]


def test_multiple_highlights_use_distinct_colors():
    client = TestClient(app)
    response = client.post("/multi/highlight",
        files={"pdf": ("sample.pdf", sample_pdf(), "application/pdf")},
        data={"notes": "[重点] photosynthesis light energy\n[定义] roots absorb water"})
    assert response.status_code == 200
    doc = fitz.open(stream=response.content, filetype="pdf")
    annots = list(doc[0].annots())
    assert len(annots) == 2
    assert annots[0].colors["stroke"] != annots[1].colors["stroke"]
    doc.close()


def test_unmatched_note_remains_unmatched():
    client = TestClient(app)
    response = client.post("/multi/preview",
        files={"pdf": ("sample.pdf", sample_pdf(), "application/pdf")},
        data={"notes": "zzzzzzzzunknownterm"})
    assert response.status_code == 200
    assert response.json()["match_count"] == 0
