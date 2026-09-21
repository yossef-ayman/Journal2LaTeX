import os
import sys
import re
from typing import Dict, List, Any, Optional, Tuple
import xml.etree.ElementTree as ET
from xml.dom import minidom

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
import fitz  # PyMuPDF

app = FastAPI(title="Academic Reference Explorer & PDF Analyzer API")

# Enable secure CORS for standalone frontend development on localhost/127.0.0.1
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Check for frontend directory
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")
if not os.path.exists(FRONTEND_DIR):
    FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

if os.path.exists(FRONTEND_DIR):
    css_dir = os.path.join(FRONTEND_DIR, "css")
    js_dir = os.path.join(FRONTEND_DIR, "js")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


def clean_text(text: str) -> str:
    """Normalize whitespace, handle line-break hyphens, and strip text."""
    if not text:
        return ""
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip()


def safe_xml_text(val: Any) -> str:
    """Sanitize text for XML output."""
    if val is None:
        return ""
    s = str(val)
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", s)


def is_arabic_text(text: str) -> bool:
    """Check if text contains Arabic characters."""
    return bool(re.search(r"[\u0600-\u06FF]", text))


def get_sorted_blocks(page: fitz.Page) -> List[dict]:
    """
    Extract text blocks from a PyMuPDF page, sorting them in natural reading order
    even for two-column, multi-column layouts, and 2-page side-by-side spreads.
    """
    page_rect = page.rect
    width = page_rect.width
    height = page_rect.height
    
    # Check if physical page is a 2-page spread (landscape aspect ratio width > height * 1.15)
    is_two_page_spread = width > height * 1.15

    def sort_viewport_blocks(text_blocks: List[dict], v_width: float, x_offset: float = 0.0) -> List[dict]:
        if not text_blocks:
            return []
            
        col_split = x_offset + (v_width / 2.0)
        left_blocks = [b for b in text_blocks if b["x1"] <= col_split * 1.1 and (b["x1"] - b["x0"]) < v_width * 0.55]
        right_blocks = [b for b in text_blocks if b["x0"] >= col_split * 0.85 and (b["x1"] - b["x0"]) < v_width * 0.55]
        
        is_multi_column = len(left_blocks) >= 2 and len(right_blocks) >= 2
        
        if is_multi_column:
            top_spanning = []
            left_col = []
            right_col = []
            bottom_spanning = []
            
            for b in text_blocks:
                b_width = b["x1"] - b["x0"]
                mid_x = (b["x0"] + b["x1"]) / 2.0
                
                if b_width > v_width * 0.55:
                    if not left_col and not right_col:
                        top_spanning.append(b)
                    else:
                        bottom_spanning.append(b)
                elif mid_x < col_split:
                    left_col.append(b)
                else:
                    right_col.append(b)
                    
            left_col.sort(key=lambda b: b["y0"])
            right_col.sort(key=lambda b: b["y0"])
            top_spanning.sort(key=lambda b: b["y0"])
            bottom_spanning.sort(key=lambda b: b["y0"])
            
            return top_spanning + left_col + right_col + bottom_spanning
        else:
            text_blocks.sort(key=lambda b: (b["y0"], b["x0"]))
            return text_blocks

    raw_blocks = page.get_text("blocks")
    all_blocks = []
    for b in raw_blocks:
        if len(b) >= 5 and b[4].strip():
            all_blocks.append({
                "bbox": (b[0], b[1], b[2], b[3]),
                "x0": b[0],
                "y0": b[1],
                "x1": b[2],
                "y1": b[3],
                "text": b[4]
            })

    if not all_blocks:
        return []

    if is_two_page_spread:
        mid_page_x = width / 2.0
        left_page_blocks = [b for b in all_blocks if (b["x0"] + b["x1"]) / 2.0 < mid_page_x]
        right_page_blocks = [b for b in all_blocks if (b["x0"] + b["x1"]) / 2.0 >= mid_page_x]
        
        sorted_left = sort_viewport_blocks(left_page_blocks, mid_page_x, 0.0)
        sorted_right = sort_viewport_blocks(right_page_blocks, mid_page_x, mid_page_x)
        return sorted_left + sorted_right
    else:
        return sort_viewport_blocks(all_blocks, width, 0.0)


def extract_doi_and_arxiv(text_full: str) -> Dict[str, Optional[str]]:
    """Extract DOI and arXiv IDs from full text."""
    doi = None
    arxiv_id = None
    
    doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text_full)
    if doi_match:
        doi = doi_match.group(0).rstrip(".,;")
        
    arxiv_match = re.search(r"arXiv:\s*(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+/\d{7})", text_full, re.IGNORECASE)
    if arxiv_match:
        arxiv_id = arxiv_match.group(1)
        
    return {"doi": doi, "arxiv_id": arxiv_id}


