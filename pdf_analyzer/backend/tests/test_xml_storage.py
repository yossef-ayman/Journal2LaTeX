import os
import io
import fitz
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from main import app
from enrichment.xml_storage import XMLStorageEngine, compute_bytes_hash, compute_query_hash

client = TestClient(app)


def test_hash_helpers():
    data = b"Sample academic PDF file content for test"
    h1 = compute_bytes_hash(data)
    h2 = compute_bytes_hash(data)
    assert h1 == h2
    assert len(h1) == 64

    q1 = compute_query_hash("Deep Learning In Medicine")
    q2 = compute_query_hash(" deep   learning in medicine  ")
    assert q1 == q2


def test_xml_storage_document_lifecycle(tmp_path):
    db_file = str(tmp_path / "test_cache.db")
    engine = XMLStorageEngine(db_path=db_file, xml_dir=str(tmp_path / "xml_store"))

    pdf_hash = "abc123456789def0"
    filename = "paper_2024.pdf"
    doc_data = {
        "title": "Deep Residual Learning for Image Recognition",
        "journal": "CVPR",
        "doi": "10.1109/CVPR.2016.90",
        "arxiv_id": "1512.03385",
        "page_count": 12,
        "authors": ["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"],
        "affiliations": ["Microsoft Research"],
        "abstract": "Deeper neural networks are more difficult to train.",
        "keywords": ["Deep Learning", "Residual Networks", "Vision"],
        "headings": [
            {"text": "Introduction", "level": 1, "page": 1},
            {"text": "Related Work", "level": 1, "page": 2}
        ],
        "references": [
            {"id": "1", "text": "LeCun, Y. et al. Deep Learning, Nature 2015."},
            {"id": "2", "text": "Krizhevsky, A. et al. ImageNet Classification with DCNNs, NeurIPS 2012."}
        ]
    }

    # Save
    xml_path = engine.save_document_xml(pdf_hash, filename, doc_data)
    assert os.path.exists(xml_path)

    # Retrieve
    cached = engine.get_cached_document(pdf_hash)
    assert cached is not None
    assert cached["cached"] is True
    assert cached["title"] == doc_data["title"]
    assert cached["journal"] == doc_data["journal"]
    assert cached["doi"] == doc_data["doi"]
    assert len(cached["authors"]) == 4
    assert cached["authors"][0] == "Kaiming He"
    assert len(cached["references"]) == 2
    assert "xml" in cached

    # List & Raw
    docs = engine.list_documents()
    assert any(d["pdf_hash"] == pdf_hash for d in docs)
    raw_xml = engine.get_document_xml_raw(pdf_hash)
    assert raw_xml is not None
    assert "<academic_document" in raw_xml


def test_xml_storage_search_incremental_merge(tmp_path):
    db_file = str(tmp_path / "test_cache.db")
    engine = XMLStorageEngine(db_path=db_file, xml_dir=str(tmp_path / "xml_store"))

    query = "Transformer Attention Mechanism"
    results_batch1 = [
        {
            "position": 0,
            "title": "Attention Is All You Need",
            "link": "https://arxiv.org/abs/1706.03762",
            "snippet": "The dominant sequence transduction models are based on complex recurrent networks.",
            "year": 2017,
            "venue": "NeurIPS",
            "authors": [{"name": "Ashish Vaswani", "author_id": "A1"}]
        }
    ]

    engine.save_search_xml(query, results_batch1)
    cached = engine.get_cached_search(query)
    assert cached is not None
    assert len(cached["results"]) == 1

    # Second batch with 1 duplicate and 1 new item
    results_batch2 = [
        {
            "position": 0,
            "title": "Attention Is All You Need",
            "link": "https://arxiv.org/abs/1706.03762",
            "snippet": "Duplicate item",
            "year": 2017
        },
        {
            "position": 1,
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "link": "https://arxiv.org/abs/1810.04805",
            "snippet": "We introduce a new language representation model called BERT.",
            "year": 2018,
            "venue": "NAACL",
            "authors": [{"name": "Jacob Devlin", "author_id": "A2"}]
        }
    ]

    engine.save_search_xml(query, results_batch2, merge=True)
    merged = engine.get_cached_search(query)
    assert merged is not None
    # Total distinct results should be exactly 2
    assert len(merged["results"]) == 2
    titles = [r["title"] for r in merged["results"]]
    assert "Attention Is All You Need" in titles
    assert "BERT: Pre-training of Deep Bidirectional Transformers" in titles


def test_xml_storage_author_lifecycle(tmp_path):
    db_file = str(tmp_path / "test_cache.db")
    engine = XMLStorageEngine(db_path=db_file, xml_dir=str(tmp_path / "xml_store"))

    author_id = "A50001"
    profile = {
        "id": author_id,
        "name": "Geoffrey Hinton",
        "display_name": "Geoffrey E. Hinton",
        "works_count": 350,
        "cited_by_count": 500000,
        "h_index": 170,
        "i10_index": 320,
        "affiliations": ["University of Toronto", "Google Brain"],
        "topics": ["Artificial Intelligence", "Deep Learning"],
        "source": "openalex"
    }

    xml_path = engine.save_author_xml(author_id, profile)
    assert os.path.exists(xml_path)

    cached_author = engine.get_cached_author(author_id)
    assert cached_author is not None
    assert cached_author["display_name"] == "Geoffrey E. Hinton"
    assert cached_author["works_count"] == 350
    assert cached_author["h_index"] == 170
    assert "University of Toronto" in cached_author["affiliations"]


def test_xml_api_endpoints():
    # 1. Documents list
    res = client.get("/xml/documents")
    assert res.status_code == 200
    data = res.json()
    assert "documents" in data

    # 2. Searches list
    res = client.get("/xml/searches")
    assert res.status_code == 200
    data = res.json()
    assert "searches" in data

    # 3. Nonexistent document
    res = client.get("/xml/document/nonexistent_hash_999")
    assert res.status_code == 404


def test_analyze_pdf_caching_lifecycle():
    # Create minimal valid PDF using PyMuPDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "An Efficient XML Storage Architecture for Academic Papers", fontsize=16)
    page.insert_text((50, 100), "Authors: Jane Doe, John Smith", fontsize=12)
    page.insert_text((50, 130), "Abstract: In this paper we introduce an instant XML storage engine.", fontsize=10)
    page.insert_text((50, 160), "1. Introduction", fontsize=14)
    page.insert_text((50, 180), "We store XML locally to prevent unnecessary token usage.", fontsize=10)
    page.insert_text((50, 210), "References", fontsize=14)
    page.insert_text((50, 230), "[1] Knuth, D. The TeXbook, Addison-Wesley 1984.", fontsize=10)
    
    pdf_bytes = doc.tobytes()
    doc.close()

    # First upload -> should parse and cache
    res1 = client.post(
        "/analyze",
        files={"file": ("test_paper.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert "pdf_hash" in data1
    assert data1["cached"] is False
    pdf_hash = data1["pdf_hash"]

    # Second upload of the EXACT same PDF -> must return INSTANTLY from local XML cache
    res2 = client.post(
        "/analyze",
        files={"file": ("test_paper.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["cached"] is True
    assert data2["pdf_hash"] == pdf_hash

    # Verify document is available via /xml/document/{pdf_hash}
    res_xml = client.get(f"/xml/document/{pdf_hash}")
    assert res_xml.status_code == 200
    assert "application/xml" in res_xml.headers["content-type"]
    assert "<academic_document" in res_xml.text
