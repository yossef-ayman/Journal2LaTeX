import os
import re
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import fitz  # PyMuPDF

app = FastAPI(title="Standalone PDF Analyzer")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")
os.makedirs(templates_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)


def clean_text(text: str) -> str:
    """Normalize whitespace and strip text."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def is_arabic_text(text: str) -> bool:
    """Check if text contains Arabic characters."""
    return bool(re.search(r"[\u0600-\u06FF]", text))


def get_sorted_blocks(page: fitz.Page) -> List[dict]:
    """
    Extract text blocks from a PyMuPDF page, sorting them in natural reading order
    even for two-column or multi-column layouts.
    """
    page_rect = page.rect
    width = page_rect.width
    
    raw_blocks = page.get_text("blocks")
    text_blocks = []
    
    for b in raw_blocks:
        if len(b) >= 5 and b[4].strip():
            text_blocks.append({
                "bbox": (b[0], b[1], b[2], b[3]),
                "x0": b[0],
                "y0": b[1],
                "x1": b[2],
                "y1": b[3],
                "text": b[4]
            })
            
    if not text_blocks:
        return []

    col_split = width / 2.0
    left_blocks = [b for b in text_blocks if b["x1"] <= col_split + 20]
    right_blocks = [b for b in text_blocks if b["x0"] >= col_split - 20]
    
    is_multi_column = len(left_blocks) >= 2 and len(right_blocks) >= 2
    
    if is_multi_column:
        text_blocks.sort(key=lambda b: (b["y0"], b["x0"]))
        
        top_spanning = []
        left_col = []
        right_col = []
        bottom_spanning = []
        
        for b in text_blocks:
            if (b["x1"] - b["x0"]) > width * 0.6:
                if not left_col and not right_col:
                    top_spanning.append(b)
                else:
                    bottom_spanning.append(b)
            elif b["x0"] < col_split:
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
    """Validate extracted author name strictly (2 to 5 words, no institutions or single words)."""
    name_clean = clean_text(name)
    name_clean = re.sub(r"^[\d\*\†\‡\§\^,#\-]+|[\d\*\†\‡\§\^,#\-\.]+$", "", name_clean).strip()
    name_clean = re.sub(r"^(?:Dr\.|Prof\.|Eng\.|Mr\.|Ms\.|Mrs\.|Ph\.D\.|أ\.D\.|أ\.د\.|د\.|م\.|أ\.|الأستاذ|الدكتور|الباحث)\s*", "", name_clean, flags=re.IGNORECASE).strip()
    
    if len(name_clean) < 3 or len(name_clean) > 50:
        return False
        
    name_lower = name_clean.lower()
    INVALID_AUTHOR_KEYWORDS = [
        "ieee", "elsevier", "springer", "mdpi", "acm", "wiley", "nature", "science", "arxiv", "biorxiv",
        "microsoft", "office", "user", "creator", "author", "admin", "writer", "distiller", "acrobat", "latex", "tex",
        "university", "dept", "department", "institute", "school", "college", "lab", "laboratory", "faculty",
        "corporation", "corp", "inc", "ltd", "center", "centre", "editor", "guest", "staff", "fellow", "member",
        "journal", "proceeding", "transactions", "symposium", "conference", "society", "abstract", "keywords",
        "introduction", "vol", "no", "pp", "pages", "received", "accepted", "revised", "copyright", "rights",
        "corresponding", "address", "email", "mail", "tel", "phone", "fax", "orcid",
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
    # Authors must have at least 2 words (First + Last Name) up to 5 words
    if len(words) < 2 or len(words) > 5:
        return False
        
    if not is_arabic_text(name_clean):
        for w in words:
            if not w[0].isupper():
                return False
                
    return True


def analyze_pdf_content(doc: fitz.Document) -> Dict[str, Any]:
    """Analyze PDF pages using PyMuPDF to extract rich structured data."""
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

    # 3. Abstract & Keywords Extraction & Precise Abstract Top Boundary
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

    # 4. Pinpoint Author Extraction (Strict separation by comma / AND / dot)
    authors = []
    affiliations = []

    if p1_blocks:
        for b in p1_blocks:
            if (title_y_end - 5) <= b["y0"] <= (abstract_y_start + 15):
                txt = b["text"].strip()
                if not txt:
                    continue
                    
                txt_clean = re.sub(r"\((?:Student\s+)?Member,\s*IEEE\)", "", txt, flags=re.IGNORECASE)
                txt_clean = re.sub(r"\((?:Fellow|Senior\s+Member),\s*IEEE\)", "", txt_clean, flags=re.IGNORECASE)
                
                if "@" in txt or any(kw in txt.lower() for kw in ["university", "department", "institute", "faculty", "school", "laboratory", "center", "جامعة", "كلية", "قسم", "معهد", "مختبر"]):
                    affiliations.append(clean_text(txt))
                else:
                    lines = [clean_text(l) for l in txt_clean.split("\n") if clean_text(l)]
                    for line in lines:
                        # Strip superscripts, numbers, asterisks
                        line_stripped = re.sub(r"[\d\*\†\‡\§\^#]+", "", line).strip()
                        line_stripped = line_stripped.rstrip(".")
                        
                        # Split by comma, 'and', '&', '،', ' و '
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
                if is_valid_author_name(a_clean):
                    authors.append(a_clean)

    authors = list(dict.fromkeys(authors))
    if not authors:
        authors = ["Unknown Author"]
        
    affiliations = list(dict.fromkeys(affiliations))[:5]

    # 5. Headings & References Extraction
    headings = []
    references = []
    in_ref_section = False
    
    for page_num in range(page_count):
        page = doc[page_num]
        p_height = page.rect.height
        header_limit = p_height * 0.08
        footer_start = p_height * 0.92
        
        blocks = get_sorted_blocks(page)
        
        for b in blocks:
            if b["y0"] < header_limit or b["y1"] > footer_start:
                continue
                
            text = b["text"].strip()
            if not text:
                continue
                
            lines = [clean_text(l) for l in text.split("\n") if clean_text(l)]
            
            for line in lines:
                if re.match(r"^(?:references|bibliography|literature cited|المراجع|قائمة المراجع)$", line, re.IGNORECASE) or \
                   re.match(r"^(?:\d+|[IVXLCDM]+)\.?\s+(?:references|bibliography|المراجع)$", line, re.IGNORECASE):
                    in_ref_section = True
                    headings.append({"text": line, "level": 1, "page": page_num + 1})
                    continue
                    
                if in_ref_section:
                    num_match = re.match(r"^(?:\[(\d+)\]|(\d+)\.|\((\d+)\))\s*(.*)", line)
                    if num_match:
                        ref_id = num_match.group(1) or num_match.group(2) or num_match.group(3)
                        ref_body = num_match.group(4).strip()
                        references.append({"id": ref_id, "text": ref_body})
                    elif len(line) > 10:
                        if references:
                            references[-1]["text"] += " " + line
                        else:
                            references.append({"id": str(len(references) + 1), "text": line})
                else:
                    is_h = False
                    h_level = 2
                    
                    if re.match(r"^[IVXLCDM]+\.\s+[A-Z]", line):
                        is_h = True
                        h_level = 1
                    elif re.match(r"^\d+(?:\.\d+)*\.?\s+[A-Z]", line):
                        is_h = True
                        num_part = line.split()[0].rstrip('.')
                        h_level = min(3, max(1, len(num_part.split('.'))))
                    elif len(line) < 55 and line.isupper() and not re.search(r"[,;:@\.]", line) and len(line.split()) <= 6:
                        is_h = True
                        h_level = 1
                        
                    if is_h:
                        headings.append({"text": line, "level": h_level, "page": page_num + 1})

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
        "headings": headings,
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
    
    structure_el = ET.SubElement(root, "structure")
    for heading in data["headings"]:
        heading_el = ET.SubElement(structure_el, "heading", {
            "level": str(heading["level"]),
            "page": str(heading["page"])
        })
        heading_el.text = heading["text"]
        
    references_el = ET.SubElement(root, "references")
    for ref in data["references"]:
        ref_el = ET.SubElement(references_el, "reference", {"id": str(ref["id"])})
        ref_el.text = ref["text"]
        
    raw_str = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(raw_str)
    return parsed.toprettyxml(indent="  ")


@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serve the single page application."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/analyze")
async def analyze_pdf(file: UploadFile = File(...)):
    """Analyze uploaded PDF and return structured JSON."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        file_bytes = await file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        analysis_results = analyze_pdf_content(doc)
        xml_content = generate_xml_string(analysis_results)
        analysis_results["xml"] = xml_content
        
        doc.close()
        return JSONResponse(content=analysis_results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error analyzing PDF: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)
