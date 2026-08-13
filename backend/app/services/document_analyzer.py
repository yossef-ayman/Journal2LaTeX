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

# The opening section of a research paper.  Every discipline and every
# publisher draws from the same small vocabulary here -- this is a property of
# how papers are written, not of how any particular journal formats them, which
# is why it is a sound landmark when *formatting* signals are unavailable
# (headings numbered by Word's list numbering, headings typed in the body font,
# headings carrying superscript note markers).  Matched against the heading text
# only after every numbering convention has been stripped, so "1. Introduction",
# "I. INTRODUCTION", "Chapter 1 Introduction" and a bare "Introduction" are one
# case.  Deliberately narrow: a false positive here would truncate the front
# matter, so only openers that essentially never appear inside a title block are
# listed, and the match must consume the whole line.
_BODY_OPENER_RE = re.compile(
    r"^(?:"
    r"introduction|background(?:\s+and\s+\w+)?|motivation|"
    r"related\s+works?|literature\s+review|state\s+of\s+the\s+art|"
    r"preliminaries|problem\s+(?:statement|formulation|definition)|"
    r"materials?\s+and\s+methods?|methods?|methodology|"
    r"experimental(?:\s+(?:setup|section|procedure))?|"
    r"theory|theoretical\s+\w+|model(?:ling|ing)?|"
    r"general\s+introduction|overview"
    r")\s*[:.]?\s*$",
    re.IGNORECASE,
)

# Every numbering convention a heading may carry, tried longest-first, so that
# the opener test above sees the title alone.  Superscript note markers that
# Word attaches to a heading ("Introduction1") flatten to trailing digits, and a
# trailing footnote glyph is equally common; both are stripped as well.
_NUMBER_PREFIXES = (_WORD_HEADING_RE, _MANUAL_HEADING_RE,
                    _ROMAN_HEADING_RE, _LETTER_HEADING_RE)

# Personal-name shape: one to five capitalised or initialised tokens, optionally
# carrying an affiliation marker.  Used to decide whether a front-matter line is
# a name list at all, so that stray table cells and running text can never be
# promoted to authors even if they survive every earlier filter.
# A name token is letters, optionally joined by a hyphen or an apostrophe
# ("Az-Zo'bi", "O'Neill", "Ben-David").  Case is checked separately, in code,
# because it must be Unicode-aware: "Akgül" and "Ünal" are capitalised names.
_NAME_TOKEN_RE = re.compile(r"^[^\W\d_]+(?:[-'’][^\W\d_]+)*[’']?$", re.UNICODE)

# Lower-case tokens that are still part of a person's name: nobiliary and
# patronymic particles.  Everything else in lower case is an ordinary word, and
# an ordinary word inside a candidate name means the line is not a name.
_NAME_PARTICLES = frozenset(
    "da de del della der den des di do dos du el la le van von ter zu "
    "bin binti ibn abu al mac mc".split()
)

# Hard ceiling on how much of a document may be classified as front matter.
# No title block in any publisher's layout runs to forty paragraphs; a boundary
# beyond this point is a detection failure, and continuing past it is what turns
# a whole paper into an author list.  The clamp is a backstop, not a heuristic:
# it only ever fires when every signal below has already failed.
_MAX_FRONT_MATTER_BLOCKS = 40

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


def _strip_heading_number(text: str) -> str:
    """A heading's title with its numbering and note markers removed.

    Comparing a heading against a vocabulary is only meaningful once the
    numbering is gone, and the numbering may be in any of four conventions --
    or supplied by Word's list numbering, in which case it is not in the text at
    all.  Trailing superscript markers, which flatten to bare digits, and the
    footnote glyphs publishers use in their place are stripped too, so a heading
    that carries a note reads the same as one that does not.
    """
    body = (text or "").strip()
    if not body:
        return ""
    for pattern in _NUMBER_PREFIXES:
        stripped = re.sub(pattern, "", body, count=1, flags=re.IGNORECASE)
        if stripped != body:
            body = stripped.strip()
            break
    return re.sub(r"[\s,]*\d*\s*[*†‡§¶°∗]*$", "", body).strip()


