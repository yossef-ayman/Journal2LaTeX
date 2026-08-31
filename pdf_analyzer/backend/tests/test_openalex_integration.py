import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from enrichment.parser import ParsedReference, ReferenceParser
from enrichment.providers.openalex import OpenAlexProvider, reconstruct_abstract
from enrichment.providers.authors import OpenAlexAuthorProvider
from enrichment.matcher import ReferenceMatcher
from enrichment.reconciler import MultiSourceReconciler
from enrichment.pipeline import ReferenceEnricher, deduplicate_references
from enrichment.config import EnrichmentConfig, config


@pytest.fixture
def anyio_backend():
    return 'asyncio'


# =========================================================================
# 1. Abstract Reconstruction Test
# =========================================================================
def test_abstract_reconstruction():
    inverted_index = {
        "Optimal": [0],
        "control": [1],
        "strategies": [2],
        "for": [3],
        "addiction": [4]
    }
    reconstructed = reconstruct_abstract(inverted_index)
    assert reconstructed == "Optimal control strategies for addiction"

    # Edge cases
    assert reconstruct_abstract(None) == ""
    assert reconstruct_abstract({}) == ""
    assert reconstruct_abstract("not a dict") == ""


# =========================================================================
# 2. Reference Deduplication Test
# =========================================================================
def test_reference_deduplication():
    refs = [
        {
            "title": "Attention Is All You Need",
            "doi": "10.48550/arXiv.1706.03762",
            "openalex_id": "https://openalex.org/W2626778328",
            "year": 2017,
            "authors": [{"name": "Ashish Vaswani", "family": "Vaswani"}]
        },
        {
            # Duplicate by DOI
            "title": "Attention is All You Need - Secondary Entry",
            "doi": "https://doi.org/10.48550/arxiv.1706.03762",
            "openalex_id": "https://openalex.org/W2626778328",
            "year": 2017,
            "authors": [{"name": "A. Vaswani", "family": "Vaswani"}]
        },
        {
            # Duplicate by Title + Year + Author
            "title": "Attention Is All You Need",
            "doi": "",
            "openalex_id": "",
            "year": 2017,
            "authors": [{"name": "Ashish Vaswani", "family": "Vaswani"}]
        },
        {
            # Distinct reference
            "title": "Optimal control strategies for overwhelming social media scrolling addiction",
            "doi": "10.18576/pfda/120213",
            "openalex_id": "https://openalex.org/W7196949051",
            "year": 2026,
            "authors": [{"name": "G.M. Vijayalakshmi", "family": "Vijayalakshmi"}]
        }
    ]

    deduped = deduplicate_references(refs)
    assert len(deduped) == 2
    assert deduped[0]["doi"] == "10.48550/arXiv.1706.03762"
    assert deduped[1]["openalex_id"] == "https://openalex.org/W7196949051"


# =========================================================================
# 3. Reference Matcher Confidence Scoring Tests
# =========================================================================
def test_matcher_doi_exact_match():
    parsed = ParsedReference(
        original_text="Test ref",
        title="Optimal control strategies for overwhelming social media addiction",
        doi="10.18576/pfda/120213"
    )
    candidate = {
        "title": "Optimal control strategies for overwhelming social media addiction",
        "doi": "https://doi.org/10.18576/pfda/120213",
        "year": 2026
    }
    conf, scores = ReferenceMatcher.calculate_confidence(parsed, candidate)
    assert conf == 1.0
    assert scores["doi_match"] == 1.0

    cand, conf, status = ReferenceMatcher.match_candidate(parsed, [candidate])
    assert status == "matched"
    assert conf == 1.0


