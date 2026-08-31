import pytest
from enrichment.parser import ParsedReference
from enrichment.reconciler import MultiSourceReconciler
from enrichment.storage import storage

def test_multi_source_reconciliation_all_sources_present():
    parsed = ParsedReference(
        original_text="Vaswani, A., Shazeer, N., Parmar, N. (2017). Attention is all you need.",
        title="Attention is all you need",
        authors=[
            {"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"},
            {"name": "Noam Shazeer", "given": "Noam", "family": "Shazeer"}
        ],
        year=2017
    )

    openalex_cands = [{
        "title": "Attention Is All You Need",
        "authors": [{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani", "author_id": "https://openalex.org/A5103024730", "source": "openalex"}],
        "year": 2017,
        "journal": "Advances in Neural Information Processing Systems",
        "doi": "10.48550/arXiv.1706.03762",
        "openalex_id": "https://openalex.org/W2626778328",
        "citation_count": 12685,
        "source": "openalex",
        "raw_file": "data/raw/openalex/test.json"
    }]

    crossref_cands = [{
        "title": "Attention Is All You Need",
        "authors": [{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani", "author_id": "", "source": "crossref"}],
        "year": 2017,
        "journal": "NeurIPS",
        "doi": "10.48550/arXiv.1706.03762",
        "citation_count": 16,
        "source": "crossref",
        "raw_file": "data/raw/crossref/test.json"
    }]

    scholar_cands = [{
        "title": "Attention is all you need",
        "authors": [{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani", "author_id": "SCHOLAR_VASWANI", "source": "google_scholar"}],
        "year": 2017,
        "journal": "NeurIPS",
        "doi": "10.48550/arXiv.1706.03762",
        "citation_count": 115000,
        "source": "google_scholar",
        "available": True,
        "raw_file": "data/raw/google_scholar/test.json"
    }]

    master = MultiSourceReconciler.reconcile(
        parsed_ref=parsed,
        openalex_candidates=openalex_cands,
        crossref_candidates=crossref_cands,
        scholar_candidates=scholar_cands
    )

    # 1. Verify Non-Destructive Preservation
    assert master["sources"]["openalex"]["matched"] is True
    assert master["sources"]["crossref"]["matched"] is True
    assert master["sources"]["google_scholar"]["matched"] is True

    # 2. Citation Counts
    citations = master["canonical"]["citation_counts"]
    assert citations["canonical_value"] == 115000
    assert citations["google_scholar"] == 115000
    assert citations["openalex"] == 12685
    assert citations["crossref"] == 16

    # 3. Canonical identifiers & authors
    assert master["canonical"]["identifiers"]["doi"]["value"] == "10.48550/arXiv.1706.03762"
    assert master["canonical"]["identifiers"]["openalex_id"]["value"] == "https://openalex.org/W2626778328"
    assert len(master["canonical_authors"]) >= 1
    assert master["canonical_authors"][0]["identifiers"]["openalex_id"] == "https://openalex.org/A5103024730"

    # 4. Verified on disk
    ref_id = master["reference_id"]
    loaded = storage.load_reference(ref_id)
    assert loaded is not None
    assert loaded["reference_id"] == ref_id

def test_multi_source_reconciliation_missing_scholar_does_not_break():
    parsed = ParsedReference(original_text="Test Ref 2020", title="Test Paper", year=2020)
    openalex_cands = [{
        "title": "Test Paper",
        "authors": [{"name": "Alice Smith", "author_id": "A123", "source": "openalex"}],
        "year": 2020,
        "citation_count": 50,
        "doi": "10.1000/182",
        "source": "openalex"
    }]

    # Scholar unconfigured
    scholar_cands = [{
        "title": "Test Paper",
        "available": False,
        "citation_count": None,
        "source": "google_scholar"
    }]

    master = MultiSourceReconciler.reconcile(
        parsed_ref=parsed,
        openalex_candidates=openalex_cands,
        crossref_candidates=[],
        scholar_candidates=scholar_cands
    )

    assert master["canonical"]["citation_counts"]["google_scholar"] is None
    assert master["canonical"]["citation_counts"]["openalex"] == 50
    assert master["canonical"]["citation_counts"]["canonical_value"] == 50
    assert master["sources"]["google_scholar"]["available"] is False

def test_regression_contaminated_reprint_doi_and_venue_rejected():
    parsed = ParsedReference(
        original_text="Vaswani, A., Shazeer, N., Parmar, N. (2017). Attention is all you need.",
        title="Attention is all you need",
        authors=[{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}],
        year=2017
    )
    # Contaminated OpenAlex response returning suspicious 10.65215 DOI and Shenzhen venue
    openalex_cands = [{
        "title": "Attention Is All You Need",
        "authors": [{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani", "author_id": "https://openalex.org/A5103024730", "source": "openalex"}],
        "year": 2025,
        "journal": "Shenzhen Medical Academy of Research and Translation",
        "doi": "10.65215/2q58a426",
        "openalex_id": "https://openalex.org/W2626778328",
        "citation_count": 6591,
        "source": "openalex"
    }]

    master = MultiSourceReconciler.reconcile(
        parsed_ref=parsed,
        openalex_candidates=openalex_cands,
        crossref_candidates=[],
        scholar_candidates=[]
    )

    # 1. Canonical DOI must NOT be the contaminated DOI
    assert master["canonical"]["identifiers"]["doi"]["value"] != "10.65215/2q58a426"
    assert master["canonical"]["identifiers"]["doi"]["value"] is None

    # 2. Canonical venue must NOT be the reprint repository
    assert master["canonical"]["venue"]["value"] != "Shenzhen Medical Academy of Research and Translation"
    assert master["canonical"]["venue"]["value"] is None

    # 3. Conflicts list must explicitly record the rejected DOI and/or venue
    conflicts = master["quality_and_conflicts"]["conflicts"]
    rejected_dois = [c.get("rejected_value") for c in conflicts if c.get("field") == "doi"]
    assert "10.65215/2q58a426" in rejected_dois

def test_provider_name_never_becomes_canonical_venue():
    parsed = ParsedReference(
        original_text="Vaswani, A. et al. (2017). Attention is all you need.",
        title="Attention is all you need",
        year=2017
    )
    # Providers passing provider names or missing venue
    openalex_cands = [{
        "title": "Attention Is All You Need",
        "authors": [{"name": "Ashish Vaswani", "source": "openalex"}],
        "year": 2017,
        "journal": "OpenAlex",
        "doi": None,
        "source": "openalex"
    }]
    scholar_cands = [{
        "title": "Attention Is All You Need",
        "authors": [{"name": "Ashish Vaswani", "source": "google_scholar"}],
        "year": 2017,
        "journal": "Google Scholar",
        "source": "google_scholar",
        "available": True
    }]

    master = MultiSourceReconciler.reconcile(
        parsed_ref=parsed,
        openalex_candidates=openalex_cands,
        crossref_candidates=[],
        scholar_candidates=scholar_cands
    )

    assert master["canonical"]["venue"]["value"] is None
    assert master["canonical"]["venue"]["source"] == "none"


