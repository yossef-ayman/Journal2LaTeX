from typing import Dict, Any, List, Optional
from enrichment.parser import ParsedReference
from enrichment.matcher import ReferenceMatcher
from enrichment.doi_verifier import DOIVerifier
from enrichment.master_record import MasterRecordBuilder, generate_reference_id
from enrichment.storage import storage


class MultiSourceReconciler:
    """
    Multi-Source Academic Aggregator & Reconciler with OpenAlex as PRIMARY.
    Combines OpenAlex (primary), Crossref (fallback), and Google Scholar (fallback/supplementary),
    applies field-level provenance, validates DOIs, detects conflicts, and synthesizes Master Records.
    """

    @classmethod
    def reconcile(
        cls,
        parsed_ref: ParsedReference,
        openalex_candidates: List[Dict[str, Any]],
        crossref_candidates: List[Dict[str, Any]],
        scholar_candidates: List[Dict[str, Any]],
        scholar_search_data: Optional[Dict[str, Any]] = None,
        telemetry: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute non-destructive multi-source reconciliation prioritizing OpenAlex."""

        # 1. Match each provider candidates independently
        alex_cand, alex_conf, alex_status = ReferenceMatcher.match_candidate(parsed_ref, openalex_candidates)
        cross_cand, cross_conf, cross_status = ReferenceMatcher.match_candidate(parsed_ref, crossref_candidates)
        schol_cand, schol_conf, schol_status = ReferenceMatcher.match_candidate(parsed_ref, scholar_candidates)

        # 2. Run DOI Verification & Conflict Detection
        provider_cands_map = {
            "openalex": openalex_candidates,
            "crossref": crossref_candidates,
            "google_scholar": scholar_candidates
        }
        doi_verif = DOIVerifier.verify(parsed_ref, provider_cands_map)
        all_conflicts = list(doi_verif.get("conflicts") or [])

        # 3. Reconcile Citation Counts (Null policy: Keep real counts, never false 0s)
        alex_cite = None
        if alex_cand and alex_cand.get("citation_count") is not None:
            alex_cite = int(alex_cand["citation_count"])

        cross_cite = None
        if cross_cand and cross_cand.get("citation_count") is not None:
            cross_cite = int(cross_cand["citation_count"])

        schol_cite = None
        if schol_cand and schol_cand.get("citation_count") is not None:
            schol_cite = int(schol_cand["citation_count"])
        elif schol_cand and (schol_cand.get("normalized_result") or {}).get("citations", {}).get("count") is not None:
            schol_cite = int((schol_cand.get("normalized_result") or {}).get("citations", {}).get("count"))

        # Canonical citation value priority: Scholar (if matched and available) -> OpenAlex (if matched) -> Crossref -> None
        canonical_citation = None
        if schol_cite is not None and schol_status == "matched":
            canonical_citation = schol_cite
        elif alex_cite is not None and alex_status == "matched":
            canonical_citation = alex_cite
        elif cross_cite is not None and cross_status == "matched":
            canonical_citation = cross_cite
        else:
            non_nulls = [c for c in (schol_cite, alex_cite, cross_cite) if c is not None]
            canonical_citation = max(non_nulls) if non_nulls else None

        citation_counts = {
            "canonical_value": canonical_citation,
            "google_scholar": schol_cite,
            "openalex": alex_cite,
            "crossref": cross_cite
        }

        # 4. Reconcile Title (OpenAlex Primary Priority)
        if alex_cand and alex_status in ("matched", "low_confidence") and alex_cand.get("title"):
            canonical_title = {
                "value": alex_cand["title"],
                "source": "openalex",
                "confidence": round(alex_conf, 2),
                "verification_status": "verified" if alex_status == "matched" else "unverified"
            }
        elif cross_cand and cross_status in ("matched", "low_confidence") and cross_cand.get("title"):
            canonical_title = {
                "value": cross_cand["title"],
                "source": "crossref",
                "confidence": round(cross_conf, 2),
                "verification_status": "verified" if cross_status == "matched" else "unverified"
            }
        elif schol_cand and schol_cand.get("title") and schol_status in ("matched", "low_confidence"):
            canonical_title = {
                "value": schol_cand["title"],
                "source": "google_scholar",
                "confidence": round(schol_conf, 2),
                "verification_status": "verified" if schol_status == "matched" else "unverified"
            }
        else:
            canonical_title = {
                "value": parsed_ref.title or parsed_ref.original_text,
                "source": "parsed",
                "confidence": 0.50 if parsed_ref.title else 0.20,
                "verification_status": "unverified"
            }

        # 5. Reconcile Publication Year
        canonical_year_val = parsed_ref.year
        year_source = "parsed"
        year_conf = 0.90 if parsed_ref.year else 0.0

        if alex_cand and alex_cand.get("year") and alex_status == "matched":
            canonical_year_val = alex_cand["year"]
            year_source = "openalex"
            year_conf = alex_conf
        elif cross_cand and cross_cand.get("year") and cross_status == "matched":
            canonical_year_val = cross_cand["year"]
            year_source = "crossref"
            year_conf = cross_conf
        elif not canonical_year_val:
            if alex_cand and alex_cand.get("year"):
                canonical_year_val = alex_cand["year"]
                year_source = "openalex"
                year_conf = alex_conf
            elif cross_cand and cross_cand.get("year"):
                canonical_year_val = cross_cand["year"]
                year_source = "crossref"
                year_conf = cross_conf
            elif schol_cand and schol_cand.get("year"):
                canonical_year_val = schol_cand["year"]
                year_source = "google_scholar"
                year_conf = schol_conf

        canonical_year = {
            "value": canonical_year_val,
            "source": year_source,
            "confidence": round(year_conf, 2),
            "verification_status": "verified" if canonical_year_val else "unverified"
        }

        # 6. Reconcile Venue / Journal (Strict Canonical Purity)
        INVALID_VENUE_NAMES = {
            "google scholar", "scholar", "openalex", "crossref", "serpapi",
            "arxiv", "unknown", "none", "n/a", "null", "undefined"
        }
        conflict_doi_values = {c.get("rejected_value") for c in all_conflicts if c.get("field") == "doi"}

        def is_valid_verified_venue(cand: Optional[Dict[str, Any]]) -> bool:
            if not cand or not cand.get("journal"):
                return False
            venue_str = str(cand["journal"]).strip()
            if not venue_str or venue_str.lower() in INVALID_VENUE_NAMES:
                return False
            cand_doi = cand.get("doi") or ""
            if cand_doi in conflict_doi_values or cand_doi.startswith("10.65215"):
                return False
            j_lower = venue_str.lower()
            if "shenzhen medical academy" in j_lower or "reprint repository" in j_lower:
                all_conflicts.append({
                    "field": "venue",
                    "provider": cand.get("source", "unknown"),
                    "rejected_value": venue_str,
                    "reason": "Rejected third-party reprint repository venue.",
                    "status": "conflict"
                })
                return False
            return True

        venue_val = parsed_ref.journal if (parsed_ref.journal and parsed_ref.journal.strip().lower() not in INVALID_VENUE_NAMES) else None
        venue_src = "parsed" if venue_val else "none"

        if not venue_val:
            if is_valid_verified_venue(alex_cand) and alex_status == "matched":
                venue_val = alex_cand["journal"]
                venue_src = "openalex"
            elif is_valid_verified_venue(cross_cand) and cross_status == "matched":
                venue_val = cross_cand["journal"]
                venue_src = "crossref"
            elif is_valid_verified_venue(schol_cand) and schol_status == "matched":
                venue_val = schol_cand["journal"]
                venue_src = "google_scholar"
            elif is_valid_verified_venue(alex_cand):
                venue_val = alex_cand["journal"]
                venue_src = "openalex"
            elif is_valid_verified_venue(cross_cand):
                venue_val = cross_cand["journal"]
                venue_src = "crossref"
            elif is_valid_verified_venue(schol_cand):
                venue_val = schol_cand["journal"]
                venue_src = "google_scholar"

        canonical_venue = {
            "value": venue_val if venue_val else None,
            "source": venue_src if venue_val else "none",
            "confidence": 0.85 if venue_val else 0.0,
            "verification_status": "verified" if venue_val else "unverified"
        }

        # 7. Reconcile Identifiers
        canonical_doi_val = doi_verif.get("canonical_doi")
        if canonical_doi_val:
            canonical_doi_val = canonical_doi_val.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()

        schol_cluster_id = (schol_cand.get("cluster_id") or (schol_cand.get("normalized_result") or {}).get("cluster_id")) if schol_cand else None
        schol_url = (schol_cand.get("scholar_url") or schol_cand.get("url") or (schol_cand.get("normalized_result") or {}).get("link")) if schol_cand else None
        schol_cited_by_url = (schol_cand.get("cited_by_url") or (schol_cand.get("normalized_result") or {}).get("citations", {}).get("link")) if schol_cand else None
        schol_cites_val = (schol_cand.get("citation_count") or (schol_cand.get("normalized_result") or {}).get("citations", {}).get("count")) if schol_cand else None
        schol_vers_val = (schol_cand.get("versions_count") or (schol_cand.get("normalized_result") or {}).get("versions", {}).get("count")) if schol_cand else None

        canonical_identifiers = {
            "doi": {
                "value": canonical_doi_val,
                "source": "doi_verifier" if canonical_doi_val else "none",
                "confidence": doi_verif.get("confidence", 0.0),
                "verification_status": doi_verif.get("status", "unverified")
            },
            "openalex_id": {
                "value": (alex_cand.get("openalex_id") if alex_cand and alex_status in ("matched", "low_confidence") else None),
                "source": "openalex",
                "confidence": round(alex_conf, 2),
                "verification_status": "verified" if alex_status == "matched" else "unverified"
            },
            "arxiv_id": {
                "value": parsed_ref.arxiv_id or DOIVerifier.extract_arxiv_id(parsed_ref.original_text) or (DOIVerifier.extract_arxiv_id(canonical_doi_val) if canonical_doi_val else None),
                "source": "arxiv_resolver",
                "confidence": 0.98 if (parsed_ref.arxiv_id or doi_verif.get("reconciled_with_arxiv")) else 0.0,
                "verification_status": "verified" if (parsed_ref.arxiv_id or doi_verif.get("reconciled_with_arxiv")) else "unverified"
            },
            "isbn": {
                "value": parsed_ref.isbn or None,
                "source": "parsed" if parsed_ref.isbn else "none",
                "confidence": 0.95 if parsed_ref.isbn else 0.0,
                "verification_status": "verified" if parsed_ref.isbn else "unverified"
            },
            "google_scholar_cluster_id": {
                "value": schol_cluster_id or None,
                "source": "google_scholar" if schol_cluster_id else "none",
                "confidence": round(schol_conf, 2) if schol_cluster_id else 0.0,
                "verification_status": "verified" if (schol_status == "matched" and schol_cluster_id) else "unverified"
            },
            "google_scholar_url": {
                "value": schol_url or None,
                "source": "google_scholar" if schol_url else "none",
                "confidence": round(schol_conf, 2) if schol_url else 0.0,
                "verification_status": "verified" if (schol_status == "matched" and schol_url) else "unverified"
            }
        }

        # 8. Reconcile Canonical Authors (OpenAlex Authorship First)
        canonical_authors: List[Dict[str, Any]] = []
        raw_authors_pool = (alex_cand.get("authors") if alex_cand and (alex_status == "matched" or not parsed_ref.authors) else None) or \
                           (cross_cand.get("authors") if cross_cand and (cross_status == "matched" or not parsed_ref.authors) else None) or \
                           (schol_cand.get("authors") if schol_cand and (schol_status == "matched" or not parsed_ref.authors) else None) or \
                           parsed_ref.authors or \
                           (alex_cand.get("authors") if alex_cand else []) or \
                           (cross_cand.get("authors") if cross_cand else []) or \
                           (schol_cand.get("authors") if schol_cand else [])

        for a in raw_authors_pool:
            a_name = a.get("display_name") or a.get("name") if isinstance(a, dict) else str(a)
            a_given = a.get("given", "") if isinstance(a, dict) else ""
            a_family = a.get("family", "") if isinstance(a, dict) else ""
            a_id = a.get("author_id") if isinstance(a, dict) else ""
            
            a_idents = (a.get("identifiers") if isinstance(a, dict) else {}) or {}
            openalex_author_id = a_id if (a_id and "openalex" in str(a_id)) else a_idents.get("openalex_id")
            orcid = a_idents.get("orcid") or (a.get("orcid") if isinstance(a, dict) else None)
            scholar_id = a_idents.get("google_scholar_id")
            
            a_affils = a.get("affiliations") if isinstance(a, dict) else []
            a_status = a.get("author_match_status") or ("matched" if openalex_author_id else ("matched" if a_name else "unverified"))

            canonical_authors.append({
                "name": a_name,
                "display_name": a_name,
                "given": a_given,
                "family": a_family,
                "author_id": openalex_author_id or a_id or "",
                "identifiers": {
                    "openalex_id": openalex_author_id or a_id or None,
                    "orcid": orcid or None,
                    "google_scholar_id": scholar_id or None
                },
                "affiliations": a_affils or [],
                "match_status": a_status,
                "confidence": 0.95 if openalex_author_id else 0.75
            })

        # 9. Abstract & Direct PDF link from OpenAlex / OA
        canonical_abstract = (alex_cand.get("abstract") if alex_cand else None) or None
        canonical_pdf_url = (alex_cand.get("pdf_url") if alex_cand else None) or \
                            (schol_cand.get("resources", [{}])[0].get("link") if schol_cand and schol_cand.get("resources") else None)

        # 10. Assemble Multi-Source Preservation Object
        sources_payload = {
            "openalex": {
                "available": bool(openalex_candidates),
                "matched": alex_status == "matched",
                "status": alex_status,
                "confidence": round(alex_conf, 2),
                "citation_count": alex_cite,
                "openalex_id": alex_cand.get("openalex_id") if alex_cand else None,
                "doi": alex_cand.get("doi") if alex_cand else None,
                "url": alex_cand.get("url") if alex_cand else None,
                "pdf_url": alex_cand.get("pdf_url") if alex_cand else None,
                "raw_file": alex_cand.get("raw_file") if alex_cand else (openalex_candidates[0].get("raw_file") if openalex_candidates else None),
                "normalized_file": alex_cand.get("normalized_file") if alex_cand else None,
                "data": alex_cand or {}
            },
            "crossref": {
                "available": bool(crossref_candidates),
                "matched": cross_status == "matched",
                "status": cross_status,
                "confidence": round(cross_conf, 2),
                "citation_count": cross_cite,
                "doi": cross_cand.get("doi") if cross_cand else None,
                "url": cross_cand.get("url") if cross_cand else None,
                "raw_file": cross_cand.get("raw_file") if cross_cand else (crossref_candidates[0].get("raw_file") if crossref_candidates else None),
                "normalized_file": cross_cand.get("normalized_file") if cross_cand else None,
                "data": cross_cand or {}
            },
            "google_scholar": {
                "available": bool(scholar_search_data.get("available")) if scholar_search_data else bool(schol_cand and schol_cand.get("available")),
                "matched": schol_status == "matched",
                "status": schol_status,
                "confidence": round(schol_conf, 2),
                "url": schol_url,
                "cluster_id": schol_cluster_id,
                "cited_by_url": schol_cited_by_url,
                "citation_count": schol_cites_val,
                "versions_count": schol_vers_val,
                "raw_file": schol_cand.get("raw_file") if schol_cand else (scholar_search_data.get("raw_file") if scholar_search_data else None),
                "normalized_file": schol_cand.get("normalized_file") if schol_cand else (scholar_search_data.get("normalized_file") if scholar_search_data else None),
                "data": (schol_cand.get("normalized_result") if schol_cand and schol_cand.get("normalized_result") else (schol_cand or {}))
            }
        }

        # 11. Compute Overall Confidence & Determine Primary Source
        if alex_status == "matched":
            overall_conf = alex_conf
        elif cross_status == "matched":
            overall_conf = cross_conf
        elif schol_status == "matched":
            overall_conf = schol_conf
        else:
            all_confs = [c for c in (alex_conf, cross_conf, schol_conf) if c > 0]
            overall_conf = max(all_confs) if all_confs else 0.0

        doi_bonus = 0.05 if doi_verif.get("status") == "verified" else 0.0
        overall_conf = min(1.0, round(overall_conf + (doi_bonus if overall_conf > 0 else 0.0), 2))

        # Best Paper Landing Page URL
        paper_url = (alex_cand.get("url") if alex_cand and alex_status in ("matched", "low_confidence") else None) or \
                    (cross_cand.get("url") if cross_cand and cross_status == "matched" else None) or \
                    (schol_cand.get("url") if schol_cand and schol_status == "matched" else None) or \
                    (f"https://doi.org/{canonical_doi_val}" if canonical_doi_val else None)

        canonical_type = {
            "value": (alex_cand.get("reference_type") if alex_cand and alex_status == "matched" else None) or parsed_ref.reference_type or "journal-article",
            "source": "openalex" if (alex_cand and alex_status == "matched") else "classifier",
            "confidence": 0.90 if (alex_cand and alex_status == "matched") else 0.75,
            "verification_status": "verified" if alex_status == "matched" else "unverified"
        }

        canonical_publisher = {
            "value": (alex_cand.get("publisher") if alex_cand and alex_status == "matched" else None) or parsed_ref.publisher or None,
            "source": "openalex" if (alex_cand and alex_status == "matched" and alex_cand.get("publisher")) else ("parsed" if parsed_ref.publisher else "none"),
            "confidence": 0.90 if (alex_cand and alex_status == "matched") else 0.0,
            "verification_status": "verified" if (alex_cand and alex_status == "matched" and alex_cand.get("publisher")) else "unverified"
        }

        # 12. Build Master Record
        master_record = MasterRecordBuilder.build(
            parsed_ref=parsed_ref,
            canonical_title=canonical_title,
            canonical_year=canonical_year,
            canonical_venue=canonical_venue,
            canonical_identifiers=canonical_identifiers,
            citation_counts=citation_counts,
            canonical_authors=canonical_authors,
            sources=sources_payload,
            doi_verification=doi_verif,
            conflicts=all_conflicts,
            overall_confidence=overall_conf,
            canonical_type=canonical_type,
            canonical_publisher=canonical_publisher,
            volume=parsed_ref.volume or None,
            issue=parsed_ref.issue or None,
            pages=parsed_ref.pages or None,
            telemetry=telemetry,
            project_id=project_id,
            abstract=canonical_abstract,
            url=paper_url
        )

        # 13. Save Master Reference to Disk
        ref_id = master_record["reference_id"]
        storage.save_reference(ref_id, master_record)

        # Save Paper record
        paper_id = canonical_identifiers.get("openalex_id", {}).get("value") or canonical_doi_val or ref_id
        storage.save_paper(paper_id, {
            "paper_id": paper_id,
            "title": canonical_title["value"],
            "year": canonical_year["value"],
            "reference_type": canonical_type["value"],
            "venue": canonical_venue["value"],
            "publisher": canonical_publisher["value"],
            "volume": parsed_ref.volume or None,
            "issue": parsed_ref.issue or None,
            "pages": parsed_ref.pages or None,
            "doi": canonical_doi_val,
            "isbn": parsed_ref.isbn or None,
            "arxiv_id": canonical_identifiers.get("arxiv_id", {}).get("value"),
            "openalex_id": canonical_identifiers.get("openalex_id", {}).get("value"),
            "citations": citation_counts,
            "authors": canonical_authors,
            "abstract": canonical_abstract,
            "url": paper_url,
            "pdf_url": canonical_pdf_url,
            "reference_id": ref_id
        })

        return master_record
