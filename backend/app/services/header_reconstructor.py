"""Publication header and footer reconstruction.

Extracts the real running header/footer content from the DOCX package (text runs
with alignment and fonts, header tables, and header images resolved through
the header relationship files) and reconstructs it in LaTeX with fancyhdr.

Templates whose document class already draws its own journal header (e.g.
NSP1.cls) are left untouched -- injecting a second fancyhdr style on top of a
class-managed header degrades fidelity instead of improving it.  The
extraction report is generated in every case.
"""

import json
import math
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.utils.imaging import rms_similarity
from app.utils.latex import escape_latex as _escape
from app.utils.logger import get_job_logger

_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "v": "urn:schemas-microsoft-com:vml",
}

_EMU_PER_PT = 12700.0
_TWIPS_PER_PT = 20.0

@dataclass
class HeaderParagraph:
    """One paragraph extracted from a DOCX header part."""

    text: str = ""
    alignment: str = "left"  # left | center | right | both
    font_family: Optional[str] = None
    font_size_pt: Optional[float] = None
    bold: bool = False
    italic: bool = False
    images: List[Dict[str, Any]] = field(default_factory=list)
    has_bottom_border: bool = False


class HeaderReconstructor:
    """Extract and rebuild the Word running header in LaTeX."""

    def reconstruct_header(
        self,
        docx_path: Path,
        workspace_dir: Path,
        intermediate_dir: Path,
        job_id: str,
        template_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract header structure from *docx_path* and inject LaTeX when appropriate.

        Args:
            docx_path: Uploaded DOCX file.
            workspace_dir: Rendering workspace containing main.tex.
            intermediate_dir: Job intermediate directory for reports.
            job_id: Job UUID for logging.
            template_metadata: Parsed template.json of the active template.

        Returns:
            The header report dictionary (also persisted as header_report.json).
        """
        logger = get_job_logger(job_id, "system")
        template_metadata = template_metadata or {}

        report: Dict[str, Any] = {
            "detected_header_structure": "none",
            "extracted_header_elements": [],
            "extracted_footer_elements": [],
            "header_images": [],
            "footer_images": [],
            "header_tables": [],
            "footer_tables": [],
            "alignment_information": {},
            "font_information": {},
            "page_geometry": {},
            "spacing": {},
            "injection_strategy": "none",
            "reconstruction_status": "Completed",
            "similarity_score_for_header_alone": None,
        }

        try:
            paragraphs, tables, footer_paragraphs, footer_tables, geometry = self._extract(
                docx_path, workspace_dir, report, logger
            )
        except Exception as exc:  # extraction must never abort the pipeline
            logger.exception("Header extraction failed: %s", exc)
            report["reconstruction_status"] = f"Extraction failed: {exc}"
            paragraphs, tables, footer_paragraphs, footer_tables, geometry = [], [], [], [], {}

        report["page_geometry"] = geometry
        report["extracted_header_elements"] = [p.text for p in paragraphs if p.text]
        report["extracted_footer_elements"] = [p.text for p in footer_paragraphs if p.text]
        report["header_tables"] = tables
        report["footer_tables"] = footer_tables
        report["alignment_information"] = {
            f"paragraph_{i + 1}": p.alignment for i, p in enumerate(paragraphs)
        }
        fonts = [
            {"family": p.font_family, "size_pt": p.font_size_pt, "bold": p.bold, "italic": p.italic}
            for p in paragraphs
            if p.font_family or p.font_size_pt
        ]
        report["font_information"] = fonts[0] if fonts else {}

        class_owns_header = self._class_provides_header(template_metadata)
        if class_owns_header:
            report["injection_strategy"] = "template-class-managed"
            logger.info("Template class draws its own header; skipping fancyhdr injection.")
        elif paragraphs or tables or footer_paragraphs or footer_tables:
            report["detected_header_structure"] = "fancyhdr reconstruction"
            report["injection_strategy"] = "fancyhdr"
            try:
                self._inject_latex_headers(
                    workspace_dir, paragraphs, tables,
                    footer_paragraphs, footer_tables, geometry, report,
                )
            except Exception as exc:
                logger.exception("Header LaTeX injection failed: %s", exc)
                report["reconstruction_status"] = f"Injection failed: {exc}"
        else:
            report["detected_header_structure"] = "no header content found"

        intermediate_dir.mkdir(parents=True, exist_ok=True)
        (intermediate_dir / "header_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        return report

    # ------------------------------------------------------------------ #
    # Extraction
    # ------------------------------------------------------------------ #

    def _extract(self, docx_path, workspace_dir, report, logger):
        geometry: Dict[str, Any] = {}
        with zipfile.ZipFile(docx_path) as zf:
            names = set(zf.namelist())
            geometry = self._extract_geometry(zf, names)
            paragraphs, tables = self._extract_parts(
                zf, names, "word/header", workspace_dir, report, "header_images"
            )
            footer_paragraphs, footer_tables = self._extract_parts(
                zf, names, "word/footer", workspace_dir, report, "footer_images"
            )
        return paragraphs, tables, footer_paragraphs, footer_tables, geometry

    def _extract_parts(self, zf, names, prefix, workspace_dir, report, image_bucket):
        """Parse all header or footer XML parts, de-duplicated across variants."""
        paragraphs: List[HeaderParagraph] = []
        tables: List[Dict[str, Any]] = []
        parts = sorted(n for n in names if n.startswith(prefix) and n.endswith(".xml"))
        for part in parts:
            rels = self._load_rels(zf, part, names)
            root = ET.fromstring(zf.read(part))
            for p_el in root.findall("w:p", _NS):
                para = self._parse_paragraph(p_el, zf, rels, names, workspace_dir, report, image_bucket)
                if para.text or para.images:
                    paragraphs.append(para)
            for tbl_el in root.findall("w:tbl", _NS):
                tbl = self._parse_table(tbl_el, zf, rels, names, workspace_dir, report, image_bucket)
                if tbl["rows"]:
                    tables.append(tbl)

        # De-duplicate identical parts (first-page vs default vs even-page).
        seen = set()
        unique = []
        for para in paragraphs:
            key = (para.text, tuple(img["file"] for img in para.images))
            if key not in seen:
                seen.add(key)
                unique.append(para)
        return unique, tables

    def _extract_geometry(self, zf, names):
        geometry = {}
        if "word/document.xml" not in names:
            return geometry
        try:
            doc_root = ET.fromstring(zf.read("word/document.xml"))
            sect = doc_root.find(".//w:sectPr", _NS)
            if sect is None:
                return geometry
            pg_sz = sect.find("w:pgSz", _NS)
            pg_mar = sect.find("w:pgMar", _NS)
            if pg_sz is not None:
                geometry["page_width_pt"] = self._twips_attr(pg_sz, "w")
                geometry["page_height_pt"] = self._twips_attr(pg_sz, "h")
            if pg_mar is not None:
                for k in ("top", "bottom", "left", "right", "header", "footer"):
                    geometry[f"margin_{k}_pt"] = self._twips_attr(pg_mar, k)
        except ET.ParseError:
            pass
        return geometry

    @staticmethod
    def _twips_attr(el, attr):
        raw = el.attrib.get(f"{{{_NS['w']}}}{attr}")
        if raw is None:
            return None
        try:
            return round(int(raw) / _TWIPS_PER_PT, 2)
        except ValueError:
            return None

    def _load_rels(self, zf, part_name, names):
        rels_name = f"word/_rels/{Path(part_name).name}.rels"
        mapping = {}
        if rels_name in names:
            try:
                root = ET.fromstring(zf.read(rels_name))
                for rel in root.findall("rel:Relationship", _NS):
                    mapping[rel.attrib.get("Id", "")] = rel.attrib.get("Target", "")
            except ET.ParseError:
                pass
        return mapping

    def _parse_paragraph(self, p_el, zf, rels, names, workspace_dir, report, image_bucket="header_images"):
        para = HeaderParagraph()

        ppr = p_el.find("w:pPr", _NS)
        if ppr is not None:
            jc = ppr.find("w:jc", _NS)
            if jc is not None:
                para.alignment = jc.attrib.get(f"{{{_NS['w']}}}val", "left")
            borders = ppr.find("w:pBdr", _NS)
            if borders is not None and borders.find("w:bottom", _NS) is not None:
                para.has_bottom_border = True

        texts = []
        for run in p_el.findall(".//w:r", _NS):
            rpr = run.find("w:rPr", _NS)
            if rpr is not None:
                fonts_el = rpr.find("w:rFonts", _NS)
                if fonts_el is not None and not para.font_family:
                    para.font_family = fonts_el.attrib.get(f"{{{_NS['w']}}}ascii")
                sz = rpr.find("w:sz", _NS)
                if sz is not None and not para.font_size_pt:
                    try:  # w:sz is half-points
                        para.font_size_pt = int(sz.attrib.get(f"{{{_NS['w']}}}val", "0")) / 2.0
                    except ValueError:
                        pass
                para.bold = para.bold or rpr.find("w:b", _NS) is not None
                para.italic = para.italic or rpr.find("w:i", _NS) is not None

            for t in run.findall("w:t", _NS):
                if t.text:
                    texts.append(t.text)

            for blip in run.findall(".//a:blip", _NS):
                embed = blip.attrib.get(f"{{{_NS['r']}}}embed", "")
                img = self._copy_header_image(zf, rels, names, embed, run, workspace_dir)
                if img:
                    para.images.append(img)
                    report[image_bucket].append(img)

            for imagedata in run.findall(".//v:imagedata", _NS):
                rel_id = imagedata.attrib.get(f"{{{_NS['r']}}}id", "")
                img = self._copy_header_image(zf, rels, names, rel_id, run, workspace_dir)
                if img:
                    para.images.append(img)
                    report[image_bucket].append(img)

        para.text = " ".join(" ".join(texts).split())
        return para

    def _copy_header_image(self, zf, rels, names, rel_id, run_el, workspace_dir):
        target = rels.get(rel_id)
        if not target:
            return None
        media_name = Path(target).name
        src = f"word/media/{media_name}"
        if src not in names:
            return None

        dest_dir = workspace_dir / "media"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / media_name
        if not dest.exists():
            dest.write_bytes(zf.read(src))

        width_pt = height_pt = None
        extent = run_el.find(".//wp:extent", _NS)
        if extent is not None:
            try:
                width_pt = round(int(extent.attrib.get("cx", 0)) / _EMU_PER_PT, 2)
                height_pt = round(int(extent.attrib.get("cy", 0)) / _EMU_PER_PT, 2)
            except ValueError:
                pass

        return {"file": f"media/{media_name}", "width_pt": width_pt, "height_pt": height_pt}

    def _parse_table(self, tbl_el, zf, rels, names, workspace_dir, report, image_bucket="header_images"):
        rows = []
        for tr in tbl_el.findall("w:tr", _NS):
            cells = []
            for tc in tr.findall("w:tc", _NS):
                cell_paras = [
                    self._parse_paragraph(p, zf, rels, names, workspace_dir, report, image_bucket)
                    for p in tc.findall("w:p", _NS)
                ]
                cells.append({
                    "text": " ".join(p.text for p in cell_paras if p.text),
                    "alignment": cell_paras[0].alignment if cell_paras else "left",
                    "images": [img for p in cell_paras for img in p.images],
                })
            if any(c["text"] or c["images"] for c in cells):
                rows.append(cells)
        return {"rows": rows}

    # ------------------------------------------------------------------ #
    # LaTeX injection
    # ------------------------------------------------------------------ #

    @staticmethod
    def _class_provides_header(template_metadata: Dict[str, Any]) -> bool:
        if template_metadata.get("class_provides_header") is not None:
            return bool(template_metadata["class_provides_header"])
        class_file = (template_metadata.get("class_file") or "").upper()
        name = (template_metadata.get("name") or template_metadata.get("template_id") or "").upper()
        return "NSP" in class_file or "JSAP" in name

    def _render_cell(self, cell: Dict[str, Any]) -> str:
        chunks = []
        for img in cell.get("images", []):
            height = img.get("height_pt")
            opts = f"height={height}pt" if height else "height=18pt"
            chunks.append(f"\\includegraphics[{opts},keepaspectratio]{{{img['file']}}}")
        if cell.get("text"):
            chunks.append(_escape(cell["text"]))
        return " ".join(chunks)

    def _render_paragraph(self, para: HeaderParagraph) -> str:
        body = self._render_cell({"images": para.images, "text": para.text})
        if not body:
            return ""
        if para.bold:
            body = f"\\textbf{{{body}}}"
        if para.italic:
            body = f"\\textit{{{body}}}"
        if para.font_size_pt:
            baseline = round(para.font_size_pt * 1.2, 1)
            body = f"{{\\fontsize{{{para.font_size_pt}}}{{{baseline}}}\\selectfont {body}}}"
        return body

    def _bucket_content(self, paragraphs, tables):
        """Group rendered paragraphs/tables into left/center/right buckets."""
        buckets = {"left": [], "center": [], "right": []}
        for para in paragraphs:
            rendered = self._render_paragraph(para)
            if not rendered:
                continue
            key = {"center": "center", "right": "right", "end": "right"}.get(para.alignment, "left")
            buckets[key].append(rendered)
        for tbl in tables:
            for row in tbl["rows"]:
                rendered_cells = [c for c in (self._render_cell(cell) for cell in row) if c]
                if not rendered_cells:
                    continue
                if len(rendered_cells) == 1:
                    buckets["center"].append(rendered_cells[0])
                else:
                    buckets["center"].append(" \\hfill ".join(rendered_cells))
        return buckets

    def _inject_latex_headers(self, workspace_dir, paragraphs, tables,
                              footer_paragraphs, footer_tables, geometry, report):
        main_tex_path = workspace_dir / "main.tex"
        if not main_tex_path.exists():
            report["reconstruction_status"] = "Skipped: main.tex not found"
            return

        content = main_tex_path.read_text(encoding="utf-8")
        begin_doc = "\\begin{document}"
        if begin_doc not in content or "% J2L-HEADER-BEGIN" in content:
            return

        rule = any(p.has_bottom_border for p in paragraphs)
        head = self._bucket_content(paragraphs, tables)
        foot = self._bucket_content(footer_paragraphs, footer_tables)

        header_heights = [img.get("height_pt") or 0 for img in report["header_images"]]
        base_height = max([14.0] + [h + 4 for h in header_heights])
        head_sep = geometry.get("margin_header_pt") or 12.0
        foot_skip = geometry.get("margin_footer_pt") or 30.0

        joined = {k: " \\\\ ".join(v) for k, v in head.items()}
        fjoined = {k: " \\\\ ".join(v) for k, v in foot.items()}

        lines = [
            "% J2L-HEADER-BEGIN (auto-generated; do not edit)",
            "\\usepackage{fancyhdr}",
            "\\usepackage{graphicx}",
            "\\pagestyle{fancy}",
            "\\fancyhf{}",
        ]
        for pos, key in (("L", "left"), ("C", "center")):
            if joined[key]:
                lines.append(f"\\fancyhead[{pos}]{{{joined[key]}}}")
        right_content = joined["right"] if joined["right"] else "\\thepage"
        lines.append(f"\\fancyhead[R]{{{right_content}}}")
        # Footer: reconstruct extracted content; page number defaults to the
        # footer center only when the header right slot already carries it.
        footer_has_content = any(fjoined.values())
        if footer_has_content:
            for pos, key in (("L", "left"), ("C", "center"), ("R", "right")):
                if fjoined[key]:
                    lines.append(f"\\fancyfoot[{pos}]{{{fjoined[key]}}}")
        lines += [
            f"\\renewcommand{{\\headrulewidth}}{{{'0.4pt' if rule else '0pt'}}}",
            "\\renewcommand{\\footrulewidth}{0pt}",
            f"\\setlength{{\\headheight}}{{{math.ceil(base_height)}pt}}",
            f"\\setlength{{\\headsep}}{{{head_sep}pt}}",
            f"\\setlength{{\\footskip}}{{{foot_skip}pt}}",
            "% J2L-HEADER-END",
            "",
        ]
        block = "\n".join(lines)
        content = content.replace(begin_doc, block + begin_doc, 1)
        main_tex_path.write_text(content, encoding="utf-8")

        report["spacing"] = {"headheight": f"{math.ceil(base_height)}pt", "headsep": f"{head_sep}pt"}

    # ------------------------------------------------------------------ #
    # Header similarity
    # ------------------------------------------------------------------ #

    def compare_headers(self, orig_page_img: Path, rend_page_img: Path) -> float:
        """RMS similarity of the top 15% strip of two rendered page images."""
        return rms_similarity(orig_page_img, rend_page_img, top_fraction=0.15)
