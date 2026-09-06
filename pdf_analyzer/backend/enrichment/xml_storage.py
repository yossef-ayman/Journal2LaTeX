import os
import re
import sqlite3
import hashlib
import threading
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
XML_STORE_DIR = os.path.join(DATA_DIR, "xml_store")
DOCUMENTS_XML_DIR = os.path.join(XML_STORE_DIR, "documents")
SEARCHES_XML_DIR = os.path.join(XML_STORE_DIR, "searches")
AUTHORS_XML_DIR = os.path.join(XML_STORE_DIR, "authors")
REFERENCES_XML_DIR = os.path.join(XML_STORE_DIR, "references")
DB_PATH = os.path.join(DATA_DIR, "cache.db")


def _ensure_xml_dirs():
    for d in (XML_STORE_DIR, DOCUMENTS_XML_DIR, SEARCHES_XML_DIR, AUTHORS_XML_DIR, REFERENCES_XML_DIR):
        os.makedirs(d, exist_ok=True)


def compute_bytes_hash(data: bytes) -> str:
    """Compute SHA-256 hash of file bytes."""
    return hashlib.sha256(data).hexdigest()


def compute_query_hash(query: str) -> str:
    """Compute normalized SHA-256 hash for a search query."""
    clean = re.sub(r"\s+", " ", (query or "").strip().lower())
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()[:24]


def safe_xml_text(val: Any) -> str:
    if val is None:
        return ""
    s = str(val)
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", s)


def prettify_xml(elem: ET.Element) -> str:
    raw = ET.tostring(elem, encoding="utf-8")
    parsed = minidom.parseString(raw)
    lines = [l for l in parsed.toprettyxml(indent="  ").split("\n") if l.strip()]
    return "\n".join(lines)