def is_valid_author_name(name: str) -> bool:
    """Validate extracted author name strictly (initials allowed, no institutions or numbers)."""
    name_clean = clean_text(name)
    name_clean = re.sub(r"^[\d\*\†\‡\§\^,#\-]+|[\d\*\†\‡\§\^,#\-\.]+$", "", name_clean).strip()
    name_clean = re.sub(r"^(?:Dr\.|Prof\.|Eng\.|Mr\.|Ms\.|Mrs\.|Ph\.D\.|أ\.D\.|أ\.د\.|د\.|م\.|أ\.|الأستاذ|الدكتور|الباحث)\s*", "", name_clean, flags=re.IGNORECASE).strip()
    
    if len(name_clean) < 3 or len(name_clean) > 60:
        return False
        
    name_lower = name_clean.lower()
    INVALID_AUTHOR_KEYWORDS = [
        "ieee", "elsevier", "springer", "mdpi", "acm", "wiley", "nature", "science", "arxiv", "biorxiv",
        "microsoft", "office", "user", "creator", "author", "admin", "writer", "distiller", "acrobat", "latex", "tex",
        "university", "dept", "department", "institute", "school", "college", "lab", "laboratory", "faculty",
        "corporation", "corp", "inc", "ltd", "center", "centre", "editor", "guest", "staff", "fellow", "member",
        "journal", "proceeding", "transactions", "symposium", "conference", "society", "abstract", "keywords",
        "introduction", "vol", "no", "pp", "pages", "received", "accepted", "revised", "copyright", "rights",
        "corresponding", "address", "email", "mail", "tel", "phone", "fax", "orcid", "http", "www", "github", "doi",
        "جامعة", "كلية", "قسم", "معهد", "مركز", "مختبر", "مجلة", "مؤتمر", "بحث", "ملخص", "دراسة", "المقدمة", "الباحث"
    ]
    
    for kw in INVALID_AUTHOR_KEYWORDS:
        if kw in name_lower:
            return False
            
    if "@" in name_lower or "http" in name_lower or "www." in name_lower or "doi:" in name_lower:
        return False
        
    if any(char.isdigit() for char in name_clean):
        return False
        
    words = name_clean.split()
    if len(words) < 2 or len(words) > 6:
        return False
        
    if not is_arabic_text(name_clean):
        valid_particles = {"van", "der", "den", "de", "von", "al", "el", "bin", "ibn", "da", "di", "del", "du"}
        for w in words:
            w_strip = w.rstrip(".,")
            if w_strip.lower() in valid_particles:
                continue
            if not w_strip or not w_strip[0].isupper():
                return False
                
    return True


def extract_manuscript_authors(doc: fitz.Document, title_y_end: float, abstract_y_start: float, metadata: dict) -> Tuple[List[str], List[str]]:
    """
    Extract clean manuscript author names and affiliations with high precision.
    Strips footnotes, superscripts, emails, and institutional noise.
    """
    authors = []
    affiliations = []
    page_count = doc.page_count
    if page_count == 0:
        return ["Unknown Author"], []

    p1 = doc[0]
    p1_height = p1.rect.height
    p1_blocks = get_sorted_blocks(p1)

    if abstract_y_start <= title_y_end + 5:
        abstract_y_start = p1_height * 0.60

    author_blocks = []
    for b in p1_blocks:
        if (title_y_end - 10) <= b["y0"] <= (abstract_y_start + 20):
            author_blocks.append(b)

    if not author_blocks:
        for b in p1_blocks:
            if (title_y_end - 10) <= b["y0"] <= (p1_height * 0.50):
                author_blocks.append(b)

    affiliation_keywords = [
        "university", "department", "dept", "institute", "faculty", "school", "college",
        "laboratory", "lab", "center", "centre", "corporation", "inc.", "ltd.", "gmbh",
        "hospital", "clinic", "polytechnic", "academy", "universität", "université",
        "جامعة", "كلية", "قسم", "معهد", "مركز", "مختبر", "أكاديمية", "مستشفى"
    ]

    for b in author_blocks:
        txt = b["text"].strip()
        if not txt:
            continue

        txt_clean = re.sub(r"\((?:Student\s+)?Member,\s*IEEE\)", "", txt, flags=re.IGNORECASE)
        txt_clean = re.sub(r"\((?:Fellow|Senior\s+Member),\s*IEEE\)", "", txt_clean, flags=re.IGNORECASE)

        lines = [clean_text(l) for l in txt_clean.split("\n") if clean_text(l)]
        for line in lines:
            line_lower = line.lower()

            if "@" in line or any(ak in line_lower for ak in affiliation_keywords):
                if len(line) < 160 and not any(kw in line_lower for kw in ["abstract", "introduction", "keywords", "index terms"]):
                    affiliations.append(clean_text(line))
                continue

            line_no_email = re.sub(r"\(?[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\)?", "", line).strip()
            line_stripped = re.sub(r"[\d\*\†\‡\§\^#\+]+", "", line_no_email).strip()
            line_stripped = line_stripped.rstrip(".")

            parts = re.split(r"\s+and\s+|\s*,\s*|\s*;\s*|\s*&\s*|\s*و\s*|\s*،\s*", line_stripped)
            for part in parts:
                p_clean = clean_text(part)
                if is_valid_author_name(p_clean):
                    authors.append(p_clean)

    if not authors:
        meta_auth = metadata.get("author")
        if meta_auth:
            for a in re.split(r"[,;]| and | و |،", meta_auth):
                a_clean = clean_text(a)
                a_stripped = re.sub(r"[\d\*\†\‡\§\^#\+]+", "", a_clean).strip()
                if is_valid_author_name(a_stripped):
                    authors.append(a_stripped)

    deduped_authors = list(dict.fromkeys(authors))
    if not deduped_authors:
        deduped_authors = ["Unknown Author"]

    deduped_affils = list(dict.fromkeys(affiliations))[:5]
    return deduped_authors, deduped_affils


