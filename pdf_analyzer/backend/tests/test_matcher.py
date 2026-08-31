import pytest
from enrichment.parser import ParsedReference
from enrichment.matcher import ReferenceMatcher
from enrichment.string_utils import normalize_string, match_authors

def test_string_normalization():
    assert normalize_string("  Hello, World! (2024)  ") == "hello world 2024"
    assert normalize_string("J. Smith et al.") == "j smith"
    assert normalize_string("Café & Résumé") == "cafe resume"

def test_author_matching():
    authors1 = [{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}]
    authors2 = [{"name": "A. Vaswani", "given": "A.", "family": "Vaswani"}]
    assert match_authors(authors1, authors2) >= 0.80

# 1. Exact/near-exact title + correct year + matching authors → matched
def test_exact_title_correct_year_matching_authors_matched():
    parsed = ParsedReference(
        original_text="Vaswani, A., Shazeer, N., Parmar, N. (2017). Attention is all you need.",
        title="Attention is all you need",
        authors=[
            {"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"},
            {"name": "Noam Shazeer", "given": "Noam", "family": "Shazeer"},
            {"name": "Niki Parmar", "given": "Niki", "family": "Parmar"}
        ],
        year=2017
    )
    candidate = {
        "title": "Attention Is All You Need",
        "authors": [
            {"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"},
            {"name": "Noam Shazeer", "given": "Noam", "family": "Shazeer"},
            {"name": "Niki Parmar", "given": "Niki", "family": "Parmar"}
        ],
        "year": 2017,
        "journal": "NeurIPS"
    }

    cand, conf, status = ReferenceMatcher.match_candidate(parsed, [candidate])
    assert status == "matched"
    assert conf >= 0.80

# 2. Same/similar title + different authors → not_found / low_confidence (NOT matched!)
def test_similar_title_different_authors_not_matched():
    parsed = ParsedReference(
        original_text="Smith, J. (2017). Attention is all you need.",
        title="Attention is all you need",
        authors=[{"name": "John Smith", "given": "John", "family": "Smith"}],
        year=2017
    )
    candidate_different_authors = {
        "title": "Attention Is All You Need",
        "authors": [{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}],
        "year": 2025,
        "doi": "10.65215/2q58a426"
    }

    cand, conf, status = ReferenceMatcher.match_candidate(parsed, [candidate_different_authors])
    assert status in ("low_confidence", "not_found")
    assert status != "matched"
    assert conf < 0.80

# 3. Different paper + similar title → not_found / low_confidence
def test_different_paper_similar_title_not_found():
    parsed = ParsedReference(
        original_text="Vaswani et al. (2017). Attention is all you need.",
        title="Attention is all you need",
        authors=[{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}],
        year=2017
    )
    different_candidate = {
        "title": "Channel Attention Is All You Need for Video Frame Interpolation",
        "authors": [{"name": "Myungsub Choi", "given": "Myungsub", "family": "Choi"}],
        "year": 2020
    }

    cand, conf, status = ReferenceMatcher.match_candidate(parsed, [different_candidate])
    assert status in ("not_found", "low_confidence")
    assert status != "matched"

# 4. Correct DOI → matched
def test_correct_doi_matched():
    parsed = ParsedReference(
        original_text="Vaswani et al 2017",
        title="Attention is all you need",
        doi="10.48550/arXiv.1706.03762",
        year=2017
    )
    candidate = {
        "title": "Attention is All You Need",
        "doi": "10.48550/arXiv.1706.03762",
        "year": 2017,
        "authors": [{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}]
    }

    cand, conf, status = ReferenceMatcher.match_candidate(parsed, [candidate])
    assert status == "matched"
    assert conf == 1.0

# 5. Missing title → not_found (la يتم اختيار نتيجة عشوائية)
def test_missing_title_not_found():
    parsed = ParsedReference(
        original_text="[1] 2017.",
        title="",
        authors=[],
        year=2017
    )
    candidate = {
        "title": "Attention Is All You Need",
        "year": 2017,
        "authors": [{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}]
    }

    cand, conf, status = ReferenceMatcher.match_candidate(parsed, [candidate])
    assert status == "not_found"
    assert conf < 0.50

# 6. Author-only reference → not_found / low_confidence
def test_author_only_reference_not_high_confidence():
    parsed = ParsedReference(
        original_text="Vaswani, A., Shazeer, N.",
        title="",
        authors=[{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}],
        year=None
    )
    candidate = {
        "title": "Attention Is All You Need",
        "year": 2017,
        "authors": [{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}]
    }

    cand, conf, status = ReferenceMatcher.match_candidate(parsed, [candidate])
    assert status in ("not_found", "low_confidence")
    assert status != "matched"
    assert conf < 0.80