class XMLStorageEngine:
    """
    Centralized XML local caching and archive engine for Journal2LaTeX.
    Provides offline-first XML persistence for PDFs, Search queries, Authors, and References.
    """

    def __init__(self, db_path: str = DB_PATH, xml_dir: Optional[str] = None):
        self.xml_store_dir = xml_dir or XML_STORE_DIR
        self.documents_xml_dir = os.path.join(self.xml_store_dir, "documents")
        self.searches_xml_dir = os.path.join(self.xml_store_dir, "searches")
        self.authors_xml_dir = os.path.join(self.xml_store_dir, "authors")
        self.references_xml_dir = os.path.join(self.xml_store_dir, "references")

        for d in (self.xml_store_dir, self.documents_xml_dir, self.searches_xml_dir, self.authors_xml_dir, self.references_xml_dir):
            os.makedirs(d, exist_ok=True)

        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_sqlite()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self):
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS xml_cache_index (
                            key_type TEXT NOT NULL,
                            lookup_key TEXT NOT NULL,
                            file_path TEXT NOT NULL,
                            title TEXT,
                            item_count INTEGER DEFAULT 0,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            PRIMARY KEY (key_type, lookup_key)
                        )
                    """)
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_xml_lookup ON xml_cache_index(key_type, lookup_key)")
            finally:
                conn.close()

    def _upsert_index(self, key_type: str, lookup_key: str, file_path: str, title: str, count: int = 0):
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        INSERT INTO xml_cache_index (key_type, lookup_key, file_path, title, item_count, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(key_type, lookup_key) DO UPDATE SET
                            file_path = excluded.file_path,
                            title = excluded.title,
                            item_count = excluded.item_count,
                            updated_at = excluded.updated_at
                    """, (key_type, lookup_key, file_path, safe_xml_text(title), count, now, now))
            finally:
                conn.close()

    # =========================================================================
    # 1. DOCUMENT / PDF XML CACHING
    # =========================================================================
    def get_cached_document(self, pdf_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve parsed academic document data from local XML if cached."""
        if not pdf_hash:
            return None
            
        xml_path = os.path.join(self.documents_xml_dir, f"doc_{pdf_hash}.xml")
        if not os.path.exists(xml_path):
            return None

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            meta_el = root.find("metadata")
            if meta_el is None:
                return None

            title = (meta_el.findtext("title") or "").strip()
            journal = (meta_el.findtext("journal") or "").strip()
            doi = (meta_el.findtext("doi") or "").strip() or None
            arxiv_id = (meta_el.findtext("arxiv_id") or "").strip() or None
            page_count_str = meta_el.findtext("page_count") or "1"
            page_count = int(page_count_str) if page_count_str.isdigit() else 1
            abstract = (meta_el.findtext("abstract") or "").strip()

            authors = []
            authors_el = meta_el.find("authors")
            if authors_el is not None:
                for a in authors_el.findall("author"):
                    if a.text and a.text.strip():
                        authors.append(a.text.strip())

            affiliations = []
            affil_el = meta_el.find("affiliations")
            if affil_el is not None:
                for aff in affil_el.findall("affiliation"):
                    if aff.text and aff.text.strip():
                        affiliations.append(aff.text.strip())

            keywords = []
            kw_el = meta_el.find("keywords")
            if kw_el is not None:
                for kw in kw_el.findall("keyword"):
                    if kw.text and kw.text.strip():
                        keywords.append(kw.text.strip())

            headings = []
            struct_el = root.find("structure")
            if struct_el is not None:
                for h in struct_el.findall("heading"):
                    lvl = int(h.attrib.get("level", "2"))
                    pg = int(h.attrib.get("page", "1"))
                    headings.append({"text": (h.text or "").strip(), "level": lvl, "page": pg})

            references = []
            refs_el = root.find("references")
            if refs_el is not None:
                for r in refs_el.findall("reference"):
                    r_id = r.attrib.get("id") or str(len(references) + 1)
                    references.append({"id": r_id, "text": (r.text or "").strip()})

            with open(xml_path, "r", encoding="utf-8") as f:
                raw_xml = f.read()

            return {
                "title": title,
                "journal": journal,
                "doi": doi,
                "arxiv_id": arxiv_id,
                "authors": authors,
                "affiliations": affiliations,
                "abstract": abstract,
                "keywords": keywords,
                "page_count": page_count,
                "headings": headings,
                "references": references,
                "xml": raw_xml,
                "cached": True,
                "cached_xml": xml_path,
                "pdf_hash": pdf_hash
            }
        except Exception:
            return None

    def save_document_xml(self, pdf_hash: str, filename: str, data: Dict[str, Any]) -> str:
        """Save complete academic document structure to XML file linked to PDF hash."""
        xml_path = os.path.join(self.documents_xml_dir, f"doc_{pdf_hash}.xml")
        now = datetime.now(timezone.utc).isoformat()

        root = ET.Element("academic_document", {
            "version": "1.0",
            "hash": pdf_hash,
            "source_filename": safe_xml_text(filename),
            "updated_at": now
        })

        meta_el = ET.SubElement(root, "metadata")
        ET.SubElement(meta_el, "title").text = safe_xml_text(data.get("title", ""))
        ET.SubElement(meta_el, "journal").text = safe_xml_text(data.get("journal", ""))
        if data.get("doi"):
            ET.SubElement(meta_el, "doi").text = safe_xml_text(data["doi"])
        if data.get("arxiv_id"):
            ET.SubElement(meta_el, "arxiv_id").text = safe_xml_text(data["arxiv_id"])
        ET.SubElement(meta_el, "page_count").text = str(data.get("page_count", 1))

        authors_el = ET.SubElement(meta_el, "authors")
        for auth in (data.get("authors") or []):
            name = auth if isinstance(auth, str) else auth.get("name", "Author")
            ET.SubElement(authors_el, "author").text = safe_xml_text(name)

        if data.get("affiliations"):
            affil_el = ET.SubElement(meta_el, "affiliations")
            for aff in data["affiliations"]:
                ET.SubElement(affil_el, "affiliation").text = safe_xml_text(aff)

        if data.get("abstract"):
            ET.SubElement(meta_el, "abstract").text = safe_xml_text(data["abstract"])

        if data.get("keywords"):
            kw_el = ET.SubElement(meta_el, "keywords")
            for kw in data["keywords"]:
                ET.SubElement(kw_el, "keyword").text = safe_xml_text(kw)

        refs_list = data.get("references") or []
        ET.SubElement(meta_el, "references_count").text = str(len(refs_list))

        struct_el = ET.SubElement(root, "structure")
        for h in (data.get("headings") or []):
            h_el = ET.SubElement(struct_el, "heading", {
                "level": str(h.get("level", 2)),
                "page": str(h.get("page", 1))
            })
            h_el.text = safe_xml_text(h.get("text", ""))

        refs_el = ET.SubElement(root, "references")
        for ref in refs_list:
            r_el = ET.SubElement(refs_el, "reference", {"id": str(ref.get("id", ""))})
            r_el.text = safe_xml_text(ref.get("text", ""))

        xml_content = prettify_xml(root)
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        self._upsert_index("document", pdf_hash, xml_path, data.get("title", ""), len(refs_list))
        return xml_path

    # =========================================================================
    # 2. SCHOLAR & TOPIC SEARCH XML CACHING
    # =========================================================================
    def get_cached_search(self, query: str) -> Optional[Dict[str, Any]]:
        """Retrieve search results from local XML archive if query exists."""
        q_hash = compute_query_hash(query)
        xml_path = os.path.join(self.searches_xml_dir, f"search_{q_hash}.xml")
        if not os.path.exists(xml_path):
            return None

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            results = []
            results_el = root.find("results")
            if results_el is not None:
                for item in results_el.findall("item"):
                    title = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    snippet = (item.findtext("snippet") or "").strip()
                    cluster_id = (item.findtext("cluster_id") or "").strip()
                    venue = (item.findtext("venue") or "").strip()
                    year_str = item.findtext("year")
                    year = int(year_str) if year_str and year_str.isdigit() else None

                    authors = []
                    authors_el = item.find("authors")
                    if authors_el is not None:
                        for a in authors_el.findall("author"):
                            a_name = (a.text or "").strip()
                            a_id = a.attrib.get("author_id") or None
                            authors.append({"name": a_name, "author_id": a_id})

                    cites_el = item.find("citations")
                    citations = None
                    if cites_el is not None:
                        cnt_str = cites_el.findtext("count")
                        cnt = int(cnt_str) if cnt_str and cnt_str.isdigit() else None
                        c_link = (cites_el.findtext("link") or "").strip()
                        citations = {"count": cnt, "link": c_link}

                    resources = []
                    res_el = item.find("resources")
                    if res_el is not None:
                        for r in res_el.findall("resource"):
                            r_title = (r.findtext("title") or "").strip()
                            r_link = (r.findtext("link") or "").strip()
                            r_fmt = (r.findtext("format") or "PDF").strip()
                            resources.append({"title": r_title, "link": r_link, "file_format": r_fmt})

                    pos_str = item.attrib.get("position", "0")
                    pos = int(pos_str) if pos_str.isdigit() else 0

                    results.append({
                        "position": pos,
                        "title": title,
                        "link": link,
                        "snippet": snippet,
                        "cluster_id": cluster_id,
                        "venue": venue,
                        "year": year,
                        "authors": authors,
                        "citations": citations,
                        "resources": resources
                    })

            return {
                "query": query,
                "count": len(results),
                "results": results,
                "available": True,
                "provider": "google_scholar",
                "cached": True,
                "source": "local_xml_cache",
                "xml_path": xml_path
            }
        except Exception:
            return None

    def save_search_xml(self, query: str, results: List[Dict[str, Any]], merge: bool = True) -> str:
        """Save or incrementally merge search query results to local XML archive."""
        q_hash = compute_query_hash(query)
        xml_path = os.path.join(self.searches_xml_dir, f"search_{q_hash}.xml")
        now = datetime.now(timezone.utc).isoformat()

        existing_results = []
        if merge and os.path.exists(xml_path):
            prev_data = self.get_cached_search(query)
            if prev_data and prev_data.get("results"):
                existing_results = prev_data["results"]

        seen_keys = set()
        combined = []
        for r in (results + existing_results):
            key = (r.get("title", "").strip().lower(), r.get("link", "").strip().lower())
            if key not in seen_keys:
                seen_keys.add(key)
                combined.append(r)

        root = ET.Element("search_archive", {
            "version": "1.0",
            "query_hash": q_hash,
            "updated_at": now
        })
        ET.SubElement(root, "query").text = safe_xml_text(query)
        ET.SubElement(root, "count").text = str(len(combined))

        results_el = ET.SubElement(root, "results")
        for idx, item in enumerate(combined):
            item_el = ET.SubElement(results_el, "item", {"position": str(idx)})
            ET.SubElement(item_el, "title").text = safe_xml_text(item.get("title", ""))
            ET.SubElement(item_el, "link").text = safe_xml_text(item.get("link", ""))
            ET.SubElement(item_el, "snippet").text = safe_xml_text(item.get("snippet", ""))
            if item.get("cluster_id"):
                ET.SubElement(item_el, "cluster_id").text = safe_xml_text(item["cluster_id"])
            if item.get("venue"):
                ET.SubElement(item_el, "venue").text = safe_xml_text(item["venue"])
            if item.get("year"):
                ET.SubElement(item_el, "year").text = str(item["year"])

            authors = item.get("authors") or []
            if authors:
                auths_el = ET.SubElement(item_el, "authors")
                for a in authors:
                    a_name = a if isinstance(a, str) else a.get("name", "")
                    a_id = "" if isinstance(a, str) else (a.get("author_id") or "")
                    attr = {"author_id": safe_xml_text(a_id)} if a_id else {}
                    a_el = ET.SubElement(auths_el, "author", attr)
                    a_el.text = safe_xml_text(a_name)

            cites = item.get("citations")
            if cites and isinstance(cites, dict):
                cites_el = ET.SubElement(item_el, "citations")
                if cites.get("count") is not None:
                    ET.SubElement(cites_el, "count").text = str(cites["count"])
                if cites.get("link"):
                    ET.SubElement(cites_el, "link").text = safe_xml_text(cites["link"])

            resources = item.get("resources") or []
            if resources:
                res_el = ET.SubElement(item_el, "resources")
                for r in resources:
                    r_el = ET.SubElement(res_el, "resource")
                    ET.SubElement(r_el, "title").text = safe_xml_text(r.get("title", ""))
                    ET.SubElement(r_el, "link").text = safe_xml_text(r.get("link", ""))
                    ET.SubElement(r_el, "format").text = safe_xml_text(r.get("file_format", "PDF"))

        xml_content = prettify_xml(root)
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        self._upsert_index("search", q_hash, xml_path, query, len(combined))
        return xml_path

    # =========================================================================
    # 3. AUTHOR PROFILE XML CACHING
    # =========================================================================
    def get_cached_author(self, author_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached author profile from local XML archive."""
        clean_id = hashlib.sha256(author_id.strip().lower().encode("utf-8")).hexdigest()[:24]
        xml_path = os.path.join(self.authors_xml_dir, f"author_{clean_id}.xml")
        if not os.path.exists(xml_path):
            return None

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            name = (root.findtext("name") or "").strip()
            display_name = (root.findtext("display_name") or name).strip()
            scholar_url = (root.findtext("scholar_url") or "").strip() or None
            orcid = (root.findtext("orcid") or "").strip() or None
            source = (root.findtext("source") or "openalex").strip()

            works_count_str = root.findtext("works_count")
            works_count = int(works_count_str) if works_count_str and works_count_str.isdigit() else None
            cited_str = root.findtext("cited_by_count")
            cited_by_count = int(cited_str) if cited_str and cited_str.isdigit() else None
            h_str = root.findtext("h_index")
            h_index = int(h_str) if h_str and h_str.isdigit() else None
            i10_str = root.findtext("i10_index")
            i10_index = int(i10_str) if i10_str and i10_str.isdigit() else None

            affiliations = []
            aff_el = root.find("affiliations")
            if aff_el is not None:
                for a in aff_el.findall("affiliation"):
                    if a.text:
                        affiliations.append(a.text.strip())

            topics = []
            top_el = root.find("topics")
            if top_el is not None:
                for t in top_el.findall("topic"):
                    if t.text:
                        topics.append(t.text.strip())

            return {
                "id": author_id,
                "name": name,
                "display_name": display_name,
                "identifiers": {
                    "openalex_id": author_id if (author_id.startswith("A") and author_id[1:].isdigit()) else None,
                    "google_scholar_id": None,
                    "orcid": orcid
                },
                "works_count": works_count,
                "cited_by_count": cited_by_count,
                "h_index": h_index,
                "i10_index": i10_index,
                "affiliations": affiliations,
                "topics": topics,
                "source": source,
                "scholar_url": scholar_url,
                "cached": True,
                "xml_path": xml_path
            }
        except Exception:
            return None

    def save_author_xml(self, author_id: str, profile: Dict[str, Any]) -> str:
        """Persist author profile metadata to structured XML archive."""
        clean_id = hashlib.sha256(author_id.strip().lower().encode("utf-8")).hexdigest()[:24]
        xml_path = os.path.join(self.authors_xml_dir, f"author_{clean_id}.xml")
        now = datetime.now(timezone.utc).isoformat()

        root = ET.Element("author_profile", {
            "version": "1.0",
            "author_id": safe_xml_text(author_id),
            "updated_at": now
        })

        ET.SubElement(root, "name").text = safe_xml_text(profile.get("name", ""))
        ET.SubElement(root, "display_name").text = safe_xml_text(profile.get("display_name") or profile.get("name", ""))
        if profile.get("scholar_url"):
            ET.SubElement(root, "scholar_url").text = safe_xml_text(profile["scholar_url"])
        if profile.get("orcid"):
            ET.SubElement(root, "orcid").text = safe_xml_text(profile["orcid"])
        ET.SubElement(root, "source").text = safe_xml_text(profile.get("source", "openalex"))

        if profile.get("works_count") is not None:
            ET.SubElement(root, "works_count").text = str(profile["works_count"])
        if profile.get("cited_by_count") is not None:
            ET.SubElement(root, "cited_by_count").text = str(profile["cited_by_count"])
        if profile.get("h_index") is not None:
            ET.SubElement(root, "h_index").text = str(profile["h_index"])
        if profile.get("i10_index") is not None:
            ET.SubElement(root, "i10_index").text = str(profile["i10_index"])

        affil_el = ET.SubElement(root, "affiliations")
        for aff in (profile.get("affiliations") or []):
            ET.SubElement(affil_el, "affiliation").text = safe_xml_text(aff)

        topics_el = ET.SubElement(root, "topics")
        for top in (profile.get("topics") or []):
            ET.SubElement(topics_el, "topic").text = safe_xml_text(top)

        xml_content = prettify_xml(root)
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        self._upsert_index("author", clean_id, xml_path, profile.get("display_name") or profile.get("name", ""), profile.get("works_count") or 0)
        return xml_path

    # =========================================================================
    # 4. INSPECTION & EXPORT HELPERS
    # =========================================================================
    def list_documents(self) -> List[Dict[str, Any]]:
        """List all indexed XML documents."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT lookup_key as pdf_hash, file_path, title, item_count as references_count, created_at, updated_at FROM xml_cache_index WHERE key_type = 'document' ORDER BY updated_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_document_xml_raw(self, pdf_hash: str) -> Optional[str]:
        """Read raw XML string for a cached document."""
        xml_path = os.path.join(self.documents_xml_dir, f"doc_{pdf_hash}.xml")
        if os.path.exists(xml_path):
            with open(xml_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def list_searches(self) -> List[Dict[str, Any]]:
        """List all indexed search queries in XML archive."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT lookup_key as query_hash, title as query, file_path, item_count as results_count, created_at, updated_at FROM xml_cache_index WHERE key_type = 'search' ORDER BY updated_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_search_xml_raw(self, query_or_hash: str) -> Optional[str]:
        """Read raw XML string for a cached search query or hash."""
        # Try as direct file first
        clean_input = (query_or_hash or "").strip()
        direct_path = os.path.join(self.searches_xml_dir, f"search_{clean_input}.xml")
        if os.path.exists(direct_path):
            with open(direct_path, "r", encoding="utf-8") as f:
                return f.read()

        # Try computing query hash
        q_hash = compute_query_hash(clean_input)
        hashed_path = os.path.join(self.searches_xml_dir, f"search_{q_hash}.xml")
        if os.path.exists(hashed_path):
            with open(hashed_path, "r", encoding="utf-8") as f:
                return f.read()

        return None


xml_storage = XMLStorageEngine()
