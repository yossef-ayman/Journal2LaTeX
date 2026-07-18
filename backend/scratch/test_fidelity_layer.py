import os
import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend folder is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

def run_fidelity_layer_test():
    client = TestClient(app)
    sample_docx = Path("tests/test.docx").resolve()
    
    if not sample_docx.exists():
        print(f"Error: {sample_docx} does not exist.")
        sys.exit(1)
        
    print("==================================================")
    print("STEP 1: Uploading Real Academic Paper DOCX...")
    print("==================================================")
    with open(sample_docx, "rb") as f:
        res = client.post("/upload", files={"file": (sample_docx.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert res.status_code == 201, f"Upload failed: {res.text}"
    job_id = res.json()["job_id"]
    print(f"Job created successfully. ID: {job_id}")

    print("\n==================================================")
    print("STEP 2: Starting conversion (Validation + AST Analysis + Asset Classification)...")
    print("==================================================")
    res = client.post("/convert", json={"job_id": job_id})
    assert res.status_code == 200, f"Conversion failed: {res.text}"
    job_data = res.json()
    print(f"Convert step status: {job_data['status']}")
    
    if job_data["status"] == "FAILED":
        print(f"Errors: {job_data['errors']}")
        sys.exit(1)

    print("\n==================================================")
    print("STEP 3: Compiling (Template Load + Latex Rendering + PDF + Fidelity Checks)...")
    print("==================================================")
    res = client.post("/compile", json={"job_id": job_id, "template_name": "JSAP"})
    assert res.status_code == 200, f"Compile failed: {res.text}"
    job_data = res.json()
    print(f"Compile step status: {job_data['status']}")
    print(f"Current Step: {job_data['current_step']}")
    
    if job_data["status"] == "FAILED":
        print(f"Errors: {job_data['errors']}")
        sys.exit(1)

    print("\n==================================================")
    print("STEP 4: Verifying structured reports and mappings...")
    print("==================================================")
    temp_dir = Path("temp") / job_id
    assets_file = temp_dir / "intermediate" / "assets.json"
    mapping_file = temp_dir / "intermediate" / "asset_mapping.json"
    fidelity_file = temp_dir / "intermediate" / "fidelity_report.json"
    output_pdf = temp_dir / "output" / "paper.pdf"
    
    assert assets_file.exists(), "assets.json was not generated!"
    assert mapping_file.exists(), "asset_mapping.json was not generated!"
    assert fidelity_file.exists(), "fidelity_report.json was not generated!"
    assert output_pdf.exists(), "paper.pdf was not generated!"
    
    print("\n[PASS] All verification files and target PDF exist.")
    
    with open(assets_file, "r", encoding="utf-8") as f:
        assets = json.load(f)
    print("\nClassified Assets (assets.json):")
    print(json.dumps(assets, indent=2))
    
    with open(mapping_file, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    print("\nAsset Mappings (asset_mapping.json):")
    print(json.dumps(mapping, indent=2))
    
    with open(fidelity_file, "r", encoding="utf-8") as f:
        fidelity = json.load(f)
    print("\nFidelity Report (fidelity_report.json):")
    print(json.dumps(fidelity, indent=2))
    
    # Assert there are no critical missing contents in the report and scores meet thresholds
    assert fidelity["content_match_score"] >= 95.0, f"Content match score low: {fidelity['content_match_score']}%"
    assert fidelity["asset_match_score"] >= 95.0, f"Asset match score low: {fidelity['asset_match_score']}%"
    assert fidelity["layout_match_score"] >= 90.0, f"Layout match score low: {fidelity['layout_match_score']}%"
    assert fidelity["critical_missing_content"] == 0, f"Critical missing content count: {fidelity['critical_missing_content']}"

    print("\n[SUCCESS] E2E Fidelity Layer verification complete. All quality targets met!")

if __name__ == "__main__":
    run_fidelity_layer_test()
