import time
import asyncio
import re
import logging
from typing import List, Dict, Any, Optional
from enrichment.parser import ReferenceParser, ParsedReference
from enrichment.cache import cache
from enrichment.config import config
from enrichment.providers import AcademicProvider, OpenAlexProvider, CrossrefProvider, GoogleScholarProvider
from enrichment.reconciler import MultiSourceReconciler
from enrichment.string_utils import normalize_string

logger = logging.getLogger("enrichment.pipeline")


def deduplicate_references(references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate a list of reference objects using a multi-key strategy:
    1. Clean DOI
    2. OpenAlex Work ID
    3. Normalized (Title + Year + First Author)
    Preserves original list order and highest enriched record.
    """
    if not references:
        return []

    seen_keys = set()
    deduped = []

    for item in references:
        doi = (item.get("doi") or "").lower().replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
        openalex_id = (item.get("openalex_id") or "").lower().strip()
        title = normalize_string(item.get("title") or item.get("text") or item.get("original_text") or "")
        year = str(item.get("year") or "")
        
        # Extract first author family name if present
        authors = item.get("authors") or []
        first_author = ""
        if authors:
            first_a = authors[0]
            if isinstance(first_a, dict):
                first_author = normalize_string(first_a.get("family") or first_a.get("name") or "")
            else:
                first_author = normalize_string(str(first_a))

        # Generate dedup keys
        keys = []
        if doi and len(doi) > 5:
            keys.append(f"doi:{doi}")
        if openalex_id and len(openalex_id) > 10:
            keys.append(f"openalex:{openalex_id}")
        if len(title) > 15:
            if first_author and year:
                keys.append(f"title_author_year:{title[:60]}_{first_author}_{year}")
            elif year:
                keys.append(f"title_year:{title[:60]}_{year}")
            else:
                keys.append(f"title:{title[:60]}")

        # Check if already seen
        is_duplicate = False
        for k in keys:
            if k in seen_keys:
                is_duplicate = True
                break

        if not is_duplicate:
            for k in keys:
                seen_keys.add(k)
            deduped.append(item)
        else:
            logger.debug(f"Filtered duplicate reference: {item.get('title') or item.get('text')}")

    return deduped


class ReferenceEnricher:
    """
    Multi-Source Reference Enrichment Pipeline with OpenAlex as Primary Provider.
    Executes parallel provider queries (OpenAlex, Crossref, Google Scholar),
    validates DOIs, reconciles multi-source metadata, persists Master Records,
    and returns rich structured objects with backward-compatible accessors.
    """
    def __init__(
        self,
        primary_provider: Optional[AcademicProvider] = None,
        fallback_provider: Optional[AcademicProvider] = None,
        scholar_provider: Optional[AcademicProvider] = None,
        threshold: Optional[float] = None
    ):
        self.primary_provider = primary_provider or OpenAlexProvider()
        self.fallback_provider = fallback_provider or CrossrefProvider()
        self.scholar_provider = scholar_provider or GoogleScholarProvider()
        self.threshold = threshold or config.match_threshold

    async def enrich_reference(self, raw_text: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich a single reference text into a standardized Master Record.
        """
        parsed_ref = ReferenceParser.parse(raw_text)

        # Check in-memory fast cache
        cached_result = cache.get(parsed_ref.doi, parsed_ref.title)
        if cached_result:
            return cached_result

        telemetry = {
            "providers_queried": [],
            "latency_ms": {},
            "candidate_counts": {},
            "errors": {}
        }

        # 1. Execute Provider Queries Concurrently
        async def fetch_openalex():
            t0 = time.perf_counter()
            try:
                cands = await self.primary_provider.search_reference(parsed_ref)
                telemetry["latency_ms"]["openalex"] = round((time.perf_counter() - t0) * 1000, 2)
                telemetry["candidate_counts"]["openalex"] = len(cands)
                telemetry["providers_queried"].append("openalex")
                return cands
            except Exception as e:
                telemetry["latency_ms"]["openalex"] = round((time.perf_counter() - t0) * 1000, 2)
                telemetry["candidate_counts"]["openalex"] = 0
                telemetry["errors"]["openalex"] = str(e)
                logger.error(f"OpenAlex query error for ref '{parsed_ref.title}': {e}")
                return []

        async def fetch_crossref():
            t0 = time.perf_counter()
            try:
                cands = await self.fallback_provider.search_reference(parsed_ref)
                telemetry["latency_ms"]["crossref"] = round((time.perf_counter() - t0) * 1000, 2)
                telemetry["candidate_counts"]["crossref"] = len(cands)
                telemetry["providers_queried"].append("crossref")
                return cands
            except Exception as e:
                telemetry["latency_ms"]["crossref"] = round((time.perf_counter() - t0) * 1000, 2)
                telemetry["candidate_counts"]["crossref"] = 0
                telemetry["errors"]["crossref"] = str(e)
                logger.debug(f"Crossref query error: {e}")
                return []

        async def fetch_scholar():
            t0 = time.perf_counter()
            try:
                cands = await self.scholar_provider.search_reference(parsed_ref)
                telemetry["latency_ms"]["google_scholar"] = round((time.perf_counter() - t0) * 1000, 2)
                telemetry["candidate_counts"]["google_scholar"] = len(cands)
                telemetry["providers_queried"].append("google_scholar")
                return cands
            except Exception as e:
                telemetry["latency_ms"]["google_scholar"] = round((time.perf_counter() - t0) * 1000, 2)
                telemetry["candidate_counts"]["google_scholar"] = 0
                telemetry["errors"]["google_scholar"] = str(e)
                return []

        alex_res, cross_res, schol_res = await asyncio.gather(
            fetch_openalex(),
            fetch_crossref(),
            fetch_scholar(),
            return_exceptions=True
        )

        openalex_cands = alex_res if isinstance(alex_res, list) else []
        crossref_cands = cross_res if isinstance(cross_res, list) else []
        scholar_cands = schol_res if isinstance(schol_res, list) else []

        # 2. Multi-Source Reconciliation & Master Record Synthesis
        master_record = MultiSourceReconciler.reconcile(
            parsed_ref=parsed_ref,
            openalex_candidates=openalex_cands,
            crossref_candidates=crossref_cands,
            scholar_candidates=scholar_cands,
            telemetry=telemetry,
            project_id=project_id
        )

        # 3. Create enriched dictionary with full Master Record & backward-compatible top-level keys
        canonical = master_record.get("canonical") or {}
        can_title = canonical.get("title", {}).get("value") if isinstance(canonical.get("title"), dict) else str(canonical.get("title") or "")
        can_year = canonical.get("year", {}).get("value") if isinstance(canonical.get("year"), dict) else canonical.get("year")
        can_venue = canonical.get("venue", {}).get("value") if isinstance(canonical.get("venue"), dict) else str(canonical.get("venue") or "")
        can_doi = canonical.get("identifiers", {}).get("doi", {}).get("value") if isinstance(canonical.get("identifiers", {}).get("doi"), dict) else ""
        can_openalex = canonical.get("identifiers", {}).get("openalex_id", {}).get("value") if isinstance(canonical.get("identifiers", {}).get("openalex_id"), dict) else ""
        can_arxiv = canonical.get("identifiers", {}).get("arxiv_id", {}).get("value") if isinstance(canonical.get("identifiers", {}).get("arxiv_id"), dict) else ""
        
        citations = canonical.get("citation_counts") or {}
        citation_count = citations.get("canonical_value") if citations.get("canonical_value") is not None else (citations.get("openalex") or citations.get("crossref") or citations.get("google_scholar") or 0)
        overall_conf = master_record.get("quality_and_conflicts", {}).get("overall_confidence", 0.0)

        # Identify primary source (OpenAlex First)
        primary_source = "none"
        if master_record.get("sources", {}).get("openalex", {}).get("matched"):
            primary_source = "openalex"
        elif master_record.get("sources", {}).get("crossref", {}).get("matched"):
            primary_source = "crossref"
        elif master_record.get("sources", {}).get("google_scholar", {}).get("matched"):
            primary_source = "google_scholar"

        match_status = "matched" if overall_conf >= self.threshold else ("low_confidence" if overall_conf >= 0.50 else "not_found")

        # Extract direct PDF URL from OpenAlex best_oa_location if available
        openalex_data = master_record.get("sources", {}).get("openalex", {}).get("data") or {}
        direct_pdf_url = openalex_data.get("pdf_url") or None

        enriched = {
            # Master Record Core Schema
            "reference_id": master_record["reference_id"],
            "project_id": master_record["project_id"],
            "created_at": master_record["created_at"],
            "input": master_record["input"],
            "canonical": master_record["canonical"],
            "canonical_authors": master_record["canonical_authors"],
            "sources": master_record["sources"],
            "doi_verification": master_record["doi_verification"],
            "quality_and_conflicts": master_record["quality_and_conflicts"],
            "telemetry": master_record["telemetry"],
            "master_record": master_record,

            # Backward-Compatible Top-Level Keys
            "original_text": raw_text,
            "title": can_title or parsed_ref.title,
            "authors": master_record.get("canonical_authors") or parsed_ref.authors,
            "year": can_year or parsed_ref.year,
            "journal": can_venue or parsed_ref.journal,
            "doi": can_doi or parsed_ref.doi,
            "arxiv_id": can_arxiv or parsed_ref.arxiv_id,
            "url": canonical.get("url") or (f"https://doi.org/{can_doi}" if can_doi else ""),
            "pdf_url": direct_pdf_url,
            "openalex_id": can_openalex or "",
            "citation_count": citation_count if citation_count is not None else 0,
            "citations": citations,
            "source": primary_source,
            "confidence": overall_conf,
            "match_status": match_status
        }

        # Put in fast in-memory cache
        cache.put(parsed_ref.doi, parsed_ref.title, enriched)
        return enriched

    async def enrich_batch(self, references: List[Dict[str, Any]], project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Enrich a list of references in parallel with automatic deduplication.
        Input format: [{"text": "..."}, ...] or list of strings.
        """
        if not references:
            return []

        # Deduplicate raw inputs first
        cleaned_inputs = []
        for item in references:
            if isinstance(item, dict):
                text = item.get("text") or item.get("original_text") or ""
                r_id = item.get("id") or item.get("reference_id")
            else:
                text = str(item)
                r_id = None
            if text.strip():
                cleaned_inputs.append({"text": text.strip(), "id": r_id})

        tasks = [self.enrich_reference(it["text"], project_id=project_id) for it in cleaned_inputs]
        results = await asyncio.gather(*tasks)

        # Deduplicate enriched results
        deduped_results = deduplicate_references(list(results))
        return deduped_results
