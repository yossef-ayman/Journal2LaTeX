import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enrichment.parser import ParsedReference

def generate_reference_id(text: str) -> str:
    """Generate clean deterministic reference identifier from text."""
    clean = (text or "").strip()
    h = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:12]
    return f"ref_{h}"

class MasterRecordBuilder:
    """
    Builds canonical Master Reference JSON records with field-level provenance,
    academic entity taxonomy, multi-source preservation, DOI verification,
    author metrics, and telemetry.
    """

    @classmethod
    def build(
        cls,
        parsed_ref: ParsedReference,
        canonical_title: Dict[str, Any],
        canonical_year: Dict[str, Any],
        canonical_venue: Dict[str, Any],
        canonical_identifiers: Dict[str, Any],
        citation_counts: Dict[str, Any],
        canonical_authors: List[Dict[str, Any]],
        sources: Dict[str, Any],
        doi_verification: Dict[str, Any],
        conflicts: List[Dict[str, Any]],
        overall_confidence: float,
        canonical_type: Optional[Dict[str, Any]] = None,
        canonical_publisher: Optional[Dict[str, Any]] = None,
        volume: Optional[str] = None,
        issue: Optional[str] = None,
        pages: Optional[str] = None,
        telemetry: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        abstract: Optional[str] = None,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Assemble standardized, extensible Master Reference Record."""
        ref_id = generate_reference_id(parsed_ref.original_text)

        # Compute metadata completeness (ratio of non-null key canonical fields)
        key_fields = [
            canonical_title.get("value"),
            canonical_year.get("value"),
            canonical_venue.get("value"),
            canonical_identifiers.get("doi", {}).get("value") or canonical_identifiers.get("arxiv_id", {}).get("value"),
            len(canonical_authors) > 0,
            citation_counts.get("canonical_value") is not None
        ]
        completeness = round(sum(bool(f) for f in key_fields) / float(len(key_fields)), 2)

        type_obj = canonical_type or {
            "value": parsed_ref.reference_type or "journal-article",
            "source": "classifier",
            "confidence": 0.85,
            "verification_status": "verified"
        }

        publisher_obj = canonical_publisher or {
            "value": parsed_ref.publisher or None,
            "source": "parsed" if parsed_ref.publisher else "none",
            "confidence": 0.80 if parsed_ref.publisher else 0.0,
            "verification_status": "verified" if parsed_ref.publisher else "unverified"
        }

        record = {
            "reference_id": ref_id,
            "project_id": project_id or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "input": {
                "original_text": parsed_ref.original_text,
                "parsed": {
                    "title": parsed_ref.title or None,
                    "authors": parsed_ref.authors,
                    "year": parsed_ref.year,
                    "reference_type": parsed_ref.reference_type,
                    "journal": parsed_ref.journal or None,
                    "publisher": parsed_ref.publisher or None,
                    "volume": parsed_ref.volume or None,
                    "issue": parsed_ref.issue or None,
                    "pages": parsed_ref.pages or None,
                    "doi": parsed_ref.doi or None,
                    "isbn": parsed_ref.isbn or None,
                    "arxiv_id": parsed_ref.arxiv_id or None
                }
            },
            "canonical": {
                "title": canonical_title,
                "year": canonical_year,
                "venue": canonical_venue,
                "reference_type": type_obj,
                "publisher": publisher_obj,
                "volume": volume or parsed_ref.volume or None,
                "issue": issue or parsed_ref.issue or None,
                "pages": pages or parsed_ref.pages or None,
                "abstract": abstract or None,
                "url": url or None,
                "identifiers": canonical_identifiers,
                "citation_counts": citation_counts
            },
            "canonical_authors": canonical_authors,
            "sources": sources,
            "doi_verification": doi_verification,
            "quality_and_conflicts": {
                "overall_confidence": round(overall_confidence, 2),
                "metadata_completeness": completeness,
                "doi_verified": doi_verification.get("status") == "verified",
                "author_verified": any(a.get("match_status") == "matched" for a in canonical_authors),
                "conflicts": conflicts
            },
            "telemetry": telemetry or {
                "providers_queried": list(sources.keys()),
                "latency_ms": {},
                "candidate_counts": {}
            }
        }

        return record
