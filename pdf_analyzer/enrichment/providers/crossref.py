import httpx
from typing import List, Dict, Any, Optional, Tuple
from enrichment.providers.base import AcademicProvider
from enrichment.parser import ParsedReference
from enrichment.string_utils import parse_author_name
from enrichment.config import config
from enrichment.storage import storage

class CrossrefProvider(AcademicProvider):
    BASE_URL = "https://api.crossref.org"

    @property
    def name(self) -> str:
        return "crossref"

    def _get_headers_and_params(self, params: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, Any]]:
        mailto = config.crossref_mailto or config.openalex_email
        headers = {
            "User-Agent": "Journal2LaTeX-PDFAnalyzer/1.0 (https://github.com/yossef-ayman/Journal2LaTeX)"
        }
        if mailto:
            headers["User-Agent"] += f" (mailto:{mailto})"
            params["mailto"] = mailto
        return headers, params

    async def search_reference(self, reference: ParsedReference) -> List[Dict[str, Any]]:
        """
        Multi-Strategy Search in Crossref API:
        Strategy 1: Direct DOI lookup if DOI is present.
        Strategy 2: query.title
        Strategy 3: query.title + query.author
        Strategy 4: query.bibliographic
        Saves raw payloads and normalized structures.
        """
        candidates_map: Dict[str, Dict[str, Any]] = {}

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Strategy 1: Direct DOI lookup
            if reference.doi:
                doi_clean = reference.doi.lower().replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
                query_key = f"doi:{doi_clean}"
                params: Dict[str, Any] = {}
                headers, params = self._get_headers_and_params(params)
                try:
                    res = await client.get(f"{self.BASE_URL}/works/{doi_clean}", params=params, headers=headers)
                    if res.status_code == 200:
                        raw_data = res.json()
                        item = raw_data.get("message", {})
                        raw_file = storage.save_raw(self.name, query_key, raw_data, status_code=200, candidate_count=1 if item else 0)
                        parsed_item = self._format_item(item, raw_file=raw_file)
                        if parsed_item:
                            key = parsed_item["doi"] or parsed_item["title"]
                            candidates_map[key] = parsed_item
                            storage.save_normalized(self.name, query_key, [parsed_item])
                except Exception:
                    pass

            # Strategy 2: query.title
            if reference.title:
                query_key = f"title:{reference.title.strip()}"
                params = {"query.title": reference.title, "rows": 10}
                headers, params = self._get_headers_and_params(params)
                try:
                    res = await client.get(f"{self.BASE_URL}/works", params=params, headers=headers)
                    if res.status_code == 200:
                        raw_data = res.json()
                        items = raw_data.get("message", {}).get("items", [])
                        raw_file = storage.save_raw(self.name, query_key, raw_data, status_code=200, candidate_count=len(items))
                        formatted_items = []
                        for item in items:
                            parsed_item = self._format_item(item, raw_file=raw_file)
                            if parsed_item:
                                key = parsed_item["doi"] or parsed_item["title"]
                                if key not in candidates_map:
                                    candidates_map[key] = parsed_item
                                formatted_items.append(parsed_item)
                        storage.save_normalized(self.name, query_key, formatted_items)
                except Exception:
                    pass

            # Strategy 3: query.title + query.author
            first_author = ""
            if reference.authors:
                first_author = reference.authors[0].get("family") or reference.authors[0].get("name") or ""
            elif reference.raw_authors:
                first_author = reference.raw_authors[0]

            if reference.title and first_author:
                query_str = f"{reference.title} {first_author}"
                query_key = f"title_author:{query_str.strip()}"
                params = {"query.title": reference.title, "query.author": first_author, "rows": 10}
                headers, params = self._get_headers_and_params(params)
                try:
                    res = await client.get(f"{self.BASE_URL}/works", params=params, headers=headers)
                    if res.status_code == 200:
                        raw_data = res.json()
                        items = raw_data.get("message", {}).get("items", [])
                        raw_file = storage.save_raw(self.name, query_key, raw_data, status_code=200, candidate_count=len(items))
                        formatted_items = []
                        for item in items:
                            parsed_item = self._format_item(item, raw_file=raw_file)
                            if parsed_item:
                                key = parsed_item["doi"] or parsed_item["title"]
                                if key not in candidates_map:
                                    candidates_map[key] = parsed_item
                                formatted_items.append(parsed_item)
                        storage.save_normalized(self.name, query_key, formatted_items)
                except Exception:
                    pass

            # Strategy 4: query.bibliographic
            if reference.title:
                bib_query = f"{reference.title} {first_author} {reference.year or ''}".strip()
                query_key = f"bib:{bib_query}"
                params = {"query.bibliographic": bib_query, "rows": 10}
                headers, params = self._get_headers_and_params(params)
                try:
                    res = await client.get(f"{self.BASE_URL}/works", params=params, headers=headers)
                    if res.status_code == 200:
                        raw_data = res.json()
                        items = raw_data.get("message", {}).get("items", [])
                        raw_file = storage.save_raw(self.name, query_key, raw_data, status_code=200, candidate_count=len(items))
                        formatted_items = []
                        for item in items:
                            parsed_item = self._format_item(item, raw_file=raw_file)
                            if parsed_item:
                                key = parsed_item["doi"] or parsed_item["title"]
                                if key not in candidates_map:
                                    candidates_map[key] = parsed_item
                                formatted_items.append(parsed_item)
                        storage.save_normalized(self.name, query_key, formatted_items)
                except Exception:
                    pass

        return list(candidates_map.values())

    def _format_item(self, item: Dict[str, Any], raw_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Convert Crossref work item to standardized candidate dict."""
        if not item:
            return None

        # Title
        titles = item.get("title") or []
        title = titles[0] if titles else ""

        # Authors
        authors: List[Dict[str, str]] = []
        raw_authors = item.get("author") or []
        for a in raw_authors:
            given = a.get("given") or ""
            family = a.get("family") or ""
            name = f"{given} {family}".strip() if given or family else a.get("name") or ""
            if name:
                authors.append({
                    "name": name,
                    "given": given,
                    "family": family,
                    "author_id": "",
                    "source": self.name,
                    "author_match_status": "ambiguous"
                })

        # Publication Year
        year = None
        created_parts = item.get("published-print", {}).get("date-parts") or \
                        item.get("published-online", {}).get("date-parts") or \
                        item.get("issued", {}).get("date-parts") or []
        if created_parts and len(created_parts[0]) > 0:
            year = int(created_parts[0][0])

        # Journal / Container Title
        container = item.get("container-title") or []
        journal = container[0] if container else (item.get("publisher") or "")

        # DOI & URL
        doi = item.get("DOI") or ""
        url = item.get("URL") or (f"https://doi.org/{doi}" if doi else "")

        citation_count = item.get("is-referenced-by-count")

        return {
            "title": title,
            "authors": authors,
            "year": year,
            "journal": journal,
            "doi": doi,
            "url": url,
            "openalex_id": "",
            "citation_count": citation_count if citation_count is not None else 0,
            "source": self.name,
            "raw_file": raw_file
        }
