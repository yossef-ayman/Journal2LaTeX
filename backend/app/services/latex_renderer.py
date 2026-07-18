import os
import json
import shutil
from pathlib import Path
from typing import Optional
from app.models.document import DocumentBlock, DocumentModel, BlockType
from app.utils.logger import get_job_logger


class LatexRendererError(Exception):
    """Exception raised when LaTeX rendering operations fail."""
    pass


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

        template_tex_path = workspace_dir / "template.tex"
        if not template_tex_path.exists():
            msg = f"Base template.tex not found in workspace: {template_tex_path}"
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

            content_tex = "\n\n".join(rendered_blocks)

            # 2. Format Authors and Institutes
            author_strings = []
            affiliations = []
            for author in doc.authors:
                if author.affiliation:
                    if author.affiliation not in affiliations:
                        affiliations.append(author.affiliation)
                    idx = affiliations.index(author.affiliation) + 1
                    author_strings.append(f"{self._escape_text(author.name)}^{{{idx}}}")
                else:
                    author_strings.append(self._escape_text(author.name))
            
            authors_tex = " \\and ".join(author_strings) if author_strings else "Author name unspecified"
            
            institute_strings = []
            for idx, aff in enumerate(affiliations):
                institute_strings.append(f"$^{{{idx+1}}}$ {self._escape_text(aff)}")
            institutes_tex = " \\\\ ".join(institute_strings) if institute_strings else ""

            # 3. Read base template
            template_content = template_tex_path.read_text(encoding="utf-8")

            # 4. Format Bibliography
            bib_tex = ""
            if doc.references:
                bib_tex = "\\begin{thebibliography}{99}\n"
                for idx, ref in enumerate(doc.references):
                    ref_text = self._escape_text(ref.strip())
                    bib_tex += f"\\bibitem{{ref{idx+1}}}\n{ref_text}\n\n"
                bib_tex += "\\end{thebibliography}\n"

            # Load template.json if exists
            template_metadata = {}
            metadata_file = workspace_dir / "template.json"
            if metadata_file.exists():
                try:
                    template_metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

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
                        img_name = Path(bio.image_path).name
                        relative_path = f"media/{img_name}"
                        
                        if is_nsp:
                            biography_tex += (
                                f"\\begin{{biographyps}}{{file={relative_path}}}{{{b_name}}}\n"
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

            # 6. Perform template substitutions
            rendered_content = template_content
            rendered_content = rendered_content.replace("__TITLE__", self._escape_text(doc.title or "Untitled Document"))
            rendered_content = rendered_content.replace("__AUTHORS__", authors_tex)
            rendered_content = rendered_content.replace("__INSTITUTES__", institutes_tex)
            rendered_content = rendered_content.replace("__ABSTRACT__", self._escape_text(doc.abstract))
            rendered_content = rendered_content.replace("__KEYWORDS__", ", ".join(self._escape_text(k) for k in doc.keywords))
            rendered_content = rendered_content.replace("__CONTENT__", content_tex)

            # Metadata replacements
            vol = doc.volume if doc.volume and doc.volume.strip() else "11"
            iss = doc.issue if doc.issue and doc.issue.strip() else "3"
            yr = doc.year if doc.year and doc.year.strip() else "2022"
            
            rec = doc.received_date if doc.received_date and doc.received_date.strip() else "25 Nov. 2022"
            rev = doc.revised_date if doc.revised_date and doc.revised_date.strip() else "4 Jan. 2023"
            acc = doc.accepted_date if doc.accepted_date and doc.accepted_date.strip() else "15 Jan. 2023"
            pub = doc.published_date if doc.published_date and doc.published_date.strip() else "1 Mar. 2023"

            rendered_content = rendered_content.replace("__VOLUME__", vol)
            rendered_content = rendered_content.replace("__ISSUE__", iss)
            rendered_content = rendered_content.replace("__YEAR__", yr)
            rendered_content = rendered_content.replace("__RECEIVED_DATE__", rec)
            rendered_content = rendered_content.replace("__REVISED_DATE__", rev)
            rendered_content = rendered_content.replace("__ACCEPTED_DATE__", acc)
            rendered_content = rendered_content.replace("__PUBLISHED_DATE__", pub)

            # 5. Write to main.tex
            main_tex_path = workspace_dir / "main.tex"
            main_tex_path.write_text(rendered_content, encoding="utf-8")

            logger.info("LaTeX document main.tex rendered successfully.")
            return main_tex_path

        except Exception as e:
            msg = f"Failed to render LaTeX document: {str(e)}"
            logger.exception(msg)
            raise LatexRendererError(msg) from e

    def _render_block(self, block: DocumentBlock, job_id: str) -> Optional[str]:
        """Render a single DocumentBlock into a LaTeX string."""
        b_type = block.type
        content = block.content

        if b_type == BlockType.PARAGRAPH:
            return self._escape_text(content.get("text", ""))

        elif b_type == BlockType.FIGURE:
            caption = self._escape_text(content.get("caption", ""))
            original_path = content.get("path", "")
            image_name = Path(original_path).name
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
        """Escape standard text but preserve mathematical blocks ($...$)."""
        if not text:
            return ""

        # Split text by $ to identify inline math portions
        parts = text.split("$")
        escaped_parts = []

        chars_map = {
            '\\': r'\textbackslash{}',
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
        }

        for i, part in enumerate(parts):
            if i % 2 == 0:
                # Outside math blocks: escape LaTeX special characters
                escaped_part = ""
                for char in part:
                    escaped_part += chars_map.get(char, char)
                escaped_parts.append(escaped_part)
            else:
                # Inside math blocks: preserve mathematical syntax completely
                escaped_parts.append(f"${part}$")

        return "".join(escaped_parts)