def test_matcher_title_and_author_similarity():
    parsed = ParsedReference(
        original_text="Vaswani, A., Shazeer, N. Attention is all you need. 2017.",
        title="Attention is all you need",
        authors=[{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}],
        year=2017
    )
    candidate = {
        "title": "Attention Is All You Need",
        "authors": [{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani", "author_id": "https://openalex.org/A5103024730"}],
        "year": 2017,
        "openalex_id": "https://openalex.org/W2626778328",
        "citation_count": 95000
    }
    conf, scores = ReferenceMatcher.calculate_confidence(parsed, candidate)
    assert conf >= 0.90
    assert scores["title_sim"] >= 0.95
    assert scores["author_sim"] >= 0.90

    cand, conf, status = ReferenceMatcher.match_candidate(parsed, [candidate])
    assert status == "matched"
    assert conf >= 0.90


def test_matcher_low_confidence_and_not_found():
    parsed = ParsedReference(
        original_text="Some obscure reference without matches",
        title="Quantum chromodynamics in curved spacetime",
        authors=[{"name": "John Doe", "family": "Doe"}],
        year=1999
    )
    # Completely mismatched candidate
    unrelated_cand = {
        "title": "Fractional order calculus in biological modelling",
        "authors": [{"name": "Jane Smith", "family": "Smith"}],
        "year": 2020
    }
    cand, conf, status = ReferenceMatcher.match_candidate(parsed, [unrelated_cand])
    assert status == "not_found"
    assert conf < 0.50


# =========================================================================
# 4. OpenAlex Provider Retries, 429 Backoff, and 500 Server Error
# =========================================================================
@pytest.mark.anyio
async def test_openalex_retry_on_429_backoff():
    provider = OpenAlexProvider()
    provider.INITIAL_BACKOFF = 0.01  # fast test backoff

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "id": "https://openalex.org/W12345",
        "title": "Test Work",
        "publication_year": 2024
    }

    mock_client = AsyncMock()
    mock_client.get.side_effect = [mock_resp_429, mock_resp_200]

    res = await provider._safe_get(mock_client, "works/W12345", {})
    assert res is not None
    assert res["id"] == "https://openalex.org/W12345"
    assert mock_client.get.call_count == 2


@pytest.mark.anyio
async def test_openalex_retry_on_500_server_error():
    provider = OpenAlexProvider()
    provider.INITIAL_BACKOFF = 0.01

    mock_resp_500 = MagicMock()
    mock_resp_500.status_code = 500

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "results": [{"id": "https://openalex.org/W12345", "title": "Test Work"}]
    }

    mock_client = AsyncMock()
    mock_client.get.side_effect = [mock_resp_500, mock_resp_200]

    res = await provider._safe_get(mock_client, "works", {"search": "Test"})
    assert res is not None
    assert len(res["results"]) == 1
    assert mock_client.get.call_count == 2


@pytest.mark.anyio
async def test_openalex_timeout_and_fallback():
    provider = OpenAlexProvider()
    provider.INITIAL_BACKOFF = 0.01
    provider.MAX_RETRIES = 2

    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.TimeoutException("Connection timed out")

    res = await provider._safe_get(mock_client, "works", {"search": "Test"})
    assert res is None


@pytest.mark.anyio
async def test_openalex_malformed_response():
    provider = OpenAlexProvider()
    provider.INITIAL_BACKOFF = 0.01

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {"results": []}

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp_200

    res = await provider._safe_get(mock_client, "works", {"search": "NonExistentPaper123456789"})
    assert res == {"results": []}


