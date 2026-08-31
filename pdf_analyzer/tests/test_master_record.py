import pytest
from enrichment.parser import ParsedReference
from enrichment.master_record import MasterRecordBuilder, generate_reference_id

def test_generate_reference_id_deterministic():
    id1 = generate_reference_id("Vaswani et al. Attention is all you need 2017")
    id2 = generate_reference_id("Vaswani et al. Attention is all you need 2017")
    assert id1 == id2
    assert id1.startswith("ref_")

def test_master_record_schema_builder():
    parsed = ParsedReference(
        original_text="Vaswani et al. 2017. Attention Is All You Need.",
        title="Attention Is All You Need",
        authors=[{"name": "Ashish Vaswani", "given": "Ashish", "family": "Vaswani"}],
        year=2017
    )

    record = MasterRecordBuilder.build(
        parsed_ref=parsed,
        canonical_title={"value": "Attention Is All You Need", "source": "openalex", "confidence": 0.98, "verification_status": "verified"},
        canonical_year={"value": 2017, "source": "parsed", "confidence": 1.0, "verification_status": "verified"},
        canonical_venue={"value": "NeurIPS", "source": "openalex", "confidence": 0.85, "verification_status": "verified"},
        canonical_identifiers={
            "doi": {"value": "10.48550/arXiv.1706.03762", "source": "doi_verifier", "confidence": 0.95, "verification_status": "verified"},
            "arxiv_id": {"value": "1706.03762", "source": "arxiv", "confidence": 1.0, "verification_status": "verified"},
            "openalex_id": {"value": "https://openalex.org/W2626778328", "source": "openalex", "confidence": 1.0, "verification_status": "verified"}
        },
        citation_counts={"canonical_value": 115000, "google_scholar": 115000, "openalex": 12685, "crossref": 16},
        canonical_authors=[{"name": "Ashish Vaswani", "match_status": "matched"}],
        sources={"openalex": {"matched": True}, "crossref": {"matched": True}, "google_scholar": {"matched": True}},
        doi_verification={"status": "verified", "canonical_doi": "10.48550/arXiv.1706.03762"},
        conflicts=[],
        overall_confidence=0.98
    )

    assert "reference_id" in record
    assert record["canonical"]["title"]["value"] == "Attention Is All You Need"
    assert record["canonical"]["citation_counts"]["canonical_value"] == 115000
    assert record["canonical"]["citation_counts"]["google_scholar"] == 115000
    assert record["canonical"]["citation_counts"]["openalex"] == 12685
    assert record["canonical"]["citation_counts"]["crossref"] == 16
    assert record["quality_and_conflicts"]["metadata_completeness"] == 1.0
    assert record["quality_and_conflicts"]["doi_verified"] is True
