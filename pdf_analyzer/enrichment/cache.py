import threading
from typing import Dict, Any, Optional
from enrichment.string_utils import normalize_string
from enrichment.config import config

class ReferenceCache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _make_key(self, doi: Optional[str], title: Optional[str]) -> Optional[str]:
        if doi and doi.strip():
            clean_doi = doi.lower().replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
            return f"doi:{clean_doi}"
        if title and title.strip():
            norm_title = normalize_string(title)
            if len(norm_title) > 5:
                return f"title:{norm_title}"
        return None

    def get(self, doi: Optional[str], title: Optional[str]) -> Optional[Dict[str, Any]]:
        if not config.cache_enabled:
            return None
        key = self._make_key(doi, title)
        if not key:
            return None
        with self._lock:
            return self._cache.get(key)

    def put(self, doi: Optional[str], title: Optional[str], result: Dict[str, Any]) -> None:
        if not config.cache_enabled:
            return
        key = self._make_key(doi, title)
        if not key:
            return
        with self._lock:
            self._cache[key] = result

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

cache = ReferenceCache()
