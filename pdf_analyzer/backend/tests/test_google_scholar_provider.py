import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from enrichment.parser import ParsedReference
from enrichment.providers.google_scholar import GoogleScholarProvider
from enrichment.config import config

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_scholar_unconfigured_key_returns_graceful_fallback():
    provider = GoogleScholarProvider()
    parsed_ref = ParsedReference(
        original_text="Vaswani et al. (2017). Attention is all you need.",
        title="Attention is all you need"
    )

    with patch.object(config, "serpapi_key", ""):
        results = await provider.search_reference(parsed_ref)
        assert len(results) >= 1
        cand = results[0]
        assert cand["source"] == "google_scholar"
        assert cand["available"] is False
        assert cand["reason"] == "SERPAPI_KEY_NOT_CONFIGURED"
        assert "scholar.google.com" in cand["scholar_url"]
        assert cand["citation_count"] is None

@pytest.mark.anyio
async def test_scholar_successful_serpapi_search():
    provider = GoogleScholarProvider()
    parsed_ref = ParsedReference(
        original_text="Vaswani et al. (2017). Attention is all you need.",
        title="Attention is all you need",
        authors=[{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}]
    )

    mock_serpapi_response = {
        "search_metadata": {"id": "search_123", "status": "Success"},
        "search_parameters": {"engine": "google_scholar", "q": "Attention is all you need Ashish Vaswani"},
        "organic_results": [
            {
                "position": 0,
                "title": "Attention is all you need",
                "result_id": "res_001",
                "link": "https://arxiv.org/abs/1706.03762",
                "snippet": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
                "publication_info": {
                    "summary": "A Vaswani, N Shazeer, N Parmar - Advances in neural information ..., 2017 - proceedings.neurips.cc",
                    "authors": [
                        {"name": "Ashish Vaswani", "author_id": "A_VASWANI_ID", "link": "https://scholar.google.com/citations?user=A_VASWANI_ID"},
                        {"name": "Noam Shazeer", "author_id": "N_SHAZEER_ID", "link": "https://scholar.google.com/citations?user=N_SHAZEER_ID"}
                    ]
                },
                "inline_links": {
                    "cited_by": {
                        "total": 115000,
                        "link": "https://scholar.google.com/scholar?cites=12345"
                    },
                    "versions": {
                        "total": 48,
                        "link": "https://scholar.google.com/scholar?cluster=12345"
                    },
                    "related_pages_link": "https://scholar.google.com/scholar?q=related:12345"
                },
                "resources": [
                    {
                        "title": "arxiv.org [PDF]",
                        "link": "https://arxiv.org/pdf/1706.03762",
                        "file_format": "PDF"
                    }
                ],
                "cluster_id": "12345"
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_serpapi_response

    with patch.object(config, "serpapi_key", "test_serpapi_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            results = await provider.search_reference(parsed_ref)
            assert len(results) == 1
            cand = results[0]
            assert cand["title"] == "Attention is all you need"
            assert cand["citation_count"] == 115000
            assert cand["available"] is True
            assert cand["raw_file"] is not None
            assert cand["normalized_file"] is not None

            norm_res = cand["normalized_result"]
            assert norm_res["position"] == 0
            assert norm_res["citations"]["count"] == 115000
            assert norm_res["versions"]["count"] == 48
            assert len(norm_res["resources"]) == 1
            assert norm_res["resources"][0]["file_format"] == "PDF"
            assert norm_res["authors"][0]["author_id"] == "A_VASWANI_ID"

@pytest.mark.anyio
async def test_scholar_http_error_graceful_handling():
    provider = GoogleScholarProvider()
    parsed_ref = ParsedReference(
        original_text="Vaswani et al. 2017",
        title="Attention is all you need"
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.json.return_value = {"error": "Rate limit reached"}

    with patch.object(config, "serpapi_key", "test_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            search_data = await provider.search_query("Attention is all you need")
            assert search_data["available"] is False
            assert search_data["error"]["status_code"] == 429
            assert "Rate limit" in search_data["error"]["detail"]
