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
        institution_keywords = ["university", "department", "institute", "school", "college", "lab", "corp", "inc", "ltd", "centre"]
        current_author: Optional[AuthorModel] = None

        for txt in intro_texts:
            # Skip dates/metadata and journal header markers
            if any(x in txt.lower() for x in ["received:", "revised:", "accepted:", "published online:", "j. stat.", "vol.", "issn", "http", "doi:", "volume", "issue"]):
                continue

            emails = email_regex.findall(txt)
            is_inst = any(k in txt.lower() for k in institution_keywords)

            if emails:
                if current_author:
                    current_author.email = emails[0]
                else:
                    current_author = AuthorModel(name="Corresponding Author", email=emails[0])
                    authors.append(current_author)
            elif is_inst:
                # This paragraph represents affiliation info. Attach to preceding authors.
                if current_author:
                    current_author.affiliation = txt
                else:
                    if authors:
                        authors[-1].affiliation = txt
            else:
                # Likely name or comma-separated authors
                # Strip footnotes tags (like Carlo Bianca^1 -> Carlo Bianca)
                cleaned_name = re.sub(r"\^\{\d+\}|\^\d+", "", txt).strip()
                names = [n.strip() for n in re.split(r",|\band\b", cleaned_name) if n.strip()]
                for name in names:
                    current_author = AuthorModel(name=name)
                    authors.append(current_author)

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
                m_rec = re.search(r"received:\s*([^,.]+)", txt, re.IGNORECASE)
                if m_rec:
                    received_date = m_rec.group(1).strip()
                m_rev = re.search(r"revised:\s*([^,.]+)", txt, re.IGNORECASE)
                if m_rev:
                    revised_date = m_rev.group(1).strip()
                m_acc = re.search(r"accepted:\s*([^,.]+)", txt, re.IGNORECASE)
                if m_acc:
                    accepted_date = m_acc.group(1).strip()
            if "published online:" in txt_lower:
                m_pub = re.search(r"published online:\s*([^,.]+)", txt, re.IGNORECASE)
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
        current_section = SectionModel(title="Introduction", level=1, blocks=[])
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

                if current_section and current_section.blocks:
                    doc.sections.append(current_section)

                current_section = SectionModel(title=header_text, level=level, blocks=[])
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
                    references_list.append(self._stringify_inlines(c))
                    counters["references"] += 1
                elif t in ("BulletList", "OrderedList"):
                    list_items = c[1] if t == "OrderedList" else c
                    for item in list_items:
                        references_list.append(self._stringify_blocks(item))
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

            parsed_block = self._parse_block(b, job_id, counters)
            if parsed_block and current_section:
                global_block_index += 1
                parsed_block.block_index = global_block_index
                parsed_block.original_order = global_block_index
                parsed_block.source_location = f"Section: {current_section.title}, Block: {global_block_index}"
                current_section.blocks.append(parsed_block)

        if current_section and current_section.blocks:
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
                    counters["figures"] += 1
                    return DocumentBlock(
                        type=BlockType.FIGURE,
                        content={
                            "caption": caption,
                            "path": src,
                            "label": None
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
                headers = []
                rows = []
                caption = "Table"

                if isinstance(c, list) and len(c) >= 5:
                    caption_block = c[1]
                    if isinstance(caption_block, dict) and "c" in caption_block:
                        caption = self._stringify_blocks(caption_block.get("c", []))
                    elif isinstance(caption_block, list):
                        caption = self._stringify_blocks(caption_block)

                    head_block = c[3]
                    if isinstance(head_block, list) and len(head_block) >= 2:
                        rows_list = head_block[1]
                        for row in rows_list:
                            cells = row[1] if len(row) >= 2 else []
                            headers = [self._stringify_blocks(cell[4] if len(cell) >= 5 else cell) for cell in cells]

                    bodies = c[4]
                    for body in bodies:
                        if isinstance(body, list) and len(body) >= 4:
                            body_rows = body[3]
                            for row in body_rows:
                                cells = row[1] if len(row) >= 2 else []
                                row_texts = [self._stringify_blocks(cell[4] if len(cell) >= 5 else cell) for cell in cells]
                                rows.append(row_texts)

                return DocumentBlock(
                    type=BlockType.TABLE,
                    content={
                        "caption": caption,
                        "headers": headers,
                        "rows": rows,
                        "label": None
                    }
                )
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
            elif t in ("Emph", "Strong", "Strikeout"):
                parts.append(self._stringify_inlines(c))
            elif t == "Quoted":
                parts.append(f'"{self._stringify_inlines(c[1])}"')
            elif t == "Code":
                parts.append(c[1])
            elif t == "Link":
                parts.append(self._stringify_inlines(c[2]))
            elif t == "Cite":
                parts.append(self._stringify_inlines(c[1]))
        return "".join(parts)

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
            elif t in ("BulletList", "OrderedList"):
                list_items = c[1] if t == "OrderedList" else c
                item_texts = [self._stringify_blocks(item) for item in list_items]
                parts.append("\n".join(f"- {txt}" for txt in item_texts))
        return "\n\n".join(parts)
