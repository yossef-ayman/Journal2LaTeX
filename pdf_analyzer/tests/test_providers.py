import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from enrichment.parser import ParsedReference
from enrichment.providers.openalex import OpenAlexProvider
from enrichment.providers.crossref import CrossrefProvider

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_openalex_provider_doi_search():
    provider = OpenAlexProvider()
    parsed_ref = ParsedReference(
        original_text="Test Ref",
        doi="10.1000/182",
        title="Test Work Title"
    )

    mock_openalex_response = {
        "results": [
            {
                "id": "https://openalex.org/W12345",
                "doi": "https://doi.org/10.1000/182",
                "display_name": "Test Work Title",
                "publication_year": 2021,
                "cited_by_count": 42,
                "authorships": [
                    {"author": {"display_name": "Alice Smith"}}
                ],
                "primary_location": {
                    "source": {"display_name": "Journal of Testing"}
                }
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_openalex_response

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        results = await provider.search_reference(parsed_ref)
        assert len(results) == 1
        assert results[0]["title"] == "Test Work Title"
        assert results[0]["doi"] == "10.1000/182"
        assert results[0]["citation_count"] == 42
        assert results[0]["source"] == "openalex"

@pytest.mark.anyio
async def test_crossref_provider_search():
    provider = CrossrefProvider()
    parsed_ref = ParsedReference(
        original_text="Crossref Test Ref",
        title="Crossref Paper Title",
        doi="10.1016/j.test.2020"
    )

    mock_crossref_response = {
        "message": {
            "title": ["Crossref Paper Title"],
            "DOI": "10.1016/j.test.2020",
            "URL": "https://doi.org/10.1016/j.test.2020",
            "published-print": {"date-parts": [[2020]]},
            "author": [{"given": "Bob", "family": "Jones"}],
            "container-title": ["Crossref Journal"],
            "is-referenced-by-count": 15
        }
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_crossref_response

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        results = await provider.search_reference(parsed_ref)
        assert len(results) == 1
        assert results[0]["title"] == "Crossref Paper Title"
        assert results[0]["doi"] == "10.1016/j.test.2020"
        assert results[0]["source"] == "crossref"

@pytest.mark.anyio
async def test_google_scholar_provider_fallback():
    from enrichment.providers.google_scholar import GoogleScholarProvider
    provider = GoogleScholarProvider()
    parsed_ref = ParsedReference(
        original_text="Vaswani et al. Attention is all you need.",
        title="Attention is all you need"
    )

    results = await provider.search_reference(parsed_ref)
    assert len(results) >= 1
    assert "Attention is all you need" in results[0]["title"]
    assert "scholar.google.com" in results[0]["scholar_url"]
    assert results[0]["source"] == "google_scholar"
