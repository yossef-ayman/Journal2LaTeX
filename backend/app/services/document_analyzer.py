import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.models.document import AuthorModel, DocumentBlock, DocumentModel, SectionModel, BlockType, AuthorBiography
from app.utils.logger import get_job_logger


# Manually-formatted numbered heading, e.g. "2. Literature Review", "3.5 Data
# Analysis", "2.2.1.1 Algorithmic Amplification".  The separator after the
# number is either whitespace or a trailing dot: Word documents frequently omit
# the space ("4.2.Descriptive Statistics"), and requiring one silently demoted
# such headings to body text, which merged their content into the previous
# section.  The lookahead rejects a following digit so that decimal values are
# not mistaken for section numbers.  Callers additionally require the paragraph
# to be short and fully bold.
_MANUAL_HEADING_RE = r"^(\d+(?:\.\s?\d+)*)(?:\.\s*|\s+)(?=[^\s\d])"

# Roman-numeral section number, the IEEE convention ("II. SYSTEM MODEL").  The
# alternation is ordered longest-first so that "III" is not matched as "II".
_ROMAN_HEADING_RE = (
    r"^((?:X{0,3})(?:IX|IV|V?I{0,3}))[.)]\s+(?=[A-Za-z])"
)
# Lettered subsection, also IEEE ("A. Signal Model").  Deliberately requires an
# upper-case word after the letter and is only consulted for paragraphs that
# already look like headings by formatting, because "A. Smith" in an author list
# has exactly the same shape.
_LETTER_HEADING_RE = r"^([A-Z])[.)]\s+(?=[A-Z])"
# A word-prefixed hierarchy label: "Chapter 1.", "Part II", "Appendix A".
# Universities and book-style theses use these instead of a bare number.
_WORD_HEADING_RE = (
    r"^(chapter|part|appendix|annex|section)\s+"
    r"([0-9]+|[IVXLC]+|[A-Z])\b[.:)]?\s*"
)

# Front-matter labels.  These mark blocks that belong to the title page even
# when they are formatted as headings, so they must not end the front matter.
# Matching is done on a normalised form (see _normalise_label) so that the
# letter-spaced Elsevier variant "A B S T R A C T" and the em-dash IEEE variant
# "Abstract-We propose" both reduce to the same key.
_ABSTRACT_LABEL_RE = re.compile(
    r"^(abstract|summary|graphical abstract|highlights)\b[\s:.–—-]*",
    re.IGNORECASE,
)
_KEYWORD_LABEL_RE = re.compile(
    r"^(keywords?|key\s*words?|index\s*terms|subject\s*terms|"
    r"mathematics subject classification|msc)\b[\s:.–—-]*",
    re.IGNORECASE,
)
# Separators used between keywords across publishers: comma, semicolon, the
# Springer middle dot, and the bullet some templates use instead.
_KEYWORD_SPLIT_RE = r"[,;·•·]|\s·\s"

_EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")

# Journal / submission furniture that surrounds the real front matter on a
# reprint or a submission cover page.  Matched generically -- volume and issue
# tags, identifiers, submission dates, licences -- rather than by naming any
# particular journal, so no publisher is special-cased.
_FURNITURE_RE = re.compile(
    r"(^|\b)("
    # "Vol." / "No." are abbreviations that occur in a masthead and essentially
    # never in a title, so they are matched without requiring a following digit:
    # a reprint header reads "J. Stat. Appl. Pro. Vol. No. (20--) 185", where
    # the numbers have been left as placeholders.
    r"vol\.|volume\s+\d|no\.\s|issue\s+\d|pp\.?\s*\d|"
    r"issn|isbn|doi\s*:|https?://|www\.|"
    r"received\s*:|revised\s*:|accepted\s*:|published(\s+online)?\s*:|"
    r"submitted\s*:|available\s+online|"
    r"copyright|©|all\s+rights\s+reserved|licen[cs]e|creative\s+commons|"
    r"preprint|manuscript\s+(id|number)"
    r")",
    re.IGNORECASE,
)


