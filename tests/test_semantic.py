"""Semantic ranking and opt-in endpoint tests; no external API calls."""
import asyncio
import fitz
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import semantic_matcher


def pdf():
    doc=fitz.open()
    p=doc.new_page()
    p.insert_text((72,72),"Plants make sugars using light energy.")
    p.insert_text((72,120),"Roots absorb moisture from the ground.")
    data=doc.tobytes();doc.close();return data


def test_cosine():
    assert semantic_matcher.cosine([1,0],[1,0]) == pytest.approx(1)
    assert semantic_matcher.cosine([1,0],[0,1]) == pytest.approx(0)


def test_candidates_rank_by_semantic_vectors(monkeypatch):
    async def fake_embeddings(texts):
        assert len(texts)==3
        return [[0,1],[1,0],[0,1]]
    monkeypatch.setattr(semantic_matcher,"_embeddings",fake_embeddings)
    result=asyncio.run(semantic_matcher.semantic_candidates(pdf(),"植物如何吸收水分"))
    assert result["candidates"][0]["page"]==1
    assert "Roots" in result["candidates"][0]["text"]
    assert result["requires_confirmation"]
    assert result["matching_method"]=="openai_embeddings"
    output=semantic_matcher.highlight_selected(pdf(),result["candidates"][0])
    doc=fitz.open(stream=output,filetype="pdf")
    assert len(list(doc[0].annots()))==1
    doc.close()


def test_consent_required():
    client=TestClient(app)
    r=client.post("/semantic/preview",
                  files={"pdf":("book.pdf",pdf(),"application/pdf")},
                  data={"notes":"roots"})
    assert r.status_code==422


def test_no_api_key_is_explicit(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY",raising=False)
    client=TestClient(app)
    r=client.post("/semantic/preview",
                  files={"pdf":("book.pdf",pdf(),"application/pdf")},
                  data={"notes":"roots","consent":"true"})
    assert r.status_code==503


def test_long_textbook_shortlist_covers_middle_and_end():
    paragraphs=[{"page":i+1,"text":f"Unique passage {i}"} for i in range(500)]
    selected=semantic_matcher._shortlist(paragraphs,"photosynthesis sunlight")
    pages={p["page"] for p in selected}
    assert len(selected)==120
    assert any(200 <= page <= 300 for page in pages)
    assert any(page >= 450 for page in pages)
    assert all(p in paragraphs for p in selected)
