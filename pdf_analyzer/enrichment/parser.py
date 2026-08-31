import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enrichment.string_utils import parse_author_name

@dataclass
class ParsedReference:
    original_text: str
    title: str = ""
    authors: List[Dict[str, str]] = field(default_factory=list)
    raw_authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    reference_type: str = "journal-article"  # journal-article, proceedings-article, book, book-chapter, preprint, unknown
    journal: str = ""
    publisher: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    isbn: str = ""
    arxiv_id: str = ""

class ReferenceParser:
    """
    Academic Reference Intelligence Parser.
    Extracts title, structured authors (given/family), year, reference type,
    journal/venue, publisher, volume, issue, pages, DOI, ISBN, and arXiv ID.
    """

    KNOWN_PUBLISHERS = [
        "Springer", "Elsevier", "IEEE", "ACM", "Nature Publishing Group",
        "Oxford University Press", "Cambridge University Press", "Wiley",
        "Routledge", "O'Reilly", "MIT Press", "Morgan Kaufmann",
        "Academic Press", "Taylor & Francis", "Frontiers Media", "MDPI",
        "Sage Publications", "De Gruyter", "Prentice Hall", "Addison-Wesley"
    ]

    CONFERENCE_KEYWORDS = [
        "proceedings", "proc.", "conference", "symposium", "workshop",
        "neurips", "icml", "cvpr", "iclr", "emnlp", "acl", "naacl",
        "iccv", "eccv", "kdd", "aaai", "ijcai", "sigir", "sigcomm"
    ]

    @staticmethod
    def extract_doi(text: str) -> Optional[str]:
        """Extract clean DOI from text."""
        match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text)
        if match:
            doi = match.group(0).rstrip(".,;")
            if doi.endswith(")") and "(" not in doi:
                doi = doi[:-1]
            return doi
        return None

    @staticmethod
    def extract_isbn(text: str) -> Optional[str]:
        """Extract ISBN-10 or ISBN-13 identifier."""
        match = re.search(r"\b(?:ISBN(?:-1[03])?:?\s*)?([0-9Xx]{1}[0-9Xx\-]{8,16}[0-9Xx]{1})\b", text, re.IGNORECASE)
        if match:
            candidate = match.group(1).replace("-", "").strip()
            if len(candidate) in (10, 13):
                return match.group(1).strip()
        return None

    @staticmethod
    def extract_year(text: str) -> Optional[int]:
        """Extract 4-digit publication year (between 1800 and 2099)."""
        matches = re.findall(r"\b(1[89]\d\d|20\d\d)\b", text)
        if matches:
            paren_match = re.search(r"\((1[89]\d\d|20\d\d)\)", text)
            if paren_match:
                return int(paren_match.group(1))
            return int(matches[0])
        return None

    @classmethod
    def extract_volume_issue_pages(cls, text: str) -> Tuple[str, str, str]:
        """Extract volume, issue number, and page ranges from citation text."""
        volume, issue, pages = "", "", ""
        
        # 1. Pattern like: 12(3): 45-67 or 12(3), 45-67
        m1 = re.search(r"\b(\d+)\s*\(\s*(\d+|[A-Za-z0-9]+)\s*\)\s*[:,\s]\s*(?:pp\.?\s*)?([A-Za-z0-9]+(?:\s*[-–—]\s*[A-Za-z0-9]+)?)\b", text)
        if m1:
            volume = m1.group(1)
            issue = m1.group(2)
            pages = m1.group(3).replace(" ", "")
            return volume, issue, pages

        # 2. Pattern like: vol. 12, no. 3, pp. 45-67
        vol_m = re.search(r"\b(?:vol\.?|volume)\s*(\d+)\b", text, re.IGNORECASE)
        if vol_m:
            volume = vol_m.group(1)
            
        iss_m = re.search(r"\b(?:no\.?|issue|number)\s*(\d+|[A-Za-z0-9]+)\b", text, re.IGNORECASE)
        if iss_m:
            issue = iss_m.group(1)

        pg_m = re.search(r"\b(?:pp\.?|pages?)\s*([A-Za-z0-9]+(?:\s*[-–—]\s*[A-Za-z0-9]+)?)\b", text, re.IGNORECASE)
        if pg_m:
            pages = pg_m.group(1).replace(" ", "")

        return volume, issue, pages

    @classmethod
    def extract_publisher(cls, text: str) -> str:
        """Identify academic publisher name if present."""
        for pub in cls.KNOWN_PUBLISHERS:
            if re.search(r"\b" + re.escape(pub) + r"\b", text, re.IGNORECASE):
                return pub
        return ""

    @classmethod
    def classify_reference_type(cls, text: str, arxiv_id: str, isbn: str, journal_str: str) -> str:
        """Classify academic reference type into standard taxonomy."""
        t_lower = text.lower()
        j_lower = journal_str.lower()

        # 1. Preprint
        if arxiv_id or "arxiv" in t_lower or "biorxiv" in t_lower or "medrxiv" in t_lower or "preprint" in t_lower:
            return "preprint"

        # 2. Conference / Proceedings Article
        for kw in cls.CONFERENCE_KEYWORDS:
            if kw in t_lower or kw in j_lower:
                return "proceedings-article"

        # 3. Book Chapter
        if re.search(r"\bin:?\s+[^,]+(?:\(eds?\.?\)|ed\.?)", text, re.IGNORECASE) or re.search(r"\bchapter\s+\d+\b", t_lower):
            return "book-chapter"

        # 4. Book
        if isbn or "book" in j_lower:
            return "book"

        pub = cls.extract_publisher(text)
        if pub and ("press" in pub.lower() or "springer" in pub.lower() or "wiley" in pub.lower()):
            if not journal_str or "journal" not in j_lower:
                if "pp." not in text.lower() and not re.search(r"\b\d+\(\d+\)", text):
                    return "book"

        # 5. Default Journal Article
        return "journal-article"

    @classmethod
    def parse(cls, raw_text: str) -> ParsedReference:
        """Parse raw reference text into complete structured bibliographic entity."""
        clean_text = raw_text.strip()
        clean_text_no_prefix = re.sub(r"^(?:\[\d+\]|\(\d+\)|\d+\.)\s*", "", clean_text)
        
        doi = cls.extract_doi(clean_text_no_prefix) or ""
        isbn = cls.extract_isbn(clean_text_no_prefix) or ""
        year = cls.extract_year(clean_text_no_prefix)
        volume, issue, pages = cls.extract_volume_issue_pages(clean_text_no_prefix)
        publisher = cls.extract_publisher(clean_text_no_prefix)
        
        # arXiv match
        arxiv_match = re.search(r"arXiv:\s*(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+/\d{7})", clean_text_no_prefix, re.IGNORECASE)
        arxiv_id = arxiv_match.group(1) if arxiv_match else ""

        title = ""
        journal = ""
        raw_authors: List[str] = []
        
        # Check quoted title: "Title" or “Title” or 'Title'
        quote_match = re.search(r"[\"“']([^\"”']{8,})[\"”']", clean_text_no_prefix)
        if quote_match:
            title = quote_match.group(1).strip()
            prefix = clean_text_no_prefix[:quote_match.start()].strip()
            suffix = clean_text_no_prefix[quote_match.end():].strip()
            
            if prefix:
                raw_authors = cls._parse_authors_part(prefix)
            if suffix:
                journal = cls._clean_journal_part(suffix)
        else:
            # Attempt year-split parsing (APA style: Authors (Year). Title. Journal...)
            year_match = re.search(r"\((1[89]\d\d|20\d\d)\)[\.,\s]*", clean_text_no_prefix)
            if year_match:
                authors_part = clean_text_no_prefix[:year_match.start()].strip()
                remainder = clean_text_no_prefix[year_match.end():].strip()
                
                if authors_part:
                    raw_authors = cls._parse_authors_part(authors_part)
                
                if remainder:
                    parts = re.split(r"[\.:]\s+", remainder, maxsplit=1)
                    title = parts[0].strip()
                    if len(parts) > 1:
                        journal = cls._clean_journal_part(parts[1])
            else:
                sentences = [s.strip() for s in re.split(r"(?<!\b[A-Z])\.(?!\d)\s+", clean_text_no_prefix) if s.strip()]
                if len(sentences) >= 3:
                    raw_authors = cls._parse_authors_part(sentences[0])
                    title = sentences[1]
                    journal = cls._clean_journal_part(" ".join(sentences[2:]))
                elif len(sentences) == 2:
                    if re.search(r"\b(?:and|&)\b|,\s*[A-Z]\b", sentences[0]):
                        raw_authors = cls._parse_authors_part(sentences[0])
                        title = sentences[1]
                    else:
                        title = sentences[0]
                        journal = cls._clean_journal_part(sentences[1])
                else:
                    title = clean_text_no_prefix

        # Cleanup title (strip trailing URLs, DOIs, years)
        title = re.sub(r"\bhttps?://\S+", "", title).strip()
        title = re.sub(r"\bdoi:\S+", "", title, flags=re.IGNORECASE).strip()
        title = re.sub(r"\bISBN:\S+", "", title, flags=re.IGNORECASE).strip()
        title = title.rstrip(".,;:")

        parsed_authors = [parse_author_name(a) for a in raw_authors if a.strip()]

        ref_type = cls.classify_reference_type(clean_text_no_prefix, arxiv_id, isbn, journal)

        return ParsedReference(
            original_text=raw_text,
            title=title,
            authors=parsed_authors,
            raw_authors=raw_authors,
            year=year,
            reference_type=ref_type,
            journal=journal,
            publisher=publisher,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi,
            isbn=isbn,
            arxiv_id=arxiv_id
        )

    @staticmethod
    def _parse_authors_part(text: str) -> List[str]:
        """Split author string into candidate author names."""
        text = text.rstrip(".")
        text = re.sub(r"\bet\s+al\.?", "", text, flags=re.IGNORECASE)
        clauses = re.split(r"\s+and\s+|\s*&\s*|\s*;\s*", text)
        authors = []
        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue
            if re.search(r"(?<=\.)\s*,\s*", clause):
                sub_parts = re.split(r"(?<=\.)\s*,\s*", clause)
                for sp in sub_parts:
                    if sp.strip():
                        authors.append(sp.strip())
            else:
                parts = [p.strip() for p in clause.split(",") if p.strip()]
                if len(parts) >= 2 and len(parts) % 2 == 0:
                    for i in range(0, len(parts), 2):
                        authors.append(f"{parts[i]}, {parts[i+1]}")
                elif len(parts) == 1:
                    authors.append(clause)
                else:
                    for p in parts:
                        authors.append(p)
        return [a for a in authors if len(a) >= 2]

    @staticmethod
    def _clean_journal_part(text: str) -> str:
        """Clean and extract journal name from suffix string."""
        text = re.sub(r"\bhttps?://\S+", "", text)
        text = re.sub(r"\bdoi:\S+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bISBN:\S+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\b\d+\s*\(\d+\)\s*:\s*\d+(?:-\d+)?", "", text)
        text = re.sub(r"\bvol\.?\s*\d+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bpp\.?\s*\d+(?:-\d+)?", "", text, flags=re.IGNORECASE)
        text = text.strip(".,;: ")
        return text[:100]
