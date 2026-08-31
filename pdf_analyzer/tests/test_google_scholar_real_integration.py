import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from enrichment.parser import ReferenceParser
from enrichment.providers.google_scholar import GoogleScholarProvider
from enrichment.reconciler import MultiSourceReconciler
from enrichment.config import config

client = TestClient(app)

@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_scholar_search_response_parsing_complete_fields():
    mock_payload = {
        "organic_results": [
            {
                "position": 0,
                "title": "Attention Is All You Need",
                "link": "https://proceedings.neurips.cc/paper/7181-attention-is-all-you-need.pdf",
                "snippet": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
                "publication_info": {
                    "summary": "A Vaswani, N Shazeer, N Parmar - Advances in neural information processing systems, 2017 - proceedings.neurips.cc",
                    "authors": [
                        {"name": "Ashish Vaswani", "author_id": "scholar_auth_01", "link": "https://scholar.google.com/citations?user=scholar_auth_01"},
                        {"name": "Noam Shazeer", "author_id": "scholar_auth_02"}
                    ]
                },
                "inline_links": {
                    "cited_by": {
                        "total": 98500,
                        "link": "https://scholar.google.com/scholar?cites=1234567890123456789"
                    },
                    "versions": {
                        "total": 42,
                        "link": "https://scholar.google.com/scholar?cluster=1234567890123456789"
                    },
                    "related_pages_link": "https://scholar.google.com/scholar?q=related:1234567890123456789"
                },
                "resources": [
                    {
                        "title": "neurips.cc [PDF]",
                        "link": "https://proceedings.neurips.cc/paper/7181-attention-is-all-you-need.pdf",
                        "file_format": "PDF"
                    }
                ],
                "cluster_id": "1234567890123456789"
            }
        ],
        "pagination": {"next": "https://scholar.google.com/scholar?start=10"}
    }

    provider = GoogleScholarProvider()
    normalized = provider._normalize_organic_results(mock_payload["organic_results"], "Attention Is All You Need", "https://scholar.google.com")
    
    assert len(normalized) == 1
    r = normalized[0]
    assert r["title"] == "Attention Is All You Need"
    assert r["link"] == "https://proceedings.neurips.cc/paper/7181-attention-is-all-you-need.pdf"
    assert r["cluster_id"] == "1234567890123456789"
    assert r["publication"]["year"] == 2017
    assert r["citations"]["count"] == 98500
    assert r["citations"]["link"] == "https://scholar.google.com/scholar?cites=1234567890123456789"
    assert r["versions"]["count"] == 42
    assert len(r["authors"]) == 2
    assert r["authors"][0]["name"] == "Ashish Vaswani"
    assert r["authors"][0]["author_id"] == "scholar_auth_01"
    assert len(r["resources"]) == 1
    assert r["resources"][0]["file_format"] == "PDF"


def test_scholar_metadata_preservation_in_reconciler():
    parsed = ReferenceParser.parse("Vaswani, A. (2017). Attention is all you need.")
    
    scholar_candidate = {
        "title": "Attention Is All You Need",
        "authors": [
            {"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani", "author_id": "scholar_vaswani", "source": "google_scholar"}
        ],
        "year": 2017,
        "journal": "Advances in Neural Information Processing Systems",
        "url": "https://proceedings.neurips.cc/paper/7181-attention-is-all-you-need.pdf",
        "scholar_url": "https://scholar.google.com/scholar?cluster=1234567890123456789",
        "cluster_id": "1234567890123456789",
        "cited_by_url": "https://scholar.google.com/scholar?cites=1234567890123456789",
        "citation_count": 98500,
        "versions_count": 42,
        "source": "google_scholar",
        "available": True,
        "raw_file": "data/raw/google_scholar/test_raw.json",
        "normalized_file": "data/normalized/google_scholar/test_norm.json",
        "normalized_result": {
            "title": "Attention Is All You Need",
            "cluster_id": "1234567890123456789",
            "citations": {"count": 98500, "link": "https://scholar.google.com/scholar?cites=1234567890123456789"},
            "versions": {"count": 42, "link": "https://scholar.google.com/scholar?cluster=1234567890123456789"}
        }
    }

    openalex_candidate = {
        "title": "Attention Is All You Need",
        "authors": [
            {"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani", "author_id": "https://openalex.org/A5103024730", "source": "openalex"}
        ],
        "year": 2017,
        "openalex_id": "https://openalex.org/W2626778328",
        "citation_count": 95000,
        "source": "openalex"
    }

    master = MultiSourceReconciler.reconcile(
        parsed_ref=parsed,
        openalex_candidates=[openalex_candidate],
        crossref_candidates=[],
        scholar_candidates=[scholar_candidate]
    )

    # 1. Verify Identifiers
    idents = master["canonical"]["identifiers"]
    assert idents["google_scholar_cluster_id"]["value"] == "1234567890123456789"
    assert idents["google_scholar_cluster_id"]["verification_status"] == "verified"
    assert idents["google_scholar_url"]["value"] == "https://scholar.google.com/scholar?cluster=1234567890123456789"

    # 2. Verify Source Preservation
    s_schol = master["sources"]["google_scholar"]
    assert s_schol["available"] is True
    assert s_schol["matched"] is True
    assert s_schol["cluster_id"] == "1234567890123456789"
    assert s_schol["citation_count"] == 98500
    assert s_schol["versions_count"] == 42
    assert s_schol["cited_by_url"] == "https://scholar.google.com/scholar?cites=1234567890123456789"

    # 3. Verify Canonical Citations Multi-Source Matrix
    cites = master["canonical"]["citation_counts"]
    assert cites["google_scholar"] == 98500
    assert cites["openalex"] == 95000
    assert cites["crossref"] is None
    assert cites["canonical_value"] == 98500


