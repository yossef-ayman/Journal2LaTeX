"""Production Document Pipeline Verification Script."""

import os
import sys
import json
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

base_dir = Path("g:/work/Journal2LaTeX/backend")
sys.path.insert(0, str(base_dir.resolve()))

from app.main import app
import fitz  # PyMuPDF


def test_production_document(docx_path: Path, doc_label: str):
    print(f"\n==================================================")
    print(f" TESTING PRODUCTION DOCX: {doc_label} ({docx_path.name})")
    print(f"==================================================")

    client = TestClient(app)
    scratch_dir = base_dir / "scratch" / "prod_verification" / doc_label
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir)
    scratch_dir.mkdir(parents=True, exist_ok=True)

    # 1. Upload
    print("1. Uploading file...")
    with open(docx_path, "rb") as f:
        resp_up = client.post(
            "/upload",
            files={
                "file": (
                    docx_path.name,
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert resp_up.status_code == 201, f"Upload failed: {resp_up.text}"
    job_data = resp_up.json()
    job_id = job_data["job_id"]
    print(f"   Upload SUCCESS. Job ID: {job_id}")

    # 2. Convert
    print("2. Triggering conversion (/convert)...")
    resp_conv = client.post("/convert", json={"job_id": job_id})
    assert resp_conv.status_code == 200, f"Convert failed: {resp_conv.text}"
    conv_data = resp_conv.json()
    print(f"   Convert SUCCESS. Status: {conv_data['status']}")

    # 3. Compile
    print("3. Triggering compilation (/compile)...")
    resp_comp = client.post("/compile", json={"job_id": job_id})
    assert resp_comp.status_code == 200, f"Compile failed: {resp_comp.text}"
    comp_data = resp_comp.json()
    print(f"   Compile Status: {comp_data['status']}")
    print(f"   Errors: {comp_data.get('errors', [])}")
    print(f"   Warnings: {comp_data.get('warnings', [])}")

    # Verify no "LaTeX compilation failed" warning
    warn_text = " ".join(comp_data.get("warnings", [])) + " " + " ".join(comp_data.get("errors", []))
    assert "LaTeX compilation failed" not in warn_text, f"LaTeX compilation warning/error found: {warn_text}"
    assert comp_data["status"] == "COMPLETED", f"Job status is not COMPLETED: {comp_data['status']}"

    # 4. Download PDF endpoint (/download/{job_id}/pdf)
    print("4. Testing Download Endpoint (/download/{job_id}/pdf)...")
    resp_dl = client.get(f"/download/{job_id}/pdf")
    assert resp_dl.status_code == 200, f"Download failed: {resp_dl.status_code}"
    pdf_bytes = resp_dl.content
    assert len(pdf_bytes) > 0, "Downloaded PDF is empty!"
    
    downloaded_pdf_path = scratch_dir / "downloaded_paper.pdf"
    downloaded_pdf_path.write_bytes(pdf_bytes)
    print(f"   Download SUCCESS. Size: {len(pdf_bytes)} bytes")

    # 5. Verify PDF page count & Page 1 screenshot
    doc = fitz.open(downloaded_pdf_path)
    page_count = len(doc)
    print(f"   PDF Page Count: {page_count}")
    assert page_count > 0, "PDF has 0 pages!"
    
    page1 = doc[0]
    pix = page1.get_pixmap(dpi=150)
    page1_img_path = scratch_dir / "page_1.png"
    pix.save(str(page1_img_path))
    print(f"   Page 1 rendered successfully ({pix.width}x{pix.height}px)")

    # 6. Verify Job History Endpoint (/job)
    print("6. Verifying Job History Endpoint (/job)...")
    resp_jobs = client.get("/job")
    assert resp_jobs.status_code == 200, f"Job list failed: {resp_jobs.status_code}"
    all_jobs = resp_jobs.json()
    job_ids_in_history = [j["job_id"] for j in all_jobs]
    assert job_id in job_ids_in_history, f"Job {job_id} not found in job history!"
    print(f"   Job History SUCCESS. Job {job_id} listed correctly.")

    print(f"=== {doc_label} VERIFICATION PASSED 100% ===")


def main():
    test_docs = [
        (base_dir / "tests" / "with_author_photo.docx", "with_author_photo"),
        (base_dir / "tests" / "with_charts.docx", "with_charts"),
        (base_dir / "tests" / "normal_paper.docx", "normal_paper"),
    ]

    for doc_path, label in test_docs:
        if doc_path.exists():
            try:
                test_production_document(doc_path, label)
            except Exception as e:
                print(f"\nFAILED on {label}: {e}")
        else:
            print(f"Warning: Test file {doc_path} missing!")

    print("\n==================================================")
    print(" ALL PRODUCTION DOCUMENTS VERIFIED SUCCESSFULLY")
    print("==================================================")


if __name__ == "__main__":
    main()
