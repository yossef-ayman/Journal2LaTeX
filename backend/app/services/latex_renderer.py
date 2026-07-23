import json
import re
from pathlib import Path
from typing import Optional
from app.models.document import DocumentBlock, DocumentModel, BlockType
from app.utils.logger import get_job_logger
from app.utils.filesystem import read_text_file
from app.utils.latex import escape_latex_keep_math
from app.utils.media_convert import latex_safe_image_name


class LatexRendererError(Exception):
    """Exception raised when LaTeX rendering operations fail."""
    pass


def replace_latex_command(content: str, command_name: str, replacement: str) -> str:
    """Find and replace the argument of a LaTeX command handling nested braces."""
    idx = 0
    while True:
        start_idx = content.find(command_name, idx)
        if start_idx == -1:
            break
        # Ensure command_name is matched as a complete word (not a prefix of a longer command)
        next_char_pos = start_idx + len(command_name)
        if next_char_pos < len(content):
            next_char = content[next_char_pos]
            if next_char.isalpha():
                idx = next_char_pos
                continue

        # Find the opening brace '{'
        brace_start = content.find("{", start_idx + len(command_name))
        if brace_start == -1 or brace_start > start_idx + len(command_name) + 10:
            idx = start_idx + len(command_name)
            continue
        
        # Find matching closing brace
        brace_count = 1
        brace_end = -1
        for i in range(brace_start + 1, len(content)):
            if content[i] == "{":
                brace_count += 1
            elif content[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    brace_end = i
                    break
        if brace_end != -1:
            content = content[:brace_start + 1] + replacement + content[brace_end:]
            idx = brace_start + 1 + len(replacement)
        else:
            idx = brace_start + 1
    return content


class LatexRenderer:
    """Service to render structured DocumentModel data into a LaTeX document project."""

    def render_document(self, doc: DocumentModel, workspace_dir: Path, job_id: str) -> Path:
        """Render a DocumentModel to main.tex in the prepared workspace.

        Args:
            doc: The DocumentModel to render.
            workspace_dir: The isolated target workspace directory containing template files.
            job_id: The job ID for logging.

        Returns:
            The Path to the created main.tex.
        """
        logger = get_job_logger(job_id, "system")
        logger.info("Starting LaTeX rendering inside workspace: %s", workspace_dir)

        # Resolve entry file dynamically
        template_metadata = self._load_template_metadata(workspace_dir)

        entry_file = template_metadata.get("entry_file") or "template.tex"
        template_tex_path = workspace_dir / entry_file

        if not template_tex_path.exists():
            msg = f"Base template entry file '{entry_file}' not found in workspace: {template_tex_path}"
            logger.error(msg)
            raise LatexRendererError(msg)

        try:
            # Reset the per-run placement log (populated by the placement policy).
            self._placement_log = []
            # Media dir, used to read a figure's *native* aspect ratio (how it
            # actually renders under keepaspectratio) for the placement policy.
            self._media_dir = workspace_dir / "media"
            # 1. Render block elements sequentially
            rendered_blocks = []
            for section in doc.sections:
                rendered_blocks.append(self._render_heading(section))
                
                # Render section blocks
                for block in section.blocks:
                    rendered_block = self._render_block(block, job_id)
                    if rendered_block:
                        rendered_blocks.append(rendered_block)

            from app.services.citation_mapper import CitationMapper
            content_tex = "\n\n".join(rendered_blocks)
            intermediate_dir = workspace_dir.parent / "intermediate"
            content_tex, citation_report = CitationMapper().map_citations(doc, content_tex, intermediate_dir)

            # 2. Format Authors and Institutes
            author_strings = []
            affiliations = []
            for author in doc.authors:
                if author.affiliation:
                    if author.affiliation not in affiliations:
                        affiliations.append(author.affiliation)
                    idx = affiliations.index(author.affiliation) + 1
                    author_strings.append(f"{self._escape_text(author.name)}$^{{{idx}}}$")
                else:
                    author_strings.append(self._escape_text(author.name))
            
            authors_tex = " \\and ".join(author_strings) if author_strings else "Author name unspecified"
            
            institute_strings = []
            for idx, aff in enumerate(affiliations):
                institute_strings.append(f"$^{{{idx+1}}}$ {self._escape_text(aff)}")
            institutes_tex = " \\\\ ".join(institute_strings) if institute_strings else ""

            # 3. Read base template
            template_content = read_text_file(template_tex_path)

            # 4. Format Bibliography
            bib_tex = ""
            if doc.references:
                bib_tex = "\\begin{thebibliography}{99}\n"
                for idx, ref in enumerate(doc.references):
                    # \bibitem numbers entries itself; strip any literal
                    # enumeration carried over from Word ("[25] ...", "25. ...")
                    # so entries do not render as "[25] [25] ...".
                    cleaned_ref = re.sub(r"^\s*(?:\[\d+\]|\d+[\.\)])\s*", "", ref.strip())
                    ref_text = self._escape_text(cleaned_ref or ref.strip())
                    bib_tex += f"\\bibitem{{ref{idx+1}}}\n{ref_text}\n\n"
                bib_tex += "\\end{thebibliography}\n"

            # 5. Format Biographies
            biography_tex = ""
            if doc.author_biographies and template_metadata.get("supported_features", {}).get("author_biographies", True):
                class_file = template_metadata.get("class_file", "")
                is_nsp = "NSP" in class_file or "JSAP" in template_metadata.get("name", "")
                
                biography_tex = "\n\n"
                for bio in doc.author_biographies:
                    b_name = self._escape_text(bio.author_name)
                    b_text = self._escape_text(bio.biography_text.strip())
                    
                    if bio.image_path:
                        img_name = latex_safe_image_name(bio.image_path)
                        relative_path = f"media/{img_name}"
                        
                        if is_nsp:
                            biography_tex += (
                                f"\\begin{{biographyps}}{{{relative_path}}}{{{b_name}}}\n"
                                f"{b_text}\\end{{biographyps}}\n\n"
                            )
                        else:
                            biography_tex += (
                                f"\\noindent\\textbf{{{b_name}}}\\\\\n"
                                f"\\includegraphics[width=1in,height=1.25in,keepaspectratio]{{{relative_path}}}\\\\\n"
                                f"{b_text}\\par\\bigskip\n\n"
                            )
                    else:
                        if is_nsp:
                            biography_tex += (
                                f"\\begin{{biography}}{{{b_name}}}\n"
                                f"{b_text}\\end{{biography}}\n\n"
                            )
                        else:
                            biography_tex += (
                                f"\\noindent\\textbf{{{b_name}}}\\\\\n"
                                f"{b_text}\\par\\bigskip\n\n"
                            )

            if bib_tex:
                content_tex += "\n\n" + bib_tex
            if biography_tex:
                if content_tex and not content_tex.endswith("\n\n"):
                    content_tex += "\n\n"
                content_tex += biography_tex

            # 6. Perform template substitutions or smart merge.
            # Fallback values come from the template's own metadata (template.json
            # "defaults"), never from hard-coded sample-paper values.
            defaults = template_metadata.get("defaults", {}) if isinstance(template_metadata, dict) else {}

            def _field(value, key):
                if value and value.strip():
                    return value.strip()
                return str(defaults.get(key, "") or "")

            vol = _field(doc.volume, "volume")
            iss = _field(doc.issue, "issue")
            yr = _field(doc.year, "year")
            rec = _field(doc.received_date, "received_date")
            rev = _field(doc.revised_date, "revised_date")
            acc = _field(doc.accepted_date, "accepted_date")
            pub = _field(doc.published_date, "published_date")

            if "__CONTENT__" not in template_content:
                # 6.a Smart Merge Strategy for Standard LaTeX Templates
                rendered_content = template_content
                
                # Replace Title, Author, Keywords in the template
                rendered_content = replace_latex_command(rendered_content, "\\title", self._escape_text(doc.title or "Untitled Document"))
                rendered_content = replace_latex_command(rendered_content, "\\author", authors_tex)
                rendered_content = replace_latex_command(rendered_content, "\\keywords", ", ".join(self._escape_text(k) for k in doc.keywords))
                
                # Replace affiliations if present
                rendered_content = replace_latex_command(rendered_content, "\\institute", institutes_tex)
                rendered_content = replace_latex_command(rendered_content, "\\address", institutes_tex)
                rendered_content = replace_latex_command(rendered_content, "\\affiliation", institutes_tex)

                # Replace running titles/authors and corresponding emails
                if doc.title:
                    rendered_content = replace_latex_command(rendered_content, "\\titlerunning", self._escape_text(doc.title))
                if doc.authors:
                    first_author = doc.authors[0].name
                    running_author = f"{first_author} et al." if len(doc.authors) > 1 else first_author
                    rendered_content = replace_latex_command(rendered_content, "\\authorrunning", self._escape_text(running_author))
                
                corresponding_email = getattr(doc, "corresponding_email", "") or ""
                if not corresponding_email:
                    for author in doc.authors:
                        if author.email:
                            corresponding_email = author.email
                            break
                rendered_content = replace_latex_command(rendered_content, "\\mail", self._escape_text(corresponding_email) if corresponding_email else "")

                # Replace dates if commands exist (otherwise clear them to prevent legacy fallbacks)
                rendered_content = replace_latex_command(rendered_content, "\\received", self._escape_text(doc.received_date) if doc.received_date else "")
                rendered_content = replace_latex_command(rendered_content, "\\revised", self._escape_text(doc.revised_date) if doc.revised_date else "")
                rendered_content = replace_latex_command(rendered_content, "\\accepted", self._escape_text(doc.accepted_date) if doc.accepted_date else "")
                rendered_content = replace_latex_command(rendered_content, "\\published", self._escape_text(doc.published_date) if doc.published_date else "")

                # Replace volume, issue, year defs if present
                rendered_content = replace_latex_command(rendered_content, "\\def\\firstpage", "1")
                rendered_content = replace_latex_command(rendered_content, "\\def\\thevol", vol)
                rendered_content = replace_latex_command(rendered_content, "\\def\\thenumber", iss)
                rendered_content = replace_latex_command(rendered_content, "\\def\\theyear", yr)

                # Replace Abstract if it's a command
                rendered_content = replace_latex_command(rendered_content, "\\abstract", self._escape_text(doc.abstract))
                rendered_content = replace_latex_command(rendered_content, "\\abstracttext", self._escape_text(doc.abstract))
                
                # Replace Abstract if it's an environment
                abstract_start = rendered_content.find("\\begin{abstract}")
                if abstract_start != -1:
                    abstract_end = rendered_content.find("\\end{abstract}", abstract_start)
                    if abstract_end != -1:
                        insert_pos = abstract_start + len("\\begin{abstract}")
                        rendered_content = (
                            rendered_content[:insert_pos] +
                            "\n" + self._escape_text(doc.abstract) + "\n" +
                            rendered_content[abstract_end:]
                        )
                
                # Replace metadata placeholders
                rendered_content = rendered_content.replace("__VOLUME__", vol)
                rendered_content = rendered_content.replace("__ISSUE__", iss)
                rendered_content = rendered_content.replace("__YEAR__", yr)
                rendered_content = rendered_content.replace("__RECEIVED_DATE__", rec)
                rendered_content = rendered_content.replace("__REVISED_DATE__", rev)
                rendered_content = rendered_content.replace("__ACCEPTED_DATE__", acc)
                rendered_content = rendered_content.replace("__PUBLISHED_DATE__", pub)

                # Merge Document Body (find first \section or \chapter after \begin{document})
                begin_doc = rendered_content.find("\\begin{document}")
                if begin_doc != -1:
                    first_sec = rendered_content.find("\\section", begin_doc)
                    if first_sec == -1:
                        first_sec = rendered_content.find("\\chapter", begin_doc)
                        
                    end_doc = rendered_content.find("\\end{document}", begin_doc)
                    
                    if first_sec != -1 and end_doc != -1 and first_sec < end_doc:
                        rendered_content = (
                            rendered_content[:first_sec] +
                            content_tex + "\n\n" +
                            rendered_content[end_doc:]
                        )
                    elif end_doc != -1:
                        insert_pos = begin_doc + len("\\begin{document}")
                        rendered_content = (
                            rendered_content[:insert_pos] +
                            "\n" + content_tex + "\n" +
                            rendered_content[end_doc:]
                        )
            else:
                # 6.b Default Placeholder Replacement Strategy
                rendered_content = template_content
                rendered_content = rendered_content.replace("__TITLE__", self._escape_text(doc.title or "Untitled Document"))
                # \and is a \maketitle-only construct (article.cls implements
                # it with tabular switching); inline title blocks need commas.
                rendered_content = rendered_content.replace(
                    "__AUTHORS__", authors_tex.replace(" \\and ", ", ")
                )
                rendered_content = rendered_content.replace("__INSTITUTES__", institutes_tex)
                rendered_content = rendered_content.replace("__ABSTRACT__", self._escape_text(doc.abstract))
                rendered_content = rendered_content.replace("__KEYWORDS__", ", ".join(self._escape_text(k) for k in doc.keywords))
                rendered_content = rendered_content.replace("__CONTENT__", content_tex)

                rendered_content = rendered_content.replace("__VOLUME__", vol)
                rendered_content = rendered_content.replace("__ISSUE__", iss)
                rendered_content = rendered_content.replace("__YEAR__", yr)
                rendered_content = rendered_content.replace("__RECEIVED_DATE__", rec)
                rendered_content = rendered_content.replace("__REVISED_DATE__", rev)
                rendered_content = rendered_content.replace("__ACCEPTED_DATE__", acc)
                rendered_content = rendered_content.replace("__PUBLISHED_DATE__", pub)
                rendered_content = self._inject_corresponding_email(rendered_content, doc)

            # If NSP template, inject graphicx package and redefine biographyps to avoid psfig crash
            is_nsp = "NSP" in template_metadata.get("class_file", "") or "JSAP" in template_metadata.get("name", "")
            if is_nsp:
                begin_doc = rendered_content.find("\\begin{document}")
                if begin_doc != -1:
                    redef = (
                        "\\usepackage{graphicx}\n"
                        "\\makeatletter\n"
                        "\\def\\biographyps#1#2{%\n"
                        "  \\par\\addvspace{21dd}\\small\\noindent\n"
                        "  \\if!#1!\\else\n"
                        "    \\noindent\\includegraphics[width=1in,height=1.25in,keepaspectratio]{#1}\\par\\smallskip\n"
                        "  \\fi\n"
                        "  {\\bfseries#2\\unskip\\ }\\ignorespaces}\n"
                        "\\def\\endbiographyps{\\par\\addvspace{12pt}}\n"
                        "\\makeatother\n"
                    )
                    rendered_content = rendered_content[:begin_doc] + redef + rendered_content[begin_doc:]

            # Structured tables need multirow and cell-colour support.
            needed_pkgs = []
            if "\\multirow" in rendered_content and "usepackage{multirow}" not in rendered_content:
                needed_pkgs.append("\\usepackage{multirow}")
            if "\\cellcolor" in rendered_content and "usepackage[table]{xcolor}" not in rendered_content:
                needed_pkgs.append("\\usepackage[table]{xcolor}")
            if "\\arraybackslash" in rendered_content and "usepackage{array}" not in rendered_content:
                needed_pkgs.append("\\usepackage{array}")
            # Inline, in-reading-order figures/tables use \begin{strip} (cuted)
            # for full-width spanning content and \captionof (caption) for the
            # numbered caption on non-floating content.
            if "[H]" in rendered_content and "usepackage{float}" not in rendered_content:
                needed_pkgs.append("\\usepackage{float}")
            if "\\begin{strip}" in rendered_content and "usepackage{cuted}" not in rendered_content:
                needed_pkgs.append("\\usepackage{cuted}")
            if "\\captionof" in rendered_content and "{caption}" not in rendered_content \
                    and "{capt-of}" not in rendered_content:
                needed_pkgs.append("\\usepackage{capt-of}")
            if needed_pkgs:
                begin_doc_pos = rendered_content.find("\\begin{document}")
                if begin_doc_pos != -1:
                    rendered_content = (
                        rendered_content[:begin_doc_pos]
                        + "\n".join(needed_pkgs) + "\n"
                        + rendered_content[begin_doc_pos:]
                    )

            # Declare Unicode characters that pdfLaTeX would otherwise drop
            # (e.g. Greek chi in "chi-squared", the true minus sign, and the
            # dot-below / ayn transliteration marks in Arabic names).  Without
            # this a value such as "χ² = 3232.818" loses its χ.  Only mappings
            # for characters actually present are emitted.
            rendered_content = self._inject_unicode_support(rendered_content)

            # 5. Write to main.tex
            main_tex_path = workspace_dir / "main.tex"
            main_tex_path.write_text(rendered_content, encoding="utf-8")

            # Persist the placement decisions for the fidelity report.
            try:
                import json as _json
                report_dir = workspace_dir.parent / "intermediate"
                report_dir.mkdir(parents=True, exist_ok=True)
                (report_dir / "placement_report.json").write_text(
                    _json.dumps(self._placement_log, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception:  # reporting must never break rendering
                pass

            logger.info("LaTeX document main.tex rendered successfully.")
            return main_tex_path

        except Exception as e:
            msg = f"Failed to render LaTeX document: {str(e)}"
            logger.exception(msg)
            raise LatexRendererError(msg) from e

    @staticmethod
    def _load_template_metadata(workspace_dir: Path) -> dict:
        """Load template.json from the workspace, tolerating absence/corruption."""
        metadata_file = workspace_dir / "template.json"
        if metadata_file.exists():
            try:
                return json.loads(metadata_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {}

    # Unicode characters pdfLaTeX does not set up by default, mapped to a safe
    # LaTeX rendering.  Latin letters with accents/macrons, dashes and curly
    # quotes are already handled by the kernel, so they are intentionally omitted.
    _UNICODE_MAP = {
        # Greek letters (statistics: chi-squared, eta-squared, alpha, ...)
        "α": "\\ensuremath{\\alpha}", "β": "\\ensuremath{\\beta}",
        "γ": "\\ensuremath{\\gamma}", "δ": "\\ensuremath{\\delta}",
        "ε": "\\ensuremath{\\varepsilon}", "η": "\\ensuremath{\\eta}",
        "θ": "\\ensuremath{\\theta}", "λ": "\\ensuremath{\\lambda}",
        "μ": "\\ensuremath{\\mu}", "π": "\\ensuremath{\\pi}",
        "ρ": "\\ensuremath{\\rho}", "σ": "\\ensuremath{\\sigma}",
        "τ": "\\ensuremath{\\tau}", "φ": "\\ensuremath{\\varphi}",
        "χ": "\\ensuremath{\\chi}", "ψ": "\\ensuremath{\\psi}",
        "ω": "\\ensuremath{\\omega}", "Δ": "\\ensuremath{\\Delta}",
        "Σ": "\\ensuremath{\\Sigma}", "Ω": "\\ensuremath{\\Omega}",
        # Mathematical operators / symbols
        "−": "\\ensuremath{-}", "×": "\\ensuremath{\\times}",
        "÷": "\\ensuremath{\\div}", "≤": "\\ensuremath{\\leq}",
        "≥": "\\ensuremath{\\geq}", "≠": "\\ensuremath{\\neq}",
        "±": "\\ensuremath{\\pm}", "≈": "\\ensuremath{\\approx}",
        "∑": "\\ensuremath{\\sum}", "√": "\\ensuremath{\\surd}",
        "·": "\\ensuremath{\\cdot}", "′": "\\ensuremath{{}^{\\prime}}",
        # Transliteration marks (Arabic romanisation of author names)
        "ʿ": "{`}", "ʾ": "{'}", "Ḍ": "\\d{D}", "ḍ": "\\d{d}",
        "Ḥ": "\\d{H}", "ḥ": "\\d{h}", "Ṣ": "\\d{S}",
        "ṣ": "\\d{s}", "Ṭ": "\\d{T}", "ṭ": "\\d{t}",
        "Ẓ": "\\d{Z}", "ẓ": "\\d{z}",
    }

    def _inject_unicode_support(self, rendered_content: str) -> str:
        """Add \\newunicodechar declarations for characters pdfLaTeX cannot
        typeset out of the box, so no value silently loses a character."""
        present = [ch for ch in self._UNICODE_MAP if ch in rendered_content]
        if not present:
            return rendered_content
        begin_doc_pos = rendered_content.find("\\begin{document}")
        if begin_doc_pos == -1:
            return rendered_content
        lines = ["\\usepackage{newunicodechar}"]
        for ch in present:
            lines.append(f"\\newunicodechar{{{ch}}}{{{self._UNICODE_MAP[ch]}}}")
        block = "\n".join(lines) + "\n"
        return (
            rendered_content[:begin_doc_pos]
            + block
            + rendered_content[begin_doc_pos:]
        )

    def _inject_corresponding_email(self, rendered_content: str, doc: DocumentModel) -> str:
        """Populate the corresponding-author e-mail in the rendered template.

        The address is taken from ``doc.corresponding_email`` (extracted from the
        DOCX footer/footnote/endnote/author block).  If the template exposes a
        ``\\mail`` placeholder it is replaced in place; otherwise, for journal
        classes that define ``\\mail`` (e.g. NSP/JSAP), ``\\mail{...}`` is
        declared just before ``\\maketitle`` so the class renders the label,
        asterisk, colour, spacing and footer placement exactly as specified by
        the journal.  A no-op when no e-mail is available.
        """
        corresponding_email = getattr(doc, "corresponding_email", "") or ""
        if not corresponding_email:
            for author in doc.authors:
                if author.email:
                    corresponding_email = author.email
                    break
        if not corresponding_email:
            return rendered_content

        escaped_mail = self._escape_text(corresponding_email)
        if "\\mail" in rendered_content:
            return replace_latex_command(rendered_content, "\\mail", escaped_mail)

        maketitle_pos = rendered_content.find("\\maketitle")
        if maketitle_pos != -1:
            return (
                rendered_content[:maketitle_pos]
                + "\\mail{" + escaped_mail + "}\n"
                + rendered_content[maketitle_pos:]
            )
        return rendered_content

    def _render_heading(self, section) -> str:
        """Render a section heading.

        When DOCX heading formatting is available, reproduce the Word heading's
        own appearance locally -- bold, body-relative font size, alignment,
        space before/after, and keep-with-next -- so the output matches the
        source document.  This is a self-contained block that does NOT redefine
        the template's \\section machinery, so a journal template's own
        sectioning styles are left intact (only this document's headings use
        the reproduced formatting).  Falls back to plain unnumbered sectioning
        when no formatting was captured.
        """
        title_tex = self._escape_text(section.title)
        fmt = getattr(section, "heading_format", None)

        if not fmt:
            cmd = {1: "section", 2: "subsection", 3: "subsubsection"}.get(
                section.level, "subsubsection"
            )
            return f"\\{cmd}*{{{title_tex}}}"

        # Body-relative font size -> a LaTeX size command (keeps the modest
        # heading/body ratio the Word document actually uses instead of the
        # template's large \section sizes).
        ratio = fmt.get("size_ratio") or 1.0
        if ratio >= 1.45:
            size_cmd = "\\LARGE"
        elif ratio >= 1.28:
            size_cmd = "\\Large"
        elif ratio >= 1.05:
            size_cmd = "\\large"
        else:
            size_cmd = "\\normalsize"

        weight = "\\bfseries" if fmt.get("bold", True) else ""
        align = fmt.get("alignment", "left")
        align_open, align_close = "", ""
        if align == "center":
            align_open, align_close = "\\begin{center}", "\\end{center}"
        # "left"/"both"(justified) -> flush-left heading (default); right is rare.
        elif align in ("right", "end"):
            align_open, align_close = "{\\raggedleft ", "\\par}"

        # Space before / after: use the DOCX values when present, else modest
        # defaults proportional to the heading size.
        before = fmt.get("space_before_pt")
        after = fmt.get("space_after_pt")
        before_tex = f"\\vspace{{{before:.1f}pt}}" if before else "\\medskip"
        after_tex = f"\\vspace{{{after:.1f}pt}}" if after else "\\smallskip"
        keep = "\\nopagebreak" if fmt.get("keep_with_next") else ""

        body = f"{{{size_cmd}{weight} {title_tex}\\par}}"
        if align_open:
            body = f"{align_open}{size_cmd}{weight} {title_tex}{align_close}"
        return (
            f"\\par{before_tex}\\noindent {body}{after_tex}{keep}"
        )

    # ------------------------------------------------------------------ #
    # Hybrid figure/table placement policy
    # ------------------------------------------------------------------ #
    # The policy scores DOCX-derived signals for each object and picks one of:
    #   inline_span   -> full-width, non-floating, exact position (cuted strip)
    #   inline_column -> in-column, non-floating, exact position (center)
    #   float_h       -> figure[H]/table[H]: pinned in place, in-column
    #   float_column  -> figure/table [htbp]: normal in-column float
    #   float_span    -> figure*/table* [tp]: full-width spanning float
    # It never globally forces [H] nor globally disables floats.

    def _native_aspect(self, relative_path: str):
        """height/width of the image *file* (how it renders under keepaspectratio),
        or None when it cannot be read."""
        try:
            media_dir = getattr(self, "_media_dir", None)
            if media_dir is None:
                return None
            path = media_dir.parent / relative_path
            if not path.exists():
                return None
            from PIL import Image
            with Image.open(path) as im:
                w, h = im.size
            return (h / w) if w else None
        except Exception:
            return None

    def _figure_aspect(self, content: dict):
        """Best available height/width ratio for a figure: the native image
        aspect (used by keepaspectratio) if known, else the Word extent's."""
        na = content.get("native_aspect")
        if na:
            return na
        w_in, h_in = content.get("width_in"), content.get("height_in")
        if w_in and h_in and w_in > 0:
            return h_in / w_in
        return None

    def _rendered_height_in(self, content: dict, is_table: bool,
                            full_width: bool, tw_in: float) -> float:
        """Estimate the object's typeset height (inches) at its placement width."""
        text_h = (tw_in or 6.9) * 1.4
        if is_table:
            rows = content.get("num_rows") or 4
            return min(rows * 0.24, text_h)  # ~0.24in per \small row
        target_w = tw_in if full_width else max((tw_in or 6.9) / 2.0 - 0.2, 1.0)
        aspect = self._figure_aspect(content)
        if aspect:
            return min(target_w * aspect, text_h)
        # Unknown dimensions (e.g. an embedded chart) render capped ~0.3\textheight.
        return 0.3 * text_h

    def _choose_placement(self, content: dict, is_table: bool):
        """Return (strategy, reason) for one figure/table from DOCX signals."""
        tw_in = content.get("text_width_in") or 6.9
        text_h = tw_in * 1.4
        caption = content.get("caption") or ""
        clen = len(caption)

        if is_table:
            wf = content.get("width_frac") or 0.0
            wide = wf >= 0.55
            word_float = False           # Word tables are block-level, in-flow
            width_note = f"table width {wf*100:.0f}% of text"
        else:
            w_in = content.get("width_in")
            if w_in and tw_in:
                wf = min(w_in / tw_in, 1.0)
                wide = wf >= 0.55
            else:
                wf = 1.0 if content.get("full_width", True) else 0.4
                wide = bool(content.get("full_width", True))
            word_float = content.get("word_inline", True) is False
            width_note = f"image {wf*100:.0f}% of text width"

        rh_col = self._rendered_height_in(content, is_table, False, tw_in)
        tall_col = rh_col > 0.85 * text_h        # too tall even for a column
        long_cap = clen > 220

        if wide:
            # Height the object would take if typeset at the FULL text width.
            if is_table:
                rh_full = self._rendered_height_in(content, True, True, tw_in)
                span_overflow = rh_full > 0.75 * text_h   # would not fit the page
            else:
                aspect = self._figure_aspect(content)   # native (rendered) aspect
                if aspect:
                    rh_full = tw_in * aspect
                    aspect_tall = aspect > 0.5          # taller than a short banner
                else:
                    rh_full = text_h            # unknown aspect -> assume it may be tall
                    aspect_tall = True
                span_overflow = aspect_tall or rh_full > 0.45 * text_h

            if word_float:
                return ("float_span",
                        f"wide ({width_note}) and floating in Word -> full-width "
                        f"spanning float (figure*/table*) reproduces Word's own float "
                        f"and lets LaTeX place it at a page slot near the reference")
            if is_table:
                if span_overflow:
                    return ("float_span",
                            f"wide table ({width_note}) that is tall (~{rh_full:.1f}in) "
                            f"-> spanning float so it is not forced to overflow a page")
                return ("inline_span",
                        f"wide table ({width_note}), short (~{rh_full:.1f}in) -> inline "
                        f"spanning both columns to hold its exact reading-order position")
            # Wide figure.
            if span_overflow:
                return ("float_h",
                        f"wide figure ({width_note}) but tall/near-square "
                        f"(~{rh_full:.1f}in at full width) -> pinned in place at column "
                        f"width ([H]) so it stays in order without overflowing the page")
            return ("inline_span",
                    f"wide figure ({width_note}), short banner shape "
                    f"(~{rh_full:.1f}in) -> inline spanning both columns, exact position")
        # Narrow: fits within one column.
        if word_float:
            return ("float_column",
                    f"narrow ({width_note}) and floating in Word -> normal single-"
                    f"column float mirrors Word and lets LaTeX optimise the page")
        if tall_col:
            return ("float_column",
                    f"narrow ({width_note}) but tall (~{rh_col:.1f}in, page-break risk) "
                    f"-> normal float avoids overflowing the column")
        return ("float_h",
                f"narrow ({width_note}), Word-inline, short (~{rh_col:.1f}in) -> pinned "
                f"in place with [H] so it stays exactly where introduced")

    def _emit_placed(self, inner_tex: str, caption: str, label_str: str,
                     kind: str, strategy: str) -> str:
        """Render one object according to the chosen placement strategy."""
        if strategy in ("inline_span", "inline_column"):
            caption_tex = f"\\captionof{{{kind}}}{{{caption}}}" if caption else ""
            parts = [inner_tex]
            if caption_tex:
                parts.append(caption_tex)
            if label_str:
                parts.append(label_str)
            # Keep object + caption as one unbreakable unit (never detaches).
            unit = (
                "\\noindent\\begin{minipage}{\\linewidth}\n\\centering\n"
                + "\n".join(parts) + "\n\\end{minipage}"
            )
            if strategy == "inline_span":
                return "\\begin{strip}\n\\centering\n" + unit + "\n\\end{strip}"
            return "\\begin{center}\n" + unit + "\n\\end{center}"

        env, place = {
            "float_h": (kind, "[H]"),
            "float_column": (kind, "[htbp]"),
            "float_span": (kind + "*", "[tp]"),
        }[strategy]
        cap = f"\\caption{{{caption}}}\n" if caption else ""
        lab = f"{label_str}\n" if label_str else ""
        return (
            f"\\begin{{{env}}}{place}\n\\centering\n{inner_tex}\n{cap}{lab}"
            f"\\end{{{env}}}"
        )

    def _place_object(self, inner_tex: str, caption: str, label_str: str,
                      kind: str, content: dict) -> str:
        """Choose a placement strategy for this object and render it, logging
        the decision + reason for the placement report."""
        strategy, reason = self._choose_placement(content, is_table=(kind == "table"))
        log = getattr(self, "_placement_log", None)
        if log is not None:
            log.append({
                "kind": kind,
                "caption": (caption or "")[:60],
                "strategy": strategy,
                "reason": reason,
            })
        return self._emit_placed(inner_tex, caption, label_str, kind, strategy)

    def _render_block(self, block: DocumentBlock, job_id: str) -> Optional[str]:
        """Render a single DocumentBlock into a LaTeX string."""
        b_type = block.type
        content = block.content

        if b_type == BlockType.PARAGRAPH:
            return self._escape_text(content.get("text", ""))

        elif b_type == BlockType.FIGURE:
            caption = self._escape_text(content.get("caption", ""))
            original_path = content.get("path", "")
            # WMF/EMF/SVG are converted to PNG during asset extraction;
            # reference the LaTeX-compatible sibling.
            image_name = latex_safe_image_name(original_path)
            relative_path = f"media/{image_name}"
            
            label_str = f"\\label{{{content.get('label')}}}" if content.get("label") else ""

            # Reproduce the original Word size exactly.  Width and height come
            # straight from the DOCX drawing extent (inches).  When the picture
            # is narrower than the text block it keeps both dimensions verbatim
            # (so small figures are NOT blown up to full width); when it is
            # wider it is scaled down to the line width preserving aspect ratio.
            width_in = content.get("width_in") or content.get("width_pt")
            height_in = content.get("height_in")
            if content.get("width_in") and height_in:
                w = content["width_in"]
                include = (
                    f"\\ifdim {w:.4f}in>\\linewidth\n"
                    f"  \\includegraphics[width=\\linewidth,keepaspectratio]{{{relative_path}}}\n"
                    f"\\else\n"
                    f"  \\includegraphics[width={w:.4f}in,height={height_in:.4f}in]{{{relative_path}}}\n"
                    f"\\fi"
                )
            elif content.get("width_in"):
                w = content["width_in"]
                include = (
                    f"\\includegraphics[width=\\ifdim {w:.4f}in>\\linewidth \\linewidth"
                    f"\\else {w:.4f}in\\fi,keepaspectratio]{{{relative_path}}}"
                )
            else:
                include = (
                    f"\\includegraphics[width=\\linewidth,height=0.3\\textheight,"
                    f"keepaspectratio]{{{relative_path}}}"
                )
            # A wide image is scaled to the line width with keepaspectratio, so
            # its true height follows the image file's *native* aspect (which can
            # differ from the possibly-distorted Word extent).  Record it so the
            # policy estimates the real rendered height.
            content = dict(content)
            content["native_aspect"] = self._native_aspect(relative_path)
            # Hybrid placement policy chooses inline / [H] / normal float /
            # spanning float per figure from its DOCX signals (Word inline vs
            # floating, size, height, caption length, two-column fit).
            return self._place_object(include, caption, label_str, "figure", content)

        elif b_type == BlockType.TABLE:
            if content.get("body_rows") or content.get("header_rows"):
                return self._render_structured_table(content)
            return self._render_flat_table(content)

        elif b_type == BlockType.EQUATION:
            latex_code = content.get("latex_code", "")
            label_str = f"\\label{{{content.get('label')}}}" if content.get("label") else ""
            # Mathematical syntax is left completely raw
            return (
                "\\begin{equation}\n"
                f"{latex_code}\n"
                f"{label_str}\n"
                "\\end{equation}"
            )

        elif b_type == BlockType.LIST:
            items = content.get("items", [])
            ordered = content.get("ordered", False)
            env = "enumerate" if ordered else "itemize"

            items_str = "\n".join(f"  \\item {self._escape_text(item)}" for item in items)
            return (
                f"\\begin{{{env}}}\n"
                f"{items_str}\n"
                f"\\end{{{env}}}"
            )

        return None

    def _render_flat_table(self, content: dict) -> str:
        """Legacy fallback for tables without structural information."""
        caption = self._escape_text(content.get("caption", ""))
        headers = content.get("headers", [])
        rows = content.get("rows", [])
        label_str = f"\\label{{{content.get('label')}}}" if content.get("label") else ""
        num_cols = len(headers) if headers else (len(rows[0]) if rows else 1)
        col_specs = "c" * num_cols
        headers_str = ""
        if headers:
            headers_str = " & ".join(self._escape_text(h) for h in headers) + " \\\\\n\\hline"
        rows_str = "\n".join(
            " & ".join(self._escape_text(cell) for cell in row) + " \\\\" for row in rows
        )
        inner = (
            "\\resizebox{\\linewidth}{!}{%\n"
            f"\\begin{{tabular}}{{{col_specs}}}\n\\hline\n"
            f"{headers_str}\n{rows_str}\n\\hline\n"
            "\\end{tabular}%\n}"
        )
        return self._place_object(inner, caption, label_str, "table", content)

    def _render_structured_table(self, content: dict) -> str:
        """Render a table preserving merges, widths, alignment, borders,
        shading and bold header cells."""
        caption = self._escape_text(content.get("caption", ""))
        label_str = f"\\label{{{content.get('label')}}}" if content.get("label") else ""
        colspecs = content.get("colspecs", [])
        header_rows = content.get("header_rows", [])
        body_rows = content.get("body_rows", [])
        has_grid = bool(content.get("has_grid"))
        shading_rows = content.get("shading_rows", [])
        row_heights = [h for h in content.get("row_heights", []) if h]
        # Table width as a fraction of the text column, taken from the DOCX so
        # the rendered table occupies the same on-page proportion as in Word.
        width_frac = content.get("width_frac")

        all_rows = header_rows + body_rows
        num_cols = len(colspecs) or max(
            (sum(c.get("colspan", 1) for c in row) for row in all_rows), default=1
        )

        # Column specification.  When the Word table width and per-column
        # widths are known, each column becomes a p{} box whose width is its
        # share of (width_frac * \textwidth).  The exact per-column padding
        # (2*\tabcolsep) is subtracted inside \dimexpr so the assembled table
        # -- content + padding + rules -- matches the Word width instead of
        # being squeezed to a narrow block.  Falls back to the previous
        # relative sizing when the width metadata is unavailable.
        sep = "|" if has_grid else ""
        have_widths = width_frac and all(
            (colspecs[i].get("width") if i < len(colspecs) else None)
            for i in range(num_cols)
        )
        parts = []
        for i in range(num_cols):
            spec = colspecs[i] if i < len(colspecs) else {}
            width = spec.get("width")
            align = spec.get("align")
            if have_widths:
                eff = width * width_frac
                prefix = {
                    "c": ">{\\centering\\arraybackslash}",
                    "r": ">{\\raggedleft\\arraybackslash}",
                }.get(align, "")
                parts.append(f"{prefix}p{{\\dimexpr {eff:.4f}\\textwidth-2\\tabcolsep\\relax}}")
            elif width:
                parts.append(f"p{{{width * 0.9:.3f}\\linewidth}}")
            else:
                parts.append(align or "l")
        col_spec_str = sep + sep.join(parts) + sep

        # Optional row-height stretch (Word trHeight is in points).
        stretch = ""
        if row_heights:
            avg = sum(row_heights) / len(row_heights)
            factor = max(1.0, min(2.0, avg / 14.0))
            if factor > 1.05:
                stretch = f"\\renewcommand{{\\arraystretch}}{{{factor:.2f}}}"

        # pending[k]: how many rows below the current one column k is still
        # covered by an open rowspan.
        pending = [0] * num_cols
        lines = []
        if has_grid:
            lines.append("\\hline")
        n_header = len(header_rows)

        for r_idx, row in enumerate(all_rows):
            fills = shading_rows[r_idx] if r_idx < len(shading_rows) else []
            consumed = [False] * num_cols
            cells_out = []
            col = 0
            for cell in row:
                # Skip columns occupied by rowspans from earlier rows.
                while col < num_cols and pending[col] > 0 and not consumed[col]:
                    cells_out.append("")
                    consumed[col] = True
                    col += 1
                if col >= num_cols:
                    break
                text = self._escape_text(cell.get("text", ""))
                if text and (cell.get("bold") or r_idx < n_header):
                    text = f"\\textbf{{{text}}}"
                fill = fills[col] if col < len(fills) else None
                if fill:
                    text = f"\\cellcolor[HTML]{{{fill}}}{text}"
                colspan = max(1, cell.get("colspan", 1))
                rowspan = max(1, cell.get("rowspan", 1))
                if rowspan > 1:
                    text = f"\\multirow{{{rowspan}}}{{*}}{{{text}}}"
                    for k in range(col, min(col + colspan, num_cols)):
                        pending[k] = rowspan - 1
                if colspan > 1:
                    mc_align = cell.get("align") or "c"
                    mc_spec = ("|" if has_grid and col == 0 else "") + mc_align + ("|" if has_grid else "")
                    text = f"\\multicolumn{{{colspan}}}{{{mc_spec}}}{{{text}}}"
                cells_out.append(text)
                col += colspan
            # Trailing columns covered by open rowspans.
            while col < num_cols:
                cells_out.append("")
                if pending[col] > 0:
                    consumed[col] = True
                col += 1
            lines.append(" & ".join(cells_out) + " \\\\")

            # A span consumed on this row expires at this boundary.
            for k in range(num_cols):
                if consumed[k] and pending[k] > 0:
                    pending[k] -= 1

            open_cols = [k for k in range(num_cols) if pending[k] > 0]
            if has_grid or r_idx == n_header - 1 or r_idx == len(all_rows) - 1:
                if not open_cols:
                    lines.append("\\hline")
                else:
                    segments = []
                    start_seg = None
                    for k in range(num_cols):
                        if pending[k] == 0:
                            if start_seg is None:
                                start_seg = k
                        elif start_seg is not None:
                            segments.append((start_seg + 1, k))
                            start_seg = None
                    if start_seg is not None:
                        segments.append((start_seg + 1, num_cols))
                    for a, b in segments:
                        lines.append(f"\\cline{{{a}-{b}}}")

        table_body = "\n".join(lines)
        # Place the table inline in the document flow (no floating), so it keeps
        # the exact DOCX reading order and its caption stays attached.  A table
        # wider than about half the text width spans both columns (strip);
        # a narrower one stays inside the current column.
        inner = (
            f"{{{stretch}\\small\n"
            f"\\begin{{tabular}}{{{col_spec_str}}}\n"
            f"{table_body}\n"
            "\\end{tabular}}"
        )
        return self._place_object(inner, caption, label_str, "table", content)

    def _escape_text(self, text: str) -> str:
        """Escape standard text but preserve inline math ($...$) spans."""
        return escape_latex_keep_math(text)