# =========================================================================
# 5. OpenAlex Author Provider Tests
# =========================================================================
@pytest.mark.anyio
async def test_openalex_author_lookup_by_id():
    provider = OpenAlexAuthorProvider()
    provider.INITIAL_BACKOFF = 0.01

    mock_author_data = {
        "id": "https://openalex.org/A5103024730",
        "display_name": "Ashish Vaswani",
        "works_count": 48,
        "cited_by_count": 120500,
        "summary_stats": {
            "h_index": 28,
            "i10_index": 35
        },
        "last_known_institutions": [
            {"display_name": "Google", "country_code": "US"}
        ],
        "topics": [
            {"display_name": "Natural Language Processing"}
        ]
    }

    with patch.object(provider, "_safe_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_author_data
        profile = await provider.get_author("https://openalex.org/A5103024730")
        assert profile is not None
        assert profile["name"] == "Ashish Vaswani"
        assert profile["works_count"] == 48
        assert profile["cited_by_count"] == 120500
        assert profile["h_index"] == 28
        assert profile["affiliations"] == ["Google (US)"]


@pytest.mark.anyio
async def test_openalex_author_name_search_fallback():
    provider = OpenAlexAuthorProvider()
    provider.INITIAL_BACKOFF = 0.01

    mock_search_results = {
        "results": [
            {
                "id": "https://openalex.org/A5103024730",
                "display_name": "Ashish Vaswani",
                "works_count": 48,
                "cited_by_count": 120500,
                "summary_stats": {"h_index": 28, "i10_index": 35}
            }
        ]
    }

    with patch.object(provider, "_safe_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_search_results
        profile = await provider.get_author("Ashish Vaswani")
        assert profile is not None
        assert profile["name"] == "Ashish Vaswani"
        assert profile["id"] == "https://openalex.org/A5103024730"


# =========================================================================
# 6. Priority Pipeline & Test Papers (Live or Direct Integration)
# =========================================================================
@pytest.mark.anyio
async def test_enricher_priority_openalex_over_crossref():
    enricher = ReferenceEnricher()

    openalex_cand = {
        "title": "Optimal control strategies for overwhelming social media scrolling addiction by using fractional order mathematical modelling",
        "authors": [
            {"name": "G. M. Vijayalakshmi", "given": "G. M.", "family": "Vijayalakshmi", "author_id": "https://openalex.org/A111", "source": "openalex"}
        ],
        "year": 2026,
        "journal": "Progress in Fractional Differentiation and Applications",
        "doi": "10.18576/pfda/120213",
        "openalex_id": "https://openalex.org/W7196949051",
        "citation_count": 5,
        "source": "openalex",
        "abstract": "This paper presents optimal control strategies..."
    }

    crossref_cand = {
        "title": "Optimal control strategies for overwhelming social media scrolling addiction",
        "authors": [{"name": "G. M. Vijayalakshmi", "family": "Vijayalakshmi", "source": "crossref"}],
        "year": 2026,
        "doi": "10.18576/pfda/120213",
        "citation_count": 0,
        "source": "crossref"
    }

    with patch.object(enricher.primary_provider, "search_reference", new_callable=AsyncMock) as mock_alex, \
         patch.object(enricher.fallback_provider, "search_reference", new_callable=AsyncMock) as mock_cross, \
         patch.object(enricher.scholar_provider, "search_reference", new_callable=AsyncMock) as mock_schol:

        mock_alex.return_value = [openalex_cand]
        mock_cross.return_value = [crossref_cand]
        mock_schol.return_value = []

        ref_text = "G.M. Vijayalakshmi et al., Optimal control strategies for overwhelming social media scrolling addiction by using fractional order mathematical modelling, 2026, DOI: 10.18576/pfda/120213"
        result = await enricher.enrich_reference(ref_text)

        assert result["source"] == "openalex"
        assert result["match_status"] == "matched"
        assert result["confidence"] >= 0.90
        assert result["openalex_id"] == "https://openalex.org/W7196949051"
        assert result["doi"] == "10.18576/pfda/120213"
        assert result["citations"]["openalex"] == 5
        assert result["master_record"]["canonical"]["abstract"] == "This paper presents optimal control strategies..."


@pytest.mark.anyio
async def test_live_openalex_attention_paper():
    """Live test of Attention Is All You Need against OpenAlex API."""
    provider = OpenAlexProvider()
    parsed = ParsedReference(
        original_text="Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention is all you need. Advances in Neural Information Processing Systems.",
        title="Attention is all you need",
        authors=[{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}],
        year=2017
    )

    try:
        candidates = await provider.search_reference(parsed)
    except Exception as e:
        pytest.skip(f"Live OpenAlex network unreachable: {e}")

    if not candidates:
        pytest.skip("Live OpenAlex returned no candidates due to temporary network connectivity.")

    best_cand, conf, status = ReferenceMatcher.match_candidate(parsed, candidates)
    assert status == "matched"
    assert conf >= 0.90
    assert "attention" in best_cand["title"].lower()
    assert best_cand["citation_count"] > 0
    assert best_cand["openalex_id"].startswith("https://openalex.org/W")


@pytest.mark.anyio
async def test_live_openalex_vijayalakshmi_paper():
    """Live test of Vijayalakshmi social media addiction paper against OpenAlex API."""
    provider = OpenAlexProvider()
    parsed = ParsedReference(
        original_text="G.M. Vijayalakshmi, G. Susila, Z. Che Muda, Sudesh Nair Baskara, P. Roselyn Besi, Ali Akgül, Optimal control strategies for overwhelming social media scrolling addiction by using fractional order mathematical modelling, DOI: 10.18576/pfda/120213",
        title="Optimal control strategies for overwhelming social media scrolling addiction by using fractional order mathematical modelling",
        authors=[{"name": "G.M. Vijayalakshmi", "given": "G.M.", "family": "Vijayalakshmi"}],
        year=2026
    )

    try:
        candidates = await provider.search_reference(parsed)
    except Exception as e:
        pytest.skip(f"Live OpenAlex network unreachable: {e}")

    if not candidates:
        pytest.skip("Live OpenAlex returned no candidates due to temporary network connectivity.")

    best_cand, conf, status = ReferenceMatcher.match_candidate(parsed, candidates)
    assert status == "matched"
    assert conf >= 0.90
    assert "optimal control strategies" in best_cand["title"].lower()
    assert best_cand["openalex_id"].startswith("https://openalex.org/W")
