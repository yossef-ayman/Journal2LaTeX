import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from enrichment.config import config

class AuthorProvider(ABC):
    """
    Abstract Base Class for Author Profile and Works Providers (OpenAlex, Google Scholar, etc.).
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def get_author(self, author_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_author_works(self, author_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        pass

class OpenAlexAuthorProvider(AuthorProvider):
    BASE_URL = "https://api.openalex.org"
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0
    TIMEOUT = 12.0

    @property
    def name(self) -> str:
        return "openalex"

    def _clean_author_id(self, author_id: str) -> str:
        """Extract clean OpenAlex author ID (e.g., A5103024730)."""
        if not author_id:
            return ""
        clean = author_id.strip()
        clean = clean.replace("https://openalex.org/", "").replace("http://openalex.org/", "")
        clean = clean.replace("authors/", "").replace("openalex:", "")
        clean = clean.strip("/")
        return clean

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": "Journal2LaTeX-PDFAnalyzer/1.0 (https://github.com/yossef-ayman/Journal2LaTeX)"
        }
        if config.openalex_email:
            headers["User-Agent"] += f" (mailto:{config.openalex_email})"
        if config.openalex_api_key:
            headers["Authorization"] = f"Bearer {config.openalex_api_key}"
        return headers

    def _get_params(self, base_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = dict(base_params or {})
        if config.openalex_email and "mailto" not in params:
            params["mailto"] = config.openalex_email
        return params

    async def _safe_get(self, client: httpx.AsyncClient, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        full_params = self._get_params(params)

        backoff = self.INITIAL_BACKOFF
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                res = await client.get(url, params=full_params, headers=headers, timeout=self.TIMEOUT)
                if res.status_code == 200:
                    return res.json()
                elif res.status_code == 404:
                    return None
                elif res.status_code in (429, 500, 502, 503, 504):
                    await asyncio.sleep(backoff)
                    backoff *= 1.5
                else:
                    return None
            except Exception:
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(backoff)
                    backoff *= 1.5
                else:
                    return None
        return None

    async def get_author(self, author_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch author profile metadata from OpenAlex API.
        If author_id is an OpenAlex ID (A...), queries /authors/{id}.
        If author_id is a person name, searches /authors?search={name}.
        """
        clean_id = self._clean_author_id(author_id)
        if not clean_id:
            return None

        async with httpx.AsyncClient() as client:
            # 1. Direct ID lookup
            if clean_id.startswith("A") and len(clean_id) > 5 and clean_id[1:].isdigit():
                data = await self._safe_get(client, f"authors/{clean_id}", {})
                if data and isinstance(data, dict) and data.get("id"):
                    return self._format_author_profile(data)

            # 2. Name search fallback
            search_name = author_id.strip()
            data = await self._safe_get(client, "authors", {"search": search_name, "per_page": 5})
            if data and isinstance(data, dict):
                results = data.get("results") or []
                if results:
                    return self._format_author_profile(results[0])

        return None

    def _format_author_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OpenAlex author object to standardized format."""
        summary_stats = data.get("summary_stats") or {}
        
        # Extract affiliations from last_known_institutions
        affiliations = []
        institutions = data.get("last_known_institutions") or []
        for inst in institutions:
            if isinstance(inst, dict) and inst.get("display_name"):
                country = inst.get("country_code")
                display = inst["display_name"]
                if country:
                    display += f" ({country})"
                affiliations.append(display)

        # Extract topics
        topics = []
        topic_objs = data.get("topics") or []
        for top in topic_objs:
            if isinstance(top, dict) and top.get("display_name"):
                topics.append(top["display_name"])

        author_id_str = data.get("id") or ""
        orcid = data.get("orcid") or ""

        return {
            "id": author_id_str,
            "name": data.get("display_name") or "",
            "display_name": data.get("display_name") or "",
            "identifiers": {
                "openalex_id": author_id_str or None,
                "orcid": orcid or None,
                "google_scholar_id": None
            },
            "works_count": data.get("works_count") or 0,
            "cited_by_count": data.get("cited_by_count") or 0,
            "h_index": summary_stats.get("h_index"),
            "i10_index": summary_stats.get("i10_index"),
            "affiliations": affiliations,
            "topics": topics,
            "source": self.name
        }

    async def get_author_works(self, author_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Fetch paginated works for an author from OpenAlex API."""
        clean_id = self._clean_author_id(author_id)
        empty_res = {"results": [], "page": page, "per_page": per_page, "total_count": 0}

        if not clean_id:
            return empty_res

        # If not direct A ID, resolve author first
        if not (clean_id.startswith("A") and len(clean_id) > 5 and clean_id[1:].isdigit()):
            resolved = await self.get_author(author_id)
            if resolved and resolved.get("id"):
                clean_id = self._clean_author_id(resolved["id"])
            else:
                return empty_res

        params: Dict[str, Any] = {
            "filter": f"author.id:{clean_id}",
            "page": page,
            "per_page": per_page
        }

        async with httpx.AsyncClient() as client:
            data = await self._safe_get(client, "works", params)
            if not data or not isinstance(data, dict):
                return empty_res

            meta = data.get("meta") or {}
            raw_results = data.get("results") or []

            works = []
            for w in raw_results:
                title = w.get("title") or w.get("display_name") or ""
                year = w.get("publication_year")
                doi = w.get("doi") or ""
                if doi:
                    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
                    url = f"https://doi.org/{doi}"
                else:
                    primary_loc = w.get("primary_location") or {}
                    url = primary_loc.get("landing_page_url") or w.get("id") or ""

                citation_count = w.get("cited_by_count") or 0

                works.append({
                    "title": title,
                    "year": year,
                    "doi": doi,
                    "url": url,
                    "citation_count": citation_count
                })

            return {
                "results": works,
                "page": page,
                "per_page": per_page,
                "total_count": meta.get("count") or len(works)
            }