def _looks_like_person_name(name: str) -> bool:
    """True when a candidate string has the shape of a person's name.

    Applied as the final gate before any text becomes an author.  Every other
    test in the extractor asks whether a line looks like something *else* -- an
    affiliation, a sentence, journal furniture -- and a line that resembles
    nothing in particular slips through them all.  This asks the opposite
    question, which is the one that actually matters: a table cell, an axis
    label, a caption fragment or a stray clause is rejected because it is not
    one to five capitalised name tokens, whatever the front-matter boundary may
    have decided about where it came from.
    """
    cleaned = (name or "").strip().strip(",;·•∗*†‡§¶")
    if not cleaned or len(cleaned) > 80:
        return False
    tokens = [t for t in re.split(r"\s+", cleaned) if t]
    if not (1 <= len(tokens) <= 5):
        return False
    capitalised = 0
    for token in tokens:
        token = token.strip(".,;()[]")
        if not token:
            continue
        if not _NAME_TOKEN_RE.match(token):
            return False
        if token[0].isupper():
            capitalised += 1
        elif token.lower() not in _NAME_PARTICLES:
            return False
    # A name has at least one capitalised token; a run of particles does not.
    return capitalised > 0


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

            # Read and parse the DOCX parts once for this call.  Every pass
            # below used to unzip and re-parse word/document.xml for itself.
            self._open_parts(docx_path)

            # Every pass below reads the raw DOCX XML to recover something
            # pandoc does not expose.  Each is an *enrichment*: the document
            # parses without it, only with less detail.  So each is isolated,
            # and a pass that meets an XML shape it cannot handle costs its own
            # enrichment and nothing else.  Warnings are accumulated here
            # because these passes run before the counters exist, and are
            # merged into the report by ``_parse_ast``.
            self._stage_warnings: List[str] = []

            def side_channel(stage: str, fn, fallback):
                try:
                    return fn()
                except Exception as exc:  # noqa: BLE001 - degradation is the contract
                    logger.warning("%s skipped: %s", stage, exc)
                    self._stage_warnings.append(
                        f"{stage} skipped after an internal error "
                        f"({type(exc).__name__}: {exc}); the document was "
                        "parsed without it"
                    )
                    return fallback

            # Styling pandoc does not expose (shading, borders, row heights,
            # exact column widths) is read from the raw XML; body-level w:tbl
            # order matches pandoc Table order.
            self._table_styles = side_channel(
                "table styling", lambda: self._extract_table_styles(docx_path), [])
            self._table_style_idx = 0
            # Usable text-column width (inches) -- lets figure placement decide
            # whether a picture spans the full width or fits inside one column.
            self._text_width_in = side_channel(
                "text width", lambda: self._extract_text_width_in(docx_path), 0.0)
            # Per-image Word placement (inline-in-text vs anchored/floating),
            # keyed by media path -- a signal for the placement policy.
            self._drawing_inline = side_channel(
                "drawing placement",
                lambda: self._extract_drawing_placement(docx_path), {})
            # Original drawing geometry in EMU, straight from the DOCX, so a
            # figure keeps the size and aspect ratio Word gave it even when
            # pandoc reports no dimensions at all.
            self._drawing_geometry = side_channel(
                "drawing geometry",
                lambda: self._extract_drawing_geometry(docx_path), {})
            # Heading formatting (bold/size/alignment/spacing/keepNext) read
            # directly from the DOCX -- keyed by whitespace-insensitive heading
            # text so it can enrich sections parsed from the Pandoc AST.
            self._heading_formats = side_channel(
                "heading formats",
                lambda: self._extract_heading_formats(docx_path), {})
            # Corresponding-author e-mail is commonly stored in the first-page
            # footer / a footnote / an endnote rather than the author block, and
            # pandoc does not surface those parts, so read them from the raw XML.
            self._corresponding_email = side_channel(
                "corresponding e-mail",
                lambda: self._extract_corresponding_email(docx_path), "")
            # How many equations the source actually contains, counted in the
            # OMML itself, so the report can say whether any were lost between
            # the DOCX and the parsed model rather than leaving it unknown.
            self._omml_census = side_channel(
                "OMML census", lambda: self._count_omml_equations(docx_path),
                {"omath": 0, "omath_para": 0, "ole_equations": 0})
            try:
                return self._parse_ast(ast_data, job_id)
            finally:
                # The cache belongs to this call only: nothing is retained
                # between documents or between requests.
                self._close_parts()

        except Exception as e:
            if not isinstance(e, DocumentAnalyzerError):
                msg = f"Unexpected error during document analysis: {str(e)}"
                logger.exception(msg)
                raise DocumentAnalyzerError(msg)
            raise

    # ------------------------------------------------------------------ #
    # Per-call DOCX part access
    # ------------------------------------------------------------------ #
    #
    # A DOCX is a zip archive, and ``word/document.xml`` is by far its largest
    # member.  Each enrichment pass below used to open the archive and parse
    # that member again for itself -- seven passes, seven unzips, seven full
    # XML parses of the same bytes, per conversion.
    #
    # The parts are therefore read and parsed once at the start of
    # ``analyze_document`` and handed to the passes.  Two properties keep this
    # honest: the cache lives on the instance for the duration of one call and
    # is discarded in that call's ``finally``, so nothing is shared between
    # documents or between requests; and every accessor falls back to opening
    # the archive itself when the cache is absent, so each pass still works
    # standalone and the tests that call them directly are unaffected.

    def _open_parts(self, docx_path: Path) -> None:
        """Read and parse the DOCX members the analysis passes need, once."""
        import zipfile
        import xml.etree.ElementTree as ET
        parts: Dict[str, Any] = {"path": str(docx_path), "xml": {}, "tree": {}}
        try:
            with zipfile.ZipFile(docx_path) as zf:
                names = set(zf.namelist())
                for member in ("word/document.xml", "word/styles.xml",
                               "word/_rels/document.xml.rels"):
                    if member in names:
                        parts["xml"][member] = zf.read(member)
                parts["names"] = names
        except Exception:
            # A malformed archive is the callers' problem to report, not this
            # helper's: leaving the cache empty makes every pass fall back to
            # its own open, which raises exactly where it did before.
            return
        for member, raw in parts["xml"].items():
            try:
                parts["tree"][member] = ET.fromstring(raw)
            except Exception:
                pass
        self._docx_parts = parts

    def _close_parts(self) -> None:
        self._docx_parts = None

    def _part_tree(self, docx_path: Path, member: str):
        """Parsed XML for a DOCX member, from this call's cache when possible.

        Returns ``None`` when the member does not exist, which is a normal
        answer: a document with no styles or no relationships simply has none.
        """
        import zipfile
        import xml.etree.ElementTree as ET
        parts = getattr(self, "_docx_parts", None)
        if parts and parts.get("path") == str(docx_path):
            if member in parts["tree"]:
                return parts["tree"][member]
            if "names" in parts and member not in parts["names"]:
                return None
        with zipfile.ZipFile(docx_path) as zf:
            try:
                return ET.fromstring(zf.read(member))
            except KeyError:
                return None

    def _part_bytes(self, docx_path: Path, member: str):
        """Raw bytes for a DOCX member, from this call's cache when possible."""
        import zipfile
        parts = getattr(self, "_docx_parts", None)
        if parts and parts.get("path") == str(docx_path):
            if member in parts["xml"]:
                return parts["xml"][member]
            if "names" in parts and member not in parts["names"]:
                return None
        with zipfile.ZipFile(docx_path) as zf:
            try:
                return zf.read(member)
            except KeyError:
                return None

    @staticmethod
    def _guard(counters: Dict[str, Any], stage: str, fn, fallback):
        """Run an analysis stage, degrading to ``fallback`` if it fails.

        Parsing a document is a chain of independent enrichments, and any one of
        them can meet a shape no author anticipated.  The requirement is that a
        failure costs only the enrichment that failed: the caller receives the
        input it would have had if the stage had never run, and the loss is
        recorded rather than swallowed.  What must never happen is a partially
        applied transformation, which is why the fallback is the pre-stage value
        and not whatever the stage managed to produce before raising.
        """
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - degradation is the contract
            counters.setdefault("warnings", []).append(
                f"{stage} skipped after an internal error ({type(exc).__name__}: {exc}); "
                "the document was parsed without it"
            )
            counters.setdefault("degraded_stages", []).append(stage)
            return fallback

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
        #
        # Each structural pass is fault-isolated: if one raises, the blocks it
        # was given are kept unchanged and a warning is recorded.  A pass that
        # fails must degrade the document to the state before that pass, never
        # to a half-rewritten AST -- a partially promoted heading tree is worse
        # than no promotion at all, because every later stage then reads a
        # structure that describes no real document.
        blocks = self._guard(counters, "heading promotion",
                             lambda: self._promote_semantic_headings(blocks), blocks)
        # Word keeps a caption in its own paragraph with no link to the object
        # it describes; pair them up before parsing so neither is duplicated.
        blocks = self._guard(counters, "caption attachment",
                             lambda: self._attach_captions(blocks), blocks)

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
        #
        # The heading-derived boundary is only as good as the *first* heading.
        # A manuscript that numbers its section headings with Word's list
        # numbering keeps them in a numbered-list paragraph, which pandoc folds
        # into an ``OrderedList`` block; such a heading can never become a
        # ``Header``, while an unnumbered late heading ("Conclusions") still
        # can.  The first heading then sits near the *end* of the paper and
        # everything before it -- the entire body -- is read as front matter and
        # fed to the author/affiliation extractor.  So the structural boundary
        # is computed either way, and it is allowed to *narrow* the front matter
        # when it was derived from the abstract/keywords labels, which is the
        # one landmark every publisher shares and therefore the only boundary
        # trustworthy enough to override a heading.  The prose-based fallback
        # inside it stays advisory (it may fire on the abstract itself), so it
        # is used only when there is no heading boundary at all.
        if blocks:
            boundary, reason = self._guard(
                counters, "front-matter boundary",
                lambda: self._front_matter_boundary(
                    blocks, len(intro_metadata_blocks), found_header),
                (len(intro_metadata_blocks), "heading"),
            )
            counters["front_matter"] = {
                "boundary": boundary, "signal": reason, "blocks": len(blocks),
            }
            if boundary != len(intro_metadata_blocks):
                intro_metadata_blocks = blocks[:boundary]
                body_blocks = blocks[boundary:]

        # Warnings raised by the raw-XML side-channel passes, which run before
        # this method and therefore have no counters to write into.
        counters["warnings"].extend(getattr(self, "_stage_warnings", []))

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
                # A superscript affiliation marker sitting *between* two names
                # is itself a separator: publishers routinely drop the comma
                # after a marked surname, and the marker flattens to a bare
                # digit run glued to that surname ("... Yan5 Khin ...").  Any
                # digit run that both follows a letter and precedes a further
                # capitalised word can only be such a marker -- a real name
                # never contains an interior number -- so splitting there
                # recovers both authors instead of losing them to one
                # unrecognisable blob.  This is a property of superscript
                # flattening, not of any one document.
                names = [part.strip()
                         for name in names
                         for part in re.split(
                             r"(?<=[^\W\d_])\d+[*†‡§¶°∗]*\s+(?=[^\W\d_])", name)
                         if part.strip()]
                for name in names:
                    marker_match = re.search(r"(\d+)\s*[*†‡§¶°]*$", name)
                    marker = int(marker_match.group(1)) if marker_match else None
                    # Strip the trailing affiliation / corresponding-author
                    # marker, whether it is a digit or one of the footnote
                    # glyphs publishers use in place of one.
                    display = re.sub(r"[\s,]*\d*\s*[*†‡§¶°∗]*$", "", name).strip()
                    if not display or not re.search(r"[A-Za-z]", display):
                        continue
                    # Final gate, applied per name rather than per line: the
                    # candidate must actually have the shape of a person's
                    # name.  Every test above asks whether the text looks like
                    # something else; this one asks whether it looks like a
                    # person, which is the only question that keeps table
                    # cells, captions, axis labels and stray body fragments out
                    # of ``\author{}`` even if the boundary were misplaced.  It
                    # must be per-name because an author line carries
                    # multi-affiliation markers ("Ali Akgul 1,2,3,*") whose
                    # comma-split fragments are not names at all.
                    if not _looks_like_person_name(display):
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

        # Reconcile what the source contains against what was recovered.  The
        # source count comes from the OMML; the recovered count is the sum of
        # standalone equation blocks and equations carried on paragraphs.  A
        # shortfall is reported rather than inferred, because an equation lost
        # in conversion is otherwise indistinguishable from a paper that never
        # had one -- which is exactly how a silently flattened equation used to
        # escape notice.
        census = getattr(self, "_omml_census", None) or {}
        if census:
            recovered = counters.get("equations", 0) + counters.get("equations_inline", 0)
            counters["equation_census"] = {
                "source_omml": census.get("omath", 0),
                "source_display_paragraphs": census.get("omath_para", 0),
                "source_ole_equation_objects": census.get("ole_equations", 0),
                "recovered": recovered,
                "recovered_as_images": counters.get("equation_images", 0),
            }
            missing = census.get("omath", 0) - recovered
            if missing > 0:
                counters["warnings"].append(
                    f"{missing} of {census['omath']} equations in the source were "
                    "not recovered as equation nodes; they may have been "
                    "converted to text or images by Word"
                )
            if census.get("ole_equations"):
                counters["warnings"].append(
                    f"{census['ole_equations']} legacy Equation Editor/MathType "
                    "object(s) are embedded as pictures rather than OMML; they "
                    "are preserved as images with their original geometry, not "
                    "as editable equations"
                )

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
                    # Pandoc's attributes are the first source of truth because
                    # they reflect any scaling it applied; where it reports
                    # nothing -- routinely the case for equation images -- the
                    # exact EMU extent read from the DOCX supplies the original
                    # geometry rather than leaving the size unknown and letting
                    # a downstream default invent one.
                    geom = getattr(self, "_drawing_geometry", {}).get(src) or {}
                    if width_in is None and geom.get("width_in"):
                        width_in = geom["width_in"]
                    if height_in is None and geom.get("height_in"):
                        height_in = geom["height_in"]
                    # The aspect ratio is always emitted: it is what lets a
                    # consumer that must fit a figure to a column resize it
                    # without distorting it, and it survives even when only one
                    # of the two dimensions is known.
                    aspect = geom.get("aspect_ratio")
                    if aspect is None and width_in and height_in:
                        aspect = round(float(width_in) / float(height_in), 6)
                    if geom.get("is_equation"):
                        counters["equation_images"] = counters.get("equation_images", 0) + 1
                    else:
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
                            # Original source geometry, exact and unrounded.
                            "emu_width": geom.get("emu_width"),
                            "emu_height": geom.get("emu_height"),
                            "aspect_ratio": aspect,
                            # wp:inline vs wp:anchor as recorded in the DOCX;
                            # distinct from ``word_inline`` only in that it is
                            # None when the drawing was not found in the XML.
                            "word_placement": (
                                None if "inline" not in geom
                                else ("inline" if geom["inline"] else "anchor")
                            ),
                            # True when the picture is a legacy Equation
                            # Editor / MathType object rather than a figure.
                            # It cannot become an Equation node -- there is no
                            # LaTeX to recover from a rasterised equation --
                            # but it must not be captioned, floated or
                            # numbered as a figure either.
                            "is_equation": bool(geom.get("is_equation")),
                        }
                    )

            # Display math is handled after the loop so that the rest of the
            # paragraph is never discarded (see _display_equation_block).
            equation = self._display_equation_block(inlines, counters)
            if equation is not None:
                return equation

            # Standard paragraph block.  A paragraph that mixes prose with an
            # equation stays a paragraph -- splitting it would reorder the
            # sentence around the equation -- but the equations it contains are
            # still carried as structured nodes beside the text, never only as
            # flattened runs.  The text keeps its ``\(...\)`` / ``\[...\]``
            # spans so that every existing consumer renders exactly as before;
            # the ``equations`` list is additive, and lets any consumer that
            # wants the equation as an object have it without re-parsing prose.
            text = self._stringify_inlines(inlines)
            if not text.strip():
                return None
            counters["paragraphs"] += 1
            content: Dict[str, Any] = {"text": text}
            math_nodes = self._collect_math_nodes(inlines)
            if math_nodes:
                content["equations"] = math_nodes
                content["has_display_math"] = any(m["display"] for m in math_nodes)
                counters["equations_inline"] = \
                    counters.get("equations_inline", 0) + len(math_nodes)
            return DocumentBlock(
                type=BlockType.PARAGRAPH,
                content=content,
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
                # Pandoc's Link is [attr, label_inlines, target]: the visible
                # text is c[1].  Reading c[2] returned the target tuple, which
                # stringifies to nothing, so every hyperlink's text vanished --
                # e-mail addresses and ORCIDs in the author block above all,
                # leaving residue like "Email:  ORCID:" that was then parsed as
                # an author.  A hyperlink with no label falls back to its URL,
                # which is what the reader sees for a bare autolink.
                label = self._stringify_inlines(c[1]) if len(c) > 1 else ""
                if not label.strip() and len(c) > 2 and isinstance(c[2], list) and c[2]:
                    label = str(c[2][0])
                parts.append(label)
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

    def _collect_math_nodes(self, inlines: Any) -> List[Dict[str, Any]]:
        """Every equation in an inline tree, in reading order, as structured data.

        An OMML equation is not a run of text that happens to contain symbols;
        it is a node with its own grammar, and the only faithful representation
        of it is its LaTeX body plus whether Word set it as a display or an
        inline equation.  Collecting them separately from the paragraph's text
        is what makes an equation a first-class object even when it shares its
        paragraph with prose -- the case in which the old code had no choice but
        to flatten it into the text, because the text was the only place it had
        to put it.

        The walk mirrors ``_collect_display_math`` and for the same reason:
        Word wraps equations in character-style runs, which pandoc emits as
        ``Span``/``Emph``/``Strong`` wrappers around the ``Math`` node, so a
        top-level scan sees none of the styled ones.
        """
        found: List[Dict[str, Any]] = []
        if not isinstance(inlines, list):
            return found
        for item in inlines:
            if not isinstance(item, dict):
                continue
            t = item.get("t")
            c = item.get("c")
            if t == "Math":
                if isinstance(c, list) and len(c) > 1 and isinstance(c[0], dict):
                    body = self._sanitize_math((c[1] or "").strip())
                    if body:
                        found.append({
                            "latex": body,
                            "display": c[0].get("t") == "DisplayMath",
                        })
            elif t in ("Emph", "Strong", "Strikeout", "Superscript", "Subscript",
                       "SmallCaps", "Underline"):
                found.extend(self._collect_math_nodes(c))
            elif t in ("Span", "Quoted"):
                found.extend(self._collect_math_nodes(
                    c[1] if isinstance(c, list) and len(c) > 1 else None))
            elif t == "Link":
                found.extend(self._collect_math_nodes(
                    c[2] if isinstance(c, list) and len(c) > 2 else None))
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
            content={
                "latex_code": latex_code, "label": None, "number": number,
                # The individual equations that make up this block, kept
                # separately so a multi-line equation remains a sequence of
                # equations rather than one opaque string.
                "equations": [{"latex": b, "display": True} for b in bodies],
            },
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

    def _front_matter_end(self, blocks: List[Dict[str, Any]]) -> Tuple[int, bool]:
        """Index of the first body block, and whether a label established it.

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
            return min(end, len(blocks)), True

        for idx in range(1, limit):
            txt = texts[idx]
            if len(txt) >= 200 and re.search(r"[.!?]\s", txt):
                return idx, False
        return len(blocks), False

    def _block_scan_texts(self, block: Dict[str, Any]) -> List[str]:
        """Every text a block offers that could be a heading, in reading order.

        A heading is not always a paragraph: when Word numbers it with list
        numbering it is a list *item*, and pandoc folds a run of such headings
        into one list block.  Scanning list items as well as paragraphs is what
        lets the boundary detector see a heading that no formatting signal can
        reach.
        """
        if not isinstance(block, dict):
            return []
        t = block.get("t")
        c = block.get("c")
        if t in ("Para", "Plain"):
            return [self._stringify_inlines(c or []).strip()]
        if t == "Header":
            return [self._stringify_inlines(c[2] if isinstance(c, list) and len(c) > 2 else []).strip()]
        if t in ("OrderedList", "BulletList"):
            items = (c[1] if isinstance(c, list) and len(c) > 1 else []) \
                if t == "OrderedList" else (c or [])
            out = []
            for item in items if isinstance(items, list) else []:
                if isinstance(item, list) and item and isinstance(item[0], dict):
                    out.append(self._stringify_blocks(item[:1]).strip())
            return out
        return []

    def _body_opener_index(self, blocks: List[Dict[str, Any]],
                           floor: int) -> Optional[int]:
        """Index of the first block that opens the body of the paper.

        Papers open their body from a small, stable vocabulary ("Introduction",
        "Background", "Materials and Methods"), and that is a fact about
        scientific writing rather than about any publisher's template.  It is
        therefore the one boundary signal that survives every layout pathology
        the formatting-based signals fail on: headings numbered by Word's list
        numbering, headings typed in the body font, headings carrying a
        superscript note marker.  The search is bounded and never looks before
        the floor, so an "Introduction" mentioned inside an abstract cannot pull
        the boundary back over the front matter.
        """
        limit = min(len(blocks), _MAX_FRONT_MATTER_BLOCKS)
        for idx in range(max(0, floor), limit):
            for text in self._block_scan_texts(blocks[idx]):
                if not text or len(text) > 120:
                    continue
                title = _strip_heading_number(_normalise_label(text))
                if title and _BODY_OPENER_RE.match(title):
                    return idx
        return None

    def _front_matter_boundary(self, blocks: List[Dict[str, Any]],
                               heading_boundary: int,
                               found_header: bool) -> Tuple[int, str]:
        """Where the front matter ends, from all available evidence.

        Four independent signals are combined, and the rule between them is
        deliberately one-directional: the boundary may only ever move *earlier*
        than the heading-derived one.  Misplacing it late is the failure that
        destroys a document -- every block before it is handed to the author and
        affiliation extractor, so a late boundary turns the body of the paper
        into a list of authors -- whereas misplacing it early merely puts a
        line of front matter at the top of the first section, which is visible
        and harmless.

        The signals, in the order they are allowed to narrow the boundary:

        * the first ``Header`` that is not an abstract/keywords label, which is
          what the caller already computed and passes in;
        * the abstract/keywords labels, the one landmark shared by every
          publisher, which also establish the *floor* -- the boundary is never
          allowed to cut into the abstract itself;
        * the body-opener vocabulary, which needs no formatting at all and is
          therefore the signal that works when the document has no usable
          heading styles;
        * a hard ceiling, because no title block in any layout runs to
          ``_MAX_FRONT_MATTER_BLOCKS`` paragraphs and a boundary beyond it is a
          detection failure rather than a long front matter.

        Returns the boundary and the name of the signal that set it, so the
        caller can report how the decision was made.
        """
        n = len(blocks)
        if not n:
            return 0, "empty"

        structural_end, from_label = self._front_matter_end(blocks)
        boundary = max(0, min(heading_boundary, n))
        reason = "heading" if found_header else "document-end"

        if not found_header:
            if structural_end < n:
                boundary = structural_end
                reason = "label" if from_label else "prose"
        elif from_label and structural_end < boundary:
            boundary = structural_end
            reason = "label"

        # The abstract and its label always belong to the front matter, so no
        # later signal may cut before them.
        floor = min(structural_end, n) if from_label else min(1, n)

        opener = self._body_opener_index(blocks, floor)
        if opener is not None and floor <= opener < boundary:
            boundary = opener
            reason = "body-opener"
        elif opener is not None and boundary < opener < min(n, _MAX_FRONT_MATTER_BLOCKS) \
                and isinstance(blocks[opener], dict) and blocks[opener].get("t") == "Header":
            # The one case in which the boundary may move *later*: a real
            # ``Header`` whose title is a body opener is a positive
            # identification of where the body starts, not an inference, so
            # everything before it is front matter by definition.  Publishers
            # place classification codes, JEL codes, MSC numbers and submission
            # notes between the keywords and the first section, and without
            # this the leading one of those becomes a stray untitled section at
            # the top of the paper.  The move is bounded by the same ceiling as
            # every other signal, so it cannot reintroduce the failure mode the
            # monotonicity rule exists to prevent.
            boundary = opener
            reason = "body-opener-header"

        ceiling = max(floor, min(n, _MAX_FRONT_MATTER_BLOCKS))
        if boundary > ceiling:
            boundary = ceiling
            reason = "clamped"

        return max(0, min(boundary, n)), reason

    def _lift_list_headings(
        self, block: Dict[str, Any], formats: Dict[str, Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Split a list block around the items that are really headings.

        Returns the replacement block sequence and how many headings were
        lifted.  When nothing is lifted the count is zero and the caller keeps
        the original block, so a document that numbers its headings any other
        way is completely unaffected.  Only an item consisting of exactly one
        short paragraph whose text the formatting pass already classified as a
        heading is lifted; list attributes and item order are otherwise kept.
        """
        kind = block.get("t")
        raw = block.get("c") or []
        if kind == "OrderedList":
            attrs, items = (raw[0], raw[1]) if len(raw) > 1 else (None, [])
        else:
            attrs, items = None, raw
        if not isinstance(items, list) or not items:
            return [block], 0

        def rebuild(chunk: List[Any]) -> Dict[str, Any]:
            return {"t": kind, "c": [attrs, chunk] if kind == "OrderedList" else chunk}

        # First pass: describe each item without deciding anything.  ``fmt`` is
        # the formatting pass's own verdict; ``shaped`` is whether the item even
        # could be a heading (a single short, non-prose paragraph).
        described: List[Tuple[Optional[List[Any]], Optional[Dict[str, Any]], bool]] = []
        for item in items:
            inlines = None
            fmt = None
            shaped = False
            if isinstance(item, list) and len(item) == 1 and isinstance(item[0], dict) \
                    and item[0].get("t") in ("Para", "Plain"):
                inlines = item[0].get("c") or []
                text = self._stringify_inlines(inlines).strip()
                if text and len(text) <= 120:
                    fmt = formats.get("".join(text.split()).lower())
                    title = _strip_heading_number(_normalise_label(text))
                    shaped = not self._looks_like_prose(text)
                    if title and _BODY_OPENER_RE.match(title):
                        # The body-opener vocabulary is evidence in its own
                        # right, so a paper whose "Introduction" the formatting
                        # pass could not see is still recovered.
                        fmt = fmt or {"level": 1}
            described.append((inlines, fmt, shaped))

        # A numbered list that is *confirmed* to contain at least one heading,
        # and every one of whose items has heading shape, is not a list at all:
        # it is the run of section headings Word numbered with list numbering
        # and pandoc folded together.  Inferring the remaining headings from
        # their confirmed siblings needs no vocabulary and no style names, so it
        # generalises to any document that numbers its headings this way -- and
        # it cannot fire on a genuine enumeration, because a real list item that
        # reads as prose fails the shape test for the whole block.
        known = [f for _, f, _ in described if f]
        # The inference needs a *majority* of confirmed siblings, not merely
        # one.  A single confirmed item is equally consistent with a genuine
        # enumeration that happens to contain one heading-like entry, and
        # promoting the rest of that list would turn ordinary bullet points
        # into sections.  Requiring most of the list to be independently
        # confirmed by the formatting pass keeps the inference to its intended
        # case -- a run of section headings Word numbered with list numbering,
        # where the formatting pass recognises most of them and misses a few.
        uniform = len(known) >= 2 and len(described) > 1 \
            and len(known) * 2 >= len(described) \
            and all(shaped and inl is not None for inl, _, shaped in described)
        if uniform:
            inferred_level = max(1, min(6, int(known[0].get("level") or 1)))
            described = [(inl, f or {"level": inferred_level}, shaped)
                         for inl, f, shaped in described]

        out: List[Dict[str, Any]] = []
        pending: List[Any] = []
        lifted = 0
        for item, (inlines, fmt, _shaped) in zip(items, described):
            if fmt and inlines is not None:
                if pending:
                    out.append(rebuild(pending))
                    pending = []
                level = max(1, min(6, int(fmt.get("level") or 1)))
                out.append({"t": "Header", "c": [level, ["", [], []], inlines]})
                lifted += 1
            else:
                pending.append(item)
        if pending:
            out.append(rebuild(pending))
        return (out, lifted) if lifted else ([block], 0)

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
            if isinstance(b, dict) and b.get("t") in ("OrderedList", "BulletList") \
                    and index > front_end:
                # A heading that Word numbered with its list numbering ("1.
                # Introduction") stays a list paragraph, and pandoc folds a run
                # of them into a single list block.  Such a heading can never
                # reach the Para branch below, so the whole paper reads as one
                # section -- or, when the only headings pandoc did see are the
                # unnumbered closing ones, the front-matter boundary lands near
                # the end of the document.  List items that the formatting pass
                # already recognised as headings are therefore lifted out of the
                # list; every other item is left in place, so a genuine
                # enumeration is untouched.
                lifted, n = self._lift_list_headings(b, formats)
                if n:
                    promoted.extend(lifted)
                    count += n
                    continue
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
            doc_root = self._part_tree(docx_path, "word/document.xml")
            styles_root = self._part_tree(docx_path, "word/styles.xml")
            if doc_root is None:
                return formats
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
            root = self._part_tree(docx_path, "word/document.xml")
            if root is None:
                return styles
            # This pass needs the archive itself as well: _grid_style_ids
            # reads styles.xml through the open handle.  Only document.xml --
            # the large member -- comes from the per-call cache.
            with zipfile.ZipFile(docx_path) as zf:
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
            rels: Dict[str, str] = {}
            rt = self._part_tree(docx_path, "word/_rels/document.xml.rels")
            if rt is not None:
                for rel in rt:
                    rels[rel.get("Id")] = rel.get("Target") or ""
            root = self._part_tree(docx_path, "word/document.xml")
            if root is None:
                return placement
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

    # An English Metric Unit is 1/914400 inch.  Word stores every drawing's
    # size in EMU, exactly, and that is the only lossless record of how large
    # the author meant a figure or an equation image to be: pandoc reports a
    # rounded value in points when it reports one at all, and reports nothing
    # for a drawing it cannot size.
    _EMU_PER_INCH = 914400.0

    def _extract_drawing_geometry(self, docx_path: Path) -> Dict[str, Dict[str, Any]]:
        """Original geometry of every embedded drawing, keyed by media path.

        Word records a drawing's size as a ``wp:extent`` in EMU and its
        placement as either ``wp:inline`` or ``wp:anchor``.  Both are properties
        of the source document, so reading them here means a figure keeps the
        size, the aspect ratio and the positioning the author gave it even when
        pandoc's own attributes are absent or rounded -- which is the usual case
        for equation images, the drawings publishers use when an equation was
        pasted as a picture rather than typed as OMML.

        Returned per drawing: ``emu_width``/``emu_height`` (exact source
        values), ``width_in``/``height_in`` (the same, converted),
        ``aspect_ratio`` (width over height, so a consumer that must scale can
        scale without distorting) and ``inline`` (``True`` for ``wp:inline``,
        ``False`` for an anchored/floating drawing).
        """
        import zipfile
        import xml.etree.ElementTree as ET
        W = self._W_NS
        WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
        A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
        geometry: Dict[str, Dict[str, Any]] = {}
        rels: Dict[str, str] = {}
        rt = self._part_tree(docx_path, "word/_rels/document.xml.rels")
        if rt is not None:
            for rel in rt:
                rels[rel.get("Id")] = rel.get("Target") or ""
        root = self._part_tree(docx_path, "word/document.xml")
        if root is None:
            return geometry

        for dr in root.iter(f"{W}drawing"):
            inline_el = dr.find(f"{WP}inline")
            anchor_el = dr.find(f"{WP}anchor")
            container = inline_el if inline_el is not None else anchor_el
            if container is None:
                continue
            extent = container.find(f"{WP}extent")
            if extent is None:
                continue
            try:
                cx = int(extent.get("cx") or 0)
                cy = int(extent.get("cy") or 0)
            except (TypeError, ValueError):
                continue
            if cx <= 0 or cy <= 0:
                continue
            blip = dr.find(f".//{A}blip")
            emb = blip.get(f"{R}embed") if blip is not None else None
            tgt = rels.get(emb) if emb else None
            if not tgt:
                continue
            key = "media/" + tgt.split("/")[-1]
            geometry.setdefault(key, {
                "emu_width": cx,
                "emu_height": cy,
                "width_in": round(cx / self._EMU_PER_INCH, 4),
                "height_in": round(cy / self._EMU_PER_INCH, 4),
                "aspect_ratio": round(cx / float(cy), 6),
                "inline": inline_el is not None,
                "is_equation": False,
            })

        # Legacy embedded objects -- above all Equation Editor and MathType
        # equations, which publishers' templates produce in very large numbers
        # -- are not DrawingML at all.  They are VML shapes inside ``w:object``,
        # sized by a CSS-like ``style`` attribute in points, and pandoc emits
        # them as ordinary pictures with no dimensions whatsoever.  Reading them
        # here is what gives an equation image its true size and, just as
        # importantly, records that the picture *is* an equation rather than a
        # figure.
        V = "{urn:schemas-microsoft-com:vml}"
        O = "{urn:schemas-microsoft-com:office:office}"
        for obj in root.iter(f"{W}object"):
            prog = ""
            for ole_el in obj.iter(f"{O}OLEObject"):
                prog = (ole_el.get("ProgID") or "").lower()
                break
            is_equation = "equation" in prog or "mathtype" in prog
            for shape in obj.iter(f"{V}shape"):
                data = shape.find(f"{V}imagedata")
                emb = data.get(f"{R}id") if data is not None else None
                tgt = rels.get(emb) if emb else None
                if not tgt:
                    continue
                w_pt, h_pt = self._vml_style_size_pt(shape.get("style") or "")
                if not (w_pt and h_pt):
                    # Word also records the object's original size in twentieths
                    # of a point on the w:object element itself; use it when the
                    # shape carries no explicit style.
                    try:
                        w_pt = int(obj.get(f"{W}dxaOrig") or 0) / 20.0
                        h_pt = int(obj.get(f"{W}dyaOrig") or 0) / 20.0
                    except (TypeError, ValueError):
                        w_pt = h_pt = 0.0
                if not (w_pt and h_pt):
                    continue
                cx = int(round(w_pt * self._EMU_PER_INCH / 72.0))
                cy = int(round(h_pt * self._EMU_PER_INCH / 72.0))
                geometry.setdefault("media/" + tgt.split("/")[-1], {
                    "emu_width": cx,
                    "emu_height": cy,
                    "width_in": round(w_pt / 72.0, 4),
                    "height_in": round(h_pt / 72.0, 4),
                    "aspect_ratio": round(w_pt / float(h_pt), 6),
                    # A VML shape inside a run is inline by construction; a
                    # floating one carries an absolute position in its style.
                    "inline": "position:absolute" not in (shape.get("style") or ""),
                    "is_equation": is_equation,
                })
        return geometry

    @staticmethod
    def _vml_style_size_pt(style: str) -> Tuple[float, float]:
        """Width and height in points from a VML ``style`` attribute.

        The attribute is a CSS-like declaration list ("width:20pt;height:15.8pt").
        Only absolute units are meaningful as a source size; a percentage is
        relative to a container this code has no view of, so it is ignored
        rather than guessed at.
        """
        units = {"pt": 1.0, "in": 72.0, "cm": 72.0 / 2.54, "mm": 72.0 / 25.4,
                 "pc": 12.0, "px": 0.75}
        out = {"width": 0.0, "height": 0.0}
        for decl in style.split(";"):
            name, _, value = decl.partition(":")
            name = name.strip().lower()
            if name not in out:
                continue
            m = re.match(r"^\s*([0-9.]+)\s*([a-z]*)\s*$", value.strip().lower())
            if not m:
                continue
            try:
                magnitude = float(m.group(1))
            except ValueError:
                continue
            out[name] = magnitude * units.get(m.group(2) or "pt", 0.0)
        return out["width"], out["height"]

    def _count_omml_equations(self, docx_path: Path) -> Dict[str, int]:
        """Census of the equations the source document actually contains.

        Counted in the OMML itself rather than inferred from the parsed model,
        so that "how many equations does this paper have" and "how many did we
        recover" are two independently measured numbers.  Without that, an
        equation lost in conversion is indistinguishable from a paper that
        never had one.

        ``omath`` counts equations proper; ``omath_para`` counts those Word set
        as their own display paragraph; ``ole_equations`` counts legacy
        Equation Editor / MathType objects, which are embedded *objects*, not
        OMML, and which pandoc surfaces as ordinary pictures -- knowing they are
        equations is what stops them being treated as figures.
        """
        import zipfile
        import xml.etree.ElementTree as ET
        M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
        O = "{urn:schemas-microsoft-com:office:office}"
        W = self._W_NS
        root = self._part_tree(docx_path, "word/document.xml")
        if root is None:
            raise KeyError("word/document.xml")
        omath_para = len(list(root.iter(f"{M}oMathPara")))
        # An oMath inside an oMathPara is the same equation counted once.
        omath = len(list(root.iter(f"{M}oMath")))
        ole = 0
        for obj in root.iter(f"{W}object"):
            for ole_el in obj.iter(f"{O}OLEObject"):
                prog = (ole_el.get("ProgID") or "").lower()
                if "equation" in prog or "mathtype" in prog:
                    ole += 1
        return {"omath": omath, "omath_para": omath_para, "ole_equations": ole}

    def _extract_text_width_in(self, docx_path: Path) -> float:
        """Usable text-column width of the document in inches (0.0 if unknown)."""
        import zipfile
        import xml.etree.ElementTree as ET
        W = self._W_NS
        try:
            root = self._part_tree(docx_path, "word/document.xml")
            if root is None:
                raise KeyError("word/document.xml")
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
