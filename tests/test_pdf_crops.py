import fitz
from fastapi.testclient import TestClient
from app.main import app
from app.pdf_crops import crop_candidate


def sample_pdf():
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((70, 80), "Plants absorb water through roots.")
    p.insert_text((70, 130), "Photosynthesis uses light to make sugars.")
    data = doc.tobytes()
    doc.close()
    return data


def test_crop_is_real_png_and_has_provenance():
    metadata, image = crop_candidate(sample_pdf(), "Plants absorb water through roots", 0)
    assert image[:8] == bytes([137,80,78,71,13,10,26,10])
    assert metadata["page"] == 1
    assert metadata["source"] == "actual_pdf_render"
    assert metadata["requires_confirmation"] is True


def test_invalid_candidate_rejected():
    try:
        crop_candidate(sample_pdf(), "roots", 9)
    except ValueError:
        pass
    else:
        assert False, "Out-of-range candidate must be rejected"


def test_read_only_preview_and_crop_api():
    client = TestClient(app)
    files = {"pdf": ("test.pdf", sample_pdf(), "application/pdf")}
    response = client.post("/v07a/candidates", files=files,
                           data={"notes": "Plants absorb water through roots"})
    assert response.status_code == 200
    assert response.json()["notion_write_enabled"] is False
    crop = client.post("/v07a/crop", files=files,
                       data={"notes": "Plants absorb water through roots", "candidate_index": "0"})
    assert crop.status_code == 200
    assert crop.headers["content-type"].startswith("image/png")
    assert crop.content.startswith(bytes([137,80,78,71]))
