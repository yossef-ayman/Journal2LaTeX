import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from enrichment.parser import ParsedReference
from enrichment.providers.openalex import OpenAlexProvider
from enrichment.providers.authors import OpenAlexAuthorProvider

client = TestClient(app)

@pytest.fixture
def anyio_backend():
    return "asyncio"

# 1. Paper returns author IDs
@pytest.mark.anyio
async def test_paper_returns_author_ids():
    provider = OpenAlexProvider()
    parsed_ref = ParsedReference(
        original_text="Vaswani et al. 2017",
        title="Attention is all you need"
    )

    mock_openalex_response = {
        "results": [
            {
                "id": "https://openalex.org/W2626778328",
                "doi": "https://doi.org/10.48550/arXiv.1706.03762",
                "display_name": "Attention Is All You Need",
                "publication_year": 2017,
                "authorships": [
                    {
                        "author": {
                            "id": "https://openalex.org/A5103024730",
                            "display_name": "Ashish Vaswani"
                        }
                    }
                ]
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_openalex_response

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        results = await provider.search_reference(parsed_ref)
        assert len(results) > 0
        authors = results[0]["authors"]
        assert len(authors) == 1
        assert authors[0]["author_id"] == "https://openalex.org/A5103024730"
        assert authors[0]["author_match_status"] == "matched"

# 2. Valid author ID returns profile (with h_index, i10_index, works_count, cited_by_count)
@pytest.mark.anyio
async def test_valid_author_id_returns_profile():
    provider = OpenAlexAuthorProvider()
    
    mock_author_data = {
        "id": "https://openalex.org/A5103024730",
        "display_name": "Ashish Vaswani",
        "works_count": 59,
        "cited_by_count": 12681,
        "summary_stats": {
            "h_index": 29,
            "i10_index": 45
        },
        "last_known_institutions": [
            {"display_name": "Google", "country_code": "US"}
        ],
        "topics": [
            {"display_name": "Natural Language Processing"}
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_author_data

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        profile = await provider.get_author("A5103024730")
        assert profile is not None
        assert profile["id"] == "https://openalex.org/A5103024730"
        assert profile["display_name"] == "Ashish Vaswani"
        assert profile["works_count"] == 59
        assert profile["cited_by_count"] == 12681
        assert profile["h_index"] == 29
        assert profile["i10_index"] == 45

# 3. Author works pagination
@pytest.mark.anyio
async def test_author_works_pagination():
    provider = OpenAlexAuthorProvider()

    mock_works_data = {
        "meta": {"count": 59},
        "results": [
            {
                "title": "Music Transformer",
                "publication_year": 2019,
                "doi": "https://doi.org/10.18653/v1/d19-1410",
                "cited_by_count": 300
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_works_data

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        works_res = await provider.get_author_works("A5103024730", page=1, per_page=10)
        assert works_res["page"] == 1
        assert works_res["per_page"] == 10
        assert works_res["total_count"] == 59
        assert len(works_res["results"]) == 1
        assert works_res["results"][0]["title"] == "Music Transformer"

# 4. Unknown author ID → 404
def test_unknown_author_id_returns_404():
    with patch.object(OpenAlexAuthorProvider, "get_author", new_callable=AsyncMock) as mock_get_author:
        mock_get_author.return_value = None
        response = client.get("/authors/A99999999999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

# 5. Ambiguous author → does not select random author
@pytest.mark.anyio
async def test_ambiguous_author_status():
    provider = OpenAlexProvider()
    
    mock_work_no_id = {
        "id": "https://openalex.org/W123",
        "title": "Paper by John Doe",
        "authorships": [
            {
                "author": {
                    "id": None,  # Missing ID
                    "display_name": "John Doe"
                }
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [mock_work_no_id]}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        ref = ParsedReference(original_text="Doe 2020", title="Paper by John Doe")
        results = await provider.search_reference(ref)
        assert len(results) > 0
        author_item = results[0]["authors"][0]
        assert author_item["author_id"] == ""
        assert author_item["author_match_status"] == "ambiguous"

# 6. API Endpoints Test
def test_api_get_author_profile_endpoint():
    mock_profile = {
        "id": "https://openalex.org/A5103024730",
        "name": "Ashish Vaswani",
        "display_name": "Ashish Vaswani",
        "works_count": 59,
        "cited_by_count": 12681,
        "h_index": 29,
        "i10_index": 45,
        "affiliations": ["Google"],
        "topics": ["Transformers"],
        "source": "openalex"
    }
    with patch.object(OpenAlexAuthorProvider, "get_author", new_callable=AsyncMock) as mock_get_author:
        mock_get_author.return_value = mock_profile

        res = client.get("/authors/A5103024730")
        assert res.status_code == 200
        data = res.json()
        assert data["display_name"] == "Ashish Vaswani"
        assert data["h_index"] == 29

def test_api_get_author_works_endpoint():
    mock_works = {
        "results": [
            {"title": "Attention Is All You Need", "year": 2017, "doi": "10.48550/arXiv.1706.03762", "citation_count": 6500}
        ],
        "page": 1,
        "per_page": 20,
        "total_count": 59
    }
    with patch.object(OpenAlexAuthorProvider, "get_author_works", new_callable=AsyncMock) as mock_get_works:
        mock_get_works.return_value = mock_works

        res = client.get("/authors/A5103024730/works?page=1&per_page=20")
        assert res.status_code == 200
        data = res.json()
        assert data["total_count"] == 59
        assert len(data["results"]) == 1
