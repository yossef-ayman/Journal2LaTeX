import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_enrich_references_empty():
    response = client.post("/references/enrich", json={"references": []})
    assert response.status_code == 200
    assert response.json() == {"results": []}

@patch("enrichment.pipeline.ReferenceEnricher.enrich_batch")
def test_enrich_references_endpoint(mock_enrich_batch):
    mock_enrich_batch.return_value = [
        {
            "original_text": "Vaswani et al 2017 Attention is all you need",
            "title": "Attention is All You Need",
            "authors": [{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}],
            "year": 2017,
            "journal": "NeurIPS",
            "doi": "10.48550/arXiv.1706.03762",
            "url": "https://doi.org/10.48550/arXiv.1706.03762",
            "openalex_id": "https://openalex.org/W2964257018",
            "citation_count": 95000,
            "source": "openalex",
            "confidence": 0.98,
            "match_status": "matched"
        }
    ]

    response = client.post(
        "/references/enrich",
        json={"references": [{"text": "Vaswani et al 2017 Attention is all you need"}]}
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    item = data["results"][0]
    assert item["title"] == "Attention is All You Need"
    assert item["match_status"] == "matched"
    assert item["confidence"] == 0.98
