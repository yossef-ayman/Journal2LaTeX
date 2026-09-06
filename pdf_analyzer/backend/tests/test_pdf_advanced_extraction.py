import io
import fitz
import pytest
from main import is_valid_author_name, analyze_pdf_content, extract_manuscript_authors, extract_academic_references


def test_is_valid_author_name():
    # Valid academic author names
    assert is_valid_author_name("Ashish Vaswani") is True
    assert is_valid_author_name("Geoffrey E. Hinton") is True
    assert is_valid_author_name("Y. LeCun") is True
    assert is_valid_author_name("Laurens van der Maaten") is True
    assert is_valid_author_name("Kaiming He") is True
    assert is_valid_author_name("أحمد محمود علي") is True

    # Invalid names (institutions, single words, numbers, emails, URLs)
    assert is_valid_author_name("Stanford University") is False
    assert is_valid_author_name("Department of Computer Science") is False
    assert is_valid_author_name("IEEE") is False
    assert is_valid_author_name("John") is False
    assert is_valid_author_name("author@email.com") is False
    assert is_valid_author_name("http://arxiv.org") is False
    assert is_valid_author_name("Abstract") is False
    assert is_valid_author_name("Vol. 12") is False


def test_extract_manuscript_authors_and_references():
    doc = fitz.open()
    
    # Page 1: Title, Authors with affiliations & superscripts, Abstract
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text((50, 80), "Deep High-Resolution Representation Learning for Visual Recognition", fontsize=18)
    page1.insert_text((50, 120), "Jingdong Wang1, Ke Sun1,2, Tianheng Cheng3, Borui Jiang4, Chaorui Deng1", fontsize=11)
    page1.insert_text((50, 138), "1Microsoft Research, 2Tsinghua University, 3Huazhong University of Science and Technology", fontsize=9)
    page1.insert_text((50, 152), "{jingdw, v-kesun}@microsoft.com", fontsize=9)
    page1.insert_text((50, 190), "Abstract - High-resolution representations are essential for position-sensitive vision problems.", fontsize=10)
    page1.insert_text((50, 240), "1. Introduction", fontsize=12)
    page1.insert_text((50, 260), "Visual recognition has been dominated by convolutional neural networks.", fontsize=10)

    # Page 2: References section followed by an Appendix (which should be excluded)
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((50, 80), "References", fontsize=14)
    page2.insert_text((50, 105), '[1] A. Krizhevsky, I. Sutskever, and G. E. Hinton, "ImageNet classification with deep convolutional neural networks," in NeurIPS, 2012.', fontsize=9)
    page2.insert_text((50, 135), '[2] K. He, X. Zhang, S. Ren, and J. Sun, "Deep residual learning for image recognition," in CVPR, 2016.', fontsize=9)
    page2.insert_text((50, 165), '[3] Vaswani, A., Shazeer, N., & Parmar, N. (2017). Attention is all you need. Advances in Neural Information Processing Systems, 30.', fontsize=9)
    
    page2.insert_text((50, 250), "Appendix A: Additional Implementation Details", fontsize=14)
    page2.insert_text((50, 275), "Here we describe the hyperparameter configuration in full detail.", fontsize=10)

    results = analyze_pdf_content(doc)
    doc.close()

    # 1. Verify Authors are extracted cleanly without superscripts or affiliations
    authors = results["authors"]
    assert len(authors) >= 4
    assert "Jingdong Wang" in authors
    assert "Ke Sun" in authors
    assert "Tianheng Cheng" in authors
    assert "Borui Jiang" in authors
    # Ensure affiliations were NOT treated as authors
    assert "Microsoft Research" not in authors
    assert "Tsinghua University" not in authors

    # 2. Verify References are extracted and structured
    refs = results["references"]
    assert len(refs) == 3
    ref_texts = [r["text"] for r in refs]
    assert any("ImageNet classification" in t for t in ref_texts)
    assert any("Deep residual learning" in t for t in ref_texts)
    assert any("Attention is all you need" in t for t in ref_texts)
    
    # 3. Check reference structured metadata
    ref1 = next(r for r in refs if "ImageNet classification" in r["text"])
    assert ref1["year"] == 2012
    assert "title" in ref1
    assert "authors" in ref1

    # 4. Verify Appendix is NOT present in references
    for r in refs:
        assert "Appendix A" not in r["text"]
        assert "hyperparameter" not in r["text"]

    # 5. Verify Document Structure (headings) is completely empty as requested
    assert results["headings"] == []


def test_doi_continuation_not_split_into_new_reference():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 80), "References", fontsize=14)
    # Ref 8 split across two lines, second line starts with 10.1088/...
    page.insert_text((50, 105), "8. Zhang, J.-S., Chen, A.-X., Abdel-Aty, M. Two atoms in dissipative cavities, J. Phys. B, 2010 DOI", fontsize=9)
    page.insert_text((50, 120), "10.1088/0953-4075/43/2/025501", fontsize=9)
    # Ref 9
    page.insert_text((50, 140), "9. Smith, J. Quantum systems and information dynamics. Nature 2021.", fontsize=9)

    refs = extract_academic_references(doc)
    doc.close()

    assert len(refs) == 2
    assert refs[0]["id"] == "8"
    assert "10.1088/0953-4075/43/2/025501" in refs[0]["text"]
    assert refs[1]["id"] == "9"
    assert "Quantum systems" in refs[1]["text"]


def test_preamble_conclusion_not_treated_as_reference_1():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 80), "References", fontsize=14)
    # Conclusion text appearing before reference 1
    page.insert_text((50, 105), "In this research, a fractional order compartmental framework for scrolling addiction is established.", fontsize=9)
    # Ref 1
    page.insert_text((50, 130), "1. Abdel-Aty, M., Obada, A. Quantum fields, Optics Review 2000.", fontsize=9)
    # Ref 2
    page.insert_text((50, 155), "2. Rehman, H.U. Soliton solutions, Alexandria Eng. J. 2024.", fontsize=9)

    refs = extract_academic_references(doc)
    doc.close()

    assert len(refs) == 2
    assert refs[0]["id"] == "1"
    assert "Abdel-Aty" in refs[0]["text"]
    assert "In this research" not in refs[0]["text"]
    assert refs[1]["id"] == "2"

