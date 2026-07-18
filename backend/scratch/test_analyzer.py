import os
import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend folder is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

def print_tree(directory: Path, indent: str = ""):
    """Print directory tree structure recursively."""
    for path in sorted(directory.iterdir()):
        if path.name.startswith("__") or path.name == ".pytest_cache":
            continue
        if path.is_dir():
            print(f"{indent}|-- {path.name}/")
            print_tree(path, indent + "|   ")
        else:
            print(f"{indent}+-- {path.name} ({path.stat().st_size} bytes)")

def test_document_analysis():
    client = TestClient(app)
    sample_docx = Path("../examples/sample.docx").resolve()
    
    if not sample_docx.exists():
        print(f"Error: {sample_docx} does not exist.")
        sys.exit(1)
        
    print("==================================================")
    print("STEP 1: Uploading DOCX...")
    print("==================================================")
    with open(sample_docx, "rb") as f:
        response = client.post("/upload", files={"file": (sample_docx.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    
    assert response.status_code == 201, f"Upload failed: {response.text}"
    job_data = response.json()
    job_id = job_data["job_id"]
    print(f"Uploaded successfully. Job ID: {job_id}")

    print("\n==================================================")
    print("STEP 2: Starting conversion (Validation + AST Analysis + Assets)...")
    print("==================================================")
    response = client.post("/convert", json={"job_id": job_id})
    assert response.status_code == 200, f"Conversion trigger failed: {response.text}"
    job_data = response.json()
    print(f"Pipeline step response:")
    print(f"Status: {job_data['status']}")
    print(f"Progress: {job_data['progress']}%")
    print(f"Current Step: {job_data['current_step']}")
    
    if job_data["status"] == "FAILED":
        print("\nPipeline failed. Errors:")
        print(job_data["errors"])
        sys.exit(1)

    print("\n==================================================")
    print("STEP 3: Verifying workspace files and logs...")
    print("==================================================")
    temp_dir = Path("temp") / job_id
    print(f"\nGenerated folder structure for job {job_id}:")
    print_tree(temp_dir)
    
    # Verify metadata and structure json
    metadata_file = temp_dir / "metadata.json"
    structure_file = temp_dir / "intermediate" / "document_structure.json"
    
    assert metadata_file.exists(), "metadata.json not found"
    assert structure_file.exists(), "document_structure.json not found"
    
    with open(structure_file, "r", encoding="utf-8") as f:
        structure = json.load(f)
        
    print("\nParsed Document Structure:")
    print(json.dumps(structure, indent=2))

    print("\nLog Files Content:")
    for log_name in ["system.log", "pandoc.log"]:
        log_file = temp_dir / "logs" / log_name
        if log_file.exists():
            print(f"\n--- {log_name} ---")
            print(log_file.read_text(encoding="utf-8").strip())

if __name__ == "__main__":
    test_document_analysis()