@pytest.mark.anyio
async def test_scholar_get_citations_parsing():
    mock_cites_api_payload = {
        "organic_results": [
            {
                "position": 0,
                "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
                "link": "https://aclanthology.org/N19-1423.pdf",
                "snippet": "We introduce a new language representation model called BERT...",
                "publication_info": {
                    "summary": "J Devlin, MW Chang, K Lee, K Toutanova - NAACL 2019, 2019 - aclanthology.org",
                    "authors": [
                        {"name": "Jacob Devlin", "author_id": "devlin_1"},
                        {"name": "Ming-Wei Chang", "author_id": "chang_2"}
                    ]
                },
                "inline_links": {
                    "cited_by": {
                        "total": 85000,
                        "link": "https://scholar.google.com/scholar?cites=999888777"
                    }
                },
                "resources": [
                    {
                        "title": "aclanthology.org [PDF]",
                        "link": "https://aclanthology.org/N19-1423.pdf",
                        "file_format": "PDF"
                    }
                ],
                "cluster_id": "999888777"
            }
        ],
        "pagination": {"next": "https://scholar.google.com/scholar?cites=12345&start=10"}
    }

    provider = GoogleScholarProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_cites_api_payload

    with patch.object(config, "serpapi_key", "mock_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            data = await provider.get_citations("1234567890", page=1, num=10)

            assert data["available"] is True
            assert data["cluster_id"] == "1234567890"
            assert data["results_count"] == 1
            citing_paper = data["results"][0]
            assert citing_paper["title"] == "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"
            assert citing_paper["publication"]["year"] == 2019
            assert citing_paper["citations"]["count"] == 85000
            assert len(citing_paper["authors"]) == 2
            assert len(citing_paper["resources"]) == 1


@pytest.mark.anyio
async def test_scholar_missing_serpapi_key_graceful_handling():
    provider = GoogleScholarProvider()
    with patch.object(config, "serpapi_key", ""):
        data = await provider.search_query("Attention Is All You Need")
        assert data["available"] is False
        assert data["reason"] == "SERPAPI_KEY_NOT_CONFIGURED"
        assert "scholar.google.com/scholar?q=" in data["scholar_url"]

        cites = await provider.get_citations("1234567890")
        assert cites["available"] is False
        assert cites["reason"] == "SERPAPI_KEY_NOT_CONFIGURED"


@pytest.mark.anyio
async def test_scholar_http_error_handling():
    provider = GoogleScholarProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.json.return_value = {"error": "Rate limit exceeded"}

    with patch.object(config, "serpapi_key", "mock_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            data = await provider.search_query("Attention Is All You Need")
            assert data["available"] is False
            assert data["error"]["status_code"] == 429
            assert "Rate limit" in data["error"]["detail"]


@pytest.mark.anyio
async def test_scholar_empty_results_handling():
    provider = GoogleScholarProvider()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"organic_results": []}

    with patch.object(config, "serpapi_key", "mock_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp

            data = await provider.search_query("xyzunknownquery123456789")
            assert data["available"] is True
            assert data["results_count"] == 0
            assert data["results"] == []
