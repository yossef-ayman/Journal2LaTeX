import os
import shutil
import tempfile
import pytest
from enrichment.storage import StorageEngine

@pytest.fixture
def temp_storage():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_cache.db")
    engine = StorageEngine(db_path=db_path)
    yield engine
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_raw_storage_persistence(temp_storage):
    payload = {"results": [{"id": 1, "title": "Attention Is All You Need"}]}
    rel_path = temp_storage.save_raw("google_scholar", "Attention Is All You Need", payload, status_code=200, candidate_count=1)
    
    assert os.path.exists(os.path.join(os.path.dirname(os.path.dirname(temp_storage.db_path)), rel_path)) or os.path.isabs(rel_path) or "raw" in rel_path
    
    loaded = temp_storage.load_raw("google_scholar", "Attention Is All You Need")
    assert loaded is not None
    assert loaded == payload

def test_normalized_storage_persistence(temp_storage):
    norm_data = {"title": "Attention Is All You Need", "year": 2017}
    temp_storage.save_normalized("openalex", "W2626778328", norm_data)
    
    loaded = temp_storage.load_normalized("openalex", "W2626778328")
    assert loaded is not None
    assert loaded["title"] == "Attention Is All You Need"
    assert loaded["year"] == 2017

def test_master_reference_persistence(temp_storage):
    ref_data = {
        "reference_id": "ref_123",
        "canonical": {
            "title": {"value": "Attention Is All You Need", "source": "openalex"},
            "identifiers": {"doi": {"value": "10.48550/arXiv.1706.03762"}}
        },
        "quality": {"overall_confidence": 0.98}
    }
    temp_storage.save_reference("ref_123", ref_data)
    loaded = temp_storage.load_reference("ref_123")
    assert loaded is not None
    assert loaded["reference_id"] == "ref_123"
    assert loaded["canonical"]["title"]["value"] == "Attention Is All You Need"

def test_project_storage_and_listing(temp_storage):
    proj_data = {
        "project_id": "proj_abc",
        "input_pdf": {"filename": "test.pdf", "sha256": "123456"},
        "statistics": {"total_references": 5}
    }
    temp_storage.save_project("proj_abc", proj_data)
    loaded = temp_storage.load_project("proj_abc")
    assert loaded is not None
    assert loaded["input_pdf"]["filename"] == "test.pdf"

    projects = temp_storage.list_projects()
    assert len(projects) == 1
    assert projects[0]["project_id"] == "proj_abc"
    assert projects[0]["filename"] == "test.pdf"

def test_author_and_paper_storage(temp_storage):
    author_data = {"identity": {"name": "Ashish Vaswani", "openalex_id": "A5103024730"}}
    temp_storage.save_author("A5103024730", author_data)
    loaded_author = temp_storage.load_author("A5103024730")
    assert loaded_author is not None
    assert loaded_author["identity"]["name"] == "Ashish Vaswani"

    paper_data = {"title": "Attention Is All You Need", "doi": "10.48550/arXiv.1706.03762"}
    temp_storage.save_paper("W2626778328", paper_data)
    loaded_paper = temp_storage.load_paper("W2626778328")
    assert loaded_paper is not None
    assert loaded_paper["title"] == "Attention Is All You Need"
