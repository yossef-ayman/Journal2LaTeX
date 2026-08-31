import re
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx

from enrichment.providers.base import AcademicProvider
from enrichment.parser import ParsedReference
from enrichment.config import config
from enrichment.string_utils import parse_author_name
from enrichment.storage import storage


class GoogleScholarProvider(AcademicProvider):
    """
    AcademicProvider for Google Scholar reference search via SerpApi
    with full raw response persistence, normalized data extraction, and citation exploration.
    """
    BASE_URL = "https://serpapi.com/search.json"

    @property
    def name(self) -> str:
        return "google_scholar"

    def build_query(self, reference: ParsedReference) -> str:
        """
        Build optimized search query for Google Scholar in priority order:
        1. Exact DOI if present.
        2. Exact title.
        3. Title + First Author.
        4. Title + Year.
        """
        if reference.doi:
            doi_clean = reference.doi.lower().replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
            return f"doi:{doi_clean}"

        first_author = ""
        if reference.authors:
            first_author = reference.authors[0].get("family") or reference.authors[0].get("name") or ""
        elif reference.raw_authors:
            first_author = reference.raw_authors[0]

        if reference.title:
            clean_title = reference.title.strip()
            if first_author:
                return f"{clean_title} {first_author}"
            if reference.year:
                return f"{clean_title} {reference.year}"
            return clean_title

        raw_clean = re.sub(r"^(?:\[\d+\]|\(\d+\)|\d+\.)\s*", "", reference.original_text or "").strip()
        return raw_clean[:120]

    async def search_query(self, query: str, num: int = 10) -> Dict[str, Any]:
        """
        Direct search query execution against SerpApi Google Scholar engine.
        Returns complete normalized schema with raw file links.
        """
        clean_q = (query or "").strip()
        if not clean_q:
            return {
                "provider": self.name,
                "available": False,
                "reason": "EMPTY_QUERY",
                "query": "",
                "results": [],
                "searched_at": datetime.now(timezone.utc).isoformat()
            }

        scholar_search_url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(clean_q)}"
        api_key = config.serpapi_key

        if not api_key:
            normalized_fallback = {
                "provider": self.name,
                "available": False,
                "reason": "SERPAPI_KEY_NOT_CONFIGURED",
                "query": clean_q,
                "scholar_url": scholar_search_url,
                "searched_at": datetime.now(timezone.utc).isoformat(),
                "results": []
            }
            norm_path = storage.save_normalized(self.name, f"search:{clean_q}", normalized_fallback)
            normalized_fallback["normalized_file"] = norm_path
            return normalized_fallback

        params = {
            "engine": "google_scholar",
            "q": clean_q,
            "api_key": api_key,
            "num": min(max(1, num), 20),
            "hl": "en"
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.get(self.BASE_URL, params=params)
                status_code = res.status_code
                if status_code != 200:
                    err_json = {}
                    try:
                        err_json = res.json()
                    except Exception:
                        pass
                    raw_file = storage.save_raw(self.name, f"search:{clean_q}", err_json or {"error": res.text[:500]}, status_code=status_code)
                    return {
                        "provider": self.name,
                        "available": False,
                        "error": {"status_code": status_code, "detail": err_json.get("error") or "SerpApi request failed"},
                        "query": clean_q,
                        "scholar_url": scholar_search_url,
                        "raw_file": raw_file,
                        "results": [],
                        "searched_at": datetime.now(timezone.utc).isoformat()
                    }

                data = res.json()
                organic = data.get("organic_results") or []
                raw_file = storage.save_raw(self.name, f"search:{clean_q}", data, status_code=200, candidate_count=len(organic))

                normalized_results = self._normalize_organic_results(organic, clean_q, scholar_search_url)

                normalized_payload = {
                    "provider": self.name,
                    "available": True,
                    "query": clean_q,
                    "scholar_url": scholar_search_url,
                    "results_count": len(normalized_results),
                    "results": normalized_results,
                    "pagination": data.get("pagination") or {},
                    "raw_file": raw_file,
                    "searched_at": datetime.now(timezone.utc).isoformat()
                }

                norm_file = storage.save_normalized(self.name, f"search:{clean_q}", normalized_payload)
                normalized_payload["normalized_file"] = norm_file
                return normalized_payload

            except Exception as exc:
                err_payload = {"error_type": type(exc).__name__, "message": str(exc)}
                raw_file = storage.save_raw(self.name, f"search:{clean_q}", err_payload, status_code=500)
                return {
                    "provider": self.name,
                    "available": False,
                    "error": err_payload,
                    "query": clean_q,
                    "scholar_url": scholar_search_url,
                    "raw_file": raw_file,
                    "results": [],
                    "searched_at": datetime.now(timezone.utc).isoformat()
                }

    async def get_citations(self, cluster_id: str, page: int = 1, num: int = 10) -> Dict[str, Any]:
        """
        Explore citing papers for a given Google Scholar cluster ID via SerpApi.
        """
        clean_c = (cluster_id or "").strip()
        if not clean_c:
            return {
                "provider": self.name,
                "available": False,
                "reason": "EMPTY_CLUSTER_ID",
                "cluster_id": "",
                "results": [],
                "searched_at": datetime.now(timezone.utc).isoformat()
            }

        scholar_cites_url = f"https://scholar.google.com/scholar?cites={urllib.parse.quote(clean_c)}"
        api_key = config.serpapi_key

        if not api_key:
            return {
                "provider": self.name,
                "available": False,
                "reason": "SERPAPI_KEY_NOT_CONFIGURED",
                "cluster_id": clean_c,
                "scholar_url": scholar_cites_url,
                "page": page,
                "results_count": 0,
                "results": [],
                "searched_at": datetime.now(timezone.utc).isoformat()
            }

        start = max(0, (page - 1) * num)
        params = {
            "engine": "google_scholar",
            "cites": clean_c,
            "api_key": api_key,
            "start": start,
            "num": min(max(1, num), 20),
            "hl": "en"
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.get(self.BASE_URL, params=params)
                if res.status_code != 200:
                    return {
                        "provider": self.name,
                        "available": False,
                        "error": {"status_code": res.status_code, "detail": "SerpApi cites request failed"},
                        "cluster_id": clean_c,
                        "scholar_url": scholar_cites_url,
                        "page": page,
                        "results": [],
                        "searched_at": datetime.now(timezone.utc).isoformat()
                    }

                data = res.json()
                organic = data.get("organic_results") or []
                raw_file = storage.save_raw(self.name, f"cites:{clean_c}:p{page}", data, status_code=200, candidate_count=len(organic))
                normalized_results = self._normalize_organic_results(organic, f"cites:{clean_c}", scholar_cites_url)

                payload = {
                    "provider": self.name,
                    "available": True,
                    "cluster_id": clean_c,
                    "scholar_url": scholar_cites_url,
                    "page": page,
                    "results_count": len(normalized_results),
                    "results": normalized_results,
                    "pagination": data.get("pagination") or {},
                    "raw_file": raw_file,
                    "searched_at": datetime.now(timezone.utc).isoformat()
                }
                storage.save_normalized(self.name, f"cites:{clean_c}:p{page}", payload)
                return payload
            except Exception as exc:
                return {
                    "provider": self.name,
                    "available": False,
                    "error": {"error_type": type(exc).__name__, "message": str(exc)},
                    "cluster_id": clean_c,
                    "scholar_url": scholar_cites_url,
                    "page": page,
                    "results": [],
                    "searched_at": datetime.now(timezone.utc).isoformat()
                }

    def _normalize_organic_results(self, organic: List[Dict[str, Any]], query: str, default_url: str) -> List[Dict[str, Any]]:
        """Extract and normalize all fields from SerpApi organic_results safely."""
        results = []
        for item in organic:
            if not isinstance(item, dict):
                continue

            title = item.get("title") or ""
            link = item.get("link") or default_url
            snippet = item.get("snippet") or ""
            pub_info = item.get("publication_info") or {}
            summary = pub_info.get("summary") or ""

            # Authors
            authors = []
            raw_authors = pub_info.get("authors") or []
            for a in raw_authors:
                if isinstance(a, dict) and a.get("name"):
                    authors.append({
                        "name": a["name"],
                        "author_id": a.get("author_id"),
                        "link": a.get("link")
                    })
                elif isinstance(a, str) and a.strip():
                    authors.append({
                        "name": a.strip(),
                        "author_id": None,
                        "link": None
                    })

            # Year extraction from publication_info summary
            year = None
            if summary:
                year_match = re.search(r"\b(1[89]\d\d|20\d\d)\b", summary)
                if year_match:
                    year = int(year_match.group(1))

            # Citations (cited_by)
            inline = item.get("inline_links") or {}
            cited_by = inline.get("cited_by")
            citation_count = None
            citation_link = None
            if isinstance(cited_by, dict):
                citation_count = cited_by.get("total")
                citation_link = cited_by.get("link")

            # Versions
            versions_obj = inline.get("versions")
            versions_count = None
            versions_link = None
            if isinstance(versions_obj, dict):
                versions_count = versions_obj.get("total")
                versions_link = versions_obj.get("link")

            # Resources (PDFs, HTML articles)
            resources = []
            raw_resources = item.get("resources") or []
            for r in raw_resources:
                if isinstance(r, dict):
                    resources.append({
                        "title": r.get("title") or "Resource",
                        "link": r.get("link") or "",
                        "file_format": r.get("file_format")
                    })

            # Related articles
            related_link = inline.get("related_pages_link")

            results.append({
                "position": item.get("position"),
                "result_id": item.get("result_id"),
                "title": title,
                "link": link,
                "snippet": snippet,
                "publication": {
                    "summary": summary,
                    "year": year,
                    "venue": summary.split(" - ")[-1] if " - " in summary else summary
                },
                "authors": authors,
                "citations": {
                    "count": citation_count,
                    "link": citation_link
                },
                "versions": {
                    "count": versions_count,
                    "link": versions_link
                },
                "resources": resources,
                "related_articles": {
                    "link": related_link
                },
                "cluster_id": item.get("cluster_id")
            })

        return results

    async def search_reference(self, reference: ParsedReference) -> List[Dict[str, Any]]:
        """
        Search reference on Google Scholar and return standard candidates for ReferenceMatcher.
        Preserves raw and normalized responses.
        """
        query = self.build_query(reference)
        if not query:
            return []

        search_data = await self.search_query(query, num=5)
        scholar_search_url = search_data.get("scholar_url") or f"https://scholar.google.com/scholar?q={urllib.parse.quote(query)}"

        if not search_data.get("available"):
            # Fallback candidate when SerpApi key is unconfigured or failed
            return [{
                "title": reference.title or query[:80],
                "authors": reference.authors,
                "year": reference.year,
                "journal": reference.journal or None,
                "doi": reference.doi,
                "url": scholar_search_url,
                "citation_count": None,
                "source": self.name,
                "scholar_url": scholar_search_url,
                "available": False,
                "reason": search_data.get("reason") or "UNAVAILABLE",
                "raw_file": search_data.get("raw_file"),
                "normalized_file": search_data.get("normalized_file")
            }]

        results = search_data.get("results") or []
        candidates = []

        for r in results:
            # Map normalized authors to parsed_author dict format for matcher compatibility
            cand_authors = []
            for a in r.get("authors") or []:
                p_auth = parse_author_name(a["name"])
                p_auth["author_id"] = a.get("author_id") or ""
                p_auth["source"] = self.name
                cand_authors.append(p_auth)

            candidates.append({
                "title": r.get("title") or reference.title,
                "authors": cand_authors or reference.authors,
                "year": r.get("publication", {}).get("year") or reference.year,
                "journal": r.get("publication", {}).get("venue") or reference.journal or None,
                "doi": reference.doi,
                "url": r.get("link") or scholar_search_url,
                "citation_count": r.get("citations", {}).get("count"),
                "source": self.name,
                "scholar_url": r.get("link") or scholar_search_url,
                "cluster_id": r.get("cluster_id"),
                "cited_by_url": r.get("citations", {}).get("link"),
                "versions_count": r.get("versions", {}).get("count"),
                "available": True,
                "raw_file": search_data.get("raw_file"),
                "normalized_file": search_data.get("normalized_file"),
                "normalized_result": r
            })

        return candidates
