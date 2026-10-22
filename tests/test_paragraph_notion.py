"""Tests for opt-in Notion export; no real network calls."""
from fastapi.testclient import TestClient
import fitz
from app.main import app
from app.notion_export import result_blocks, append_result

def _pdf():
    doc=fitz.open()
    p=doc.new_page()
    p.insert_text((72,72),"Photosynthesis converts light energy into chemical energy.")
    p.insert_text((72,120),"Roots absorb water and nutrients from the soil.")
    data=doc.tobytes()
    doc.close()
    return data

def test_best_paragraph_preview():
    client=TestClient(app)
    r=client.post("/paragraph/preview",files={"pdf":("book.pdf",_pdf(),"application/pdf")},
                  data={"notes":"photosynthesis light energy"})
    assert r.status_code==200
    body=r.json()
    assert body["match_count"]==1
    assert body["best_match"]["page"]==1
    assert "Photosynthesis" in body["best_match"]["text"]
    assert body["requires_confirmation"]

def test_paragraph_highlight():
    client=TestClient(app)
    r=client.post("/paragraph/highlight",files={"pdf":("book.pdf",_pdf(),"application/pdf")},
                  data={"notes":"photosynthesis light energy"})
    assert r.status_code==200
    doc=fitz.open(stream=r.content,filetype="pdf")
    assert len(list(doc[0].annots()))==1
    doc.close()

def test_notion_blocks_are_source_grounded():
    summary={"best_match":{"page":2,"text":"Roots absorb water."}}
    blocks=result_blocks(summary,"Botany")
    assert blocks[1]["paragraph"]["rich_text"][0]["text"]["content"].endswith("Page: 2")
    assert blocks[2]["quote"]["rich_text"][0]["text"]["content"]=="Roots absorb water."

def test_publish_disabled_without_demo_guard(monkeypatch):
    monkeypatch.delenv("DEMO_ACCESS_TOKEN",raising=False)
    client=TestClient(app)
    r=client.post("/notion/publish",files={"pdf":("book.pdf",_pdf(),"application/pdf")},
                  data={"notes":"photosynthesis","page_id":"a"*32})
    assert r.status_code==503
