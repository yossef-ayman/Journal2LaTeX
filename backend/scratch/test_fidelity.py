import os
import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend folder is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

def test_fidelity_run(docx_path: Path, template_name: str = "default"):
    client = TestClient(app)
    
    if not docx_path.exists():
        print(f"File {docx_path} not found. Skipping.")
        return False
        
    print(f"\n==================================================")
    print(f"RUNNING FIDELITY TEST FOR: {docx_path.name}")
    print(f"==================================================")
    
    # 1. Upload
    print("Uploading document...")
    with open(docx_path, "rb") as f:
        res = client.post("/upload", files={"file": (docx_path.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert res.status_code == 201, f"Upload failed: {res.text}"
    job_id = res.json()["job_id"]
    
    # 2. Convert / Analyze
    print("Analyzing document structure and extracting assets...")
    res = client.post("/convert", json={"job_id": job_id})
    assert res.status_code == 200, f"Conversion failed: {res.text}"
    
    # 3. Compile
    print(f"Compiling with template: {template_name}...")
    res = client.post("/compile", json={"job_id": job_id, "template_name": template_name})
    assert res.status_code == 200, f"Compile failed: {res.text}"
    job_data = res.json()
    
    # 4. Verify outputs
    temp_dir = Path("temp") / job_id
    report_file = temp_dir / "intermediate" / "conversion_report.json"
    pdf_file = temp_dir / "output" / "paper.pdf"
    
    assert report_file.exists(), "Conversion report not generated!"
    assert pdf_file.exists(), f"Output PDF not generated! Status: {job_data['status']}. Errors: {job_data['errors']}"
    
    with open(report_file, "r", encoding="utf-8") as f:
        report = json.load(f)
        
    print("\n--- Verification Report ---")
    print(json.dumps(report, indent=2))
    
    print("\nFidelity Metrics:")
    print(f"  - Paragraphs parsed: {report['paragraphs']}")
    print(f"  - Figures extracted: {report['figures']}")
    print(f"  - Tables extracted:  {report['tables']}")
    print(f"  - Equations parsed:  {report['equations']}")
    print(f"  - References parsed: {report['references']}")
    
    if report["warnings"]:
        print("\nWarnings:")
        for w in report["warnings"]:
            print(f"  [WARNING] {w}")
            
    print("\nFidelity checks:")
    assert report["paragraphs"] > 0, "No paragraphs extracted"
    print("  [PASS] Document content extracted successfully.")
    
    print(f"  [PASS] PDF generated successfully (Size: {pdf_file.stat().st_size} bytes)")
    return True

if __name__ == "__main__":
    tests_dir = Path("tests")
    test_file = tests_dir / "test.docx"
    
    # Run on main test file
    success = test_fidelity_run(test_file, "default")
    
    # If successful, try the JSAP template as well
    if success:
        test_fidelity_run(test_file, "JSAP")
