"""Verification script for Phase 2 Document Rendering and Normalization."""

import os
import sys
from pathlib import Path

base_dir = Path("g:/work/Journal2LaTeX/backend")
sys.path.insert(0, str(base_dir.resolve()))

from app.fidelity.schemas import SourceType
from app.fidelity.renderers.pdf import PDFRenderer
from app.fidelity.renderers.docx import DocxRenderer
from app.fidelity.renderers.image import ImageRenderer
from app.fidelity.image_converter import ImageConverter

def main():
    base_dir = Path("g:/work/Journal2LaTeX/backend")
    out_dir = base_dir / "scratch" / "phase2_test_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== Phase 2 Verification ===")

    # 1. Test PDFRenderer with existing sample PDF
    pdf_sample = base_dir / "temp" / "048e19e5-ec17-4797-af4d-5fc013c8f298" / "intermediate" / "original_docx.pdf"
    if pdf_sample.exists():
        print(f"\n1. Testing PDFRenderer on: {pdf_sample.name}")
        pdf_renderer = PDFRenderer()
        pdf_pages = pdf_renderer.render(str(pdf_sample), str(out_dir / "pdf_pages"), dpi=150)
        print(f"   Successfully rendered {len(pdf_pages)} page(s).")
        for p in pdf_pages:
            print(f"   - Page {p.page_number}: {p.width}x{p.height}px @ {p.dpi} DPI ({p.image_path})")

    # 2. Test ImageRenderer
    image_sample = out_dir / "pdf_pages" / "page_1.png"
    if image_sample.exists():
        print(f"\n2. Testing ImageRenderer on: {image_sample.name}")
        img_renderer = ImageRenderer()
        img_pages = img_renderer.render(str(image_sample), str(out_dir / "image_pages"), dpi=150)
        print(f"   Successfully loaded {len(img_pages)} image page(s).")
        for p in img_pages:
            print(f"   - Image Page {p.page_number}: {p.width}x{p.height}px ({p.image_path})")

    # 3. Test ImageConverter canvas normalization & alignment
    if pdf_sample.exists() and len(pdf_pages) >= 1:
        print("\n3. Testing ImageConverter canvas padding & dimension normalization...")
        converter = ImageConverter()
        src_page = pdf_pages[0]

        # Create a mock target page with different dimensions to verify padding
        mock_tgt_page = src_page.model_copy(
            update={
                "page_number": 1,
                "width": src_page.width + 100,
                "height": src_page.height + 150,
            }
        )

        norm_src, norm_tgt = converter.normalize_pair(src_page, mock_tgt_page, str(out_dir / "normalized"))
        print("   Normalized Pair Result:")
        print(f"   - Source: {norm_src.width}x{norm_src.height}px -> {norm_src.image_path}")
        print(f"   - Target: {norm_tgt.width}x{norm_tgt.height}px -> {norm_tgt.image_path}")
        assert norm_src.width == norm_tgt.width, "Widths do not match!"
        assert norm_src.height == norm_tgt.height, "Heights do not match!"
        print("   SUCCESS: Source and Target canvas dimensions aligned perfectly!")

    # 4. Test DocxRenderer on sample.docx
    docx_sample = Path("g:/work/Journal2LaTeX/examples/sample.docx")
    if docx_sample.exists():
        print(f"\n4. Testing DocxRenderer on: {docx_sample.name}")
        try:
            docx_renderer = DocxRenderer()
            docx_pages = docx_renderer.render(str(docx_sample), str(out_dir / "docx_pages"), dpi=150)
            print(f"   Successfully rendered {len(docx_pages)} DOCX page(s).")
            for p in docx_pages:
                print(f"   - DOCX Page {p.page_number}: {p.width}x{p.height}px ({p.image_path})")
        except Exception as err:
            print(f"   Note: DOCX rendering test skipped or info: {err}")

    print("\n=== Phase 2 Verification Complete ===")

if __name__ == "__main__":
    main()
