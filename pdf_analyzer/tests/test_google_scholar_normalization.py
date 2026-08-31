import pytest
from enrichment.providers.google_scholar import GoogleScholarProvider

def test_normalization_missing_and_partial_fields():
    provider = GoogleScholarProvider()
    
    organic = [
        {
            "position": 1,
            "title": "Minimal Paper Title",
            "link": "https://example.com/paper",
            # snippet missing
            # publication_info missing
            # inline_links missing
            # resources missing
        },
        {
            "position": 2,
            "title": "Paper with authors only",
            "link": "https://example.com/paper2",
            "publication_info": {
                "summary": "J Doe, 2021",
                "authors": ["John Doe"]
            },
            "inline_links": {
                "cited_by": {"total": 5, "link": "https://scholar.google.com/cites=2"},
            }
        }
    ]

    normalized = provider._normalize_organic_results(organic, "test query", "https://scholar.google.com")
    assert len(normalized) == 2
    
    # Check item 1
    item1 = normalized[0]
    assert item1["position"] == 1
    assert item1["title"] == "Minimal Paper Title"
    assert item1["snippet"] == ""
    assert item1["citations"]["count"] is None
    assert item1["citations"]["link"] is None
    assert item1["versions"]["count"] is None
    assert item1["versions"]["link"] is None
    assert item1["resources"] == []
    assert item1["related_articles"]["link"] is None
    assert item1["cluster_id"] is None

    # Check item 2
    item2 = normalized[1]
    assert item2["position"] == 2
    assert item2["publication"]["year"] == 2021
    assert len(item2["authors"]) == 1
    assert item2["authors"][0]["name"] == "John Doe"
    assert item2["authors"][0]["author_id"] is None
    assert item2["citations"]["count"] == 5

def test_build_query_priority():
    provider = GoogleScholarProvider()
    from enrichment.parser import ParsedReference

    ref_doi = ParsedReference(original_text="Raw", title="Paper Title", doi="10.1000/182")
    assert provider.build_query(ref_doi) == "doi:10.1000/182"

    ref_title_author = ParsedReference(original_text="Raw", title="Paper Title", authors=[{"family": "Smith", "name": "John Smith"}])
    assert provider.build_query(ref_title_author) == "Paper Title Smith"

    ref_title_year = ParsedReference(original_text="Raw", title="Paper Title", year=2024)
    assert provider.build_query(ref_title_year) == "Paper Title 2024"
