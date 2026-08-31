import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from enrichment.storage import storage
from enrichment.config import config

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_entities():
    # Setup test reference
    master_ref = {
        "reference_id": "ref_test_001",
        "project_id": "proj_test_001",
        "input": {"original_text": "Vaswani et al. 2017. Attention Is All You Need."},
        "canonical": {
            "title": {"value": "Attention Is All You Need", "source": "openalex", "confidence": 0.98, "verification_status": "verified"},
            "year": {"value": 2017, "source": "parsed"},
            "venue": {"value": "NeurIPS"},
            "identifiers": {"doi": {"value": "10.48550/arXiv.1706.03762"}}
        },
        "canonical_authors": [{"name": "Ashish Vaswani"}],
        "sources": {
            "openalex": {"matched": True, "confidence": 0.98},
            "crossref": {"matched": True, "confidence": 0.85},
            "google_scholar": {"matched": True, "confidence": 0.97}
        },
        "quality_and_conflicts": {"overall_confidence": 0.98, "conflicts": []},
        "doi_verification": {"status": "verified", "canonical_doi": "10.48550/arXiv.1706.03762"}
    }
    storage.save_reference("ref_test_001", master_ref)

    # Setup test paper
    paper_record = {
        "paper_id": "paper_test_001",
        "title": "Attention Is All You Need",
        "year": 2017,
        "doi": "10.48550/arXiv.1706.03762",
        "citations": {"canonical_value": 115000}
    }
    storage.save_paper("paper_test_001", paper_record)

    # Setup test project
    project_record = {
        "project_id": "proj_test_001",
        "input_pdf": {"filename": "transformer.pdf", "sha256": "abc12345"},
        "references": [
            {"id": "1", "text": "Vaswani 2017", "reference_id": "ref_test_001"}
        ]
    }
    storage.save_project("proj_test_001", project_record)


def test_get_reference_endpoint_success():
    res = client.get("/references/ref_test_001")
    assert res.status_code == 200
    data = res.json()
    assert data["reference_id"] == "ref_test_001"
    assert data["canonical"]["title"]["value"] == "Attention Is All You Need"

def test_get_reference_endpoint_404():
    res = client.get("/references/ref_non_existent")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_get_reference_sources_endpoint():
    res = client.get("/references/ref_test_001/sources")
    assert res.status_code == 200
    data = res.json()
    assert "sources" in data
    assert "openalex" in data["sources"]
    assert "google_scholar" in data["sources"]

def test_get_paper_endpoint():
    res = client.get("/papers/paper_test_001")
    assert res.status_code == 200
    data = res.json()
    assert data["paper_id"] == "paper_test_001"
    assert data["title"] == "Attention Is All You Need"

def test_get_paper_endpoint_404():
    res = client.get("/papers/paper_unknown")
    assert res.status_code == 404

def test_scholar_search_empty_query_400():
    res = client.get("/scholar/search?q=")
    assert res.status_code == 400

def test_scholar_search_unconfigured_key_fallback():
    with patch.object(config, "serpapi_key", ""):
        res = client.get("/scholar/search?q=Attention+is+all+you+need")
        assert res.status_code == 200
        data = res.json()
        assert data["available"] is False
        assert data["reason"] == "SERPAPI_KEY_NOT_CONFIGURED"
        assert "scholar_url" in data

def test_scholar_search_mocked_serpapi():
    mock_serpapi_res = {
        "organic_results": [
            {
                "position": 1,
                "title": "Attention is all you need",
                "link": "https://arxiv.org/abs/1706.03762",
                "inline_links": {"cited_by": {"total": 115000}}
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_serpapi_res

    with patch.object(config, "serpapi_key", "mock_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            res = client.get("/scholar/search?q=Attention+is+all+you+need&num=5")
            assert res.status_code == 200
            data = res.json()
            assert data["available"] is True
            assert len(data["results"]) == 1
            assert data["results"][0]["title"] == "Attention is all you need"
            assert data["results"][0]["citations"]["count"] == 115000

def test_get_project_endpoint():
    res = client.get("/projects/proj_test_001")
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == "proj_test_001"
    assert data["input_pdf"]["filename"] == "transformer.pdf"

def test_get_project_endpoint_404():
    res = client.get("/projects/proj_unknown")
    assert res.status_code == 404

def test_export_project_json():
    res = client.get("/projects/proj_test_001/export?format=json")
    assert res.status_code == 200
    data = res.json()
    assert "project" in data
    assert "references" in data
    assert len(data["references"]) == 1
    assert data["references"][0]["reference_id"] == "ref_test_001"

def test_export_project_bibtex():
    res = client.get("/projects/proj_test_001/export?format=bibtex")
    assert res.status_code == 200
    assert "@article{" in res.text
    assert "Attention Is All You Need" in res.text

def test_export_project_invalid_format_400():
    res = client.get("/projects/proj_test_001/export?format=pdf_bundle")
    assert res.status_code == 400
