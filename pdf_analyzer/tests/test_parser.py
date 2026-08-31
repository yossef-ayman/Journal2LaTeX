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