def extract_academic_references(doc: fitz.Document) -> List[Dict[str, Any]]:
    """
    State-of-the-art reference extraction from academic PDF documents.
    Extracts all references, normalizes them, and extracts structured metadata (title, authors, year, doi, venue).
    """
    page_count = doc.page_count
    if page_count == 0:
        return []

    ref_header_pattern = re.compile(
        r"^(?:\d+[\.\)]?\s*|[IVXLCDM]+[\.\)]?\s*|\[\s*\d+\s*\]\s*)?(?:references|bibliography|literature cited|works cited|references and notes|المراجع|قائمة المراجع|المصادر والمراجع|المصادر|ثبت المراجع)\b[\s:—\-]*$",
        re.IGNORECASE
    )

    stop_header_pattern = re.compile(
        r"^(?:\d+[\.\)]?\s*|[IVXLCDM]+[\.\)]?\s*)?(?:appendix(?:\s+[A-Z0-9]+)?|appendices|author biograph(?:y|ies)|biographical notes?|about the authors?|الملحق|سيرة المؤلفين)\b",
        re.IGNORECASE
    )

    in_ref_section = False
    ref_raw_lines = []

    for page_num in range(page_count):
        page = doc[page_num]
        p_height = page.rect.height
        header_limit = p_height * 0.08
        footer_start = p_height * 0.92

        blocks = get_sorted_blocks(page)

        for b in blocks:
            text = b["text"].strip()
            if not text:
                continue

            lines = [clean_text(l) for l in text.split("\n") if clean_text(l)]

            for line in lines:
                if not in_ref_section:
                    if ref_header_pattern.match(line):
                        in_ref_section = True
                        continue
                else:
                    if (b["y0"] < header_limit or b["y1"] > footer_start) and len(line) < 100:
                        continue

                    if ref_raw_lines and stop_header_pattern.match(line):
                        in_ref_section = False
                        break

                    ref_raw_lines.append(line)

        if not in_ref_section and ref_raw_lines:
            break

    if not ref_raw_lines:
        return []

    raw_references: List[Dict[str, str]] = []
    
    def _is_doi_or_url(s: str) -> bool:
        t = s.strip()
        return bool(re.match(r"^(?:https?://|doi:\s*|doi\.org/|10\.\d{4,9}/|\d{4,9}/)", t, re.IGNORECASE))

    def _match_ref_start(s: str):
        if _is_doi_or_url(s):
            return None
        return re.match(r"^(?:\[\s*(\d{1,4})\s*\]|\(\s*(\d{1,4})\s*\)\s*|(\d{1,4})\s*[\.\)]\s+)(.*)", s)

    numbered_matches = [
        _match_ref_start(l)
        for l in ref_raw_lines
    ]
    num_count = sum(1 for m in numbered_matches if m is not None)

    if num_count >= 2:
        current_id = "1"
        current_text_parts = []
        has_started_refs = False

        for line in ref_raw_lines:
            num_m = _match_ref_start(line)
            # Ensure line isn't a DOI continuation when previous line ended with DOI indicator
            prev_ended_with_doi = (
                bool(current_text_parts) and
                bool(re.search(r"\bdoi:?$", current_text_parts[-1].strip(), re.IGNORECASE))
            )
            if num_m and not prev_ended_with_doi:
                if current_text_parts and has_started_refs:
                    raw_references.append({
                        "id": current_id,
                        "text": " ".join(current_text_parts)
                    })
                has_started_refs = True
                current_id = num_m.group(1) or num_m.group(2) or num_m.group(3) or str(len(raw_references) + 1)
                rem = num_m.group(4).strip()
                current_text_parts = [rem] if rem else []
            else:
                if has_started_refs:
                    if current_text_parts:
                        if current_text_parts[-1].endswith("-") and not current_text_parts[-1].endswith(" -"):
                            current_text_parts[-1] = current_text_parts[-1][:-1] + line
                        else:
                            current_text_parts.append(line)
                    else:
                        current_text_parts.append(line)

        if current_text_parts and has_started_refs:
            raw_references.append({
                "id": current_id,
                "text": " ".join(current_text_parts)
            })

    else:
        current_parts = []
        for line in ref_raw_lines:
            is_start = False
            if not _is_doi_or_url(line):
                if re.match(r"^[A-Z\u0600-\u06FF][a-zA-Z\u0600-\u06FF\s\.,\-–&]+\s*(?:\(\s*1[89]\d\d|20\d\d\s*\)|1[89]\d\d\.|20\d\d\.)", line):
                    is_start = True
                elif re.match(r"^[A-Z\u0600-\u06FF][a-zA-Z\u0600-\u06FF\-]+,\s+[A-Z]\.", line) and not (current_parts and not current_parts[-1].endswith(".")):
                    is_start = True

            if is_start and current_parts:
                raw_references.append({
                    "id": str(len(raw_references) + 1),
                    "text": " ".join(current_parts)
                })
                current_parts = [line]
            else:
                if current_parts:
                    if current_parts[-1].endswith("-") and not current_parts[-1].endswith(" -"):
                        current_parts[-1] = current_parts[-1][:-1] + line
                    else:
                        current_parts.append(line)
                else:
                    current_parts.append(line)

        if current_parts:
            raw_references.append({
                "id": str(len(raw_references) + 1),
                "text": " ".join(current_parts)
            })

    from enrichment.parser import ReferenceParser
    structured_references = []
    
    for ref in raw_references:
        raw_txt = clean_text(ref["text"])
        if len(raw_txt) < 8:
            continue

        parsed = ReferenceParser.parse(raw_txt)
        
        ref_obj = {
            "id": ref["id"],
            "text": raw_txt,
            "title": parsed.title or raw_txt,
            "authors": parsed.authors,
            "year": parsed.year,
            "journal": parsed.journal,
            "doi": parsed.doi or None,
            "arxiv_id": parsed.arxiv_id or None,
            "reference_type": parsed.reference_type
        }
        structured_references.append(ref_obj)

    from enrichment.pipeline import deduplicate_references
    return deduplicate_references(structured_references)


