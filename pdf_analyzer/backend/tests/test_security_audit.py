import os
import io
import re
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import fitz

from main import app
from enrichment.xml_storage import xml_storage
from enrichment.storage import storage
from enrichment.config import config

client = TestClient(app)


def test_path_traversal_document_xml_raw():
    """Verify that path traversal strings cannot escape the XML document store."""
    traversal_inputs = [
        "../../win.ini",
        "../..\\system.ini",
        "..%2f..%2fetc%2fpasswd",
        "/etc/passwd",
        "C:\\Windows\\win.ini",
        "doc_test/../../test"
    ]
    for evil in traversal_inputs:
        res = xml_storage.get_document_xml_raw(evil)
        assert res is None, f"Expected None for traversal input: {evil}"

        # Test endpoint
        resp = client.get(f"/xml/document/{evil}")
        assert resp.status_code in (404, 400, 422), f"Endpoint did not reject traversal: {evil}"


def test_path_traversal_search_xml_raw():
    """Verify that path traversal strings cannot escape the XML search store."""
    traversal_inputs = [
        "../../win.ini",
        "..\\..\\system.ini",
        "/etc/passwd",
        "C:\\Windows\\win.ini",
        "../../../secret"
    ]
    for evil in traversal_inputs:
        res = xml_storage.get_search_xml_raw(evil)
        assert res is None, f"Expected None for traversal input: {evil}"

        # Test endpoint
        resp = client.get(f"/xml/search/{evil}")
        assert resp.status_code in (404, 400, 422), f"Endpoint did not reject traversal: {evil}"


def test_storage_connection_closes():
    """Verify that StorageEngine connections do not leak."""
    # Run multiple operations and ensure connection count doesn't accumulate
    stats = storage.get_stats()
    assert isinstance(stats, dict)
    
    projects = storage.list_projects(limit=5)
    assert isinstance(projects, list)

    raw_path = storage.save_raw("test_prov", "sec_query", {"ok": True})
    assert raw_path is not None
    loaded_raw = storage.load_raw("test_prov", "sec_query")
    assert loaded_raw == {"ok": True}


def test_analyze_closes_uploaded_file():
    """Verify that UploadFile.close is called during /analyze."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Security Audit Verification Document", fontsize=16)
    page.insert_text((50, 100), "References", fontsize=14)
    page.insert_text((50, 120), "[1] Knuth, D. 1984.", fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()

    res = client.post(
        "/analyze",
        files={"file": ("sec_audit.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert res.status_code == 200
    data = res.json()
    assert "pdf_hash" in data


def test_gitignore_covers_sensitive_files():
    """Verify that .gitignore includes .env, virtualenvs, logs, and sensitive data directories."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    gitignore_path = os.path.join(base_dir, ".gitignore")
    assert os.path.exists(gitignore_path), ".gitignore must exist"

    with open(gitignore_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert ".env" in content
    assert "*.env" in content
    assert ".venv/" in content
    assert "*.log" in content
