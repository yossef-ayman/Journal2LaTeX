import pytest
from enrichment.parser import ParsedReference
from enrichment.doi_verifier import DOIVerifier

def test_doi_normalization_and_syntax():
    assert DOIVerifier.normalize_doi("https://doi.org/10.1000/182") == "10.1000/182"
    assert DOIVerifier.normalize_doi("http://dx.doi.org/10.1000/182.") == "10.1000/182"
    assert DOIVerifier.normalize_doi("doi: 10.1016/j.test.2020;") == "10.1016/j.test.2020"
    
    assert DOIVerifier.is_valid_syntax("10.1000/182") is True
    assert DOIVerifier.is_valid_syntax("10.48550/arXiv.1706.03762") is True
    assert DOIVerifier.is_valid_syntax("not-a-doi") is False
    assert DOIVerifier.is_valid_syntax("") is False

def test_extract_arxiv_id():
    assert DOIVerifier.extract_arxiv_id("10.48550/arXiv.1706.03762") == "1706.03762"
    assert DOIVerifier.extract_arxiv_id("arXiv:1706.03762v5") == "1706.03762v5"
    assert DOIVerifier.extract_arxiv_id("10.1016/j.jhai.2020") is None

def test_verify_doi_matching_candidate():
    ref = ParsedReference(
        original_text="Vaswani et al. (2017). Attention is all you need.",
        title="Attention is all you need",
        authors=[{"family": "Vaswani", "name": "Ashish Vaswani"}],
        year=2017,
        doi="10.48550/arXiv.1706.03762"
    )
    candidates = {
        "openalex": [{
            "title": "Attention Is All You Need",
            "doi": "10.48550/arXiv.1706.03762",
            "authors": [{"family": "Vaswani", "name": "Ashish Vaswani"}],
            "year": 2017
        }]
    }
    verif = DOIVerifier.verify(ref, candidates)
    assert verif["status"] == "verified"
    assert verif["canonical_doi"] == "10.48550/arXiv.1706.03762"
    assert verif["confidence"] >= 0.85

def test_verify_doi_detects_suspicious_reprint_conflict():
    ref = ParsedReference(
        original_text="Vaswani, A., Shazeer, N., Parmar, N. (2017). Attention is all you need.",
        title="Attention is all you need",
        authors=[{"family": "Vaswani", "name": "Ashish Vaswani"}],
        year=2017
    )
    # OpenAlex candidate returned suspicious reprint DOI 10.65215
    candidates = {
        "openalex": [{
            "title": "Attention Is All You Need",
            "doi": "10.65215/2q58a426",
            "authors": [{"family": "Vaswani", "name": "Ashish Vaswani"}],
            "year": 2025
        }]
    }
    verif = DOIVerifier.verify(ref, candidates)
    assert verif["status"] == "conflict"
    assert verif["canonical_doi"] is None
    assert len(verif["conflicts"]) == 1
    assert "10.65215" in verif["conflicts"][0]["reason"]

def test_verify_doi_arxiv_reconciliation():
    ref = ParsedReference(
        original_text="Vaswani et al. (2017). Attention is all you need. arXiv:1706.03762",
        title="Attention is all you need",
        authors=[{"family": "Vaswani", "name": "Ashish Vaswani"}],
        year=2017,
        arxiv_id="1706.03762"
    )
    # Provider returns bad/suspicious DOI
    candidates = {
        "openalex": [{
            "title": "Attention Is All You Need",
            "doi": "10.65215/2q58a426",
            "authors": [{"family": "Vaswani", "name": "Ashish Vaswani"}],
            "year": 2025
        }]
    }
    verif = DOIVerifier.verify(ref, candidates)
    assert verif["status"] == "verified"
    assert verif["reconciled_with_arxiv"] is True
    assert verif["canonical_doi"] == "10.48550/arXiv.1706.03762"
    assert len(verif["conflicts"]) >= 1

def test_missing_doi_and_arxiv():
    ref = ParsedReference(original_text="Book by author 2020", title="Some Book")
    verif = DOIVerifier.verify(ref, {})
    assert verif["status"] == "missing"
    assert verif["canonical_doi"] is None
