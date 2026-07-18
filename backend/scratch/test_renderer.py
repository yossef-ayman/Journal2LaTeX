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

def test_full_renderer_pipeline():
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
    print(f"Convert step status: {job_data['status']}")
    
    if job_data["status"] == "FAILED":
        print("\nPipeline failed at conversion. Errors:")
        print(job_data["errors"])
        sys.exit(1)

    print("\n==================================================")
    print("STEP 3: Compiling (Template Load + Latex Rendering + PDF Compilation)...")
    print("==================================================")
    response = client.post("/compile", json={"job_id": job_id, "template_name": "JSAP"})
    assert response.status_code == 200, f"Compile trigger failed: {response.text}"
    job_data = response.json()
    print(f"Compile step status: {job_data['status']}")
    print(f"Current Step: {job_data['current_step']}")
    
    if job_data["status"] == "FAILED":
        print("\nPipeline failed at compilation. Errors:")
        print(job_data["errors"])
        print_logs(job_id)
        sys.exit(1)

    print("\n==================================================")
    print("STEP 4: Verifying workspace files and logs...")
    print("==================================================")
    temp_dir = Path("temp") / job_id
    print(f"\nGenerated folder structure for job {job_id}:")
    print_tree(temp_dir)
    
    main_tex_file = temp_dir / "rendered" / "main.tex"
    output_pdf_file = temp_dir / "output" / "paper.pdf"
    
    assert main_tex_file.exists(), "main.tex not found"
    assert output_pdf_file.exists(), "paper.pdf not found in output folder"
    
    print("\nRendered LaTeX content (main.tex):")
    print("--------------------------------------------------")
    print(main_tex_file.read_text(encoding="utf-8"))
    print("--------------------------------------------------")

    print("\nLog Files Content:")
    for log_name in ["system.log", "pandoc.log", "compiler.log"]:
        log_file = temp_dir / "logs" / log_name
        if log_file.exists():
            print(f"\n--- {log_name} ---")
            print(log_file.read_text(encoding="utf-8").strip())

def print_logs(job_id: str):
    log_dir = Path("temp") / job_id / "logs"
    if log_dir.exists():
        for f in log_dir.iterdir():
            print(f"\n--- {f.name} ---")
            print(f.read_text(encoding="utf-8").strip())

if __name__ == "__main__":
    test_full_renderer_pipeline()
