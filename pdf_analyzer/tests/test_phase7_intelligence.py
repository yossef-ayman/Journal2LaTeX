import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from enrichment.parser import ReferenceParser, ParsedReference
from enrichment.reconciler import MultiSourceReconciler
from enrichment.doi_verifier import DOIVerifier
from main import app

client = TestClient(app)

def test_reference_parser_given_family_authors():
    text = "Vaswani, Ashish, Shazeer, Noam, Parmar, Niki, & Uszkoreit, Jakob (2017). Attention is all you need."
    parsed = ReferenceParser.parse(text)
    
    assert len(parsed.authors) >= 3
    assert parsed.authors[0]["family"] == "Vaswani"
    assert parsed.authors[0]["given"] == "Ashish"
    assert parsed.year == 2017
    assert "Attention is all you need" in parsed.title

def test_reference_type_classification():
    # 1. Preprint
    p1 = ReferenceParser.parse("Devlin, J. et al. (2018). BERT: Pre-training of deep bidirectional transformers. arXiv:1810.04805.")
    assert p1.reference_type == "preprint"
    assert p1.arxiv_id == "1810.04805"

    # 2. Proceedings Article
    p2 = ReferenceParser.parse("Vaswani, A. et al. (2017). Attention is all you need. In Proceedings of the 31st Conference on Neural Information Processing Systems (NeurIPS), pp. 5998-6008.")
    assert p2.reference_type == "proceedings-article"
    assert p2.pages == "5998-6008"

    # 3. Book
    p3 = ReferenceParser.parse("Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press, ISBN: 978-0262035613.")
    assert p3.reference_type == "book"
    assert p3.publisher == "MIT Press"
    assert "978-0262035613" in p3.isbn

    # 4. Book Chapter
    p4 = ReferenceParser.parse("Smith, J. (2020). Neural Networks. In: A. Brown (ed.) Handbook of AI, pp. 100-125. Springer.")
    assert p4.reference_type == "book-chapter"
    assert p4.publisher == "Springer"

    # 5. Journal Article with Volume/Issue/Pages
    p5 = ReferenceParser.parse("Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. Neural Computation, 9(8): 1735-1780.")
    assert p5.reference_type == "journal-article"
    assert p5.volume == "9"
    assert p5.issue == "8"
    assert p5.pages == "1735-1780"

def test_author_resolution_with_orcid_and_identifiers():
    parsed = ParsedReference(
        original_text="Vaswani, A. (2017). Attention is all you need.",
        title="Attention is all you need",
        year=2017
    )
    openalex_cands = [{
        "title": "Attention Is All You Need",
        "authors": [
            {
                "name": "Ashish Vaswani",
                "given": "Ashish",
                "family": "Vaswani",
                "author_id": "https://openalex.org/A5103024730",
                "orcid": "0000-0002-1234-5678",
                "source": "openalex"
            }
        ],
        "year": 2017,
        "openalex_id": "https://openalex.org/W2626778328",
        "citation_count": 95000,
        "source": "openalex"
    }]

    master = MultiSourceReconciler.reconcile(
        parsed_ref=parsed,
        openalex_candidates=openalex_cands,
        crossref_candidates=[],
        scholar_candidates=[]
    )

    authors = master["canonical_authors"]
    assert len(authors) == 1
    assert authors[0]["identifiers"]["openalex_id"] == "https://openalex.org/A5103024730"
    assert authors[0]["identifiers"]["orcid"] == "0000-0002-1234-5678"
    assert authors[0]["match_status"] == "matched"

def test_scholar_citations_endpoint_empty_cluster():
    res = client.get("/scholar/citations/")
    assert res.status_code == 404

def test_scholar_citations_endpoint_unconfigured_fallback():
    with patch("enrichment.config.config.serpapi_key", None):
        res = client.get("/scholar/citations/1234567890")
        assert res.status_code == 200
        data = res.json()
        assert data["available"] is False
        assert data["reason"] == "SERPAPI_KEY_NOT_CONFIGURED"
        assert "cites=1234567890" in data["scholar_url"]

def test_scholar_citations_endpoint_mocked_results():
    mock_normalized_response = {
        "provider": "google_scholar",
        "available": True,
        "cluster_id": "1234567890",
        "scholar_url": "https://scholar.google.com/scholar?cites=1234567890",
        "page": 1,
        "results_count": 1,
        "results": [
            {
                "position": 0,
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "link": "https://arxiv.org/abs/1810.04805",
                "snippet": "We introduce a new language representation model...",
                "publication": {
                    "summary": "J Devlin, MW Chang - arXiv preprint arXiv:1810.04805, 2018",
                    "year": 2018,
                    "venue": "arXiv preprint"
                },
                "authors": [{"name": "Jacob Devlin", "author_id": "JD123"}],
                "citations": {"count": 85000, "link": "https://scholar.google.com/scholar?cites=999"}
            }
        ],
        "pagination": {},
        "raw_file": "data/raw/google_scholar/test.json"
    }

    with patch("main.GoogleScholarProvider.get_citations", new_callable=AsyncMock) as mock_cites:
        mock_cites.return_value = mock_normalized_response

        res = client.get("/scholar/citations/1234567890?page=1&num=10")
        assert res.status_code == 200
        data = res.json()
        assert data["available"] is True
        assert data["results_count"] == 1
        assert data["results"][0]["title"] == "BERT: Pre-training of Deep Bidirectional Transformers"
        assert data["results"][0]["citations"]["count"] == 85000

def test_missing_fields_produce_null_never_hallucinated():
    parsed = ReferenceParser.parse("Smith, J. Simple Title.")
    master = MultiSourceReconciler.reconcile(
        parsed_ref=parsed,
        openalex_candidates=[],
        crossref_candidates=[],
        scholar_candidates=[]
    )

    # Missing venue, year, doi must remain None / unverified
    assert master["canonical"]["venue"]["value"] is None
    assert master["canonical"]["year"]["value"] is None
    assert master["canonical"]["identifiers"]["doi"]["value"] is None
    assert master["canonical"]["citation_counts"]["canonical_value"] is None