class GoogleScholarAuthorProvider(AuthorProvider):
    """
    AuthorProvider for Google Scholar via SerpApi.
    Supports author profile queries, citation indices (h-index, i10-index), co-authors, and articles.
    """
    BASE_URL = "https://serpapi.com/search.json"

    @property
    def name(self) -> str:
        return "google_scholar"

    def _clean_author_id(self, author_id: str) -> str:
        if not author_id:
            return ""
        clean = author_id.strip()
        clean = clean.replace("https://scholar.google.com/citations?user=", "").replace("http://scholar.google.com/citations?user=", "")
        clean = clean.replace("google_scholar:", "").replace("scholar:", "")
        if "&" in clean:
            clean = clean.split("&")[0]
        return clean.strip("/")

    async def _resolve_author_id_by_name(self, name_query: str, api_key: str, client: httpx.AsyncClient) -> Optional[str]:
        """Search Google Scholar profiles by author name to get SerpApi author_id."""
        try:
            params = {
                "engine": "google_scholar_profiles",
                "mauthors": name_query,
                "api_key": api_key
            }
            res = await client.get(self.BASE_URL, params=params, timeout=10.0)
            if res.status_code == 200:
                data = res.json()
                profiles = data.get("profiles") or []
                if profiles and isinstance(profiles, list):
                    return profiles[0].get("author_id")
        except Exception:
            pass
        return None

    async def get_author(self, author_id: str) -> Optional[Dict[str, Any]]:
        """Fetch Google Scholar author profile metadata via SerpApi."""
        clean_id = self._clean_author_id(author_id)
        api_key = config.serpapi_key

        async with httpx.AsyncClient(timeout=10.0) as client:
            # If clean_id is not a standard Scholar ID (usually ~12 chars) or if key available, attempt name search
            if api_key and (not clean_id or len(clean_id) < 5 or " " in clean_id):
                resolved_id = await self._resolve_author_id_by_name(author_id, api_key, client)
                if resolved_id:
                    clean_id = resolved_id

            if not api_key:
                # Return rich fallback metadata format with direct live profile links
                display_name = author_id if " " in author_id else clean_id
                import urllib.parse
                scholar_url = f"https://scholar.google.com/citations?user={clean_id}" if clean_id and not " " in clean_id else f"https://scholar.google.com/scholar?q=author:%22{urllib.parse.quote(display_name)}%22"
                return {
                    "id": scholar_url,
                    "name": display_name,
                    "display_name": display_name,
                    "works_count": 0,
                    "cited_by_count": 0,
                    "h_index": None,
                    "i10_index": None,
                    "affiliations": ["Google Scholar Profile"],
                    "topics": ["Scholar Search"],
                    "source": self.name,
                    "serpapi_missing_key": True,
                    "scholar_url": scholar_url
                }

            params = {
                "engine": "google_scholar_author",
                "author_id": clean_id,
                "api_key": api_key,
                "hl": "en"
            }

            try:
                res = await client.get(self.BASE_URL, params=params)
                if res.status_code != 200:
                    return None

                data = res.json()
                author_data = data.get("author") or {}
                cited_by_data = data.get("cited_by") or {}
                articles = data.get("articles") or []

                # Parse citations, h-index, i10-index from cited_by.table
                cited_by_count = 0
                h_index = None
                i10_index = None

                table = cited_by_data.get("table") or []
                for row in table:
                    if isinstance(row, dict):
                        if "citations" in row:
                            cited_by_count = row["citations"].get("all") or 0
                        elif "h_index" in row or "indice_h" in row:
                            h_obj = row.get("h_index") or row.get("indice_h") or {}
                            h_index = h_obj.get("all")
                        elif "i10_index" in row or "indice_i10" in row:
                            i10_obj = row.get("i10_index") or row.get("indice_i10") or {}
                            i10_index = i10_obj.get("all")

                # Topics / Interests
                topics = []
                interests = author_data.get("interests") or []
                for item in interests:
                    if isinstance(item, dict) and item.get("title"):
                        topics.append(item["title"])

                # Co-authors
                co_authors = []
                raw_co_authors = data.get("co_authors") or []
                for ca in raw_co_authors:
                    if isinstance(ca, dict) and ca.get("name"):
                        co_authors.append({
                            "name": ca["name"],
                            "author_id": ca.get("author_id") or "",
                            "affiliations": ca.get("affiliations") or "",
                            "thumbnail": ca.get("thumbnail") or ""
                        })

                affils = [author_data["affiliations"]] if author_data.get("affiliations") else []

                return {
                    "id": f"https://scholar.google.com/citations?user={clean_id}",
                    "name": author_data.get("name") or clean_id,
                    "display_name": author_data.get("name") or clean_id,
                    "works_count": len(articles),
                    "cited_by_count": cited_by_count,
                    "h_index": h_index,
                    "i10_index": i10_index,
                    "affiliations": affils,
                    "topics": topics,
                    "co_authors": co_authors,
                    "thumbnail": author_data.get("thumbnail"),
                    "source": self.name,
                    "scholar_url": f"https://scholar.google.com/citations?user={clean_id}"
                }
            except Exception:
                return None

    async def get_author_works(self, author_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Fetch author articles from SerpApi Google Scholar Author API."""
        clean_id = self._clean_author_id(author_id)
        api_key = config.serpapi_key
        empty_res = {"results": [], "page": page, "per_page": per_page, "total_count": 0}

        if not api_key:
            return empty_res

        start = (page - 1) * per_page
        params = {
            "engine": "google_scholar_author",
            "author_id": clean_id,
            "api_key": api_key,
            "start": start,
            "num": per_page,
            "hl": "en"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(self.BASE_URL, params=params)
                if res.status_code != 200:
                    return empty_res

                data = res.json()
                raw_articles = data.get("articles") or []

                works = []
                for a in raw_articles:
                    title = a.get("title") or ""
                    link = a.get("link") or ""
                    year_val = None
                    if a.get("year"):
                        try:
                            year_val = int(a["year"])
                        except ValueError:
                            pass
                    
                    cited_by_obj = a.get("cited_by") or {}
                    citation_count = cited_by_obj.get("value") if isinstance(cited_by_obj, dict) else 0

                    works.append({
                        "title": title,
                        "year": year_val,
                        "doi": "",
                        "url": link,
                        "citation_count": citation_count or 0
                    })

                return {
                    "results": works,
                    "page": page,
                    "per_page": per_page,
                    "total_count": len(works)
                }
            except Exception:
                return empty_res
