from io import BytesIO

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


def test_terms():
    assert extract_terms("- photosynthesis\n2. chlorophyll") == ["photosynthesis", "chlorophyll"]


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_highlight():
    response = client.post("/highlight", files={"pdf": ("book.pdf", make_pdf(), "application/pdf")}, data={"notes": "photosynthesis"})
    assert response.status_code == 200
    assert response.headers["x-highlight-matches"] == "1"
    doc = fitz.open(stream=response.content, filetype="pdf")
    assert len(list(doc[0].annots())) == 1
    doc.close()


def test_invalid_pdf():
    response = client.post("/highlight", files={"pdf": ("bad.pdf", b"not pdf", "application/pdf")}, data={"notes": "photosynthesis"})
    assert response.status_code == 422
