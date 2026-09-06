import pytest
from enrichment.parser import ReferenceParser

def test_extract_doi():
    text1 = "Vaswani et al. (2017). Attention is all you need. doi:10.48550/arXiv.1706.03762."
    text2 = "Smith, J. (2020). Paper. https://doi.org/10.1016/j.jhai.2020.01.002"
    text3 = "No DOI here"

    assert ReferenceParser.extract_doi(text1) == "10.48550/arXiv.1706.03762"
    assert ReferenceParser.extract_doi(text2) == "10.1016/j.jhai.2020.01.002"
    assert ReferenceParser.extract_doi(text3) is None

def test_extract_year():
    assert ReferenceParser.extract_year("Smith, J. (2020). Deep Learning...") == 2020
    assert ReferenceParser.extract_year("Einstein, A. (1935). Quantum paper.") == 1935
    assert ReferenceParser.extract_year("No year in text") is None

def test_parse_reference_with_quotes():
    raw = '[1] A. Einstein, "Can quantum-mechanical description of physical reality be considered complete?", Phys. Rev. 47, 777 (1935).'
    parsed = ReferenceParser.parse(raw)

    assert parsed.title == "Can quantum-mechanical description of physical reality be considered complete?"
    assert parsed.year == 1935
    assert len(parsed.authors) > 0

def test_parse_reference_apa_format():
    raw = "Vaswani, A., Shazeer, N., & Parmar, N. (2017). Attention is all you need. Advances in Neural Information Processing Systems, 30. https://doi.org/10.48550/arXiv.1706.03762"
    parsed = ReferenceParser.parse(raw)

    assert parsed.title == "Attention is all you need"
    assert parsed.year == 2017
    assert parsed.doi == "10.48550/arXiv.1706.03762"
    assert len(parsed.authors) >= 2

def test_parse_reference_initials():
    raw = "J. Smith, A. B. Johnson. Machine Learning in Healthcare Systems. Journal of AI, 2021."
    parsed = ReferenceParser.parse(raw)

    assert "Machine Learning" in parsed.title
    assert parsed.year == 2021
    assert len(parsed.authors) >= 1

def test_parse_user_reference_unquoted_with_initials():
    raw = (
        "Zhang, J.-S., Chen, A.-X., Abdel-Aty, M. "
        "Two atoms in dissipative cavities in dispersive limit: Entanglement sudden death and long-lived entanglement, "
        "Journal of Physics B Atomic Molecular and Optical Physics, 2010, 43(2), 025501 "
        "DOI: 10.1088/0953-4075/43/2/025501"
    )
    parsed = ReferenceParser.parse(raw)

    assert parsed.title == "Two atoms in dissipative cavities in dispersive limit: Entanglement sudden death and long-lived entanglement"
    assert len(parsed.authors) == 3
    assert parsed.authors[0]["family"] == "Zhang"
    assert parsed.authors[2]["family"] == "Abdel-Aty"
    assert parsed.year == 2010
    assert "Journal of Physics B" in parsed.journal
    assert parsed.doi == "10.1088/0953-4075/43/2/025501"
    assert parsed.reference_type == "journal-article"

def test_classify_not_book_chapter_on_embedded_ed():
    # Words like 'long-lived' or 'connected' should NOT trigger book-chapter
    text = "Two atoms in dissipative cavities in dispersive limit: Entanglement sudden death and long-lived entanglement"
    ref_type = ReferenceParser.classify_reference_type(text, arxiv_id="", isbn="", journal_str="Journal of Physics B")
    assert ref_type == "journal-article"

def test_parse_ieee_journal_tail_agrawal():
    raw = (
        "Om P. Agrawal, Ozlem Defterli, Dumitru Baleanu, "
        "Fractional Optimal Control Problems with Several State and Control Variables, "
        "Journal of Vibration and Control 16(13) (2010) 1967–1976 "
        "DOI: https://doi.org/10.1177/1077546310368943"
    )
    parsed = ReferenceParser.parse(raw)
    assert parsed.title == "Fractional Optimal Control Problems with Several State and Control Variables"
    assert len(parsed.authors) == 3
    assert parsed.year == 2010
    assert parsed.journal == "Journal of Vibration and Control"
    assert parsed.volume == "16"
    assert parsed.pages == "1967–1976"
    assert parsed.doi == "10.1177/1077546310368943"

def test_parse_ieee_journal_tail_vijayalakshmi():
    raw = (
        "Vijayalakshmi G.M, P. Roselyn Besi, Ali Akgul, "
        "Fractional commensurate model on Covid-19 with microbial coinfections: An optimal control analysis, "
        "Optimal Control Applications and Methods 45(4) (2024) 3093–3112 "
        "DOI: https://doi.org/10.1002/oca."
    )
    parsed = ReferenceParser.parse(raw)
    assert parsed.title == "Fractional commensurate model on Covid-19 with microbial coinfections: An optimal control analysis"
    assert len(parsed.authors) == 3
    assert parsed.year == 2024
    assert parsed.journal == "Optimal Control Applications and Methods"
    assert parsed.volume == "45"
    assert parsed.doi == "10.1002/oca"

def test_parse_with_broken_spaces_url_doi():
    raw = (
        "Vijayalakshmi G.M, M. Ariyanatchi, "
        "Adams–Bashforth Moulton Numerical Approach on Dengue Fractional Atangana Baleanu Caputo Model and Stability Analysis, "
        "International Journal of Applied and Computational Mathematics 10 (2024) 32 "
        "DOI: https: //doi.org/10.1007/s40819-023-01662-6"
    )
    parsed = ReferenceParser.parse(raw)
    assert parsed.title == "Adams–Bashforth Moulton Numerical Approach on Dengue Fractional Atangana Baleanu Caputo Model and Stability Analysis"
    assert len(parsed.authors) == 2
    assert parsed.year == 2024
    assert parsed.volume == "10"
    assert parsed.pages == "32"
    assert parsed.doi == "10.1007/s40819-023-01662-6"
