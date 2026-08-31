import re
from typing import Dict, List, Any, Optional, Tuple
from enrichment.parser import ParsedReference
from enrichment.string_utils import normalize_string, calculate_string_similarity, match_authors

class DOIVerifier:
    """
    Dedicated DOI Verification & Integrity Layer.
    Validates syntax, detects metadata conflicts across providers, reconciles with arXiv,
    and prevents contaminated/suspicious third-party DOIs from becoming canonical.
    """

    DOI_REGEX = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$", re.IGNORECASE)
    ARXIV_DOI_REGEX = re.compile(r"^10\.48550/arXiv\.(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+/\d{7})$", re.IGNORECASE)

    # Known reprint / third-party aggregator prefixes that often misattribute original classic papers
    SUSPICIOUS_REPRINT_PREFIXES = {
        "10.65215": "Third-party reprint repository (e.g. Shenzhen Medical Academy re-index)",
    }

    @classmethod
    def normalize_doi(cls, raw_doi: Optional[str]) -> Optional[str]:
        """Clean and normalize raw DOI string."""
        if not raw_doi or not isinstance(raw_doi, str):
            return None
        doi = raw_doi.strip()
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
        doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
        doi = doi.rstrip(".,; ")
        if doi.endswith(")") and "(" not in doi:
            doi = doi[:-1]
        doi = doi.strip()
        return doi if doi else None

    @classmethod
    def is_valid_syntax(cls, doi: Optional[str]) -> bool:
        """Check if normalized string matches strict DOI syntax."""
        clean = cls.normalize_doi(doi)
        if not clean:
            return False
        return bool(cls.DOI_REGEX.match(clean))

    @classmethod
    def extract_arxiv_id(cls, text_or_doi: Optional[str]) -> Optional[str]:
        """Extract clean arXiv identifier from DOI or string."""
        if not text_or_doi:
            return None
        clean = cls.normalize_doi(text_or_doi) or text_or_doi
        m = cls.ARXIV_DOI_REGEX.match(clean)
        if m:
            return m.group(1)
        m2 = re.search(r"arXiv:\s*(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+/\d{7})", text_or_doi, re.IGNORECASE)
        if m2:
            return m2.group(1)
        return None

    @classmethod
    def verify(
        cls,
        parsed_ref: ParsedReference,
        provider_candidates: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Comprehensive verification of DOI across parsed reference and provider candidates.
        Returns:
            - status: "verified" | "conflict" | "unverified" | "missing"
            - canonical_doi: verified DOI or None
            - reconciled_with_arxiv: bool
            - confidence: float
            - reason: explanation of verification outcome
            - conflicts: list of rejected/conflicting DOIs
            - unverified_dois: list of secondary DOIs that failed strict verification
        """
        conflicts = []
        unverified_dois = []
        candidate_dois: List[Tuple[str, str, Dict[str, Any]]] = []  # (provider, doi, candidate_dict)

        # 1. Gather all candidate DOIs from providers and parsed reference
        if parsed_ref.doi:
            clean_parsed = cls.normalize_doi(parsed_ref.doi)
            if clean_parsed:
                candidate_dois.append(("parsed", clean_parsed, {"title": parsed_ref.title, "authors": parsed_ref.authors, "year": parsed_ref.year}))

        for prov_name, cands in provider_candidates.items():
            for c in cands:
                c_doi = cls.normalize_doi(c.get("doi"))
                if c_doi:
                    candidate_dois.append((prov_name, c_doi, c))

        # Check if reference has arXiv identifier
        ref_arxiv = parsed_ref.arxiv_id or cls.extract_arxiv_id(parsed_ref.original_text)

        if not candidate_dois and not ref_arxiv:
            return {
                "status": "missing",
                "canonical_doi": None,
                "reconciled_with_arxiv": False,
                "confidence": 0.0,
                "reason": "No DOI or arXiv identifier present in reference or provider results.",
                "conflicts": [],
                "unverified_dois": []
            }

        # 2. Evaluate each candidate DOI
        verified_dois = []

        for prov, doi, cand in candidate_dois:
            if not cls.is_valid_syntax(doi):
                unverified_dois.append({
                    "value": doi,
                    "source": prov,
                    "reason": "Invalid DOI syntax",
                    "status": "unverified"
                })
                continue

            # Check if this DOI prefix is known to be a suspicious reprint
            prefix = doi.split("/")[0] if "/" in doi else ""
            is_suspicious_prefix = prefix in cls.SUSPICIOUS_REPRINT_PREFIXES

            # Check consistency with parsed reference
            cand_title = cand.get("title") or ""
            cand_authors = cand.get("authors") or []
            cand_year = cand.get("year")

            title_sim = calculate_string_similarity(parsed_ref.title, cand_title) if parsed_ref.title else 0.5
            author_sim = match_authors(parsed_ref.authors or parsed_ref.raw_authors, cand_authors) if parsed_ref.authors else 0.5

            year_diff = abs(int(parsed_ref.year) - int(cand_year)) if (parsed_ref.year and cand_year) else 0

            # If DOI prefix is suspicious reprint and original reference is older or has arXiv
            if is_suspicious_prefix:
                conflict_reason = f"DOI prefix '{prefix}' belongs to {cls.SUSPICIOUS_REPRINT_PREFIXES[prefix]}. Incompatible with original source."
                conflicts.append({
                    "field": "doi",
                    "provider": prov,
                    "rejected_value": doi,
                    "reason": conflict_reason,
                    "status": "conflict"
                })
                continue

            # If title or authors mismatch significantly
            if title_sim < 0.65 or (author_sim < 0.20 and len(parsed_ref.authors) > 0):
                conflicts.append({
                    "field": "doi",
                    "provider": prov,
                    "rejected_value": doi,
                    "reason": f"Metadata mismatch (title_sim={title_sim:.2f}, author_sim={author_sim:.2f})",
                    "status": "conflict"
                })
                continue

            # If passed consistency checks
            verified_dois.append({
                "doi": doi,
                "source": prov,
                "title_sim": title_sim,
                "author_sim": author_sim,
                "year_diff": year_diff
            })

        # 3. Handle arXiv reconciliation
        if ref_arxiv:
            arxiv_doi = f"10.48550/arXiv.{ref_arxiv}"
            # If no genuine publisher DOI verified or if all candidate DOIs had conflicts
            if not verified_dois:
                return {
                    "status": "verified",
                    "canonical_doi": arxiv_doi,
                    "reconciled_with_arxiv": True,
                    "confidence": 0.98,
                    "reason": f"Reconciled with authentic arXiv repository DOI ({arxiv_doi}).",
                    "conflicts": conflicts,
                    "unverified_dois": unverified_dois
                }

        # 4. Select canonical DOI
        if verified_dois:
            # Prefer parsed or Crossref or OpenAlex verified DOI with lowest year diff and highest title_sim
            verified_dois.sort(key=lambda x: (x["source"] == "parsed", x["source"] == "crossref", x["title_sim"]), reverse=True)
            top = verified_dois[0]
            return {
                "status": "verified",
                "canonical_doi": top["doi"],
                "reconciled_with_arxiv": bool(ref_arxiv and cls.extract_arxiv_id(top["doi"])),
                "confidence": round(0.85 + 0.15 * top["title_sim"], 2),
                "reason": f"Verified with {top['source']} metadata consistency (title_sim={top['title_sim']:.2f}).",
                "conflicts": conflicts,
                "unverified_dois": unverified_dois
            }

        # If we had candidates but all failed verification
        if conflicts:
            return {
                "status": "conflict",
                "canonical_doi": None,
                "reconciled_with_arxiv": False,
                "confidence": 0.20,
                "reason": "All candidate DOIs presented metadata conflicts or suspicious repository origins.",
                "conflicts": conflicts,
                "unverified_dois": unverified_dois
            }

        return {
            "status": "unverified",
            "canonical_doi": None,
            "reconciled_with_arxiv": False,
            "confidence": 0.30,
            "reason": "DOI could not be conclusively verified against trusted bibliographic sources.",
            "conflicts": conflicts,
            "unverified_dois": unverified_dois
        }
