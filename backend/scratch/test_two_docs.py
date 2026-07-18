import os
import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend folder is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

def run_e2e_for_doc(docx_path: Path, template_name: str) -> dict:
    client = TestClient(app)
    
    print(f"\n==================================================")
    print(f"RUNNING E2E PIPELINE FOR: {docx_path.name}")
    print(f"==================================================")
    
    # 1. Upload
    with open(docx_path, "rb") as f:
        res = client.post("/upload", files={"file": (docx_path.name, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert res.status_code == 201, f"Upload failed: {res.text}"
    job_id = res.json()["job_id"]
    
    # 2. Convert (Validate + Analyze + Extract Assets + Classify Assets)
    res = client.post("/convert", json={"job_id": job_id})
    assert res.status_code == 200, f"Convert failed: {res.text}"
    
    # 3. Compile (Load Template + Render LaTeX + Compile + Fidelity Checker)
    res = client.post("/compile", json={"job_id": job_id, "template_name": template_name})
    assert res.status_code == 200, f"Compile failed: {res.text}"
    
    # Load outputs
    temp_dir = Path("temp") / job_id
    assets_file = temp_dir / "intermediate" / "assets.json"
    mapping_file = temp_dir / "intermediate" / "asset_mapping.json"
    fidelity_file = temp_dir / "intermediate" / "fidelity_report.json"
    structure_file = temp_dir / "intermediate" / "document_structure.json"
    
    with open(structure_file, "r", encoding="utf-8") as f:
        structure = json.load(f)
    with open(assets_file, "r", encoding="utf-8") as f:
        assets = json.load(f)
    with open(mapping_file, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    with open(fidelity_file, "r", encoding="utf-8") as f:
        fidelity = json.load(f)
        
    return {
        "job_id": job_id,
        "structure": structure,
        "assets": assets,
        "mapping": mapping,
        "fidelity": fidelity
    }

def print_validation_report(name: str, res: dict):
    fidelity = res["fidelity"]
    structure = res["structure"]
    assets = res["assets"]["assets"]
    
    print(f"\n==================================================")
    print(f"VALIDATION REPORT: {name}")
    print(f"==================================================")
    
    # 1. Content Validation
    print("\n[1] Content Validation:")
    print(f"  - Title:        {structure.get('title')}")
    print(f"  - Authors:      {[a.get('name') for a in structure.get('authors', [])]}")
    print(f"  - Affiliations: {[a.get('affiliation') for a in structure.get('authors', []) if a.get('affiliation')]}")
    print(f"  - Abstract:     {structure.get('abstract')[:120]}..." if structure.get('abstract') else "  - Abstract:     None")
    print(f"  - Keywords:     {structure.get('keywords')}")
    print(f"  - Sections:     {[s.get('title') for s in structure.get('sections', [])]}")
    print(f"  - References:   {len(structure.get('references', []))} items")
    print(f"  - Biographies:  {[b.get('author_name') for b in structure.get('author_biographies', [])]}")
    
    # 2. Asset Validation
    print("\n[2] Asset Validation:")
    print(f"  - Total Extracted:      {len(assets)}")
    print(f"  - Author Photos:        {len([a for a in assets if a.get('type') == 'author_photo'])}")
    print(f"  - Figures:              {len([a for a in assets if a.get('type') == 'figure'])}")
    print(f"  - Logos:                {len([a for a in assets if a.get('type') == 'logo'])}")
    print(f"  - Missing Assets:       {fidelity.get('missing_assets')}")
    
    # 3. Layout Validation
    pdf_val = fidelity.get("pdf_validations", {})
    print("\n[3] Layout Validation:")
    print(f"  - Empty Pages Detected: {pdf_val.get('empty_pages_detected')}")
    print(f"  - Text Overflows:       {pdf_val.get('text_overflow_warnings')} warnings")
    print(f"  - LaTeX Warnings:       {len(pdf_val.get('latex_log_warnings', []))} warnings")
    
    # 4. Fidelity Scores
    print("\n[4] Fidelity Scores:")
    print(f"  - content_match_score:  {fidelity.get('content_match_score')}%")
    print(f"  - asset_match_score:    {fidelity.get('asset_match_score')}%")
    print(f"  - layout_match_score:   {fidelity.get('layout_match_score')}%")
    print(f"  - overall_fidelity_score: {fidelity.get('overall_fidelity_score')}%")

if __name__ == "__main__":
    tests_dir = Path("tests")
    doc_with_photo = tests_dir / "with_author_photo.docx"
    doc_normal = tests_dir / "normal_paper.docx"
    
    res_photo = run_e2e_for_doc(doc_with_photo, "JSAP")
    print_validation_report("DOCX with Author Photo", res_photo)
    
    res_normal = run_e2e_for_doc(doc_normal, "JSAP")
    print_validation_report("DOCX without Author Photo", res_normal)
    
    # Threshold checks for PASS/FAIL
    # Target: content >= 95%, asset >= 95%, layout >= 90%, critical_missing == 0
    scores_photo = res_photo["fidelity"]
    scores_normal = res_normal["fidelity"]
    
    passed_photo = (
        scores_photo["content_match_score"] >= 95.0 and
        scores_photo["asset_match_score"] >= 95.0 and
        scores_photo["layout_match_score"] >= 90.0 and
        scores_photo["critical_missing_content"] == 0
    )
    
    passed_normal = (
        scores_normal["content_match_score"] >= 95.0 and
        scores_normal["asset_match_score"] >= 95.0 and
        scores_normal["layout_match_score"] >= 90.0 and
        scores_normal["critical_missing_content"] == 0
    )
    
    print("\n==================================================")
    print("FINAL SUMMARY REPORT")
    print("==================================================")
    print(f"DOCX with Author Photo:    {'PASS' if passed_photo else 'FAIL'}")
    print(f"DOCX without Author Photo: {'PASS' if passed_normal else 'FAIL'}")
    
    critical_missing = scores_photo["critical_missing_content"] + scores_normal["critical_missing_content"]
    failed_checks = []
    if scores_photo["content_match_score"] < 95.0: failed_checks.append("with_author_photo: content_match_score < 95%")
    if scores_photo["asset_match_score"] < 95.0: failed_checks.append("with_author_photo: asset_match_score < 95%")
    if scores_photo["layout_match_score"] < 90.0: failed_checks.append("with_author_photo: layout_match_score < 90%")
    
    if scores_normal["content_match_score"] < 95.0: failed_checks.append("normal_paper: content_match_score < 95%")
    if scores_normal["asset_match_score"] < 95.0: failed_checks.append("normal_paper: asset_match_score < 95%")
    if scores_normal["layout_match_score"] < 90.0: failed_checks.append("normal_paper: layout_match_score < 90%")
    
    print(f"Critical Missing Content:  {critical_missing}")
    print(f"Failed Checks:             {failed_checks if failed_checks else 'None'}")
    
    if passed_photo and passed_normal:
        print("\nRECOMMENDATION: Ready for Phase 6")
    else:
        print("\nRECOMMENDATION: Needs fixes before Phase 6")
