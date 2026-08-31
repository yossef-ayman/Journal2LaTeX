import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from enrichment.parser import ParsedReference
from enrichment.providers.openalex import OpenAlexProvider
from enrichment.providers.crossref import CrossrefProvider
from enrichment.providers.google_scholar import GoogleScholarProvider
from enrichment.storage import storage
from enrichment.config import config

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_openalex_persists_raw_and_normalized():
    provider = OpenAlexProvider()
    parsed_ref = ParsedReference(original_text="Vaswani 2017", title="Attention is all you need")

    mock_resp_data = {
        "results": [
            {
                "id": "https://openalex.org/W2626778328",
                "display_name": "Attention Is All You Need",
                "publication_year": 2017,
                "cited_by_count": 12685,
                "authorships": [{"author": {"id": "https://openalex.org/A5103024730", "display_name": "Ashish Vaswani"}}]
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_resp_data

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        candidates = await provider.search_reference(parsed_ref)
        assert len(candidates) > 0
        assert candidates[0]["title"] == "Attention Is All You Need"
        assert candidates[0]["raw_file"] is not None
        
        # Verify raw and normalized exist in storage
        raw_loaded = storage.load_raw("openalex", "title:Attention is all you need")
        assert raw_loaded is not None
        assert "results" in raw_loaded
        assert len(raw_loaded["results"]) == 1

        norm_loaded = storage.load_normalized("openalex", "title:Attention is all you need")
        assert norm_loaded is not None
        assert len(norm_loaded) == 1
        assert norm_loaded[0]["title"] == "Attention Is All You Need"

@pytest.mark.anyio
async def test_crossref_persists_raw_and_normalized():
    provider = CrossrefProvider()
    parsed_ref = ParsedReference(original_text="Attention 2017", title="Attention Is All You Need", doi="10.48550/arXiv.1706.03762")

    mock_resp_data = {
        "message": {
            "title": ["Attention Is All You Need"],
            "DOI": "10.48550/arXiv.1706.03762",
            "is-referenced-by-count": 16,
            "author": [{"given": "Ashish", "family": "Vaswani"}]
        }
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_resp_data

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        candidates = await provider.search_reference(parsed_ref)
        assert len(candidates) > 0
        assert candidates[0]["title"] == "Attention Is All You Need"
        assert candidates[0]["raw_file"] is not None

        raw_loaded = storage.load_raw("crossref", "doi:10.48550/arxiv.1706.03762")
        assert raw_loaded is not None
        assert raw_loaded["message"]["DOI"] == "10.48550/arXiv.1706.03762"
