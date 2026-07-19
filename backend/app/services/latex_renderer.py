import json
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
            # 1. Render block elements sequentially
            rendered_blocks = []
            for section in doc.sections:
                # Add section header
                # We determine header style based on level
                if section.level == 1:
                    rendered_blocks.append(f"\\section{{{self._escape_text(section.title)}}}")
                elif section.level == 2:
                    rendered_blocks.append(f"\\subsection{{{self._escape_text(section.title)}}}")
                else:
                    rendered_blocks.append(f"\\subsubsection{{{self._escape_text(section.title)}}}")
                
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
                    ref_text = self._escape_text(ref.strip())
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
                
                corresponding_email = ""
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
                rendered_content = rendered_content.replace("__AUTHORS__", authors_tex)
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

            # 5. Write to main.tex
            main_tex_path = workspace_dir / "main.tex"
            main_tex_path.write_text(rendered_content, encoding="utf-8")

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
            return (
                "\\begin{figure}[htbp]\n"
                "\\centering\n"
                f"\\includegraphics[width=\\linewidth,height=0.3\\textheight,keepaspectratio]{{{relative_path}}}\n"
                f"\\caption{{{caption}}}\n"
                f"{label_str}\n"
                "\\end{figure}"
            )

        elif b_type == BlockType.TABLE:
            caption = self._escape_text(content.get("caption", ""))
            headers = content.get("headers", [])
            rows = content.get("rows", [])
            label_str = f"\\label{{{content.get('label')}}}" if content.get("label") else ""

            # Determine column alignment
            num_cols = len(headers) if headers else (len(rows[0]) if rows else 1)
            col_specs = "c" * num_cols

            # Format headers
            headers_str = ""
            if headers:
                headers_str = " & ".join(self._escape_text(h) for h in headers) + " \\\\\n\\hline"

            # Format rows
            rows_str = ""
            if rows:
                rows_str = "\n".join(" & ".join(self._escape_text(cell) for cell in row) + " \\\\" for row in rows)

            return (
                "\\begin{table}[htbp]\n"
                "\\centering\n"
                "\\resizebox{\\linewidth}{!}{%\n"
                f"\\begin{{tabular}}{{{col_specs}}}\n"
                "\\hline\n"
                f"{headers_str}\n"
                f"{rows_str}\n"
                "\\hline\n"
                "\\end{tabular}%\n"
                "}\n"
                f"\\caption{{{caption}}}\n"
                f"{label_str}\n"
                "\\end{table}"
            )

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

    def _escape_text(self, text: str) -> str:
        """Escape standard text but preserve inline math ($...$) spans."""
        return escape_latex_keep_math(text)


