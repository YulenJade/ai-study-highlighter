"""Batch Notion publishing requires explicit selection and revalidated matches."""
import json
import fitz
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.notion_export import multi_result_blocks


def pdf():
    doc=fitz.open();p=doc.new_page()
    p.insert_text((72,72),"Photosynthesis converts light energy into chemical energy.")
    p.insert_text((72,120),"Roots absorb water and nutrients.")
    b=doc.tobytes();doc.close();return b


def summary():
    return {"results":[
        {"matched":True,"note":"photosynthesis","category":"key","page":1,"text":"Photosynthesis converts light energy."},
        {"matched":False,"note":"unknown","category":"key"},
    ]}


def test_selected_blocks_are_source_grounded():
    blocks=multi_result_blocks(summary(),"Botany",[0])
    assert len(blocks)==6
    assert blocks[4]["quote"]["rich_text"][0]["text"]["content"]=="Photosynthesis converts light energy."


@pytest.mark.parametrize("indices", [[],[1],[0,0],[2],[-1],[True]])
def test_invalid_selections_rejected(indices):
    with pytest.raises(ValueError):
        multi_result_blocks(summary(),"Botany",indices)


def test_publish_requires_confirmation(monkeypatch):
    monkeypatch.setenv("DEMO_ACCESS_TOKEN","test")
    client=TestClient(app)
    import base64
    auth="Basic "+base64.b64encode(b"demo:test").decode()
    r=client.post("/multi/notion/publish",
        headers={"Authorization":auth},
        files={"pdf":("book.pdf",pdf(),"application/pdf")},
        data={"notes":"photosynthesis","page_id":"a"*32,
              "selected_indices":json.dumps([0]),"confirmed":"false"})
    assert r.status_code==422
