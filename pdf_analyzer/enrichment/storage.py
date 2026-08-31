import os
import json
import sqlite3
import hashlib
import tempfile
import threading
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

PROJECTS_DIR = os.path.join(DATA_DIR, "projects")
REFERENCES_DIR = os.path.join(DATA_DIR, "references")
PAPERS_DIR = os.path.join(DATA_DIR, "papers")
AUTHORS_DIR = os.path.join(DATA_DIR, "authors")
RAW_DIR = os.path.join(DATA_DIR, "raw")
NORMALIZED_DIR = os.path.join(DATA_DIR, "normalized")
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")

DB_PATH = os.path.join(DATA_DIR, "cache.db")


def _ensure_directories():
    """Ensure all standard storage directories exist."""
    dirs = [
        DATA_DIR,
        PROJECTS_DIR,
        REFERENCES_DIR,
        PAPERS_DIR,
        AUTHORS_DIR,
        RAW_DIR,
        os.path.join(RAW_DIR, "openalex"),
        os.path.join(RAW_DIR, "crossref"),
        os.path.join(RAW_DIR, "google_scholar"),
        NORMALIZED_DIR,
        os.path.join(NORMALIZED_DIR, "openalex"),
        os.path.join(NORMALIZED_DIR, "crossref"),
        os.path.join(NORMALIZED_DIR, "google_scholar"),
        EXPORTS_DIR
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def hash_key(key: str) -> str:
    """Generate deterministic SHA256 hex digest for any string key."""
    clean_k = (key or "").strip().lower()
    return hashlib.sha256(clean_k.encode("utf-8")).hexdigest()[:16]


def safe_filename(name: str) -> str:
    """Convert arbitrary identifiers (e.g. DOIs, URLs) to filesystem-safe string."""
    clean = (name or "").strip()
    clean = clean.replace("https://", "").replace("http://", "")
    clean = clean.replace("openalex.org/", "").replace("doi.org/", "")
    clean = clean.replace("/", "_").replace(":", "_").replace("?", "_").replace("&", "_")
    return "".join(c for c in clean if c.isalnum() or c in ("-", "_", ".")).strip("._") or "unnamed"


def _atomic_write_json(file_path: str, data: Any) -> None:
    """Safely write JSON to disk atomically using temporary file rename."""
    parent_dir = os.path.dirname(file_path)
    os.makedirs(parent_dir, exist_ok=True)
    
    # Write to a temp file in the same directory to guarantee atomic rename on POSIX/Windows
    with tempfile.NamedTemporaryFile("w", dir=parent_dir, delete=False, encoding="utf-8") as tf:
        temp_name = tf.name
        json.dump(data, tf, indent=2, ensure_ascii=False)
        tf.flush()
        os.fsync(tf.fileno())

    # Atomic replace
    os.replace(temp_name, file_path)


def _safe_read_json(file_path: str) -> Optional[Dict[str, Any]]:
    """Safely read JSON file from disk."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


class StorageEngine:
    """
    Core persistence engine providing:
    1. Structured atomic JSON storage for Raw, Normalized, Master References, Papers, Authors, and Projects.
    2. SQLite indexing/caching (data/cache.db) for ultra-fast lookups without replacing JSON files as primary truth.
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        _ensure_directories()
        self._init_sqlite()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self):
        """Initialize SQLite index tables."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # 1. Projects index
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS projects_idx (
                        project_id TEXT PRIMARY KEY,
                        filename TEXT,
                        sha256 TEXT,
                        total_references INTEGER,
                        file_path TEXT,
                        created_at TEXT
                    )
                """)
                # 2. References index
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS references_idx (
                        ref_id TEXT PRIMARY KEY,
                        project_id TEXT,
                        canonical_title TEXT,
                        canonical_doi TEXT,
                        confidence REAL,
                        file_path TEXT,
                        created_at TEXT
                    )
                """)
                # 3. Papers index
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS papers_idx (
                        paper_id TEXT PRIMARY KEY,
                        title TEXT,
                        doi TEXT,
                        arxiv_id TEXT,
                        openalex_id TEXT,
                        file_path TEXT,
                        created_at TEXT
                    )
                """)
                # 4. Authors index
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS authors_idx (
                        author_id TEXT PRIMARY KEY,
                        name TEXT,
                        openalex_id TEXT,
                        scholar_id TEXT,
                        file_path TEXT,
                        created_at TEXT
                    )
                """)
                # 5. Raw cache index (for fast TTL/provider cache checks)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS raw_cache_idx (
                        cache_key TEXT PRIMARY KEY,
                        provider TEXT,
                        query TEXT,
                        status_code INTEGER,
                        candidate_count INTEGER,
                        file_path TEXT,
                        created_at TEXT
                    )
                """)
                conn.commit()

    # ==========================================
    # 1. RAW PROVIDER STORAGE
    # ==========================================
    def save_raw(self, provider: str, query_key: str, data: Any, status_code: int = 200, candidate_count: int = 0) -> str:
        """Save unmodified raw provider payload to disk and index in SQLite."""
        prov = provider.lower().strip()
        h_key = hash_key(f"{prov}:{query_key}")
        prov_dir = os.path.join(RAW_DIR, prov)
        os.makedirs(prov_dir, exist_ok=True)
        file_path = os.path.join(prov_dir, f"{h_key}.json")

        wrapped_payload = {
            "provider": prov,
            "query_key": query_key,
            "query_hash": h_key,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "status_code": status_code,
            "candidate_count": candidate_count,
            "raw_response": data
        }

        _atomic_write_json(file_path, wrapped_payload)

        # Index in SQLite
        try:
            rel_path = os.path.relpath(file_path, BASE_DIR).replace("\\", "/")
            with self._lock:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO raw_cache_idx
                        (cache_key, provider, query, status_code, candidate_count, file_path, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (h_key, prov, query_key[:500], status_code, candidate_count, rel_path, wrapped_payload["saved_at"]))
                    conn.commit()
        except Exception:
            pass

        return os.path.relpath(file_path, BASE_DIR).replace("\\", "/")

    def load_raw(self, provider: str, query_key: str) -> Optional[Dict[str, Any]]:
        """Load raw provider payload from disk."""
        prov = provider.lower().strip()
        h_key = hash_key(f"{prov}:{query_key}")
        file_path = os.path.join(RAW_DIR, prov, f"{h_key}.json")
        res = _safe_read_json(file_path)
        if res and "raw_response" in res:
            return res["raw_response"]
        return res

    # ==========================================
    # 2. NORMALIZED PROVIDER STORAGE
    # ==========================================
    def save_normalized(self, provider: str, entity_key: str, data: Any) -> str:
        """Save normalized provider schema to disk."""
        prov = provider.lower().strip()
        h_key = hash_key(f"{prov}:{entity_key}")
        prov_dir = os.path.join(NORMALIZED_DIR, prov)
        os.makedirs(prov_dir, exist_ok=True)
        file_path = os.path.join(prov_dir, f"{h_key}.json")

        wrapped = {
            "provider": prov,
            "entity_key": entity_key,
            "normalized_at": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        _atomic_write_json(file_path, wrapped)
        return os.path.relpath(file_path, BASE_DIR).replace("\\", "/")

    def load_normalized(self, provider: str, entity_key: str) -> Optional[Dict[str, Any]]:
        """Load normalized provider schema from disk."""
        prov = provider.lower().strip()
        h_key = hash_key(f"{prov}:{entity_key}")
        file_path = os.path.join(NORMALIZED_DIR, prov, f"{h_key}.json")
        res = _safe_read_json(file_path)
        if res and "data" in res:
            return res["data"]
        return res

    # ==========================================
    # 3. MASTER REFERENCE STORAGE
    # ==========================================
    def save_reference(self, ref_id: str, data: Dict[str, Any]) -> str:
        """Save Master Reference JSON to disk and update SQLite index."""
        file_path = os.path.join(REFERENCES_DIR, f"{safe_filename(ref_id)}.json")
        _atomic_write_json(file_path, data)

        try:
            rel_path = os.path.relpath(file_path, BASE_DIR).replace("\\", "/")
            canonical = data.get("canonical") or {}
            title_val = canonical.get("title", {}).get("value") if isinstance(canonical.get("title"), dict) else str(canonical.get("title") or "")
            doi_val = canonical.get("identifiers", {}).get("doi", {}).get("value") if isinstance(canonical.get("identifiers", {}).get("doi"), dict) else ""
            quality = data.get("quality") or {}
            conf = quality.get("overall_confidence", 0.0)
            proj_id = data.get("project_id", "")
            now_iso = data.get("created_at") or datetime.now(timezone.utc).isoformat()

            with self._lock:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO references_idx
                        (ref_id, project_id, canonical_title, canonical_doi, confidence, file_path, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (ref_id, proj_id, title_val[:500], doi_val, conf, rel_path, now_iso))
                    conn.commit()
        except Exception:
            pass

        return os.path.relpath(file_path, BASE_DIR).replace("\\", "/")

    def load_reference(self, ref_id: str) -> Optional[Dict[str, Any]]:
        """Load Master Reference JSON from disk."""
        file_path = os.path.join(REFERENCES_DIR, f"{safe_filename(ref_id)}.json")
        return _safe_read_json(file_path)

    # ==========================================
    # 4. PAPER STORAGE
    # ==========================================
    def save_paper(self, paper_id: str, data: Dict[str, Any]) -> str:
        """Save canonical Paper record to disk and index in SQLite."""
        file_path = os.path.join(PAPERS_DIR, f"{safe_filename(paper_id)}.json")
        _atomic_write_json(file_path, data)

        try:
            rel_path = os.path.relpath(file_path, BASE_DIR).replace("\\", "/")
            title = data.get("title") or ""
            doi = data.get("doi") or ""
            arxiv = data.get("arxiv_id") or ""
            openalex = data.get("openalex_id") or ""
            now_iso = data.get("saved_at") or datetime.now(timezone.utc).isoformat()

            with self._lock:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO papers_idx
                        (paper_id, title, doi, arxiv_id, openalex_id, file_path, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (paper_id, title[:500], doi, arxiv, openalex, rel_path, now_iso))
                    conn.commit()
        except Exception:
            pass

        return os.path.relpath(file_path, BASE_DIR).replace("\\", "/")

    def load_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Load Paper record from disk."""
        file_path = os.path.join(PAPERS_DIR, f"{safe_filename(paper_id)}.json")
        return _safe_read_json(file_path)

    # ==========================================
    # 5. AUTHOR STORAGE
    # ==========================================
    def save_author(self, author_id: str, data: Dict[str, Any]) -> str:
        """Save aggregated Author record to disk and index in SQLite."""
        file_path = os.path.join(AUTHORS_DIR, f"{safe_filename(author_id)}.json")
        _atomic_write_json(file_path, data)

        try:
            rel_path = os.path.relpath(file_path, BASE_DIR).replace("\\", "/")
            identity = data.get("identity") or {}
            name = identity.get("name") or data.get("name") or data.get("display_name") or ""
            openalex_id = identity.get("openalex_id") or ""
            scholar_id = identity.get("google_scholar_id") or ""
            now_iso = data.get("saved_at") or datetime.now(timezone.utc).isoformat()

            with self._lock:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO authors_idx
                        (author_id, name, openalex_id, scholar_id, file_path, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (author_id, name[:300], openalex_id, scholar_id, rel_path, now_iso))
                    conn.commit()
        except Exception:
            pass

        return os.path.relpath(file_path, BASE_DIR).replace("\\", "/")

    def load_author(self, author_id: str) -> Optional[Dict[str, Any]]:
        """Load Author record from disk."""
        file_path = os.path.join(AUTHORS_DIR, f"{safe_filename(author_id)}.json")
        return _safe_read_json(file_path)

    # ==========================================
    # 6. PROJECT STORAGE
    # ==========================================
    def save_project(self, project_id: str, data: Dict[str, Any]) -> str:
        """Save entire PDF Analysis Project record to disk and update SQLite index."""
        file_path = os.path.join(PROJECTS_DIR, f"{safe_filename(project_id)}.json")
        _atomic_write_json(file_path, data)

        try:
            rel_path = os.path.relpath(file_path, BASE_DIR).replace("\\", "/")
            pdf_info = data.get("input_pdf") or {}
            fn = pdf_info.get("filename") or ""
            sha = pdf_info.get("sha256") or ""
            stats = data.get("statistics") or {}
            total_refs = stats.get("total_references") or len(data.get("references") or [])
            now_iso = data.get("created_at") or datetime.now(timezone.utc).isoformat()

            with self._lock:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO projects_idx
                        (project_id, filename, sha256, total_references, file_path, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (project_id, fn[:300], sha, total_refs, rel_path, now_iso))
                    conn.commit()
        except Exception:
            pass

        return os.path.relpath(file_path, BASE_DIR).replace("\\", "/")

    def load_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Load Project record from disk."""
        file_path = os.path.join(PROJECTS_DIR, f"{safe_filename(project_id)}.json")
        return _safe_read_json(file_path)

    def list_projects(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recently analyzed projects from SQLite index."""
        with self._lock:
            with self._get_connection() as conn:
                rows = conn.execute("""
                    SELECT project_id, filename, sha256, total_references, file_path, created_at
                    FROM projects_idx
                    ORDER BY created_at DESC LIMIT ?
                """, (limit,)).fetchall()
                return [dict(r) for r in rows]

    def get_stats(self) -> Dict[str, int]:
        """Return counts of saved entities across disk indexes."""
        with self._lock:
            with self._get_connection() as conn:
                p_cnt = conn.execute("SELECT COUNT(*) FROM projects_idx").fetchone()[0]
                r_cnt = conn.execute("SELECT COUNT(*) FROM references_idx").fetchone()[0]
                pa_cnt = conn.execute("SELECT COUNT(*) FROM papers_idx").fetchone()[0]
                a_cnt = conn.execute("SELECT COUNT(*) FROM authors_idx").fetchone()[0]
                raw_cnt = conn.execute("SELECT COUNT(*) FROM raw_cache_idx").fetchone()[0]
                return {
                    "projects": p_cnt,
                    "references": r_cnt,
                    "papers": pa_cnt,
                    "authors": a_cnt,
                    "raw_responses": raw_cnt
                }


# Global singleton storage instance
storage = StorageEngine()
