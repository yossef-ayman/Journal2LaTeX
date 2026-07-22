import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.models.document import AuthorModel, DocumentBlock, DocumentModel, SectionModel, BlockType, AuthorBiography
from app.utils.logger import get_job_logger


class DocumentAnalyzerError(Exception):
    """Exception raised when document analysis fails."""
    pass


class DocumentAnalyzer:
    """Service to parse DOCX files into structured block models with fallback metadata extraction."""

    def analyze_document(self, docx_path: Path, job_id: str) -> Tuple[DocumentModel, Dict[str, Any]]:
        """Analyze the input DOCX file and construct a structured DocumentModel and conversion report.

        Args:
            docx_path: Path to the input DOCX file.
            job_id: The job ID for logging.

        Returns:
            A tuple of (DocumentModel, report_dict).

        Raises:
            DocumentAnalyzerError: If analysis fails.
        """
        logger = get_job_logger(job_id, "system")
        logger.info("Starting improved document analysis for: %s", docx_path)

        if not docx_path.exists():
            msg = f"Document not found at: {docx_path}"
            logger.error(msg)
            raise DocumentAnalyzerError(msg)

        # Run pandoc to get JSON AST representation
        cmd = [
            settings.PANDOC_PATH,
            str(docx_path),
            "-t", "json"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8"
            )

            if result.returncode != 0:
                msg = f"Pandoc AST generation failed: {result.stderr}"
                logger.error(msg)
                raise DocumentAnalyzerError(msg)

            ast_data = json.loads(result.stdout)
            # Styling pandoc does not expose (shading, borders, row heights,
            # exact column widths) is read from the raw XML; body-level w:tbl
            # order matches pandoc Table order.
            self._table_styles = self._extract_table_styles(docx_path)
            self._table_style_idx = 0
            # Heading formatting (bold/size/alignment/spacing/keepNext) read
            # directly from the DOCX -- keyed by whitespace-insensitive heading
            # text so it can enrich sections parsed from the Pandoc AST.
            self._heading_formats = self._extract_heading_formats(docx_path)
            # Corresponding-author e-mail is commonly stored in the first-page
            # footer / a footnote / an endnote rather than the author block, and
            # pandoc does not surface those parts, so read them from the raw XML.
            self._corresponding_email = self._extract_corresponding_email(docx_path)
            return self._parse_ast(ast_data, job_id)

        except Exception as e:
            if not isinstance(e, DocumentAnalyzerError):
                msg = f"Unexpected error during document analysis: {str(e)}"
                logger.exception(msg)
                raise DocumentAnalyzerError(msg)
            raise

    def _parse_ast(self, ast: Dict[str, Any], job_id: str) -> Tuple[DocumentModel, Dict[str, Any]]:
        """Parse Pandoc AST into DocumentModel and count elements for reporting."""
        logger = get_job_logger(job_id, "system")
        meta = ast.get("meta", {})
        blocks = ast.get("blocks", [])

        # Setup counters for report
        counters = {
            "paragraphs": 0,
            "figures": 0,
            "tables": 0,
            "equations": 0,
            "references": 0,
            "warnings": []
        }

        # Separate metadata blocks from body blocks
        intro_metadata_blocks = []
        body_blocks = []
        found_header = False

        for b in blocks:
            if b.get("t") == "Header":
                found_header = True
            if not found_header:
                intro_metadata_blocks.append(b)
            else:
                body_blocks.append(b)

        # Clean/Stringify the metadata blocks
        intro_texts = []
        for b in intro_metadata_blocks:
            if b.get("t") in ("Para", "Plain"):
                txt = self._stringify_inlines(b.get("c", [])).strip()
                if txt:
                    intro_texts.append(txt)

        title = ""
        authors: List[AuthorModel] = []
        abstract_text = ""
        keywords_list = []

        # Heuristics for Title/Author/Abstract extraction from initial paragraphs
        # 1. Title Extraction
        if "title" in meta:
            title = self._stringify_inlines(meta["title"].get("c", []))

        if not title.strip() and intro_texts:
            # Check the first few paragraphs. The title is usually longer than a journal volume tag.
            for txt in intro_texts[:3]:
                # Skip typical journal metadata strings
                if any(x in txt.lower() for x in ["j. stat.", "vol.", "issn", "http", "doi:"]):
                    continue
                # First substantial paragraph is likely the title
                if len(txt) > 20:
                    title = txt
                    intro_texts.remove(txt)
                    break

        # 2. Extract Abstract & Keywords directly from inline paragraphs starting with "Abstract:" or "Keywords:"
        abstract_para_indices = []
        keywords_para_indices = []

        for idx, txt in enumerate(list(intro_texts)):
            txt_lower = txt.lower().strip()
            if txt_lower.startswith("abstract:") or txt_lower.startswith("abstract"):
                abstract_text = re.sub(r"^abstract(text)?:?\s*", "", txt, flags=re.IGNORECASE).strip()
                abstract_para_indices.append(txt)
            elif txt_lower.startswith("keywords:") or txt_lower.startswith("key words:") or txt_lower.startswith("key-words:"):
                raw_kw = re.sub(r"^key(words|\s*words)?:?\s*", "", txt, flags=re.IGNORECASE).strip()
                keywords_list = [w.strip() for w in re.split(r",|;", raw_kw) if w.strip()]
                keywords_para_indices.append(txt)

        # Remove abstract and keyword blocks from metadata paragraphs to avoid duplicate processing
        for txt in abstract_para_indices + keywords_para_indices:
            if txt in intro_texts:
                intro_texts.remove(txt)

        # 3. Process Author & Affiliation lists from remaining metadata paragraphs
        email_regex = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
        author_markers = {}  # id(AuthorModel) -> superscript affiliation index
        institution_keywords = ["university", "department", "institute", "school", "college", "lab", "corp", "inc", "ltd", "centre"]
        current_author: Optional[AuthorModel] = None

        for txt in intro_texts:
            # Skip dates/metadata and journal header markers
            if any(x in txt.lower() for x in ["received:", "revised:", "accepted:", "published online:", "j. stat.", "vol.", "issn", "http", "doi:", "volume", "issue"]):
                continue

            emails = email_regex.findall(txt)
            is_inst = (
                any(k in txt.lower() for k in institution_keywords)
                and len(txt) <= 300  # longer texts are body/abstract, not affiliations
            )

            if emails:
                if current_author:
                    current_author.email = emails[0]
                else:
                    current_author = AuthorModel(name="Corresponding Author", email=emails[0])
                    authors.append(current_author)
            elif is_inst:
                # Affiliation paragraph.  If it starts with an index digit
                # ("1 Professor in ..."), attach it to the author(s) carrying
                # that superscript marker; otherwise attach to the latest author.
                idx_match = re.match(r"^(\d{1,2})\s*(?=[A-Za-z])(.*)$", txt, re.DOTALL)
                if idx_match:
                    marker = int(idx_match.group(1))
                    body = idx_match.group(2).strip()
                    matched = False
                    for author in authors:
                        if author_markers.get(id(author)) == marker:
                            author.affiliation = body
                            matched = True
                    if not matched and current_author:
                        current_author.affiliation = body
                elif current_author:
                    current_author.affiliation = txt
                elif authors:
                    authors[-1].affiliation = txt
            else:
                # Likely a name list: "Abdallah Almahaireh1, Baha' Shawaqfeh2, and ..."
                # Superscript affiliation markers arrive as plain trailing
                # digits after inline flattening; capture them for affiliation
                # matching, then strip them from the display name.
                cleaned = re.sub(r"\^\{\d+\}|\^\d+", "", txt).strip()
                # An author line is short; a long paragraph here is a summary or
                # abstract sentence that leaked into the front matter -- never a
                # name list, so skip it (prevents abstract text becoming authors).
                if len(cleaned) > 120:
                    continue
                names = [n.strip() for n in re.split(r",|\band\b", cleaned) if n.strip()]
                for name in names:
                    marker_match = re.search(r"(\d+)\s*\*?$", name)
                    marker = int(marker_match.group(1)) if marker_match else None
                    display = re.sub(r"\s*\d+\s*\*?$", "", name).strip()
                    if not display:
                        continue
                    current_author = AuthorModel(name=display)
                    if marker is not None:
                        author_markers[id(current_author)] = marker
                    authors.append(current_author)

        # Fallback: an unlabelled abstract is usually the longest early paragraph.
        if not abstract_text:
            for txt in intro_texts:
                if len(txt) > 350 and not email_regex.search(txt):
                    abstract_text = txt
                    intro_texts.remove(txt)
                    break

        # Fallback if no authors parsed
        if "author" in meta and not authors:
            auth_meta = meta["author"]
            if isinstance(auth_meta, list):
                for auth in auth_meta:
                    authors.append(AuthorModel(name=self._stringify_inlines(auth.get("c", []) if isinstance(auth, dict) else [auth])))

        # Extract metadata fields
        received_date = ""
        revised_date = ""
        accepted_date = ""
        published_date = ""
        volume = ""
        issue = ""
        year = ""
        doi = ""

        for txt in intro_texts:
            txt_lower = txt.lower().strip()
            if "received:" in txt_lower:
                m_rec = re.search(r"received:\s*([^,]+)", txt, re.IGNORECASE)
                if m_rec:
                    received_date = m_rec.group(1).strip()
                m_rev = re.search(r"revised:\s*([^,]+)", txt, re.IGNORECASE)
                if m_rev:
                    revised_date = m_rev.group(1).strip()
                m_acc = re.search(r"accepted:\s*([^,]+)", txt, re.IGNORECASE)
                if m_acc:
                    accepted_date = m_acc.group(1).strip()
            if "published online:" in txt_lower:
                m_pub = re.search(r"published online:\s*([^,]+)", txt, re.IGNORECASE)
                if m_pub:
                    published_date = m_pub.group(1).strip()
            if "vol." in txt_lower or "no." in txt_lower or "j. stat." in txt_lower:
                m_vol = re.search(r"vol\.\s*([a-zA-Z\d-]+|\d+)", txt, re.IGNORECASE)
                if m_vol:
                    volume = m_vol.group(1).strip()
                m_no = re.search(r"no\.\s*([a-zA-Z\d-]+|\d+)", txt, re.IGNORECASE)
                if m_no:
                    issue = m_no.group(1).strip()
                m_yr = re.search(r"\((\d{4})\)", txt)
                if m_yr:
                    year = m_yr.group(1).strip()
            if "doi:" in txt_lower:
                m_doi = re.search(r"doi:\s*(\S+)", txt, re.IGNORECASE)
                if m_doi:
                    doi = m_doi.group(1).strip()

        doc = DocumentModel(
            title=title,
            authors=authors,
            received_date=received_date,
            revised_date=revised_date,
            accepted_date=accepted_date,
            published_date=published_date,
            volume=volume,
            issue=issue,
            year=year,
            doi=doi
        )

        # Resolve the corresponding-author e-mail.  Priority: an e-mail found in
        # the front-matter author block (already attached to an author above),
        # otherwise the e-mail read from the footer/footnote/endnote.  The value
        # is stored on the model so the renderer can emit it through the
        # journal template's native corresponding-author command, and is also
        # attached to the asterisk/first author so the relationship is kept.
        footer_email = getattr(self, "_corresponding_email", "") or ""
        existing_email = next((a.email for a in authors if a.email), "")
        corresponding_email = existing_email or footer_email
        if corresponding_email:
            doc.corresponding_email = corresponding_email
            # Attach to the corresponding author (the one carrying the '*'
            # marker if identifiable, else the first author) when not already set.
            if not existing_email and authors and not authors[0].email:
                authors[0].email = corresponding_email
        current_section = SectionModel(title="Introduction", level=1, blocks=[])
        current_section_synthetic = True  # drop only if it never gains content
        references_list = []
        global_block_index = 0

        in_abstract = False
        in_keywords = False
        in_references = False
        in_biography = False
        current_bio: Optional[AuthorBiography] = None

        for b in body_blocks:
            t = b.get("t")
            c = b.get("c")

            if t == "Header":
                level = c[0]
                header_text = self._stringify_inlines(c[2])
                header_lower = header_text.lower().strip()

                in_abstract = "abstract" in header_lower
                in_keywords = "keyword" in header_lower
                in_references = any(ref in header_lower for ref in ["references", "bibliography", "works cited"])
                in_biography = any(bio in header_lower for bio in ["author biography", "authors biography", "biography"])

                if in_abstract or in_keywords or in_references or in_biography:
                    continue

                if current_section and (current_section.blocks or not current_section_synthetic):
                    doc.sections.append(current_section)

                # Keep Word's own heading number (headings are rendered
                # unnumbered downstream, so the manual number is what shows).
                current_section = SectionModel(
                    title=header_text.strip(), level=level, blocks=[],
                    heading_format=self._heading_format_for(header_text),
                )
                current_section_synthetic = False
                continue

            if t in ("Para", "Plain"):
                para_text = self._stringify_inlines(c).strip()
                para_lower = para_text.lower()
                if para_lower in ["authors biography", "author biography", "biography"]:
                    in_abstract = False
                    in_keywords = False
                    in_references = False
                    in_biography = True
                    continue
                elif para_lower in ["references", "bibliography", "works cited"]:
                    in_abstract = False
                    in_keywords = False
                    in_references = True
                    in_biography = False
                    continue

            if in_abstract:
                if t in ("Para", "Plain"):
                    abstract_text += self._stringify_inlines(c) + "\n"
                continue
            elif in_keywords:
                if t in ("Para", "Plain"):
                    text = self._stringify_inlines(c)
                    words = [w.strip() for w in re.split(r",|;", text) if w.strip()]
                    keywords_list.extend(words)
                continue
            elif in_references:
                if t in ("Para", "Plain"):
                    ref_text = self._stringify_inlines(c).strip()
                    if ref_text:  # skip blank paragraphs (they became empty \bibitems)
                        references_list.append(ref_text)
                        counters["references"] += 1
                elif t in ("BulletList", "OrderedList"):
                    list_items = c[1] if t == "OrderedList" else c
                    for item in list_items:
                        ref_text = self._stringify_blocks(item).strip()
                        if ref_text:
                            references_list.append(ref_text)
                            counters["references"] += 1
                continue
            elif in_biography:
                if t == "Table":
                    try:
                        # Extract all rows from table head and table bodies
                        all_rows = []
                        
                        # Table Head rows (often used for the first author biography row by Word/Pandoc default styles)
                        head_rows = c[3][1] if len(c[3]) >= 2 else []
                        all_rows.extend(head_rows)
                        
                        # Table Bodies rows
                        bodies = c[4]
                        for body in bodies:
                            if isinstance(body, list) and len(body) >= 4:
                                body_rows = body[3]
                                all_rows.extend(body_rows)
                                
                        for row in all_rows:
                            cells = row[1] if len(row) >= 2 else []
                            row_text = ""
                            row_img = None
                            
                            for cell in cells:
                                cell_blocks = cell[4] if len(cell) >= 5 else []
                                txt = self._stringify_blocks(cell_blocks).strip()
                                img = self._find_image_in_blocks(cell_blocks)
                                if img:
                                    row_img = img
                                if txt and len(txt) > len(row_text):
                                    row_text = txt
                                    
                            if row_text:
                                matched_name = None
                                for author in doc.authors:
                                    if row_text.lower().startswith(author.name.lower()):
                                        matched_name = author.name
                                        break
                                if not matched_name:
                                    words = row_text.split()
                                    matched_name = " ".join(words[:2]) if len(words) >= 2 else "Author"
                                    
                                doc.author_biographies.append(AuthorBiography(
                                    author_name=matched_name,
                                    image_path=row_img,
                                    biography_text=row_text
                                ))
                    except Exception as e:
                        logger.error("Failed to parse biography table: %s", str(e))
                elif t in ("Para", "Plain"):
                    text = self._stringify_inlines(c).strip()
                    if not text:
                        continue

                    img_path = None
                    for item in c:
                        if isinstance(item, dict) and item.get("t") == "Image":
                            img_c = item.get("c", [])
                            img_path = img_c[2][0] if len(img_c) > 2 and len(img_c[2]) > 0 else ""
                            break

                    if img_path:
                        if not current_bio:
                            current_bio = AuthorBiography(author_name="Author", image_path=img_path, biography_text="")
                        else:
                            current_bio.image_path = img_path
                    else:
                        if not current_bio:
                            matched_name = None
                            for author in doc.authors:
                                if text.lower().startswith(author.name.lower()):
                                    matched_name = author.name
                                    break
                            if not matched_name:
                                words = text.split()
                                matched_name = " ".join(words[:2]) if len(words) >= 2 else "Author"
                            
                            current_bio = AuthorBiography(author_name=matched_name, biography_text=text)
                        else:
                            if current_bio.biography_text:
                                current_bio.biography_text += "\n\n" + text
                            else:
                                current_bio.biography_text = text
                continue

            # Many journal manuscripts style section headings as manually
            # bold-numbered paragraphs ("2. Literature Review", "2.4.3 ...")
            # instead of Word Heading styles, so pandoc reports them as normal
            # paragraphs.  Detect them and split sections to restore hierarchy.
            if t in ("Para", "Plain"):
                heading_level = self._detect_manual_heading(c)
                if heading_level is not None:
                    heading_text = self._stringify_inlines(c).strip()
                    if current_section and (current_section.blocks or not current_section_synthetic):
                        doc.sections.append(current_section)
                    current_section = SectionModel(
                        title=heading_text, level=heading_level, blocks=[],
                        heading_format=self._heading_format_for(heading_text),
                    )
                    current_section_synthetic = False
                    continue

            parsed_block = self._parse_block(b, job_id, counters)
            if parsed_block and current_section:
                global_block_index += 1
                parsed_block.block_index = global_block_index
                parsed_block.original_order = global_block_index
                parsed_block.source_location = f"Section: {current_section.title}, Block: {global_block_index}"
                current_section.blocks.append(parsed_block)

        if current_section and (current_section.blocks or not current_section_synthetic):
            doc.sections.append(current_section)

        if current_bio:
            doc.author_biographies.append(current_bio)

        # Set final document metadata
        doc.abstract = abstract_text.strip()
        doc.keywords = keywords_list
        doc.references = references_list

        logger.info(
            "Parsed document: title='%s', authors=%d, sections=%d, references=%d",
            doc.title, len(doc.authors), len(doc.sections), len(doc.references)
        )

        return doc, counters

    def _parse_block(self, block: Dict[str, Any], job_id: str, counters: Dict[str, Any]) -> Optional[DocumentBlock]:
        """Convert an AST block into a DocumentBlock and increment metrics."""
        t = block.get("t")
        c = block.get("c")

        if t in ("Para", "Plain"):
            inlines = c
            for item in inlines:
                if not isinstance(item, dict):
                    continue
                item_t = item.get("t")
                item_c = item.get("c", [])

                if item_t == "Image":
                    caption = self._stringify_inlines(item_c[1])
                    src = item_c[2][0] if len(item_c) > 2 and len(item_c[2]) > 0 else ""
                    width_in, height_in = self._image_dimensions_in(item_c)
                    counters["figures"] += 1
                    return DocumentBlock(
                        type=BlockType.FIGURE,
                        content={
                            "caption": caption,
                            "path": src,
                            "label": None,
                            # Original Word size (inches) from the DOCX drawing
                            # extent, surfaced by pandoc in the Image attributes.
                            "width_in": width_in,
                            "height_in": height_in,
                        }
                    )

                if item_t == "Math":
                    math_type = item_c[0].get("t") if len(item_c) > 0 else ""
                    latex_code = item_c[1] if len(item_c) > 1 else ""
                    if math_type == "DisplayMath":
                        counters["equations"] += 1
                        return DocumentBlock(
                            type=BlockType.EQUATION,
                            content={
                                "latex_code": latex_code,
                                "label": None
                            }
                        )

            # Standard paragraph block
            text = self._stringify_inlines(inlines)
            if not text.strip():
                return None
            counters["paragraphs"] += 1
            return DocumentBlock(
                type=BlockType.PARAGRAPH,
                content={"text": text}
            )

        elif t == "Table":
            counters["tables"] += 1
            try:
                if not isinstance(c, list) or len(c) < 5:
                    raise ValueError("unexpected table AST shape")
                return DocumentBlock(type=BlockType.TABLE, content=self._parse_table_rich(c))
            except Exception as e:
                counters["warnings"].append(f"Table parsing error: {str(e)}")
                return DocumentBlock(
                    type=BlockType.TABLE,
                    content={"caption": "Table parsing error", "headers": [], "rows": [], "label": None}
                )

        elif t in ("BulletList", "OrderedList"):
            items = []
            list_content = c[1] if t == "OrderedList" else c
            for item in list_content:
                item_text = self._stringify_blocks(item)
                if item_text.strip():
                    items.append(item_text)

            counters["paragraphs"] += len(items)
            return DocumentBlock(
                type=BlockType.LIST,
                content={
                    "items": items,
                    "ordered": t == "OrderedList"
                }
            )

        return None

    def _find_image_in_blocks(self, blocks: List[Dict[str, Any]]) -> Optional[str]:
        """Find the first image path in a list of blocks."""
        for b in blocks:
            if not isinstance(b, dict):
                continue
            t = b.get("t")
            c = b.get("c")
            if t in ("Para", "Plain"):
                for item in c:
                    if isinstance(item, dict) and item.get("t") == "Image":
                        img_c = item.get("c", [])
                        return img_c[2][0] if len(img_c) > 2 and len(img_c[2]) > 0 else None
        return None

    def _stringify_inlines(self, inlines: List[Dict[str, Any]]) -> str:
        """Convert inline elements into plain string."""
        parts = []
        for item in inlines:
            if not isinstance(item, dict):
                continue
            t = item.get("t")
            c = item.get("c")

            if t == "Str":
                parts.append(c)
            elif t == "Space":
                parts.append(" ")
            elif t == "SoftBreak":
                parts.append(" ")
            elif t == "LineBreak":
                parts.append("\n")
            elif t == "Math":
                parts.append(f"${c[1]}$")
            elif t in ("Emph", "Strong", "Strikeout", "Superscript", "Subscript",
                       "SmallCaps", "Underline"):
                # Formatting wrappers: keep the text content (superscripted
                # citation markers like "[2]" must survive for citation mapping).
                parts.append(self._stringify_inlines(c))
            elif t == "Span":
                parts.append(self._stringify_inlines(c[1]))
            elif t == "Quoted":
                parts.append(f'"{self._stringify_inlines(c[1])}"')
            elif t == "Code":
                parts.append(c[1])
            elif t == "Link":
                parts.append(self._stringify_inlines(c[2]))
            elif t == "Cite":
                parts.append(self._stringify_inlines(c[1]))
        return "".join(parts)

    def _heading_format_for(self, title: str) -> Optional[Dict[str, Any]]:
        """Look up DOCX heading formatting for a section title (whitespace-
        insensitive match)."""
        formats = getattr(self, "_heading_formats", {}) or {}
        key = "".join((title or "").split()).lower()
        return formats.get(key)

    def _extract_corresponding_email(self, docx_path: Path) -> str:
        """Read the corresponding-author e-mail from the raw DOCX parts.

        Journal templates place the corresponding-author note in many different
        locations, most of which pandoc never surfaces.  Every part that could
        carry it is scanned -- the body, all footers (first-page / default /
        even), all headers (first-page / default / even), footnotes, endnotes
        and author-note parts.  Each e-mail found is scored: a paragraph that
        also carries a corresponding-author / e-mail label or an asterisk /
        superscript marker outranks a bare address, and among equal scores the
        location order above breaks ties.  The single best candidate is
        returned, so a duplicated address (e.g. repeated in every footer)
        yields exactly one copy.  Nothing is hardcoded: the address, the label
        and the author are all read from the file.  Best-effort -- returns ""
        when no e-mail can be found, so no empty label is ever rendered.
        """
        import zipfile
        import xml.etree.ElementTree as ET

        W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        email_re = re.compile(r"[\w.\-+]+@[\w\-]+(?:\.[\w\-]+)+")
        label_re = re.compile(r"correspond|e-?mail\s*:|author\s+note", re.IGNORECASE)
        marker_re = re.compile("^\\s*[*∗✱٭†‡§\\d]")

        def paragraph_texts(xml_bytes: bytes):
            """Yield the concatenated text of each <w:p> paragraph."""
            try:
                root = ET.fromstring(xml_bytes)
            except ET.ParseError:
                return
            for p in root.iter(f"{W}p"):
                runs = [t.text or "" for t in p.iter(f"{W}t")]
                text = "".join(runs).strip()
                if text:
                    yield text

        try:
            with zipfile.ZipFile(docx_path) as zf:
                names = set(zf.namelist())
                # Locations in tie-break preference order.  Footers and the
                # author-note parts are where corresponding-author lines almost
                # always live; the body and headers are lower-priority fallbacks.
                footer_parts = sorted(
                    n for n in names if re.match(r"word/footer\d*\.xml$", n)
                )
                header_parts = sorted(
                    n for n in names if re.match(r"word/header\d*\.xml$", n)
                )
                note_parts = [
                    n for n in ("word/footnotes.xml", "word/endnotes.xml")
                    if n in names
                ]
                body_parts = [n for n in ("word/document.xml",) if n in names]
                ordered_parts = (
                    footer_parts + note_parts + body_parts + header_parts
                )

                best_email = ""
                best_score = -1
                for loc_rank, part in enumerate(ordered_parts):
                    try:
                        xml_bytes = zf.read(part)
                    except KeyError:
                        continue
                    for text in paragraph_texts(xml_bytes):
                        m = email_re.search(text)
                        if not m:
                            continue
                        email = m.group(0).rstrip(".,;:)")
                        # Score: labelled note (+2) beats an asterisk/superscript
                        # marker (+1) beats a bare address (0); earlier locations
                        # win ties via a small location bonus.
                        score = 0
                        if label_re.search(text):
                            score += 2
                        if marker_re.match(text):
                            score += 1
                        score = score * 100 + (len(ordered_parts) - loc_rank)
                        if score > best_score:
                            best_score = score
                            best_email = email
                return best_email
        except Exception:  # noqa: BLE001 - best-effort extraction
            return ""

    def _extract_heading_formats(self, docx_path: Path) -> Dict[str, Dict[str, Any]]:
        """Read per-heading formatting straight from word/document.xml.

        Detects headings by (a) a Heading 1..9 paragraph style, (b) an explicit
        outline level, or (c) a formatting fallback (fully-bold, numbered, short
        paragraph -- the same rule used for the Pandoc-AST pass).  For each it
        records level, bold, absolute + body-relative font size, alignment,
        space-before / space-after (points), and keep-with-next.  Best-effort:
        any failure returns an empty map and the renderer falls back to plain
        sectioning.
        """
        import zipfile
        import xml.etree.ElementTree as ET

        W = self._W_NS
        formats: Dict[str, Dict[str, Any]] = {}
        try:
            with zipfile.ZipFile(docx_path) as zf:
                doc_root = ET.fromstring(zf.read("word/document.xml"))
                styles_root = None
                if "word/styles.xml" in zf.namelist():
                    styles_root = ET.fromstring(zf.read("word/styles.xml"))
        except Exception:
            return formats

        # Body font size + heading-style level/bold/size from styles.xml.
        body_size = 11.0
        style_levels: Dict[str, int] = {}
        style_info: Dict[str, Dict[str, Any]] = {}
        if styles_root is not None:
            for st in styles_root.findall(f"{W}style"):
                sid = st.get(f"{W}styleId", "")
                name_el = st.find(f"{W}name")
                name = name_el.get(f"{W}val", "") if name_el is not None else ""
                st_rpr = st.find(f"{W}rPr")
                st_bold = st_rpr is not None and st_rpr.find(f"{W}b") is not None
                st_size = None
                if st_rpr is not None:
                    szn = st_rpr.find(f"{W}sz")
                    if szn is not None:
                        try:
                            st_size = int(szn.get(f"{W}val")) / 2.0
                        except (TypeError, ValueError):
                            st_size = None
                if sid == "Normal" and st_size:
                    body_size = st_size
                lvl = None
                m = re.match(r"heading\s*(\d)", name.lower())
                if m:
                    lvl = int(m.group(1))
                else:
                    olvl = st.find(f"{W}pPr/{W}outlineLvl")
                    if olvl is not None:
                        try:
                            lvl = int(olvl.get(f"{W}val")) + 1
                        except (TypeError, ValueError):
                            lvl = None
                if lvl is not None:
                    style_levels[sid] = lvl
                    style_info[sid] = {"bold": st_bold, "size_pt": st_size}

        body = doc_root.find(f"{W}body")
        if body is None:
            return formats

        for p in body.findall(f"{W}p"):
            text = " ".join(t.text for t in p.iter(f"{W}t") if t.text).strip()
            if not text or len(text) > 120:
                continue
            ppr = p.find(f"{W}pPr")
            style_id = None
            outline = None
            if ppr is not None:
                st = ppr.find(f"{W}pStyle")
                style_id = st.get(f"{W}val") if st is not None else None
                ol = ppr.find(f"{W}outlineLvl")
                if ol is not None:
                    try:
                        outline = int(ol.get(f"{W}val")) + 1
                    except (TypeError, ValueError):
                        outline = None

            # First run bold + size.
            bold = False
            size_pt = None
            r = p.find(f"{W}r")
            if r is not None:
                rpr = r.find(f"{W}rPr")
                if rpr is not None:
                    bold = rpr.find(f"{W}b") is not None
                    sz = rpr.find(f"{W}sz")
                    if sz is not None:
                        try:
                            size_pt = int(sz.get(f"{W}val")) / 2.0
                        except (TypeError, ValueError):
                            size_pt = None
            if ppr is not None and not bold:
                mark = ppr.find(f"{W}rPr")
                if mark is not None and mark.find(f"{W}b") is not None:
                    bold = True

            # Decide heading + level: style > outline > numbered-bold fallback.
            level = None
            if style_id in style_levels:
                level = style_levels[style_id]
                # Inherit bold / size from the heading style when the run
                # itself does not set them.
                info = style_info.get(style_id, {})
                if not bold and info.get("bold"):
                    bold = True
                if size_pt is None and info.get("size_pt"):
                    size_pt = info["size_pt"]
            elif outline is not None:
                level = outline
            else:
                num = re.match(r"^(\d+(?:\.\s?\d+)*)\.?\s+\S", text)
                if num and bold:
                    depth = len([x for x in re.split(r"\.\s?", num.group(1)) if x])
                    level = max(1, min(4, depth))
            if level is None:
                continue

            align = "left"
            before_pt = after_pt = None
            keep_next = False
            if ppr is not None:
                jc = ppr.find(f"{W}jc")
                if jc is not None:
                    align = jc.get(f"{W}val", "left")
                sp = ppr.find(f"{W}spacing")
                if sp is not None:
                    before_pt = self._twips_to_pt(sp.get(f"{W}before"))
                    after_pt = self._twips_to_pt(sp.get(f"{W}after"))
                keep_next = ppr.find(f"{W}keepNext") is not None

            key = "".join(text.split()).lower()
            formats[key] = {
                "level": level,
                "bold": bool(bold),
                "size_pt": size_pt,
                "body_size_pt": body_size,
                "size_ratio": round(size_pt / body_size, 3) if size_pt else 1.0,
                "alignment": align,
                "space_before_pt": before_pt,
                "space_after_pt": after_pt,
                "keep_with_next": keep_next,
            }
        return formats

    @staticmethod
    def _twips_to_pt(val) -> Optional[float]:
        try:
            return round(int(val) / 20.0, 1)
        except (TypeError, ValueError):
            return None

    def _detect_manual_heading(self, inlines: List[Dict[str, Any]]) -> Optional[int]:
        """Return the heading level for a manually-formatted numbered heading
        paragraph, or None if the paragraph is ordinary body text.

        A heading here is a short, fully-bold paragraph beginning with a
        dotted section number ("2.", "1.1", "2.4.3 ...").  The level equals the
        count of numeric components (capped at 4).  Requiring the paragraph to
        be entirely bold avoids misclassifying numbered body text such as
        affiliation lines ("3 Associate Professor ...").
        """
        text = self._stringify_inlines(inlines).strip()
        if not text or len(text) > 100:
            return None
        m = re.match(r"^(\d+(?:\.\s?\d+)*)\.?\s+\S", text)
        if not m:
            return None
        # Every visible inline must be Strong (bold).
        saw_bold = False
        for item in inlines:
            if not isinstance(item, dict):
                continue
            t = item.get("t")
            if t in ("Space", "SoftBreak", "LineBreak"):
                continue
            if t != "Strong":
                return None
            saw_bold = True
        if not saw_bold:
            return None
        depth = len([p for p in re.split(r"\.\s?", m.group(1)) if p])
        return max(1, min(4, depth))

    def _stringify_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """Convert block elements into plain string."""
        parts = []
        for b in blocks:
            if not isinstance(b, dict):
                continue
            t = b.get("t")
            c = b.get("c")

            if t in ("Para", "Plain"):
                parts.append(self._stringify_inlines(c))
            elif t == "Header":
                parts.append(self._stringify_inlines(c[2]))
            elif t == "BlockQuote":
                # Word list items frequently arrive as BlockQuote wrappers.
                parts.append(self._stringify_blocks(c))
            elif t == "Div":
                parts.append(self._stringify_blocks(c[1]))
            elif t == "LineBlock":
                parts.append(" ".join(self._stringify_inlines(line) for line in c))
            elif t in ("BulletList", "OrderedList"):
                list_items = c[1] if t == "OrderedList" else c
                item_texts = [self._stringify_blocks(item) for item in list_items]
                parts.append("\n".join(f"- {txt}" for txt in item_texts))
            elif t == "Table":
                # Word cells sometimes hold a nested table (e.g. a single-value
                # box wrapping a p-value like ".701").  Without this the cell
                # content is dropped and the cell renders blank, so recurse into
                # the nested table and keep its text.
                nested = self._stringify_nested_table_text(c)
                if nested:
                    parts.append(nested)
        return "\n\n".join(parts)

    def _stringify_nested_table_text(self, c: List[Any]) -> str:
        """Flatten the visible text of a (possibly nested) pandoc Table node.

        Pandoc Table = [attr, caption, colspecs, head, [bodies], foot].  Each
        row is [attr, [cells]] and each cell is
        [attr, align, rowspan, colspan, blocks].  Cell text is collected in
        row order and joined so multi-value nested tables keep every value.
        """
        try:
            def rows_of(section_rows):
                out = []
                for row in section_rows:
                    if not isinstance(row, list) or len(row) < 2:
                        continue
                    cell_texts = []
                    for cell in row[1]:
                        if isinstance(cell, list) and len(cell) >= 5:
                            txt = self._stringify_blocks(cell[4]).strip()
                            if txt:
                                cell_texts.append(txt)
                    if cell_texts:
                        out.append(" ".join(cell_texts))
                return out

            lines = []
            head = c[3] if len(c) > 3 else None
            if isinstance(head, list) and len(head) >= 2:
                lines += rows_of(head[1])
            for body in (c[4] if len(c) > 4 else []):
                if isinstance(body, list) and len(body) >= 4:
                    lines += rows_of(body[3])
            foot = c[5] if len(c) > 5 else None
            if isinstance(foot, list) and len(foot) >= 2:
                lines += rows_of(foot[1])
            return "\n".join(lines)
        except Exception:
            return ""

    # ------------------------------------------------------------------ #
    # Table structure extraction
    # ------------------------------------------------------------------ #

    _W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

    def _extract_table_styles(self, docx_path: Path) -> List[Dict[str, Any]]:
        """Read shading, borders, row heights and grid widths for each
        body-level table directly from word/document.xml."""
        import zipfile
        import xml.etree.ElementTree as ET

        W = self._W_NS
        styles: List[Dict[str, Any]] = []
        try:
            with zipfile.ZipFile(docx_path) as zf:
                root = ET.fromstring(zf.read("word/document.xml"))
                grid_style_ids = self._grid_style_ids(zf)
            body = root.find(f"{W}body")
            if body is None:
                return styles
            text_width_tw = self._text_width_twips(body, W)
            for tbl in body.findall(f"{W}tbl"):
                col_widths = [int(g.get(f"{W}w", 0)) for g in tbl.findall(f"{W}tblGrid/{W}gridCol")]
                # Table width as a fraction of the text column: prefer an
                # explicit dxa tblW, else fall back to the grid-column sum.
                # This lets the renderer reproduce the same on-page proportion.
                tblw_el = tbl.find(f"{W}tblPr/{W}tblW")
                total_tw = 0
                if tblw_el is not None and tblw_el.get(f"{W}type") == "dxa":
                    total_tw = int(tblw_el.get(f"{W}w", 0) or 0)
                if total_tw <= 0:
                    total_tw = sum(w for w in col_widths if w > 0)
                width_frac = None
                if text_width_tw and total_tw > 0:
                    width_frac = round(min(total_tw / text_width_tw, 1.0), 4)
                style_el = tbl.find(f"{W}tblPr/{W}tblStyle")
                style_id = style_el.get(f"{W}val", "") if style_el is not None else ""
                has_grid = (
                    tbl.find(f"{W}tblPr/{W}tblBorders") is not None
                    or style_id in grid_style_ids
                    or "grid" in style_id.lower()
                )
                shading_rows = []
                row_heights = []
                for tr in tbl.findall(f"{W}tr"):
                    fills = []
                    for tc in tr.findall(f"{W}tc"):
                        shd = tc.find(f"{W}tcPr/{W}shd")
                        fill = shd.get(f"{W}fill") if shd is not None else None
                        if fill in (None, "auto"):
                            fill = None
                        span_el = tc.find(f"{W}tcPr/{W}gridSpan")
                        span = int(span_el.get(f"{W}val", 1)) if span_el is not None else 1
                        fills.extend([fill] * span)
                    shading_rows.append(fills)
                    trh = tr.find(f"{W}trPr/{W}trHeight")
                    row_heights.append(
                        round(int(trh.get(f"{W}val", 0)) / 20.0, 1) if trh is not None else None
                    )
                styles.append({
                    "col_widths_tw": col_widths,
                    "has_grid": has_grid,
                    "shading_rows": shading_rows,
                    "row_heights": row_heights,
                    "width_frac": width_frac,
                })
        except Exception:
            pass  # styling is best-effort; structure never depends on it
        return styles

    @staticmethod
    def _text_width_twips(body, W) -> int:
        """Usable text-column width (page width minus L/R margins), in twips."""
        try:
            sect = body.find(f"{W}sectPr")
            if sect is None:
                for el in body.iter(f"{W}sectPr"):
                    sect = el
                    break
            if sect is None:
                return 0
            pg = sect.find(f"{W}pgSz")
            mar = sect.find(f"{W}pgMar")
            if pg is None or mar is None:
                return 0
            page_w = int(pg.get(f"{W}w", 0) or 0)
            left = int(mar.get(f"{W}left", 0) or 0)
            right = int(mar.get(f"{W}right", 0) or 0)
            return max(page_w - left - right, 0)
        except Exception:
            return 0

    def _grid_style_ids(self, zf) -> set:
        """Style IDs in styles.xml whose definition draws table borders."""
        import re as _re
        ids = set()
        try:
            styles_xml = zf.read("word/styles.xml").decode("utf-8", "ignore")
            for m in _re.finditer(
                r'<w:style [^>]*w:styleId="([^"]+)"(.*?)</w:style>', styles_xml, _re.S
            ):
                if "<w:tblBorders>" in m.group(2):
                    ids.add(m.group(1))
        except Exception:
            pass
        return ids

    _PANDOC_ALIGN = {
        "AlignLeft": "l", "AlignCenter": "c", "AlignRight": "r", "AlignDefault": None,
    }

    @staticmethod
    def _image_dimensions_in(image_c: List[Any]):
        """Original image size in inches from a pandoc Image node.

        Pandoc copies the DOCX drawing extent into the Image attribute list as
        ``width``/``height`` (e.g. ``6.36in``, ``480px``, ``12cm``).  Returns
        ``(width_in, height_in)`` with either value ``None`` when absent or
        unparseable, so the renderer can reproduce the exact Word dimensions
        instead of stretching the picture to the line width.
        """
        try:
            attrs = image_c[0][2] if image_c and len(image_c[0]) > 2 else []
        except (IndexError, TypeError):
            return None, None

        unit_to_in = {
            "in": 1.0, "pt": 1.0 / 72.27, "px": 1.0 / 96.0, "bp": 1.0 / 72.0,
            "cm": 1.0 / 2.54, "mm": 1.0 / 25.4, "pc": 12.0 / 72.27, "em": None,
        }
        dims = {}
        for key, raw in attrs:
            if key not in ("width", "height"):
                continue
            m = re.match(r"^\s*([\d.]+)\s*([a-z%]*)\s*$", str(raw), re.IGNORECASE)
            if not m:
                continue
            value = float(m.group(1))
            unit = (m.group(2) or "in").lower()
            factor = unit_to_in.get(unit)
            if factor is None:  # relative/unknown unit -> let renderer decide
                continue
            dims[key] = round(value * factor, 4)
        return dims.get("width"), dims.get("height")

    def _parse_table_cell(self, cell: List[Any]) -> Dict[str, Any]:
        """Pandoc Cell = [attr, alignment, rowspan, colspan, blocks]."""
        attr, align, rowspan, colspan, blocks = cell
        return {
            "text": self._stringify_blocks(blocks).strip(),
            "rowspan": int(rowspan),
            "colspan": int(colspan),
            "align": self._PANDOC_ALIGN.get(align.get("t") if isinstance(align, dict) else None),
            "bold": self._cell_is_bold(blocks),
        }

    @staticmethod
    def _cell_is_bold(blocks: List[Any]) -> bool:
        """True when every visible inline of the cell is Strong-wrapped."""
        saw_content = False
        for b in blocks:
            if not isinstance(b, dict) or b.get("t") not in ("Para", "Plain"):
                continue
            for item in b.get("c", []):
                if not isinstance(item, dict):
                    continue
                t = item.get("t")
                if t in ("Space", "SoftBreak"):
                    continue
                if t != "Strong":
                    return False
                saw_content = True
        return saw_content

    def _parse_table_rich(self, c: List[Any]) -> Dict[str, Any]:
        """Extract the full pandoc table structure plus XML styling."""
        caption = "Table"
        caption_block = c[1]
        if isinstance(caption_block, dict) and "c" in caption_block:
            caption = self._stringify_blocks(caption_block.get("c", [])) or "Table"
        elif isinstance(caption_block, list):
            caption = self._stringify_blocks(caption_block) or "Table"

        colspecs = []
        for spec in (c[2] or []):
            align = self._PANDOC_ALIGN.get(spec[0].get("t")) if spec and isinstance(spec[0], dict) else None
            width = None
            if len(spec) > 1 and isinstance(spec[1], dict) and spec[1].get("t") == "ColWidth":
                width = float(spec[1]["c"])
            colspecs.append({"align": align, "width": width})

        def parse_rows(rows_list):
            return [
                [self._parse_table_cell(cell) for cell in row[1]]
                for row in rows_list
                if len(row) >= 2
            ]

        header_rows = parse_rows(c[3][1]) if isinstance(c[3], list) and len(c[3]) >= 2 else []
        body_rows = []
        for body in c[4]:
            if isinstance(body, list) and len(body) >= 4:
                body_rows.extend(parse_rows(body[3]))

        # Attach XML styling for this table (body-level order == pandoc order).
        style = {}
        styles = getattr(self, "_table_styles", [])
        idx = getattr(self, "_table_style_idx", 0)
        if idx < len(styles):
            style = styles[idx]
        self._table_style_idx = idx + 1

        total_tw = sum(style.get("col_widths_tw", [])) or None
        if total_tw and not any(cs["width"] for cs in colspecs):
            for cs, tw in zip(colspecs, style.get("col_widths_tw", [])):
                cs["width"] = tw / total_tw

        # Legacy flat view (kept for fidelity/asset reports and old renderers).
        flat_headers = [cell["text"] for cell in header_rows[-1]] if header_rows else []
        flat_rows = [[cell["text"] for cell in row] for row in body_rows]

        return {
            "caption": caption,
            "label": None,
            "colspecs": colspecs,
            "header_rows": header_rows,
            "body_rows": body_rows,
            "has_grid": style.get("has_grid", False),
            "shading_rows": style.get("shading_rows", []),
            "row_heights": style.get("row_heights", []),
            "width_frac": style.get("width_frac"),
            "headers": flat_headers,
            "rows": flat_rows,
        }