def analyze_pdf_content(doc: fitz.Document) -> Dict[str, Any]:
    """Analyze PDF pages using PyMuPDF to extract clean metadata, authors, and references."""
    metadata = doc.metadata or {}
    page_count = doc.page_count
    
    first_3_pages_text = ""
    for p in range(min(3, page_count)):
        first_3_pages_text += doc[p].get_text("text") + "\n"
        
    identifiers = extract_doi_and_arxiv(first_3_pages_text)
    doi = identifiers["doi"]
    arxiv_id = identifiers["arxiv_id"]
    
    all_spans = []
    for page_num in range(min(3, page_count)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" in b:
                for line in b["lines"]:
                    for span in line["spans"]:
                        span_text = span["text"].strip()
                        if span_text:
                            all_spans.append({
                                "text": span_text,
                                "size": round(span["size"], 1),
                                "font": span["font"],
                                "flags": span["flags"],
                                "bbox": span["bbox"],
                                "page": page_num + 1
                            })
                            
    size_freq = {}
    for span in all_spans:
        size = span["size"]
        size_freq[size] = size_freq.get(size, 0) + len(span["text"])
        
    body_size = max(size_freq, key=size_freq.get) if size_freq else 10.0

    # 1. Journal / Publisher Name Extraction
    journal = None
    journal_patterns = [
        r"(?:IEEE|Elsevier|Springer|ACM|Nature|Science|MDPI|Wiley|ArXiv|PLOS|Frontiers|Taylor\s*&\s*Francis|Cell\s+Press|ACS|RSC|Sage|BMJ)",
        r"(?:Journal of [A-Za-z0-9\s]+|Transactions on [A-Za-z0-9\s]+|Proceedings of [A-Za-z0-9\s]+)",
        r"(?:International Conference on [A-Za-z0-9\s]+|Symposium on [A-Za-z0-9\s]+)"
    ]
    
    for page_num in range(min(2, page_count)):
        page = doc[page_num]
        p_height = page.rect.height
        header_limit = p_height * 0.15
        footer_start = p_height * 0.85
        
        blocks = get_sorted_blocks(page)
        for b in blocks:
            y0, y1 = b["y0"], b["y1"]
            txt = b["text"].strip()
            if (y0 < header_limit or y1 > footer_start) and len(txt) < 200:
                for pat in journal_patterns:
                    m = re.search(pat, txt, re.IGNORECASE)
                    if m:
                        journal = clean_text(m.group(0))
                        break
            if journal:
                break
        if journal:
            break
            
    if not journal:
        if doi:
            journal = f"DOI: {doi}"
        elif arxiv_id:
            journal = f"arXiv:{arxiv_id}"
        else:
            journal = metadata.get("publisher") or metadata.get("producer") or metadata.get("creator") or "Unknown Publisher/Journal"
            if len(journal) > 60 or "distiller" in journal.lower() or "acrobat" in journal.lower():
                journal = "Scientific Publication"

    # 2. Title Extraction & Precise Title Bottom Boundary
    title = ""
    title_y_end = 0
    p1_spans = [s for s in all_spans if s["page"] == 1 and s["bbox"][1] < doc[0].rect.height * 0.5] if page_count > 0 else []
    
    header_blacklist = [r"^preprint", r"^working paper", r"^vol\.\s*\d+", r"^issn", r"^doi:", r"^http", r"^ieee", r"^accepted"]
    filtered_spans = []
    for s in p1_spans:
        txt_low = s["text"].lower()
        if not any(re.search(pat, txt_low) for pat in header_blacklist):
            filtered_spans.append(s)
            
    if filtered_spans:
        max_size = max(s["size"] for s in filtered_spans)
        if max_size >= body_size * 1.15:
            title_spans = [s for s in filtered_spans if abs(s["size"] - max_size) <= 1.5]
            title_spans.sort(key=lambda s: (s["bbox"][1], s["bbox"][0]))
            title = clean_text(" ".join(s["text"] for s in title_spans))
            title_y_end = max(s["bbox"][3] for s in title_spans)
            
    if not title or len(title) < 5:
        meta_title = clean_text(metadata.get("title"))
        if meta_title and len(meta_title) >= 5 and not meta_title.lower().endswith(".pdf"):
            title = meta_title
        else:
            title = "Untitled Article"

    if title_y_end == 0 and page_count > 0:
        title_y_end = doc[0].rect.height * 0.15

    # 3. Abstract & Keywords Extraction
    abstract = ""
    keywords = []
    abstract_y_start = doc[0].rect.height * 0.65 if page_count > 0 else 500
    
    p1_blocks = get_sorted_blocks(doc[0]) if page_count > 0 else []
    p2_blocks = get_sorted_blocks(doc[1]) if page_count > 1 else []
    first_pages_blocks = p1_blocks + p2_blocks
    
    for idx, b in enumerate(p1_blocks):
        txt = b["text"].strip()
        if re.search(r"^(?:abstract|summary|ملخص|المقدمة|introduction|1\.\s+introduction|i\.\s+introduction)", txt, re.IGNORECASE):
            abstract_y_start = min(abstract_y_start, b["y0"])
            
    for idx, b in enumerate(first_pages_blocks):
        txt = b["text"].strip()
        abs_match = re.match(r"^(?:abstract|summary|ملخص)\b[\s:—\-.]*(.*)", txt, re.IGNORECASE | re.DOTALL)
        if abs_match:
            abs_text = abs_match.group(1).strip()
            if len(abs_text) > 20:
                abstract = clean_text(abs_text)
            elif idx + 1 < len(first_pages_blocks):
                abstract = clean_text(first_pages_blocks[idx + 1]["text"])
            break
            
    for b in first_pages_blocks:
        txt = b["text"].strip()
        kw_match = re.match(r"^(?:keywords|index terms|key words|الكلمات المفتاحية|الكلمات الدالة)\b[\s:—\-.]*(.*)", txt, re.IGNORECASE | re.DOTALL)
        if kw_match:
            kw_str = kw_match.group(1).strip()
            raw_kws = re.split(r"[,;•—،]", kw_str)
            keywords = [clean_text(k) for k in raw_kws if clean_text(k) and len(clean_text(k)) < 60]
            break

    # 4. Supercharged Manuscript Author Extraction
    authors, affiliations = extract_manuscript_authors(doc, title_y_end, abstract_y_start, metadata)

    # 5. Supercharged Academic References Extraction (No document structure headings)
    references = extract_academic_references(doc)

    return {
        "title": title,
        "journal": journal,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "authors": authors,
        "affiliations": affiliations,
        "abstract": abstract,
        "keywords": keywords,
        "page_count": page_count,
        "headings": [],  # Document structure omitted as requested
        "references": references,
    }


def generate_xml_string(data: Dict[str, Any]) -> str:
    """Generate structured XML string from analysis data."""
    root = ET.Element("document")
    
    metadata_el = ET.SubElement(root, "metadata")
    ET.SubElement(metadata_el, "title").text = data["title"]
    ET.SubElement(metadata_el, "journal").text = data["journal"]
    if data.get("doi"):
        ET.SubElement(metadata_el, "doi").text = data["doi"]
    if data.get("arxiv_id"):
        ET.SubElement(metadata_el, "arxiv_id").text = data["arxiv_id"]
    ET.SubElement(metadata_el, "page_count").text = str(data["page_count"])
    
    authors_el = ET.SubElement(metadata_el, "authors")
    for author in data["authors"]:
        ET.SubElement(authors_el, "author").text = author
        
    if data.get("affiliations"):
        affil_el = ET.SubElement(metadata_el, "affiliations")
        for aff in data["affiliations"]:
            ET.SubElement(affil_el, "affiliation").text = aff
            
    if data.get("abstract"):
        ET.SubElement(metadata_el, "abstract").text = data["abstract"]
        
    if data.get("keywords"):
        kw_el = ET.SubElement(metadata_el, "keywords")
        for kw in data["keywords"]:
            ET.SubElement(kw_el, "keyword").text = kw
            
    ET.SubElement(metadata_el, "references_count").text = str(len(data["references"]))
    
    if data.get("headings"):
        structure_el = ET.SubElement(root, "structure")
        for heading in data["headings"]:
            heading_el = ET.SubElement(structure_el, "heading", {
                "level": str(heading.get("level", 1)),
                "page": str(heading.get("page", 1))
            })
            heading_el.text = safe_xml_text(heading.get("text", ""))
        
    references_el = ET.SubElement(root, "references")
    for ref in (data.get("references") or []):
        ref_el = ET.SubElement(references_el, "reference", {"id": str(ref.get("id", ""))})
        ref_el.text = safe_xml_text(ref.get("text", ""))
        
    raw_str = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(raw_str)
    return parsed.toprettyxml(indent="  ")


@app.get("/", response_class=HTMLResponse)
@app.get("/author", response_class=HTMLResponse)
@app.get("/author/", response_class=HTMLResponse)
@app.get("/reference", response_class=HTMLResponse)
@app.get("/reference/", response_class=HTMLResponse)
@app.get("/paper", response_class=HTMLResponse)
@app.get("/paper/", response_class=HTMLResponse)
async def serve_index():
    """Serve the frontend single page application for main dashboard or dedicated author/reference pages."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>PDF Analyzer API</h2><p>Frontend not found. Access API documentation at <a href='/docs'>/docs</a></p>")


import hashlib
from datetime import datetime, timezone
from pydantic import BaseModel
from enrichment.storage import storage
from enrichment.providers import OpenAlexAuthorProvider, GoogleScholarAuthorProvider, GoogleScholarProvider
from enrichment import ReferenceEnricher
from enrichment.xml_storage import xml_storage


@app.post("/analyze")
async def analyze_pdf(file: UploadFile = File(...), enrich_references: bool = False):
    """Analyze uploaded PDF, create project record, and return structured JSON."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        file_bytes = await file.read()
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        # 1. Check local XML cache first - 0 parsing, 0 tokens, 0ms!
        cached_results = xml_storage.get_cached_document(sha256_hash)
        if cached_results and not enrich_references:
            if not cached_results.get("project_id"):
                cached_results["project_id"] = f"project_cached_{sha256_hash[:8]}"
            return JSONResponse(content=cached_results)

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        analysis_results = analyze_pdf_content(doc)
        
        # Deterministic project ID
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        project_id = f"project_{timestamp_str}_{sha256_hash[:8]}"
        analysis_results["project_id"] = project_id
        analysis_results["pdf_hash"] = sha256_hash
        analysis_results["cached"] = False

        if enrich_references and analysis_results.get("references"):
            enricher = ReferenceEnricher()
            enriched = await enricher.enrich_batch(analysis_results["references"], project_id=project_id)
            analysis_results["enriched_references"] = enriched
            
        xml_content = generate_xml_string(analysis_results)
        analysis_results["xml"] = xml_content
        
        # Save structured document to local XML archive linked to SHA-256 hash!
        xml_storage.save_document_xml(sha256_hash, file.filename, analysis_results)
        
        # Save project record to disk
        project_record = {
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "input_pdf": {
                "filename": file.filename,
                "sha256": sha256_hash,
                "size_bytes": len(file_bytes),
                "page_count": analysis_results.get("page_count", 0)
            },
            "metadata": {
                "title": analysis_results.get("title"),
                "journal": analysis_results.get("journal"),
                "doi": analysis_results.get("doi"),
                "arxiv_id": analysis_results.get("arxiv_id"),
                "authors": analysis_results.get("authors", [])
            },
            "references": [
                {
                    "id": ref.get("id"),
                    "text": ref.get("text") or ref.get("original_text") or "",
                    "reference_id": (ref.get("reference_id") if isinstance(ref, dict) else None)
                }
                for ref in (analysis_results.get("enriched_references") or analysis_results.get("references") or [])
            ],
            "headings": analysis_results.get("headings", []),
            "xml": xml_content,
            "statistics": {
                "total_references": len(analysis_results.get("references") or []),
                "enriched_count": len(analysis_results.get("enriched_references") or [])
            }
        }
        storage.save_project(project_id, project_record)
        
        doc.close()
        return JSONResponse(content=analysis_results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error analyzing PDF: {str(e)}")


class ReferenceItem(BaseModel):
    text: str

class EnrichRequest(BaseModel):
    references: List[ReferenceItem]
    project_id: Optional[str] = None

@app.post("/references/enrich")
async def enrich_references_endpoint(request: EnrichRequest):
    """
    Enrich extracted reference strings with multi-source aggregation (OpenAlex, Crossref, Google Scholar).
    Saves Master Records and persists to disk.
    """
    if not request.references:
        return JSONResponse(content={"results": []})
        
    enricher = ReferenceEnricher()
    items = [{"text": ref.text} for ref in request.references]
    enriched_results = await enricher.enrich_batch(items, project_id=request.project_id)
    
    return JSONResponse(content={"results": enriched_results})


@app.get("/references/{ref_id}/sources")
async def get_reference_sources_endpoint(ref_id: str):
    """Get multi-source comparison (OpenAlex vs Crossref vs Google Scholar) for a reference."""
    record = storage.load_reference(ref_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Reference '{ref_id}' not found.")
    
    sources_data = {
        "reference_id": ref_id,
        "canonical": record.get("canonical"),
        "sources": record.get("sources"),
        "quality_and_conflicts": record.get("quality_and_conflicts"),
        "doi_verification": record.get("doi_verification")
    }
    return JSONResponse(content=sources_data)


@app.get("/references/{ref_id}")
async def get_reference_endpoint(ref_id: str, project_id: Optional[str] = None):
    """Get complete Master JSON Record of an enriched reference from disk storage with project fallback."""
    record = storage.load_reference(ref_id)
    if not record and project_id:
        proj = storage.load_project(project_id)
        if proj:
            for r in (proj.get("references") or []):
                r_id = str(r.get("reference_id") or r.get("id") or "")
                if r_id and (r_id == ref_id or ref_id.endswith(r_id)):
                    record = storage.load_reference(r.get("reference_id")) if r.get("reference_id") else None
                    if not record:
                        record = {
                            "reference_id": ref_id,
                            "project_id": project_id,
                            "title": r.get("text"),
                            "original_text": r.get("text"),
                            "canonical": {
                                "title": {"value": r.get("text")},
                                "reference_type": {"value": "journal-article"}
                            }
                        }
                    break
    if not record:
        raise HTTPException(status_code=404, detail=f"Reference '{ref_id}' not found.")
    return JSONResponse(content=record)


@app.get("/papers/{paper_id:path}")
async def get_paper_endpoint(paper_id: str):
    """Get canonical Paper Record from disk storage."""
    paper = storage.load_paper(paper_id)
    if not paper:
        # Fallback check in references
        ref = storage.load_reference(paper_id)
        if ref:
            return JSONResponse(content=ref.get("canonical", {}))
        raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found.")
    return JSONResponse(content=paper)


@app.get("/authors/{author_id:path}/works")
async def get_author_works_endpoint(author_id: str, page: int = 1, per_page: int = 20, provider: str = "openalex"):
    """
    Get paginated publication works of an author by author ID.
    Supports provider='openalex' or provider='google_scholar'.
    """
    if provider.lower() in ("google_scholar", "scholar") or author_id.startswith("scholar:") or author_id.startswith("google_scholar:"):
        prov_instance = GoogleScholarAuthorProvider()
    else:
        prov_instance = OpenAlexAuthorProvider()
        
    result = await prov_instance.get_author_works(author_id, page=page, per_page=per_page)
    return JSONResponse(content={
        "results": result.get("results") or [],
        "page": page,
        "per_page": per_page,
        "total_count": result.get("total_count") or 0
    })


@app.get("/authors/{author_id:path}")
async def get_author_profile_endpoint(author_id: str, provider: str = "openalex", refresh: bool = False):
    """
    Get author profile details with multi-source metric aggregation.
    Supports provider='openalex' or provider='google_scholar'.
    """
    clean_id = (author_id or "").strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="Author ID must not be empty.")

    # 1. Check local XML cache first - 0 API tokens consumed!
    if not refresh:
        cached_author = xml_storage.get_cached_author(clean_id)
        if cached_author:
            return JSONResponse(content=cached_author)

    # 2. Check provider first if explicit or fetch live
    if provider.lower() in ("google_scholar", "scholar") or clean_id.startswith("scholar:") or clean_id.startswith("google_scholar:"):
        prov_instance = GoogleScholarAuthorProvider()
    else:
        prov_instance = OpenAlexAuthorProvider()
        
    profile = await prov_instance.get_author(clean_id)
    
    if not profile:
        # Check local storage fallback
        cached_author = storage.load_author(clean_id)
        if cached_author:
            display_name = cached_author.get("display_name") or cached_author.get("name") or cached_author.get("identity", {}).get("name") or clean_id
            cached_author["display_name"] = display_name
            cached_author["name"] = display_name
            return JSONResponse(content=cached_author)
        raise HTTPException(status_code=404, detail=f"Author '{clean_id}' not found.")
    
    # Structure into multi-source author format
    author_name = profile.get("display_name") or profile.get("name") or clean_id
    metrics = {
        "openalex": {
            "works_count": profile.get("works_count"),
            "cited_by_count": profile.get("cited_by_count"),
            "h_index": profile.get("h_index"),
            "i10_index": profile.get("i10_index")
        } if profile.get("source") == "openalex" else {},
        "google_scholar": {
            "cited_by_count": profile.get("cited_by_count"),
            "h_index": profile.get("h_index"),
            "i10_index": profile.get("i10_index")
        } if profile.get("source") == "google_scholar" else {}
    }

    aggregated = {
        "id": profile.get("id"),
        "name": author_name,
        "display_name": author_name,
        "identifiers": {
            "openalex_id": profile.get("id") if profile.get("source") == "openalex" else None,
            "google_scholar_id": profile.get("scholar_url") if profile.get("source") == "google_scholar" else None,
            "orcid": None
        },
        "metrics": metrics,
        "works_count": profile.get("works_count") or 0,
        "cited_by_count": profile.get("cited_by_count") or 0,
        "h_index": profile.get("h_index"),
        "i10_index": profile.get("i10_index"),
        "affiliations": profile.get("affiliations") or [],
        "topics": profile.get("topics") or [],
        "source": profile.get("source"),
        "scholar_url": profile.get("scholar_url")
    }

    storage.save_author(clean_id, aggregated)
    xml_storage.save_author_xml(clean_id, aggregated)
    return JSONResponse(content=aggregated)


@app.get("/scholar/search")
async def scholar_search_endpoint(q: str, num: int = 10, refresh: bool = False):
    """
    Search Google Scholar directly from within website via SerpApi.
    Checks local XML archive first to save API credits (0 tokens, 0ms).
    Persists and incrementally merges all results into structured XML.
    """
    clean_q = (q or "").strip()
    if not clean_q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' must not be empty.")

    from enrichment.config import config
    if not config.serpapi_key:
        provider = GoogleScholarProvider()
        results = await provider.search_query(clean_q, num=num)
        return JSONResponse(content=results)

    # 1. Local XML Cache hit check
    if not refresh:
        cached_search = xml_storage.get_cached_search(clean_q)
        if cached_search and cached_search.get("results"):
            return JSONResponse(content=cached_search)

    # 2. Live search query
    provider = GoogleScholarProvider()
    results = await provider.search_query(clean_q, num=num)

    # 3. Save / merge incrementally into XML archive
    if results and "results" in results and results.get("available") is not False:
        xml_storage.save_search_xml(clean_q, results.get("results", []))

    return JSONResponse(content=results)


@app.get("/scholar/author/{author_id:path}")
async def scholar_author_endpoint(author_id: str):
    """Get Google Scholar author profile and metrics via SerpApi."""
    clean_id = (author_id or "").strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="Author ID must not be empty.")

    provider = GoogleScholarAuthorProvider()
    profile = await provider.get_author(clean_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Google Scholar author '{author_id}' not found.")
    return JSONResponse(content=profile)


@app.get("/scholar/citations/{cluster_id}")
async def scholar_citations_endpoint(cluster_id: str, page: int = 1, num: int = 10):
    """
    Explore citing papers for a given Google Scholar cluster ID.
    Returns paginated citing papers with Title, Authors, Year, Venue, Citations, etc.
    """
    clean_c = (cluster_id or "").strip()
    if not clean_c:
        raise HTTPException(status_code=400, detail="Cluster ID must not be empty.")

    provider = GoogleScholarProvider()
    citations_data = await provider.get_citations(clean_c, page=page, num=num)
    return JSONResponse(content=citations_data)


@app.get("/openalex/citations/{work_id:path}")
async def openalex_citations_endpoint(work_id: str, page: int = 1, num: int = 10):
    """
    Explore citing publications for a given OpenAlex work ID (W...) or DOI.
    Returns paginated citing works with title, authors, year, venue, citations, OA PDF links.
    """
    clean_id = (work_id or "").strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="Work ID must not be empty.")

    from enrichment.providers import OpenAlexProvider
    provider = OpenAlexProvider()
    citations_data = await provider.get_citations(clean_id, page=page, num=num)
    return JSONResponse(content=citations_data)


@app.get("/projects/{project_id:path}/export")
async def export_project_endpoint(project_id: str, format: str = "json"):
    """Export complete project data in JSON, BibTeX, or XML format."""
    proj = storage.load_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")

    fmt = format.lower().strip()
    if fmt not in ("json", "bibtex", "xml"):
        raise HTTPException(status_code=400, detail=f"Export format '{format}' is not supported. Supported: json, bibtex, xml")

    if fmt == "json":
        # Load all Master Reference records referenced in project
        master_refs = []
        for ref_item in (proj.get("references") or []):
            r_id = ref_item.get("reference_id")
            if r_id:
                loaded_ref = storage.load_reference(r_id)
                if loaded_ref:
                    master_refs.append(loaded_ref)
                else:
                    master_refs.append(ref_item)
            else:
                master_refs.append(ref_item)

        export_bundle = {
            "project": proj,
            "references": master_refs,
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
        return JSONResponse(content=export_bundle)

    elif fmt == "bibtex":
        # Generate BibTeX entries
        bib_entries = []
        for idx, ref_item in enumerate(proj.get("references") or []):
            r_id = ref_item.get("reference_id")
            loaded_ref = storage.load_reference(r_id) if r_id else None
            
            can = (loaded_ref.get("canonical") if loaded_ref else {}) or {}
            title = can.get("title", {}).get("value") if isinstance(can.get("title"), dict) else (ref_item.get("text") or f"ref_{idx+1}")
            year = can.get("year", {}).get("value") if isinstance(can.get("year"), dict) else ""
            venue = can.get("venue", {}).get("value") if isinstance(can.get("venue"), dict) else ""
            doi = can.get("identifiers", {}).get("doi", {}).get("value") if isinstance(can.get("identifiers", {}).get("doi"), dict) else ""
            
            authors_list = []
            if loaded_ref and loaded_ref.get("canonical_authors"):
                for a in loaded_ref["canonical_authors"]:
                    authors_list.append(a.get("name") or "")
            
            authors_str = " and ".join(filter(None, authors_list)) or "Unknown"
            cite_key = f"ref_{idx+1}"

            bib_entry = f"@article{{{cite_key},\n"
            bib_entry += f"  title = {{{title}}},\n"
            bib_entry += f"  author = {{{authors_str}}},\n"
            if year:
                bib_entry += f"  year = {{{year}}},\n"
            INVALID_EXPORT_VENUES = {"google scholar", "scholar", "openalex", "crossref", "serpapi", "arxiv", "none", "unknown", "n/a", "null", "undefined"}
            if venue and str(venue).strip() and str(venue).strip().lower() not in INVALID_EXPORT_VENUES:
                bib_entry += f"  journal = {{{str(venue).strip()}}},\n"
            if doi and str(doi).strip():
                bib_entry += f"  doi = {{{str(doi).strip()}}},\n"
            bib_entry += "}\n"
            bib_entries.append(bib_entry)

        return HTMLResponse(content="\n".join(bib_entries), media_type="text/plain")

    elif fmt == "xml":
        xml_content = proj.get("xml")
        if not xml_content:
            data = {
                "title": proj.get("metadata", {}).get("title"),
                "journal": proj.get("metadata", {}).get("journal"),
                "doi": proj.get("metadata", {}).get("doi"),
                "arxiv_id": proj.get("metadata", {}).get("arxiv_id"),
                "page_count": proj.get("input_pdf", {}).get("page_count", 0),
                "authors": proj.get("metadata", {}).get("authors", []),
                "affiliations": proj.get("metadata", {}).get("affiliations", []),
                "abstract": proj.get("metadata", {}).get("abstract", ""),
                "keywords": proj.get("metadata", {}).get("keywords", []),
                "headings": proj.get("headings", []),
                "references": proj.get("references", []),
            }
            xml_content = generate_xml_string(data)
        return HTMLResponse(content=xml_content, media_type="application/xml")


@app.get("/projects/{project_id:path}")
async def get_project_endpoint(project_id: str):
    """Get project metadata, input PDF details, and reference index."""
    proj = storage.load_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return JSONResponse(content=proj)


@app.get("/xml/documents")
async def list_xml_documents_endpoint():
    """List all indexed XML documents stored locally in XML archive."""
    docs = xml_storage.list_documents()
    return JSONResponse(content={"count": len(docs), "documents": docs})


@app.get("/xml/document/{pdf_hash}")
async def get_xml_document_endpoint(pdf_hash: str):
    """Retrieve raw XML content for a specific cached PDF document."""
    clean_h = (pdf_hash or "").strip()
    xml_content = xml_storage.get_document_xml_raw(clean_h)
    if not xml_content:
        raise HTTPException(status_code=404, detail=f"XML document for hash '{clean_h}' not found.")
    return HTMLResponse(content=xml_content, media_type="application/xml")


@app.get("/xml/searches")
async def list_xml_searches_endpoint():
    """List all cached search queries stored locally in XML."""
    searches = xml_storage.list_searches()
    return JSONResponse(content={"count": len(searches), "searches": searches})


@app.get("/xml/search/{query_or_hash}")
async def get_xml_search_endpoint(query_or_hash: str):
    """Retrieve raw XML content for a cached search query or hash."""
    clean_qh = (query_or_hash or "").strip()
    xml_content = xml_storage.get_search_xml_raw(clean_qh)
    if not xml_content:
        raise HTTPException(status_code=404, detail=f"XML search archive for '{clean_qh}' not found.")
    return HTMLResponse(content=xml_content, media_type="application/xml")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return HTMLResponse(content="", status_code=204)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)