def _normalise_label(text: str) -> str:
    """Collapse a display label to a comparable form.

    Elsevier sets section labels letter-spaced ("A B S T R A C T"); Word stores
    that literally, so a plain comparison against "abstract" fails.  When a
    string is composed only of single characters separated by spaces the spaces
    are removed, which maps the letter-spaced form onto the ordinary one and
    leaves every normal label untouched.
    """
    stripped = (text or "").strip()
    if not stripped:
        return ""
    parts = stripped.split()
    if len(parts) > 2 and all(len(p) == 1 for p in parts):
        return "".join(parts)
    return stripped


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
            # Usable text-column width (inches) -- lets figure placement decide
            # whether a picture spans the full width or fits inside one column.
            self._text_width_in = self._extract_text_width_in(docx_path)
            # Per-image Word placement (inline-in-text vs anchored/floating),
            # keyed by media path -- a signal for the placement policy.
            self._drawing_inline = self._extract_drawing_placement(docx_path)
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

        # Headings that Word never marked as headings -- direct-formatted
        # manuscripts, IEEE and Elsevier submissions -- are recovered here so
        # the split below and the section tree both see a real hierarchy.
        blocks = self._promote_semantic_headings(blocks)
        # Word keeps a caption in its own paragraph with no link to the object
        # it describes; pair them up before parsing so neither is duplicated.
        blocks = self._attach_captions(blocks)

        # Separate metadata blocks from body blocks.  The boundary is the first
        # *body* heading.  "Abstract" and "Keywords" are frequently formatted as
        # headings in their own right, and treating one of those as the start of
        # the body strands the abstract in section 1 and empties the title page,
        # so a front-matter label does not close the front matter.
        intro_metadata_blocks = []
        body_blocks = []
        found_header = False

        for b in blocks:
            if not found_header and b.get("t") == "Header":
                c = b.get("c") or []
                htxt = _normalise_label(
                    self._stringify_inlines(c[2] if len(c) > 2 else [])
                )
                if not (_ABSTRACT_LABEL_RE.match(htxt) or _KEYWORD_LABEL_RE.match(htxt)):
                    found_header = True
            if not found_header:
                intro_metadata_blocks.append(b)
            else:
                body_blocks.append(b)

        # A manuscript typed with no heading styles and no direct formatting on
        # its headings ("Introduction" set in the same 11pt regular as the body)
        # yields no Header at all, so the loop above never closes the front
        # matter and the entire document is swallowed as metadata: the pipeline
        # still reports success, but the PDF contains only a title page and
        # every remaining page is lost.  The front matter has a definite end
        # whether or not a heading marks it, so when no boundary was found one
        # is located structurally and the remainder is restored as body.
        if not found_header and blocks:
            split_at = self._front_matter_end(blocks)
            if split_at < len(blocks):
                intro_metadata_blocks = blocks[:split_at]
                body_blocks = blocks[split_at:]

        # Clean/Stringify the metadata blocks.  Header text is kept inline with
        # the paragraphs so that a standalone "Abstract" / "Keywords" label can
        # still be associated with the text that follows it.
        intro_texts = []
        for b in intro_metadata_blocks:
            if b.get("t") in ("Para", "Plain"):
                txt = self._stringify_inlines(b.get("c", [])).strip()
                if txt:
                    intro_texts.append(txt)
            elif b.get("t") == "Header":
                c = b.get("c") or []
                txt = self._stringify_inlines(c[2] if len(c) > 2 else []).strip()
                if txt:
                    intro_texts.append(txt)
            elif b.get("t") == "Table":
                # Springer and IEEE frequently lay the author block out in an
                # invisible table.  Its cells are front matter, not a data
                # table, and were previously discarded outright.
                for cell in self._table_cell_texts(b):
                    if cell:
                        intro_texts.append(cell)

        title = ""
        authors: List[AuthorModel] = []
        abstract_text = ""
        keywords_list = []

        # Heuristics for Title/Author/Abstract extraction from initial paragraphs
        # 1. Title Extraction
        if "title" in meta:
            title = self._stringify_inlines(meta["title"].get("c", []))

        if not title.strip() and intro_texts:
            # Search a little deeper than the first few paragraphs: thesis title
            # pages open with a university name and a degree statement, and
            # journal reprints open with a masthead.
            for txt in intro_texts[:8]:
                if self._is_journal_furniture(txt):
                    continue
                if _ABSTRACT_LABEL_RE.match(_normalise_label(txt)) or \
                        _KEYWORD_LABEL_RE.match(_normalise_label(txt)):
                    break
                # A title is a substantial line that is not a sentence and not
                # an address or a name list.
                if len(txt) > 20 and len(txt) <= 300 and not _EMAIL_RE.search(txt):
                    title = txt
                    intro_texts.remove(txt)
                    break

        # 2. Abstract & Keywords.  Publishers differ in both the label wording
        # ("Abstract", "Summary", "Index Terms", "Key words") and in whether the
        # label shares a paragraph with its content ("Abstract-We propose ...")
        # or stands alone as its own heading.  Both layouts are handled, and the
        # label itself is matched on the normalised form so the letter-spaced
        # Elsevier variant "A B S T R A C T" is recognised too.
        consumed: List[str] = []
        for idx, txt in enumerate(intro_texts):
            norm = _normalise_label(txt)
            m_abs = _ABSTRACT_LABEL_RE.match(norm)
            m_kw = _KEYWORD_LABEL_RE.match(norm)
            if m_abs and not abstract_text:
                rest = norm[m_abs.end():].strip()
                if not rest:
                    # Standalone label: the abstract is the paragraph after it.
                    nxt = intro_texts[idx + 1] if idx + 1 < len(intro_texts) else ""
                    if nxt and not _KEYWORD_LABEL_RE.match(_normalise_label(nxt)):
                        abstract_text = nxt
                        consumed.append(nxt)
                    consumed.append(txt)
                else:
                    abstract_text = rest
                    consumed.append(txt)
            elif m_kw and not keywords_list:
                rest = norm[m_kw.end():].strip()
                if not rest:
                    nxt = intro_texts[idx + 1] if idx + 1 < len(intro_texts) else ""
                    if nxt:
                        rest = nxt
                        consumed.append(nxt)
                    consumed.append(txt)
                else:
                    consumed.append(txt)
                keywords_list = [
                    w.strip(" .;·•") for w in re.split(_KEYWORD_SPLIT_RE, rest)
                    if w.strip(" .;·•")
                ]

        # Remove abstract and keyword blocks from metadata paragraphs to avoid duplicate processing
        for txt in consumed:
            if txt in intro_texts:
                intro_texts.remove(txt)

        # 3. Process Author & Affiliation lists from remaining metadata paragraphs
        email_regex = _EMAIL_RE
        author_markers = {}  # id(AuthorModel) -> superscript affiliation index
        institution_keywords = ["university", "department", "institute", "school", "college", "lab",
                                "corp", "inc", "ltd", "centre", "center", "faculty", "academy",
                                "hospital", "clinic", "foundation", "polytechnic"]
        current_author: Optional[AuthorModel] = None
        # Affiliation paragraphs that carried no index marker, kept in reading
        # order so they can be associated positionally once the whole front
        # matter has been seen (see the unmarked-affiliation pass below).
        unmarked_affiliations: List[str] = []
        # Authors nominated for correspondence by a footnote glyph on the name.
        starred_authors: List[AuthorModel] = []

        for txt in intro_texts:
            # Skip masthead / submission metadata.  Detected by shape rather
            # than by naming journals, so an unfamiliar publisher behaves the
            # same as a familiar one.
            if self._is_journal_furniture(txt):
                continue
            # A degree statement or a similar title-page sentence is prose, not
            # a name list; letting it through turned whole sentences into
            # "authors" on thesis front matter.
            if len(txt) > 200:
                continue

            emails = email_regex.findall(txt)
            is_inst = (
                any(k in txt.lower() for k in institution_keywords)
                and len(txt) <= 300  # longer texts are body/abstract, not affiliations
            )

            if emails:
                # Prefer the author the address actually belongs to.  A
                # corresponding-author note usually appears after the whole
                # name list, so attaching it to whichever author happened to be
                # parsed last credited the wrong person; matching the local
                # part against the surnames fixes that without any per-journal
                # rule.
                owner = self._author_for_email(emails[0], authors)
                if owner is not None:
                    owner.email = emails[0]
                elif current_author:
                    current_author.email = emails[0]
                else:
                    current_author = AuthorModel(name="Corresponding Author", email=emails[0])
                    authors.append(current_author)
                # An address very often shares its paragraph with the
                # affiliation it belongs to ("Institute of Marine Sciences,
                # University of Bergen, Norway  ingrid.sorensen@uib.no"), so the
                # paragraph is not finished with once the address is taken: the
                # remainder is still an affiliation and is processed as one
                # below.  Treating an address as terminal, which is what the
                # bare elif used to do, left every author of such a document
                # with no affiliation at all.
                txt = email_regex.sub("", txt).strip(" ,;·•∗*")
                is_inst = is_inst and bool(txt)

            if is_inst:
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
                else:
                    # No index marker.  Which author the line belongs to cannot
                    # be decided yet: the paragraph may precede the names
                    # (Springer/Elsevier put a single shared affiliation under
                    # the author line, plain Word manuscripts often list one per
                    # author), so it is queued and associated after the whole
                    # front matter has been read.  Attaching it to whichever
                    # author happened to be parsed last -- what this used to do
                    # -- credited only the final author and left the rest empty.
                    unmarked_affiliations.append(txt)
            elif not emails:
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
                # A name list is not a sentence.  Title pages carry degree
                # statements, dedications and submission notes that are short
                # enough to pass the length test but are plainly prose.
                if self._looks_like_prose(cleaned) and not re.search(r"\d\s*$", cleaned):
                    continue
                # Springer separates authors with a middle dot rather than a
                # comma, and several publishers use a bullet; both are treated
                # as list separators alongside the comma and "and".
                names = [n.strip() for n in re.split(r",|;|·|•|·|\band\b", cleaned) if n.strip()]
                for name in names:
                    marker_match = re.search(r"(\d+)\s*[*†‡§¶°]*$", name)
                    marker = int(marker_match.group(1)) if marker_match else None
                    # Strip the trailing affiliation / corresponding-author
                    # marker, whether it is a digit or one of the footnote
                    # glyphs publishers use in place of one.
                    display = re.sub(r"[\s,]*\d*\s*[*†‡§¶°∗]*$", "", name).strip()
                    if not display or not re.search(r"[A-Za-z]", display):
                        continue
                    current_author = AuthorModel(name=display)
                    if marker is not None:
                        author_markers[id(current_author)] = marker
                    # A footnote glyph on a name is the near-universal way of
                    # nominating the corresponding author, whatever the
                    # publisher; it is a signal on the text, not a style name.
                    if re.search(r"[*∗✱٭†‡]\s*$", name):
                        starred_authors.append(current_author)
                    authors.append(current_author)

        # Associate the affiliation paragraphs that carried no index marker.
        # Two shapes cover essentially every manuscript: one affiliation shared
        # by everyone, and one affiliation per author in the same order as the
        # name list.  Anything in between falls back to the shared reading,
        # which is the safer error -- an author with a slightly too general
        # affiliation still renders, an author with none does not.
        if unmarked_affiliations and authors:
            unaffiliated = [a for a in authors if not a.affiliation]
            if len(unmarked_affiliations) == 1:
                for author in unaffiliated:
                    author.affiliation = unmarked_affiliations[0]
            elif len(unmarked_affiliations) == len(unaffiliated):
                for author, aff in zip(unaffiliated, unmarked_affiliations):
                    author.affiliation = aff
            else:
                for idx, author in enumerate(unaffiliated):
                    author.affiliation = unmarked_affiliations[
                        min(idx, len(unmarked_affiliations) - 1)
                    ]

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
            # Attach the address to the person it actually belongs to.  The
            # address's own local part is the strongest signal and is tried
            # first; failing that, a footnote glyph on a name nominates the
            # corresponding author; only when neither is available does the
            # first author stand in.  Blindly crediting the first author, which
            # is what this used to do, mis-assigned the address on manuscripts
            # whose corresponding author is not listed first.
            if not existing_email and authors:
                target = (
                    self._author_for_email(corresponding_email, authors)
                    or (starred_authors[0] if starred_authors else None)
                    or authors[0]
                )
                if not target.email:
                    target.email = corresponding_email

        # Record who the paper nominates for correspondence.  The author holding
        # the corresponding address is the definitive answer; a footnote glyph is
        # the fallback when no address could be resolved to a person.
        if authors:
            holder = next((a for a in authors if a.email and a.email == doc.corresponding_email), None)
            if holder is None and starred_authors:
                holder = starred_authors[0]
            if holder is None and doc.corresponding_email:
                holder = next((a for a in authors if a.email), None)
            if holder is not None:
                holder.is_corresponding = True
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
                    # A picture wider than half the text column cannot sit inside
                    # one column of a two-column layout, so it must span the full
                    # width; narrower ones stay inline in the column.  Unknown
                    # width defaults to spanning (the common journal-figure case).
                    tw_in = getattr(self, "_text_width_in", 0.0) or 0.0
                    full_width = (width_in is None) or (not tw_in) or (
                        width_in > tw_in / 2.0
                    )
                    word_inline = getattr(self, "_drawing_inline", {}).get(src, True)
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
                            "full_width": full_width,
                            # Placement signals consumed by the renderer's policy.
                            "word_inline": word_inline,
                            "text_width_in": tw_in,
                        }
                    )

            # Display math is handled after the loop so that the rest of the
            # paragraph is never discarded (see _display_equation_block).
            equation = self._display_equation_block(inlines, counters)
            if equation is not None:
                return equation

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
                parts.append(self._math_to_text(c))
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

    def _collect_display_math(self, inlines: Any) -> List[str]:
        """Every DisplayMath body in an inline tree, in reading order.

        The tree is walked recursively because Word wraps equations in
        character-style runs, which pandoc emits as ``Span``/``Emph``/``Strong``
        around the ``Math`` node.  Only inspecting the top level -- as the old
        code did -- missed every styled equation.
        """
        found: List[str] = []
        if not isinstance(inlines, list):
            return found
        for item in inlines:
            if not isinstance(item, dict):
                continue
            t = item.get("t")
            c = item.get("c")
            if t == "Math":
                if isinstance(c, list) and len(c) > 1 and isinstance(c[0], dict):
                    if c[0].get("t") == "DisplayMath" and (c[1] or "").strip():
                        cleaned = self._sanitize_math(c[1].strip())
                        if cleaned:
                            found.append(cleaned)
            elif t in ("Emph", "Strong", "Strikeout", "Superscript", "Subscript",
                       "SmallCaps", "Underline"):
                found.extend(self._collect_display_math(c))
            elif t in ("Span", "Quoted"):
                found.extend(self._collect_display_math(c[1] if isinstance(c, list) and len(c) > 1 else None))
            elif t == "Link":
                found.extend(self._collect_display_math(c[2] if isinstance(c, list) and len(c) > 2 else None))
        return found

    def _display_equation_block(self, inlines: Any,
                                counters: Dict[str, Any]) -> Optional[DocumentBlock]:
        """Turn a display-equation paragraph into an EQUATION block.

        Returns None when the paragraph is *not* purely an equation, in which
        case the caller renders it as an ordinary paragraph -- the math still
        survives, embedded as a ``\\[...\\]`` span, so no equation can ever be
        lost or downgraded to plain text.  The previous implementation returned
        an EQUATION block on the first display node and silently discarded every
        other inline in the paragraph, which threw away the equation number that
        Word almost always places on the same line.
        """
        bodies = self._collect_display_math(inlines)
        if not bodies:
            return None

        residual = self._stringify_inlines(inlines)
        for body in bodies:
            residual = residual.replace(f"\\[{body}\\]", "", 1)

        # Word writes the equation number as "(3)" on the same line, usually
        # after a tab.  Capture it so the original numbering is reproduced
        # exactly instead of being replaced by LaTeX's own counter.
        number = None
        num_match = re.search(r"\(\s*([0-9]+(?:[.\-][0-9A-Za-z]+)*|[A-Za-z][.\-][0-9]+)\s*\)",
                              residual)
        if num_match:
            number = num_match.group(1)
            residual = residual[:num_match.start()] + residual[num_match.end():]

        # Anything left beyond punctuation/whitespace means this paragraph is
        # prose that happens to contain a display equation; keep it as prose.
        if re.sub(r"[\s.,;:]", "", residual):
            return None

        if len(bodies) == 1:
            latex_code = bodies[0]
        else:
            # Several display equations in one Word paragraph form a multi-line
            # equation; gathered keeps them centred as separate lines.
            latex_code = ("\\begin{gathered}\n"
                          + " \\\\\n".join(bodies)
                          + "\n\\end{gathered}")

        counters["equations"] += 1
        return DocumentBlock(
            type=BlockType.EQUATION,
            content={"latex_code": latex_code, "label": None, "number": number},
        )

    # Characters Word stores literally inside an equation but which have no
    # meaning to TeX's math mode.  Left as-is they are either dropped silently
    # by the font or raise "Package inputenc Error: Unicode character not set
    # up".  Each maps to the construct a mathematician would have typed.
    _MATH_UNICODE = {
        "²": "^{2}", "³": "^{3}", "¹": "^{1}",
        "⁰": "^{0}", "⁴": "^{4}", "⁵": "^{5}",
        "⁶": "^{6}", "⁷": "^{7}", "⁸": "^{8}", "⁹": "^{9}",
        "⁺": "^{+}", "⁻": "^{-}", "ⁿ": "^{n}",
        "₀": "_{0}", "₁": "_{1}", "₂": "_{2}", "₃": "_{3}",
        "₄": "_{4}", "₅": "_{5}", "₆": "_{6}", "₇": "_{7}",
        "₈": "_{8}", "₉": "_{9}",
        "×": r"\times ", "÷": r"\div ", "±": r"\pm ",
        "∓": r"\mp ", "≠": r"\neq ", "≤": r"\leq ",
        "≥": r"\geq ", "≈": r"\approx ", "≡": r"\equiv ",
        "∞": r"\infty ", "∂": r"\partial ", "∇": r"\nabla ",
        "√": r"\sqrt{}", "∫": r"\int ", "∑": r"\sum ",
        "∏": r"\prod ", "∈": r"\in ", "∉": r"\notin ",
        "⊂": r"\subset ", "⊆": r"\subseteq ", "→": r"\to ",
        "⇒": r"\Rightarrow ", "⇔": r"\Leftrightarrow ",
        "∀": r"\forall ", "∃": r"\exists ", "·": r"\cdot ",
        "…": r"\dots ", "′": "'", "″": "''",
        "°": r"^{\circ}", "′′": "''",
    }
    # Greek letters are named rather than enumerated one by one: the block is
    # contiguous, so the LaTeX command follows from the code point.
    _GREEK_LOWER = ("alpha beta gamma delta epsilon zeta eta theta iota kappa "
                    "lambda mu nu xi omicron pi rho varsigma sigma tau upsilon "
                    "phi chi psi omega").split()
    _GREEK_UPPER = ("Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa "
                    "Lambda Mu Nu Xi Omicron Pi Rho Sigmaf Sigma Tau Upsilon "
                    "Phi Chi Psi Omega").split()
    # Upper-case Greek letters that TeX has no command for are identical to
    # Latin capitals and are written as such.
    _GREEK_UPPER_LATIN = {"Alpha": "A", "Beta": "B", "Epsilon": "E", "Zeta": "Z",
                          "Eta": "H", "Iota": "I", "Kappa": "K", "Mu": "M",
                          "Nu": "N", "Omicron": "O", "Rho": "P", "Tau": "T",
                          "Chi": "X", "Sigmaf": r"\Sigma "}

    @classmethod
    def _sanitize_math(cls, body: str) -> str:
        """Make an equation body safe for TeX math mode without changing it.

        Word stores many symbols as literal Unicode even inside an equation --
        a superscript two, a Greek letter typed from the keyboard, a times sign
        -- because the OMML only records the glyph.  Pandoc passes them through
        verbatim, and in math mode they are dropped or raise an inputenc error,
        which is how an exponent silently disappeared from a rendered matrix.
        Each is replaced by the equivalent TeX construct, so the equation is
        preserved exactly rather than being degraded or lost.
        """
        if not body:
            return ""
        out = []
        for ch in body:
            mapped = cls._MATH_UNICODE.get(ch)
            if mapped is not None:
                out.append(mapped)
                continue
            code = ord(ch)
            if 0x03B1 <= code <= 0x03C9:  # lower-case Greek
                out.append("\\" + cls._GREEK_LOWER[code - 0x03B1] + " ")
                continue
            if 0x0391 <= code <= 0x03A9:  # upper-case Greek
                name = cls._GREEK_UPPER[code - 0x0391]
                out.append(cls._GREEK_UPPER_LATIN.get(name) or ("\\" + name + " "))
                continue
            out.append(ch)
        # Collapse the spaces the replacements introduce; TeX ignores them in
        # math mode anyway and the result is easier to read.
        return re.sub(r"\s{2,}", " ", "".join(out)).strip()

    @staticmethod
    def _math_to_text(c: Any) -> str:
        """Render a pandoc ``Math`` inline as a delimited LaTeX math span.

        Display and inline math are kept distinct.  Flattening display math into
        ``$...$`` (as this used to do) breaks every multi-line construct: a
        ``\\\\`` row separator or an ``aligned`` environment inside single-dollar
        math is a hard LaTeX error ("Missing $ inserted").  ``\\(``/``\\[`` are
        used rather than ``$`` so that a literal currency ``$`` elsewhere in the
        same paragraph can never be mistaken for a delimiter.
        """
        if not isinstance(c, list) or len(c) < 2:
            return ""
        kind = c[0].get("t") if isinstance(c[0], dict) else ""
        body = (c[1] or "").strip()
        if not body:
            return ""
        body = DocumentAnalyzer._sanitize_math(body)
        if not body:
            return ""
        if kind == "DisplayMath":
            return f"\\[{body}\\]"
        return f"\\({body}\\)"

    @staticmethod
    def _author_for_email(email: str, authors: List[AuthorModel]) -> Optional[AuthorModel]:
        """The author whose name appears in an address's local part, if any.

        Institutional addresses are built from the person's name in a handful of
        shapes ("j.whitfield@", "alvarez@", "mei_ling.chou@"), so the surname --
        the longest name token -- is looked for among the local part's own
        tokens.  Returns None when no author matches, leaving the caller's
        positional fallback in charge.
        """
        local = (email or "").split("@")[0].lower()
        if not local:
            return None
        pieces = {p for p in re.split(r"[._\-0-9]+", local) if len(p) >= 3}
        if not pieces:
            return None
        best = None
        best_len = 0
        for author in authors:
            for token in re.split(r"[\s.\-']+", (author.name or "").lower()):
                if len(token) >= 3 and token in pieces and len(token) > best_len:
                    best, best_len = author, len(token)
        if best is not None:
            return best
        # Some addresses run the name together with no separator at all
        # ("jwhitfield@", "mkowalczyk@"), so no token boundary exists to split
        # on.  Only the surname -- the last name token -- is looked for as a
        # substring: given names are shared across people far too often for a
        # bare substring hit on one to identify anybody, and the length floor
        # keeps short particles ("de", "van", "abu") from matching by accident.
        for author in authors:
            tokens = [t for t in re.split(r"[\s.\-']+", (author.name or "").lower()) if t]
            if not tokens:
                continue
            surname = tokens[-1]
            if len(surname) >= 5 and surname in local and len(surname) > best_len:
                best, best_len = author, len(surname)
        return best

    @staticmethod
    def _is_journal_furniture(text: str) -> bool:
        """True for masthead / submission-metadata lines on a title page."""
        t = (text or "").strip()
        if not t:
            return True
        return bool(_FURNITURE_RE.search(t))

    # A caption paragraph: a label, a number, then a separator or a capitalised
    # phrase.  The trailing condition is what separates a caption from a
    # cross-reference in running text -- "Table 1. Residual bias" and "Table 1:
    # Results" are captions, while "Table 1 summarises the residual bias" is a
    # sentence that merely mentions the table.
    _CAPTION_RE = re.compile(
        r"^(?P<kind>table|tab\.|figure|fig\.|chart|scheme|plate|exhibit)\s*"
        r"(?P<num>[0-9]+(?:\.[0-9]+)*|[IVXLC]+|[A-Z](?:\.[0-9]+)?)\s*"
        r"(?:(?P<sep>[.:—–)-]\s*)|(?=[A-Z]))",
        re.IGNORECASE,
    )

    def _caption_text(self, caption_block: Any) -> str:
        """Text of a pandoc ``Caption``, whatever shape it arrives in.

        A pandoc 3 Caption is ``[maybe-short-caption, [blocks]]``; older paths
        in this file also saw it wrapped in a dict.  Reading the list form as if
        it were a plain block list yields "" because its first element is the
        short caption (usually null), which made every real caption look empty.
        """
        if isinstance(caption_block, dict):
            return self._stringify_blocks(caption_block.get("c", []) or []).strip()
        if isinstance(caption_block, list):
            if len(caption_block) == 2 and isinstance(caption_block[1], list):
                return self._stringify_blocks(caption_block[1]).strip()
            return self._stringify_blocks(
                [b for b in caption_block if isinstance(b, dict)]).strip()
        return ""

    @classmethod
    def _caption_kind(cls, text: str) -> Optional[str]:
        """"table" / "figure" when a paragraph is a caption, else None."""
        t = (text or "").strip()
        if not t or len(t) > 400:
            return None
        m = cls._CAPTION_RE.match(t)
        if not m:
            return None
        rest = t[m.end():].strip()
        # A caption says something; a bare label with nothing after it is not
        # one, and a remainder starting lower-case is running prose.
        if not rest or (rest[:1].islower() and not m.group("sep")):
            return None
        kind = m.group("kind").lower().rstrip(".")
        return "table" if kind in ("table", "tab") else "figure"

    def _strip_caption_label(self, inlines: List[Dict[str, Any]],
                             text: str) -> List[Dict[str, Any]]:
        """Drop the "Table 1." / "Figure 2:" prefix from caption inlines.

        LaTeX generates the label and number itself, so keeping Word's copy
        renders "Table 1: Table 1. Residual bias ...".  The prefix is removed by
        character count rather than by rebuilding the text, which preserves any
        formatting, symbols or math the rest of the caption contains.
        """
        m = self._CAPTION_RE.match((text or "").strip())
        if not m:
            return inlines
        remaining = m.end()
        out: List[Dict[str, Any]] = []
        for item in inlines:
            if remaining <= 0:
                out.append(item)
                continue
            if not isinstance(item, dict):
                continue
            t = item.get("t")
            if t == "Space":
                remaining -= 1
                continue
            if t == "Str":
                s = item.get("c") or ""
                if len(s) <= remaining:
                    remaining -= len(s)
                    continue
                out.append({"t": "Str", "c": s[remaining:]})
                remaining = 0
                continue
            # A non-text inline (math, an image) cannot be part of the label.
            remaining = 0
            out.append(item)
        # Never return an empty caption -- that would look like no caption at
        # all and re-trigger the placeholder.
        while out and isinstance(out[0], dict) and out[0].get("t") == "Space":
            out.pop(0)
        return out or inlines

    def _attach_captions(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Pair caption paragraphs with the table or figure they describe.

        Word has no structural link between a picture and the "Figure 3. ..."
        paragraph under it -- they are two independent paragraphs -- so a
        caption used to be rendered twice: once as loose body text and once as
        the auto-generated "Table 1: Table" that the renderer emitted for a
        table it believed to be uncaptioned.  Each uncaptioned table/figure
        therefore adopts the caption paragraph immediately after it, or
        immediately before it when the manuscript places captions above (the
        convention for tables at most publishers).
        """
        texts = [
            self._stringify_inlines(b.get("c") or []).strip()
            if isinstance(b, dict) and b.get("t") in ("Para", "Plain") else ""
            for b in blocks
        ]
        kinds = [self._caption_kind(t) for t in texts]
        used: set = set()

        def find(target: str, index: int) -> Optional[int]:
            for j in (index + 1, index - 1):
                if 0 <= j < len(blocks) and j not in used and kinds[j] == target:
                    return j
            return None

        for i, b in enumerate(blocks):
            if not isinstance(b, dict):
                continue
            if b.get("t") == "Table":
                c = b.get("c")
                if not isinstance(c, list) or len(c) < 2:
                    continue
                if self._caption_text(c[1]):
                    continue  # already captioned in the DOCX
                j = find("table", i)
                if j is None:
                    continue
                inlines = self._strip_caption_label(blocks[j].get("c") or [], texts[j])
                if isinstance(c[1], dict):
                    c[1]["c"] = [{"t": "Plain", "c": inlines}]
                else:
                    c[1] = [None, [{"t": "Plain", "c": inlines}]]
                used.add(j)
            elif b.get("t") in ("Para", "Plain") and i not in used:
                for item in (b.get("c") or []):
                    if not isinstance(item, dict) or item.get("t") != "Image":
                        continue
                    item_c = item.get("c") or []
                    if len(item_c) < 2 or self._stringify_inlines(item_c[1]).strip():
                        continue
                    j = find("figure", i)
                    if j is None:
                        continue
                    item_c[1] = self._strip_caption_label(
                        blocks[j].get("c") or [], texts[j])
                    used.add(j)
                    break

        return [b for i, b in enumerate(blocks) if i not in used]

    def _table_cell_texts(self, block: Dict[str, Any]) -> List[str]:
        """Plain text of every cell in a pandoc ``Table``, in reading order.

        The pandoc 3 table AST is deeply nested and its exact shape varies with
        the presence of a caption, head and foot, so the structure is walked
        generically for ``Para``/``Plain`` nodes rather than indexed positionally.
        """
        texts: List[str] = []

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                if node.get("t") in ("Para", "Plain"):
                    txt = self._stringify_inlines(node.get("c") or []).strip()
                    if txt:
                        texts.append(txt)
                    return
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(block.get("c"))
        return texts

    def _front_matter_end(self, blocks: List[Dict[str, Any]]) -> int:
        """Index of the first body block when no heading marks the boundary.

        Used only as a safety net: a document whose headings carry no style, no
        outline level and no visual distinction produces no ``Header``, and
        without a boundary every block is read as front matter and the body is
        lost.  Two structural landmarks are tried, in order of reliability.

        The keywords / abstract labels are the one convention every publisher
        shares, so the last of them ends the front matter -- plus the paragraph
        after it when the label stands alone and its content follows.  Failing
        that, running prose is itself the landmark: title, authors and
        affiliations are all short, unpunctuated lines, so the first long
        sentence-bearing paragraph is where the body starts.  Both are capped so
        a pathological document cannot swallow more than the opening pages, and
        the caller only ever widens the body, never narrows it.
        """
        texts: List[str] = []
        for b in blocks:
            t = b.get("t")
            if t in ("Para", "Plain"):
                texts.append(self._stringify_inlines(b.get("c") or []).strip())
            elif t == "Header":
                c = b.get("c") or []
                texts.append(self._stringify_inlines(c[2] if len(c) > 2 else []).strip())
            else:
                texts.append("")

        limit = min(len(texts), 25)
        last_label = -1
        label_standalone = False
        for idx in range(limit):
            norm = _normalise_label(texts[idx])
            if not norm:
                continue
            m = _ABSTRACT_LABEL_RE.match(norm) or _KEYWORD_LABEL_RE.match(norm)
            if m:
                last_label = idx
                label_standalone = not norm[m.end():].strip()
        if last_label >= 0:
            end = last_label + (2 if label_standalone else 1)
            return min(end, len(blocks))

        for idx in range(1, limit):
            txt = texts[idx]
            if len(txt) >= 200 and re.search(r"[.!?]\s", txt):
                return idx
        return len(blocks)

    def _promote_semantic_headings(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Turn semantically-detected headings into real pandoc ``Header`` blocks.

        Pandoc emits a ``Header`` only for paragraphs carrying a Word *Heading*
        style.  A manuscript that was typed with direct formatting -- bold, a
        larger font, all-caps -- therefore arrives as an unbroken run of ``Para``
        blocks, and every downstream stage (front-matter boundary, section
        tree, numbering) collapses.  The raw-XML pass has already classified
        those paragraphs by document semantics; this rewrites the AST to agree
        with it, so the rest of the analyzer needs no special case.

        Only paragraphs whose *entire* text matches a detected heading are
        rewritten, and a paragraph that pandoc already made a Header is left
        alone, so the pass is a no-op on documents that do use heading styles.
        """
        formats = getattr(self, "_heading_formats", {}) or {}
        if not formats:
            return blocks

        # The title of a paper carries exactly the signals of a heading -- bold,
        # larger, centred -- so promoting inside the front matter would turn the
        # title into section 1 and leave the title page empty.  The front matter
        # is bounded by the abstract / keywords labels, which is the one
        # structural landmark every publisher shares; when a manuscript has
        # neither, only the opening few blocks are protected.
        texts = [
            self._stringify_inlines(b.get("c") or []).strip()
            if isinstance(b, dict) and b.get("t") in ("Para", "Plain") else ""
            for b in blocks
        ]
        front_end = -1
        for i, t in enumerate(texts[:40]):
            if not t:
                continue
            norm = _normalise_label(t)
            if _ABSTRACT_LABEL_RE.match(norm) or _KEYWORD_LABEL_RE.match(norm):
                front_end = i
        if front_end < 0:
            front_end = 2

        promoted: List[Dict[str, Any]] = []
        count = 0
        for index, b in enumerate(blocks):
            if not isinstance(b, dict) or b.get("t") not in ("Para", "Plain"):
                promoted.append(b)
                continue
            inlines = b.get("c") or []
            text = texts[index]
            if not text or len(text) > 120:
                promoted.append(b)
                continue
            if index <= front_end:
                # Front matter: never a section heading, and the labels
                # themselves must stay ordinary paragraphs so that the
                # metadata extraction can still read their content.
                promoted.append(b)
                continue
            fmt = formats.get("".join(text.split()).lower())
            if not fmt:
                promoted.append(b)
                continue
            level = max(1, min(6, int(fmt.get("level") or 1)))
            promoted.append({"t": "Header", "c": [level, ["", [], []], inlines]})
            count += 1

        if count:
            self._promoted_heading_count = count
        return promoted

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

        # Every paragraph's text in reading order.  The per-paragraph loop below
        # can only see one paragraph at a time, but a document that gives its
        # headings no visual distinction at all can only be read from context --
        # what surrounds a line -- so the sequence is kept for the structural
        # pass that runs after it.
        para_texts = [
            " ".join(t.text for t in p.iter(f"{W}t") if t.text).strip()
            for p in body.findall(f"{W}p")
        ]

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

            # Paragraph-level presentation.  Read before the level decision
            # because the semantic fallback below uses alignment and spacing as
            # corroborating heading signals.
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

            # Decide heading + level: style > outline > semantic fallback.
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
                # Multi-signal semantic detection: the manuscript need not use
                # Word heading styles at all, which is the normal case for a
                # plain Word paper and for IEEE / Elsevier submissions.
                level = self._semantic_heading_level(
                    text, bold, size_pt, body_size, align, before_pt, keep_next
                )
            if level is None:
                continue

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
                # Recorded so the tiering pass below can tell a heading found by
                # the semantic fallback from one the document declared outright.
                "semantic": level is not None and style_id not in style_levels and outline is None,
                "numbered": self._numbering_depth(text) is not None,
            }

        # Structural pass for documents that declare no headings at all: no
        # heading style, no outline level, and no bold / size / spacing contrast
        # for the semantic fallback to find.  Such a manuscript is not
        # unstructured -- its headings are still short standalone lines wedged
        # between paragraphs of running prose -- but that structure is only
        # visible in the sequence, never in one paragraph.  This runs solely when
        # nothing else matched, so a document that does declare its headings is
        # untouched and cannot regress.
        if not formats:
            for idx, text in enumerate(para_texts):
                if not text or len(text) > 60:
                    continue
                # A heading is a label, not a sentence: it does not end in
                # terminal punctuation and it is not an address or a citation.
                if re.search(r"[.,;:!?]$", text) or _EMAIL_RE.search(text):
                    continue
                if len(text.split()) > 8:
                    continue
                norm = _normalise_label(text)
                if _ABSTRACT_LABEL_RE.match(norm) or _KEYWORD_LABEL_RE.match(norm):
                    continue
                # The line must actually head something: the paragraph after it
                # is running prose.  Without this every short line in the front
                # matter -- author names, affiliations, dates -- would qualify.
                nxt = next((t for t in para_texts[idx + 1:idx + 3] if t), "")
                if len(nxt) < 200 or not re.search(r"[.!?]", nxt):
                    continue
                # ... and it must follow prose too, which is what separates a
                # heading from the title and author lines opening the document.
                prev = next((t for t in reversed(para_texts[max(0, idx - 3):idx]) if t), "")
                prev_norm = _normalise_label(prev)
                closes_front_matter = bool(
                    _ABSTRACT_LABEL_RE.match(prev_norm) or _KEYWORD_LABEL_RE.match(prev_norm)
                )
                if len(prev) < 200 and not closes_front_matter:
                    continue
                key = "".join(text.split()).lower()
                formats.setdefault(key, {
                    "level": self._numbering_depth(text) or 1,
                    "bold": False,
                    "size_pt": body_size,
                    "body_size_pt": body_size,
                    "size_ratio": 1.0,
                    "alignment": "left",
                    "space_before_pt": None,
                    "space_after_pt": None,
                    "keep_with_next": False,
                    "semantic": True,
                    "numbered": self._numbering_depth(text) is not None,
                })

        # Rank the unnumbered headings the semantic fallback found.  Their level
        # cannot be decided one paragraph at a time -- "set apart from the body"
        # is all a single paragraph can show -- but across the document the sizes
        # separate cleanly into tiers: whatever size the largest of them uses is
        # the section level, and anything set smaller than that is a subsection.
        # Without this every unnumbered heading collapsed to level 1 and the
        # subsection hierarchy was lost.
        semantic_sizes = [
            info["size_pt"] for info in formats.values()
            if info.get("semantic") and not info.get("numbered") and info.get("size_pt")
        ]
        if semantic_sizes:
            # The section tier is the size that *recurs*, not the largest one.
            # A paper's title carries the same signals as a heading and is set
            # larger than any of them, so keying off the maximum demoted every
            # real section to a subsection.  Sections repeat; a title appears
            # once, so the modal size identifies the tier without the extractor
            # needing to know where the front matter ends.
            counts = {}
            for size in semantic_sizes:
                counts[size] = counts.get(size, 0) + 1
            section_size = max(counts, key=lambda s: (counts[s], s))
            for info in formats.values():
                if info.get("semantic") and not info.get("numbered") and info.get("size_pt") \
                        and info["size_pt"] < section_size and info["level"] == 1:
                    info["level"] = 2
        return formats

    @staticmethod
    def _numbering_depth(text: str) -> Optional[int]:
        """Hierarchy depth implied by a section number, or None if unnumbered.

        Covers the four numbering conventions that appear across publishers:
        decimal ("3.2.1"), roman ("IV."), word-prefixed ("Chapter 2.") and, at
        the end, single-letter ("B.").  The letter form is reported as depth 2
        because IEEE uses it exclusively for subsections under a roman-numbered
        section.
        """
        t = (text or "").strip()
        if not t:
            return None
        m = re.match(_MANUAL_HEADING_RE, t)
        if m:
            return max(1, min(4, len([x for x in re.split(r"\.\s?", m.group(1)) if x])))
        if re.match(_WORD_HEADING_RE, t, re.IGNORECASE):
            return 1
        if re.match(_ROMAN_HEADING_RE, t) and re.match(r"^[IVX]+[.)]", t):
            return 1
        if re.match(_LETTER_HEADING_RE, t):
            return 2
        return None

    @staticmethod
    def _looks_like_prose(text: str) -> bool:
        """True when a short paragraph is still a sentence rather than a title.

        Headings do not end in a full stop (a trailing dot after a bare section
        number is not one), do not contain sentence-internal punctuation, and are
        not long.  Applying this before any formatting signal is what stops a
        short bold lead-in sentence from being promoted to a section.
        """
        t = (text or "").strip()
        if not t:
            return True
        if len(t.split()) > 14:
            return True
        # Strip any leading section number first, in every convention, so that
        # the punctuation test below judges the title itself.  Without this,
        # "Chapter 1. Introduction" reads as a sentence because of the dot that
        # belongs to the numbering.
        body = t
        for pattern in (_WORD_HEADING_RE, _MANUAL_HEADING_RE, _ROMAN_HEADING_RE,
                        _LETTER_HEADING_RE):
            stripped = re.sub(pattern, "", body, count=1, flags=re.IGNORECASE)
            if stripped != body:
                body = stripped.strip()
                break
        # A trailing full stop marks a sentence.  Personal initials ("J. A.
        # Whitfield") and common abbreviations are not sentence punctuation, so
        # only a stop after a real word counts.
        if re.search(r"(?<![A-Z])[a-z]{2,}[.?!]$", body) or body.endswith(("?", "!")):
            return True
        if ";" in body:
            return True
        return False

    def _semantic_heading_level(
        self,
        text: str,
        bold: bool,
        size_pt: Optional[float],
        body_size: float,
        align: str,
        space_before: Optional[float],
        keep_next: bool,
    ) -> Optional[int]:
        """Heading level from document semantics, or None for body text.

        This is the fallback used when a paragraph carries neither a Heading
        style nor an outline level -- the normal situation in a plain Word
        manuscript, an IEEE paper, or anything a co-author has retyped.  No
        single signal is sufficient on its own: a numbered line can be an
        affiliation ("3 Associate Professor ..."), an all-caps line can be an
        acronym, and bold text can be a lead-in.  A level is therefore returned
        only when a *numbering* or *prominence* signal is corroborated by a
        second, independent one.
        """
        t = (text or "").strip()
        if not t or self._looks_like_prose(t):
            return None

        letters = [ch for ch in t if ch.isalpha()]
        if not letters:
            return None

        depth = self._numbering_depth(t)
        all_caps = len(letters) >= 3 and all(ch.isupper() for ch in letters)
        larger = bool(size_pt and body_size and size_pt >= body_size * 1.12)
        # A weaker size signal: any increase over the body size at all.  Running
        # text never steps its size up mid-document, so even a one-point rise is
        # evidence of a heading -- but only evidence, which is why it is counted
        # alongside the others rather than acting alone.  Subheadings are exactly
        # where this matters: a publisher that sets sections a few points above
        # the body typically sets subsections only one point above it.
        slightly_larger = bool(size_pt and body_size and size_pt > body_size)
        spaced = bool(space_before and space_before >= 6.0)
        centered = align in ("center", "centre")

        # Independent corroborating evidence that this line is set apart.
        prominence = sum(
            (1 if bold else 0,
             1 if larger else (1 if slightly_larger else 0),
             1 if all_caps else 0,
             1 if keep_next else 0,
             1 if spaced else 0)
        )

        if depth is not None:
            # A number plus any one prominence signal.  Without corroboration a
            # numbered line is far more likely to be a list item or an indexed
            # affiliation than a section.
            if prominence >= 1:
                # The single-letter form is ambiguous enough to demand that the
                # rest of the line be set apart in its own right.
                if depth == 2 and re.match(_LETTER_HEADING_RE, t) and not (bold or all_caps):
                    return None
                return depth
            return None

        # Unnumbered: needs two prominence signals, one of which must be a
        # visual weight (bold / larger / caps) rather than mere spacing.
        if prominence >= 2 and (bold or larger or all_caps or slightly_larger):
            return 2 if centered and not (bold or larger) else 1
        return None

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
        m = re.match(_MANUAL_HEADING_RE, text)
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

    def _extract_drawing_placement(self, docx_path: Path) -> Dict[str, bool]:
        """Map each embedded image (by ``media/...`` path) to whether Word placed
        it *inline* in the text (``wp:inline``) or *floating* (``wp:anchor``).

        This is a placement signal, not styling: an image Word itself floats is
        a natural LaTeX float, whereas an inline image should hold its position.
        """
        import zipfile
        import xml.etree.ElementTree as ET
        W = self._W_NS
        WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
        A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
        placement: Dict[str, bool] = {}
        try:
            with zipfile.ZipFile(docx_path) as zf:
                rels: Dict[str, str] = {}
                try:
                    rt = ET.fromstring(zf.read("word/_rels/document.xml.rels"))
                    for rel in rt:
                        rels[rel.get("Id")] = rel.get("Target") or ""
                except Exception:
                    pass
                root = ET.fromstring(zf.read("word/document.xml"))
            for dr in root.iter(f"{W}drawing"):
                is_inline = dr.find(f"{WP}inline") is not None
                blip = dr.find(f".//{A}blip")
                emb = blip.get(f"{R}embed") if blip is not None else None
                tgt = rels.get(emb) if emb else None
                if tgt:
                    placement.setdefault("media/" + tgt.split("/")[-1], is_inline)
        except Exception:
            pass
        return placement

    def _extract_text_width_in(self, docx_path: Path) -> float:
        """Usable text-column width of the document in inches (0.0 if unknown)."""
        import zipfile
        import xml.etree.ElementTree as ET
        W = self._W_NS
        try:
            with zipfile.ZipFile(docx_path) as zf:
                root = ET.fromstring(zf.read("word/document.xml"))
            body = root.find(f"{W}body")
            if body is None:
                return 0.0
            tw = self._text_width_twips(body, W)
            return round(tw / 1440.0, 4) if tw else 0.0
        except Exception:
            return 0.0

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
        # Read through _caption_text so that the pandoc 3 Caption shape
        # ([short-caption, blocks]) is understood; reading it as a bare block
        # list returned "" and every table was captioned "Table".
        caption = self._caption_text(c[1]) or "Table"

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
            # Row count is a page-break-risk signal for the placement policy.
            "num_rows": len(header_rows) + len(body_rows),
            "text_width_in": getattr(self, "_text_width_in", 0.0) or 0.0,
            "headers": flat_headers,
            "rows": flat_rows,
        }
