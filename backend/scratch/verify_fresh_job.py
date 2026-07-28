"""Script to verify pipeline from scratch on a fresh job and collect all required artifacts."""

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


def main():
    client = TestClient(app)
    sample_docx = Path("g:/work/Journal2LaTeX/examples/sample.docx").resolve()
    scratch_dir = base_dir / "scratch" / "fresh_job_verification"
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir)
    scratch_dir.mkdir(parents=True, exist_ok=True)

    print("=== STEP 1: Uploading Fresh Sample DOCX ===")
    with open(sample_docx, "rb") as f:
        resp = client.post(
            "/upload",
            files={
                "file": (
                    sample_docx.name,
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    job_id = resp.json()["job_id"]
    print(f"Fresh Job ID: {job_id}")

    print("\n=== STEP 2: Running Conversion (/convert) ===")
    resp = client.post("/convert", json={"job_id": job_id})
    assert resp.status_code == 200, f"Convert failed: {resp.text}"

    temp_job_dir = base_dir / "temp" / job_id

    print("\n=== STEP 3: Preparing Template & Rendering main.tex ===")
    # Trigger load_template and render_latex via pipeline service to capture main.tex BEFORE compilation
    from app.services.pipeline_service import PipelineService
    ps = PipelineService()
    ps.load_template(job_id, "default")
    tex_path = ps.render_latex(job_id)
    assert tex_path and tex_path.exists(), "LaTeX rendering failed!"

    # Artifact A: main.tex BEFORE compilation
    before_tex_content = tex_path.read_text(encoding="utf-8")
    (scratch_dir / "main_before.tex").write_text(before_tex_content, encoding="utf-8")
    print(f"Saved main.tex BEFORE compilation ({len(before_tex_content)} bytes)")

    print("\n=== STEP 4: Running Compilation #1 (/compile) ===")
    resp_compile1 = client.post("/compile", json={"job_id": job_id})
    assert resp_compile1.status_code == 200, f"Compile #1 failed: {resp_compile1.text}"
    job_data1 = resp_compile1.json()
    print("Compile #1 Status:", job_data1["status"])
    assert job_data1["status"] != "FAILED", f"Compile #1 failed: {job_data1['errors']}"

    # Artifact B: main.tex AFTER compilation #1
    after_tex_content = tex_path.read_text(encoding="utf-8")
    (scratch_dir / "main_after_comp1.tex").write_text(after_tex_content, encoding="utf-8")
    print(f"Saved main.tex AFTER compilation #1 ({len(after_tex_content)} bytes)")

    # Artifact C: Output paper.pdf
    output_pdf = temp_job_dir / "output" / "paper.pdf"
    assert output_pdf.exists(), "paper.pdf was not generated!"
    shutil.copy(output_pdf, scratch_dir / "paper.pdf")
    print(f"Saved output paper.pdf ({output_pdf.stat().st_size} bytes)")

    # Artifact D: Render Page 1 to PNG proof
    doc = fitz.open(output_pdf)
    print(f"Generated PDF Page Count: {len(doc)}")
    assert len(doc) > 0, "PDF has 0 pages!"
    page1 = doc[0]
    pix = page1.get_pixmap(dpi=150)
    page1_png_path = scratch_dir / "page_1_proof.png"
    pix.save(str(page1_png_path))
    print(f"Saved Page 1 proof screenshot: {page1_png_path} ({pix.width}x{pix.height}px)")

    # Artifact E: Logs
    compiler_log = temp_job_dir / "logs" / "compiler.log"
    main_log = temp_job_dir / "rendered" / "main.log"
    if compiler_log.exists():
        shutil.copy(compiler_log, scratch_dir / "compiler.log")
    if main_log.exists():
        shutil.copy(main_log, scratch_dir / "main.log")

    print("\n=== STEP 5: Testing Idempotency (Compilations #2 & #3) ===")
    
    # Compilation #2
    resp2 = client.post("/compile", json={"job_id": job_id})
    comp2_job = resp2.json()
    comp2_status = "PASS" if resp2.status_code == 200 and comp2_job["status"] != "FAILED" else "FAIL"
    tex_comp2 = tex_path.read_text(encoding="utf-8")
    (scratch_dir / "main_after_comp2.tex").write_text(tex_comp2, encoding="utf-8")

    # Compilation #3
    resp3 = client.post("/compile", json={"job_id": job_id})
    comp3_job = resp3.json()
    comp3_status = "PASS" if resp3.status_code == 200 and comp3_job["status"] != "FAILED" else "FAIL"
    tex_comp3 = tex_path.read_text(encoding="utf-8")
    (scratch_dir / "main_after_comp3.tex").write_text(tex_comp3, encoding="utf-8")

    print("\n----------------------------------------")
    print(f"Compilation #1: PASS")
    print(f"Compilation #2: {comp2_status}")
    print(f"Compilation #3: {comp3_status}")
    print("----------------------------------------")

    # Byte-for-byte check
    is_comp1_comp2_identical = (after_tex_content == tex_comp2)
    is_comp2_comp3_identical = (tex_comp2 == tex_comp3)

    print(f"main.tex byte-for-byte identical (Comp 1 vs Comp 2): {is_comp1_comp2_identical}")
    print(f"main.tex byte-for-byte identical (Comp 2 vs Comp 3): {is_comp2_comp3_identical}")

    assert is_comp1_comp2_identical and is_comp2_comp3_identical, "main.tex was modified on consecutive compilations!"

    print("\n=== ALL CHECKS PASSED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
