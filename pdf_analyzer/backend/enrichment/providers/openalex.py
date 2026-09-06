import os
import re
import time
import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional, Tuple
from enrichment.providers.base import AcademicProvider
from enrichment.parser import ParsedReference
from enrichment.string_utils import parse_author_name, normalize_string
from enrichment.config import config
from enrichment.storage import storage

logger = logging.getLogger("enrichment.openalex")


def reconstruct_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    """
    Reconstruct natural language abstract from OpenAlex abstract_inverted_index.
    Example: {"This": [0], "paper": [1], "presents": [2]} -> "This paper presents"
    """
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    try:
        word_positions: List[Tuple[int, str]] = []
        for word, positions in inverted_index.items():
            if isinstance(positions, list):
                for pos in positions:
                    if isinstance(pos, int):
                        word_positions.append((pos, str(word)))
        word_positions.sort(key=lambda x: x[0])
        return " ".join(w for _, w in word_positions)
    except Exception as e:
        logger.debug(f"Failed to reconstruct abstract: {e}")
        return ""


class OpenAlexProvider(AcademicProvider):
    """
    Primary Academic Metadata Provider using OpenAlex API (https://api.openalex.org).
    Supports API key authentication, exponential backoff retries (429 / 500 / timeouts),
    multi-strategy search (DOI exact, OpenAlex ID, clean title, title + author),
    and rich metadata extraction (citations, authors, institutions, topics, OA links, abstract).
    """
    BASE_URL = "https://api.openalex.org"
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0
    TIMEOUT = 12.0

    @property
    def name(self) -> str:
        return "openalex"

    def _get_headers(self) -> Dict[str, str]:
        """Build request headers without logging or exposing API key."""
        headers = {
            "User-Agent": "Journal2LaTeX-PDFAnalyzer/1.0 (https://github.com/yossef-ayman/Journal2LaTeX)"
        }
        if config.openalex_email:
            headers["User-Agent"] += f" (mailto:{config.openalex_email})"
        
        # Add Authorization header if API key configured
        if config.openalex_api_key:
            headers["Authorization"] = f"Bearer {config.openalex_api_key}"
            
        return headers

    def _get_params(self, base_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build query parameters."""
        params = dict(base_params or {})
        if config.openalex_email and "mailto" not in params:
            params["mailto"] = config.openalex_email
        if config.openalex_api_key and "api_key" not in params:
            params["api_key"] = config.openalex_api_key
        return params

    async def _safe_get(self, client: httpx.AsyncClient, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute GET request with exponential backoff retry on 429, 5xx, or network timeout.
        Never logs or leaks API keys.
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        full_params = self._get_params(params)

        backoff = self.INITIAL_BACKOFF
        for attempt in range(1, self.MAX_RETRIES + 1):
            t0 = time.perf_counter()
            try:
                # Sanitized debug log (no API key)
                log_params = {k: v for k, v in full_params.items() if k != "api_key"}
                logger.debug(f"[OpenAlex] GET {url} params={log_params} (attempt {attempt}/{self.MAX_RETRIES})")
                
                res = await client.get(url, params=full_params, headers=headers, timeout=self.TIMEOUT)
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

                logger.debug(f"[OpenAlex] Status: {res.status_code} in {elapsed_ms}ms")

                if res.status_code == 200:
                    return res.json()
                elif res.status_code == 404:
                    return None
                elif res.status_code == 429:
                    logger.warning(f"[OpenAlex] Rate limit (429) on attempt {attempt}. Retrying in {backoff:.1f}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                elif res.status_code in (500, 502, 503, 504):
                    logger.warning(f"[OpenAlex] Server error ({res.status_code}) on attempt {attempt}. Retrying in {backoff:.1f}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 1.5
                else:
                    logger.warning(f"[OpenAlex] Unexpected status {res.status_code} for query: {log_params}")
                    return None

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
                logger.warning(f"[OpenAlex] Network error/timeout ({exc.__class__.__name__}) on attempt {attempt} after {elapsed_ms}ms. Retrying...")
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(backoff)
                    backoff *= 1.5
                else:
                    logger.error(f"[OpenAlex] Request failed after {self.MAX_RETRIES} attempts.")
                    return None
            except Exception as exc:
                logger.error(f"[OpenAlex] Unexpected error during request: {type(exc).__name__}: {str(exc)}")
                return None

        return None

    async def search_reference(self, reference: ParsedReference) -> List[Dict[str, Any]]:
        """
        Multi-Strategy Search in OpenAlex API:
        Strategy 1: Direct DOI lookup / filter if DOI is present.
        Strategy 2: Exact/clean Title search.
        Strategy 3: Title + First Author search.
        Strategy 4: Quoted substring title search if title has punctuation.
        Saves raw payloads and normalized structures.
        """
        candidates_map: Dict[str, Dict[str, Any]] = {}

        async with httpx.AsyncClient() as client:
            # ─────────────────────────────────────────────────────────────
            # Strategy 1: Direct DOI lookup (Highest Priority)
            # ─────────────────────────────────────────────────────────────
            if reference.doi:
                doi_clean = reference.doi.lower().replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
                query_key = f"doi:{doi_clean}"
                
                # 1a. Try direct work lookup by DOI endpoint
                raw_data = await self._safe_get(client, f"works/https://doi.org/{doi_clean}", {})
                if raw_data and isinstance(raw_data, dict) and raw_data.get("id"):
                    raw_file = storage.save_raw(self.name, query_key, raw_data, status_code=200, candidate_count=1)
                    parsed_w = self._format_work(raw_data, raw_file=raw_file)
                    if parsed_w:
                        key = parsed_w.get("doi") or parsed_w.get("openalex_id") or "cand_1"
                        candidates_map[key] = parsed_w
                        storage.save_normalized(self.name, query_key, [parsed_w])
                else:
                    # 1b. Try works filter by DOI
                    params = {"filter": f"doi:https://doi.org/{doi_clean}", "per_page": 5}
                    raw_data = await self._safe_get(client, "works", params)
                    if raw_data and isinstance(raw_data, dict):
                        works = raw_data.get("results", [])
                        if works:
                            raw_file = storage.save_raw(self.name, query_key, raw_data, status_code=200, candidate_count=len(works))
                            formatted_works = []
                            for w in works:
                                parsed_w = self._format_work(w, raw_file=raw_file)
                                if parsed_w:
                                    key = parsed_w.get("doi") or parsed_w.get("openalex_id") or parsed_w.get("title")
                                    candidates_map[key] = parsed_w
                                    formatted_works.append(parsed_w)
                            storage.save_normalized(self.name, query_key, formatted_works)

            # If DOI lookup yielded a candidate with DOI match, we can return early
            if candidates_map and any(c.get("doi") and reference.doi and c["doi"].lower() == reference.doi.lower().replace("https://doi.org/", "").strip() for c in candidates_map.values()):
                return list(candidates_map.values())

            # ─────────────────────────────────────────────────────────────
            # Strategy 2: Search by Clean Title
            # ─────────────────────────────────────────────────────────────
            clean_title = (reference.title or "").strip()
            # Strip outer quotes and normalize
            clean_title = re.sub(r'^["“\'‘]+|["”\'’]+$', '', clean_title).strip()
            
            if clean_title and len(clean_title) >= 5:
                query_key = f"title:{clean_title}"
                params = {"search": clean_title, "per_page": 10}
                raw_data = await self._safe_get(client, "works", params)
                if raw_data and isinstance(raw_data, dict):
                    works = raw_data.get("results", [])
                    raw_file = storage.save_raw(self.name, query_key, raw_data, status_code=200, candidate_count=len(works))
                    formatted_works = []
                    for w in works:
                        parsed_w = self._format_work(w, raw_file=raw_file)
                        if parsed_w:
                            key = parsed_w.get("doi") or parsed_w.get("openalex_id") or parsed_w.get("title")
                            if key not in candidates_map:
                                candidates_map[key] = parsed_w
                            formatted_works.append(parsed_w)
                    if formatted_works:
                        storage.save_normalized(self.name, query_key, formatted_works)

            # ─────────────────────────────────────────────────────────────
            # Strategy 3: Search by Title + First Author
            # ─────────────────────────────────────────────────────────────
            first_author = ""
            if reference.authors:
                first_author = reference.authors[0].get("family") or reference.authors[0].get("name") or ""
            elif reference.raw_authors:
                first_author = reference.raw_authors[0]

            # Strip initials / numbers
            first_author = re.sub(r'^[A-Z]\.\s*', '', first_author).strip()

            if clean_title and first_author and len(first_author) >= 2:
                query_str = f"{clean_title} {first_author}"
                query_key = f"title_author:{query_str}"
                params = {"search": query_str, "per_page": 10}
                raw_data = await self._safe_get(client, "works", params)
                if raw_data and isinstance(raw_data, dict):
                    works = raw_data.get("results", [])
                    raw_file = storage.save_raw(self.name, query_key, raw_data, status_code=200, candidate_count=len(works))
                    formatted_works = []
                    for w in works:
                        parsed_w = self._format_work(w, raw_file=raw_file)
                        if parsed_w:
                            key = parsed_w.get("doi") or parsed_w.get("openalex_id") or parsed_w.get("title")
                            if key not in candidates_map:
                                candidates_map[key] = parsed_w
                            formatted_works.append(parsed_w)
                    if formatted_works:
                        storage.save_normalized(self.name, query_key, formatted_works)

            # ─────────────────────────────────────────────────────────────
            # Strategy 4: Fallback to Raw Text Search (first 150 chars)
            # ─────────────────────────────────────────────────────────────
            if not candidates_map and reference.original_text:
                clean_raw = re.sub(r"^(?:\[\d+\]|\(\d+\)|\d+\.)\s*", "", reference.original_text).strip()
                if len(clean_raw) > 15:
                    query_str = clean_raw[:140]
                    query_key = f"raw:{query_str}"
                    params = {"search": query_str, "per_page": 5}
                    raw_data = await self._safe_get(client, "works", params)
                    if raw_data and isinstance(raw_data, dict):
                        works = raw_data.get("results", [])
                        if works:
                            raw_file = storage.save_raw(self.name, query_key, raw_data, status_code=200, candidate_count=len(works))
                            formatted_works = []
                            for w in works:
                                parsed_w = self._format_work(w, raw_file=raw_file)
                                if parsed_w:
                                    key = parsed_w.get("doi") or parsed_w.get("openalex_id") or parsed_w.get("title")
                                    if key not in candidates_map:
                                        candidates_map[key] = parsed_w
                                    formatted_works.append(parsed_w)
                            storage.save_normalized(self.name, query_key, formatted_works)

        return list(candidates_map.values())

    def _format_work(self, work: Dict[str, Any], raw_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Convert full OpenAlex work object to standardized candidate dictionary
        preserving authorships, identifiers, citation counts, OA locations, abstract, and topics.
        """
        if not work or not isinstance(work, dict):
            return None

        # 1. Title / Display Name
        title = work.get("title") or work.get("display_name") or ""
        if not title:
            return None

        # 2. Authorships Extraction
        authors: List[Dict[str, Any]] = []
        memberships = work.get("authorships") or []
        for m in memberships:
            author_obj = m.get("author") or {}
            display_name = author_obj.get("display_name") or ""
            author_id = author_obj.get("id") or ""
            orcid = author_obj.get("orcid") or ""
            
            # Institutions / Affiliations
            institutions_list = []
            countries_list = []
            for inst in m.get("institutions") or []:
                if isinstance(inst, dict) and inst.get("display_name"):
                    institutions_list.append(inst["display_name"])
                    if inst.get("country_code"):
                        countries_list.append(inst["country_code"])
            
            raw_affil = (m.get("raw_affiliation_strings") or [""])[0]

            if display_name:
                parsed_a = parse_author_name(display_name)
                parsed_a["author_id"] = author_id
                parsed_a["display_name"] = display_name
                parsed_a["source"] = self.name
                parsed_a["author_match_status"] = "matched" if author_id else "ambiguous"
                parsed_a["identifiers"] = {
                    "openalex_id": author_id or None,
                    "orcid": orcid or None,
                    "google_scholar_id": None
                }
                parsed_a["affiliations"] = institutions_list or ([raw_affil] if raw_affil else [])
                parsed_a["countries"] = list(set(countries_list))
                authors.append(parsed_a)

        # 3. Publication Year & Date
        year = work.get("publication_year")
        publication_date = work.get("publication_date") or ""

        # 4. Journal / Venue / Source
        primary_loc = work.get("primary_location") or {}
        source_obj = primary_loc.get("source") or {}
        journal = source_obj.get("display_name") or ""
        publisher = source_obj.get("host_organization_name") or ""
        issn_l = source_obj.get("issn_l") or ""

        # 5. Type
        work_type = work.get("type") or "journal-article"
        # Map OpenAlex types to standard taxonomy
        type_mapping = {
            "article": "journal-article",
            "journal-article": "journal-article",
            "book": "book",
            "book-chapter": "book-chapter",
            "proceedings-article": "proceedings-article",
            "conference": "proceedings-article",
            "preprint": "preprint",
            "dissertation": "thesis"
        }
        ref_type = type_mapping.get(work_type, "journal-article")

        # 6. DOI & URLs
        doi = work.get("doi") or ""
        if doi:
            doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
            doi_url = f"https://doi.org/{doi}"
        else:
            doi_url = ""

        openalex_id = work.get("id") or ""
        
        # Best Landing Page & PDF URLs
        landing_page_url = primary_loc.get("landing_page_url") or doi_url or openalex_id
        pdf_url = primary_loc.get("pdf_url") or ""
        
        # Check best_oa_location if primary_location has no PDF
        best_oa = work.get("best_oa_location") or {}
        if not pdf_url and best_oa.get("pdf_url"):
            pdf_url = best_oa["pdf_url"]
        if not landing_page_url and best_oa.get("landing_page_url"):
            landing_page_url = best_oa["landing_page_url"]

        # 7. Citations Count
        cited_by_count = work.get("cited_by_count")
        citation_count = int(cited_by_count) if cited_by_count is not None else 0

        # 8. Open Access Metadata
        open_access_meta = work.get("open_access") or {}
        is_oa = open_access_meta.get("is_oa", False)
        oa_status = open_access_meta.get("oa_status") or "closed"

        # 9. Topics / Concepts
        topics = []
        for top in work.get("topics") or []:
            if isinstance(top, dict) and top.get("display_name"):
                topics.append(top["display_name"])
        if not topics:
            for conc in work.get("concepts") or []:
                if isinstance(conc, dict) and conc.get("display_name"):
                    topics.append(conc["display_name"])

        # 10. Abstract Reconstruction
        abstract = reconstruct_abstract(work.get("abstract_inverted_index"))

        # 11. Pagination & Volume
        biblio = work.get("biblio") or {}
        volume = biblio.get("volume") or ""
        issue = biblio.get("issue") or ""
        first_page = biblio.get("first_page") or ""
        last_page = biblio.get("last_page") or ""
        pages = f"{first_page}-{last_page}" if (first_page and last_page and first_page != last_page) else (first_page or last_page or "")

        return {
            "title": title,
            "display_name": title,
            "authors": authors,
            "year": year,
            "publication_date": publication_date,
            "journal": journal,
            "venue": journal,
            "publisher": publisher,
            "reference_type": ref_type,
            "volume": volume,
            "issue": issue,
            "pages": pages,
            "doi": doi,
            "url": landing_page_url,
            "pdf_url": pdf_url or None,
            "openalex_id": openalex_id,
            "citation_count": citation_count,
            "cited_by_count": citation_count,
            "is_oa": is_oa,
            "oa_status": oa_status,
            "abstract": abstract or None,
            "topics": topics[:6],
            "referenced_works_count": len(work.get("referenced_works") or []),
            "related_works": (work.get("related_works") or [])[:5],
            "source": self.name,
            "raw_file": raw_file
        }

    async def get_citations(self, work_id: str, page: int = 1, num: int = 10) -> Dict[str, Any]:
        """
        Fetch citing publications for an OpenAlex work (W...) using filter=cites:{work_id}.
        """
        clean_id = (work_id or "").strip()
        clean_id = clean_id.replace("https://openalex.org/", "").replace("http://openalex.org/", "").strip()
        if not clean_id:
            return {
                "provider": self.name,
                "available": False,
                "work_id": "",
                "results": [],
                "page": page,
                "total_count": 0
            }

        params = {
            "filter": f"cites:{clean_id}",
            "page": page,
            "per_page": min(max(1, num), 20)
        }

        async with httpx.AsyncClient() as client:
            raw_data = await self._safe_get(client, "works", params)
            if not raw_data or not isinstance(raw_data, dict):
                return {
                    "provider": self.name,
                    "available": False,
                    "work_id": clean_id,
                    "results": [],
                    "page": page,
                    "total_count": 0
                }

            meta = raw_data.get("meta") or {}
            works = raw_data.get("results") or []
            formatted = []
            for w in works:
                fw = self._format_work(w)
                if fw:
                    formatted.append(fw)

            return {
                "provider": self.name,
                "available": True,
                "work_id": clean_id,
                "results": formatted,
                "page": page,
                "total_count": meta.get("count") or len(formatted)
            }
