import re
import os
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.utils.logger import get_job_logger

class GraphicsExtractor:
    """Service to extract and render complex graphics, DrawingML, VML, SmartArt, and Charts from DOCX files."""

    def extract_graphics(self, docx_path: Path, output_dir: Path, job_id: str) -> Dict[str, Any]:
        logger = get_job_logger(job_id, "graphics_extractor")
        logger.info("Starting advanced graphics extraction for job: %s", job_id)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "total_graphics_detected": 0,
            "total_graphics_rendered": 0,
            "missing_graphics": 0,
            "render_methods": {},
            "bounding_boxes": [],
            "unsupported_objects": []
        }
        
        try:
            with zipfile.ZipFile(docx_path) as zf:
                file_list = zf.namelist()
                
                # Check for document.xml
                if "word/document.xml" not in file_list:
                    logger.error("word/document.xml missing in zip.")
                    return report
                    
                doc_xml = zf.read("word/document.xml")
                root = ET.fromstring(doc_xml)
                
                # Namespace definitions
                namespaces = {
                    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
                    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
                    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
                    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
                    "v": "urn:schemas-microsoft-com:vml"
                }
                
                # Find all drawing elements
                drawings = root.findall(".//w:drawing", namespaces)
                picts = root.findall(".//w:pict", namespaces)
                
                report["total_graphics_detected"] = len(drawings) + len(picts)
                logger.info("Detected %d drawings and %d pict elements", len(drawings), len(picts))
                
                # Process Drawings
                for idx, drawing in enumerate(drawings):
                    obj_id = f"drawing_{idx+1}"
                    # Default analysis
                    obj_type = "DrawingML"
                    width = "100"
                    height = "100"
                    
                    # Try to extract dimensions from wp:extent
                    extent = drawing.find(".//wp:extent", namespaces)
                    if extent is not None:
                        width = extent.attrib.get("cx", "100")
                        height = extent.attrib.get("cy", "100")
                        
                    # Extract layout / inline vs anchor
                    is_anchor = drawing.find(".//wp:anchor", namespaces) is not None
                    layout = "anchor" if is_anchor else "inline"
                    
                    # Check for SmartArt, Chart or Picture inside
                    graphic = drawing.find(".//a:graphic", namespaces)
                    render_method = "PNG"
                    
                    if graphic is not None:
                        graphic_data = graphic.find(".//a:graphicData", namespaces)
                        if graphic_data is not None:
                            uri = graphic_data.attrib.get("uri", "")
                            if "chart" in uri:
                                obj_type = "Chart"
                                render_method = "SVG"
                            elif "diagram" in uri:
                                obj_type = "SmartArt"
                                render_method = "SVG"
                                
                    # If picture, extract the image file from media
                    pic = drawing.find(".//pic:pic", namespaces)
                    if pic is not None:
                        obj_type = "Picture"
                        render_method = "PNG"
                        # Try to copy corresponding image from word/media if exists
                        blip = pic.find(".//a:blip", namespaces)
                        if blip is not None:
                            embed_id = blip.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed", "")
                            # Map embed ID to media path via document.xml.rels
                            media_name = self._resolve_rel(zf, embed_id, logger)
                            if media_name:
                                src_path = f"word/media/{media_name}"
                                if src_path in file_list:
                                    dest_path = output_dir / media_name
                                    dest_path.write_bytes(zf.read(src_path))
                                    report["total_graphics_rendered"] += 1
                                    
                    # Record bounding box details
                    report["bounding_boxes"].append({
                        "id": obj_id,
                        "type": obj_type,
                        "width": width,
                        "height": height,
                        "layout": layout,
                        "render_method": render_method
                    })
                    report["render_methods"][render_method] = report["render_methods"].get(render_method, 0) + 1
                    
                # Process VML picts
                for idx, pict in enumerate(picts):
                    obj_id = f"vml_{idx+1}"
                    obj_type = "VML"
                    render_method = "TikZ"
                    
                    shape = pict.find(".//v:shape", namespaces)
                    if shape is not None:
                        style = shape.attrib.get("style", "")
                        # Try to parse bounding box from style
                        width_match = re.search(r'width:([\d\.]+\w+)', style)
                        height_match = re.search(r'height:([\d\.]+\w+)', style)
                        w_val = width_match.group(1) if width_match else "unknown"
                        h_val = height_match.group(1) if height_match else "unknown"
                        
                        imagedata = shape.find(".//v:imagedata", namespaces)
                        if imagedata is not None:
                            obj_type = "VML Image"
                            render_method = "PNG"
                            rel_id = imagedata.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id", "")
                            media_name = self._resolve_rel(zf, rel_id, logger)
                            if media_name:
                                src_path = f"word/media/{media_name}"
                                if src_path in file_list:
                                    dest_path = output_dir / media_name
                                    dest_path.write_bytes(zf.read(src_path))
                                    report["total_graphics_rendered"] += 1
                                    
                        report["bounding_boxes"].append({
                            "id": obj_id,
                            "type": obj_type,
                            "width": w_val,
                            "height": h_val,
                            "layout": "VML Inline",
                            "render_method": render_method
                        })
                        report["render_methods"][render_method] = report["render_methods"].get(render_method, 0) + 1
                        
            # Save report
            report_path = output_dir.parent / "graphics_report.json"
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            logger.info("Advanced graphics extraction completed successfully. Report saved to %s", report_path)
            
        except Exception as e:
            logger.exception("Failed to extract advanced graphics: %s", str(e))
            
        return report

    def _resolve_rel(self, zf: zipfile.ZipFile, rel_id: str, logger) -> Optional[str]:
        # Parse document.xml.rels to map Relationship ID to target filename
        try:
            if "word/_rels/document.xml.rels" in zf.namelist():
                rels_xml = zf.read("word/_rels/document.xml.rels")
                root = ET.fromstring(rels_xml)
                for rel in root.findall(".//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
                    if rel.attrib.get("Id") == rel_id:
                        target = rel.attrib.get("Target", "")
                        return Path(target).name
        except Exception as e:
            logger.error("Failed to parse relationships XML: %s", str(e))
        return None


# --------------------------------------------------------------------------- #
# Office-native object extraction (charts, SmartArt, shapes, groups, OLE)
# --------------------------------------------------------------------------- #

_OO_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "o": "urn:schemas-microsoft-com:office:office",
    "v": "urn:schemas-microsoft-com:vml",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "dgm": "http://schemas.openxmlformats.org/drawingml/2006/diagram",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
}
_EMU_PER_PT = 12700.0

# Register canonical prefixes so serialized mini-documents keep Word-friendly names.
for _prefix, _uri in _OO_NS.items():
    ET.register_namespace(_prefix, _uri)
ET.register_namespace("", "")


class OfficeObjectExtractor:
    """Extract every Office-native visual object from a DOCX individually.

    Detection covers Word/Excel charts, SmartArt diagrams, DrawingML shapes,
    text boxes, grouped objects, OLE embedded graphics, and VML drawings.
    Plain raster/vector pictures (PNG/JPEG/SVG/WMF/EMF) are handled by the
    ordinary media path; this class targets the objects that only Office
    applications can render.

    Rendering isolates each object into a minimal single-paragraph DOCX that
    keeps the original package's parts and relationships (so chart XML, styles
    and embedded workbooks resolve), converts that document alone with
    LibreOffice headless, and crops the result to the object's bounding box --
    the page as a whole is never used as the figure.
    """

    def __init__(self) -> None:
        from app.utils.logger import get_job_logger  # local import: avoid cycles
        self._get_logger = get_job_logger

    # -- public API ------------------------------------------------------ #

    def extract_objects(self, docx_path: Path, media_dir: Path, job_id: str) -> List[Dict[str, Any]]:
        """Detect and render all Office-native objects.

        Returns a list of dicts:
        ``{"file", "type", "width_pt", "height_pt", "anchor_text", "caption",
        "label", "paragraph_index"}`` in document order.  Never raises;
        failures are logged and reported per object.
        """
        logger = self._get_logger(job_id, "graphics_extractor")
        media_dir.mkdir(parents=True, exist_ok=True)
        objects: List[Dict[str, Any]] = []

        try:
            with zipfile.ZipFile(docx_path) as zf:
                package = {n: zf.read(n) for n in zf.namelist()}
        except (OSError, zipfile.BadZipFile) as exc:
            logger.error("Cannot open DOCX for object extraction: %s", exc)
            return objects

        if "word/document.xml" not in package:
            return objects
        try:
            root = ET.fromstring(package["word/document.xml"])
        except ET.ParseError as exc:
            logger.error("document.xml parse error: %s", exc)
            return objects

        body = root.find("w:body", _OO_NS)
        if body is None:
            return objects
        paragraphs = body.findall("w:p", _OO_NS)
        sect_pr = body.find("w:sectPr", _OO_NS)

        # 1. Detect objects paragraph by paragraph, in document order.
        detections = []
        for p_idx, para in enumerate(paragraphs):
            for kind, extent in self._detect_native_objects(para):
                # Decorative separators (hairline-height rule shapes) are part
                # of the header/body styling, not figures -- skip them.
                if extent is not None and (
                    extent[0] / _EMU_PER_PT < 3 or extent[1] / _EMU_PER_PT < 3
                ):
                    continue
                detections.append({
                    "paragraph_index": p_idx,
                    "type": kind,
                    "width_pt": round(extent[0] / _EMU_PER_PT, 2) if extent else None,
                    "height_pt": round(extent[1] / _EMU_PER_PT, 2) if extent else None,
                    "para": para,
                    "anchor_text": self._nearest_text(paragraphs, p_idx, direction=-1),
                    "caption": self._caption_text(paragraphs, p_idx),
                })
        if not detections:
            logger.info("No Office-native objects detected.")
            return objects
        logger.info("Detected %d Office-native objects: %s",
                    len(detections), [d["type"] for d in detections])

        # 2. Build one isolated mini-DOCX per object.
        import tempfile
        with tempfile.TemporaryDirectory(prefix="j2l_officeobj_") as tmp:
            tmp_dir = Path(tmp)
            mini_paths = []
            for i, det in enumerate(detections, 1):
                mini = tmp_dir / f"office_obj_{i}.docx"
                try:
                    self._write_isolated_docx(package, det["para"], sect_pr, mini)
                    mini_paths.append((mini, det, i))
                except Exception as exc:
                    logger.warning("Failed to isolate object %d (%s): %s", i, det["type"], exc)

            # 3. Render all isolated documents in one LibreOffice batch.
            rendered = self._render_batch(tmp_dir, [m for m, _, _ in mini_paths], logger)

            # 4. Rasterize each object PDF to a cropped, lossless PNG.
            for mini, det, i in mini_paths:
                pdf = rendered.get(mini.stem)
                out_png = media_dir / f"office_obj_{i}.png"
                ok = pdf is not None and self._pdf_to_cropped_png(pdf, out_png, logger)
                entry = {
                    "file": f"media/{out_png.name}" if ok else None,
                    "type": det["type"],
                    "width_pt": det["width_pt"],
                    "height_pt": det["height_pt"],
                    "anchor_text": det["anchor_text"],
                    "caption": det["caption"],
                    "label": f"fig:office{i}",
                    "paragraph_index": det["paragraph_index"],
                    "rendered": bool(ok),
                }
                objects.append(entry)
                if not ok:
                    logger.warning("Object %d (%s) could not be rendered.", i, det["type"])

        logger.info("Office object extraction: %d/%d rendered.",
                    sum(1 for o in objects if o["rendered"]), len(objects))
        return objects

    # -- detection ------------------------------------------------------- #

    def _detect_native_objects(self, para):
        """Yield (type, (cx, cy)|None) for each Office-native object in a paragraph."""
        results = []
        seen_fallback = self._fallback_elements(para)

        for drawing in para.findall(".//w:drawing", _OO_NS):
            if id(drawing) in seen_fallback:
                continue  # mc:Fallback duplicates the mc:Choice content
            extent = None
            ext_el = drawing.find(".//wp:extent", _OO_NS)
            if ext_el is not None:
                try:
                    extent = (int(ext_el.get("cx", 0)), int(ext_el.get("cy", 0)))
                except ValueError:
                    extent = None
            gd = drawing.find(".//a:graphicData", _OO_NS)
            uri = gd.get("uri", "") if gd is not None else ""
            if "chart" in uri:
                results.append(("chart", extent))
            elif "diagram" in uri:
                results.append(("smartart", extent))
            elif "wordprocessingGroup" in uri:
                results.append(("group", extent))
            elif "wordprocessingShape" in uri:
                wsp = drawing.find(".//wps:wsp", _OO_NS)
                has_text = wsp is not None and wsp.find(".//w:txbxContent", _OO_NS) is not None
                geom = wsp.find(".//a:prstGeom", _OO_NS) if wsp is not None else None
                is_plain_box = geom is not None and geom.get("prst") == "rect"
                results.append(("textbox" if has_text and is_plain_box else "shape", extent))
            # pictures (pic:pic) are handled by the ordinary media path

        # OLE embedded graphics (w:object)
        for obj in para.findall(".//w:object", _OO_NS):
            if id(obj) in seen_fallback:
                continue
            results.append(("ole", None))

        # VML drawings that are not simple images (no imagedata)
        for pict in para.findall(".//w:pict", _OO_NS):
            if id(pict) in seen_fallback:
                continue
            if pict.find(".//v:imagedata", _OO_NS) is None:
                results.append(("vml-shape", None))
        return results

    @staticmethod
    def _fallback_elements(para):
        """ids of all elements under mc:Fallback (to skip duplicated content)."""
        ids = set()
        for fb in para.findall(".//mc:Fallback", _OO_NS):
            for el in fb.iter():
                ids.add(id(el))
        return ids

    def _nearest_text(self, paragraphs, idx, direction):
        """Nearest non-empty, non-caption paragraph text before/after idx."""
        j = idx + direction
        while 0 <= j < len(paragraphs):
            text = self._para_text(paragraphs[j])
            if text and not re.match(r"^(figure|fig\.?|table)\s*\d", text, re.IGNORECASE):
                return text[:120]
            j += direction
        return ""

    def _caption_text(self, paragraphs, idx):
        """Caption paragraph directly following the object, if any."""
        for j in (idx + 1, idx + 2):
            if j < len(paragraphs):
                text = self._para_text(paragraphs[j])
                if not text:
                    continue
                style = paragraphs[j].find(".//w:pStyle", _OO_NS)
                styled = style is not None and "caption" in (style.get(
                    f"{{{_OO_NS['w']}}}val", "").lower())
                if styled or re.match(r"^(figure|fig\.?)\s*\d", text, re.IGNORECASE):
                    return text
                break
        return ""

    @staticmethod
    def _para_text(para):
        return " ".join(
            t.text for t in para.findall(".//w:t", _OO_NS) if t.text
        ).strip()

    # -- isolation & rendering ------------------------------------------- #

    @staticmethod
    def _write_isolated_docx(package, para, sect_pr, out_path):
        """Write a copy of the package whose body contains only *para*."""
        w = _OO_NS["w"]
        root = ET.Element(f"{{{w}}}document")
        body = ET.SubElement(root, f"{{{w}}}body")
        body.append(para)
        if sect_pr is not None:
            body.append(sect_pr)
        doc_xml = ET.tostring(root, xml_declaration=True, encoding="UTF-8")

        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for name, data in package.items():
                zout.writestr(name, doc_xml if name == "word/document.xml" else data)

    @staticmethod
    def _render_batch(tmp_dir, mini_paths, logger):
        """Convert isolated object documents to PDF.

        Native Office objects (charts, SmartArt, shapes) can only be rendered
        by an Office application.  LibreOffice headless is used when available
        (cross-platform, one batch call); otherwise Microsoft Word COM is used
        as a fallback so the objects still render on Windows hosts that have
        Word but not LibreOffice.  Returns {mini.stem: pdf_path} for successes.
        """
        import shutil as _shutil
        import subprocess as _subprocess
        from app.core.config import settings as _settings

        rendered = {}
        if not mini_paths:
            return rendered

        def collect():
            for p in mini_paths:
                pdf = p.with_suffix(".pdf")
                if pdf.exists() and p.stem not in rendered:
                    rendered[p.stem] = pdf

        # 1. Preferred backend: LibreOffice headless (single batch conversion).
        soffice = _shutil.which(_settings.SOFFICE_PATH) or _shutil.which("libreoffice")
        if soffice:
            try:
                result = _subprocess.run(
                    [soffice, "--headless", "--norestore", "--convert-to", "pdf",
                     "--outdir", str(tmp_dir)] + [str(p) for p in mini_paths],
                    capture_output=True, text=True, check=False,
                    timeout=_settings.COMPILE_TIMEOUT,
                )
                if result.returncode != 0:
                    logger.warning("LibreOffice object rendering rc=%d: %s",
                                   result.returncode, (result.stderr or "")[:300])
            except (OSError, _subprocess.SubprocessError) as exc:
                logger.warning("LibreOffice object rendering failed: %s", exc)
            collect()

        # 2. Fallback: Microsoft Word COM for any objects still un-rendered
        #    (e.g. Windows hosts without LibreOffice installed).
        pending = [p for p in mini_paths if p.stem not in rendered]
        if pending:
            if soffice:
                logger.warning("%d Office object(s) unrendered by LibreOffice; "
                               "trying Microsoft Word COM.", len(pending))
            else:
                logger.info("LibreOffice unavailable; rendering %d Office object(s) "
                            "via Microsoft Word COM.", len(pending))
            OfficeObjectExtractor._render_with_word_com(pending, logger)
            collect()

        still_missing = [p.stem for p in mini_paths if p.stem not in rendered]
        if still_missing:
            logger.warning("No Office backend could render: %s "
                           "(install LibreOffice or Microsoft Word).", still_missing)
        return rendered

    @staticmethod
    def _render_with_word_com(mini_paths, logger) -> None:
        """Convert each isolated object DOCX to a sibling PDF using Word COM.

        No-op (with a warning) on non-Windows hosts or when pywin32 / Word is
        unavailable.  Each document is opened read-only and exported as PDF
        (wdFormatPDF = 17); COM is initialised/uninitialised for the worker
        thread and Word is always quit in a finally block to avoid orphaned
        WINWORD.EXE processes.
        """
        import sys as _sys
        if _sys.platform != "win32":
            logger.info("Microsoft Word COM fallback is only available on Windows.")
            return
        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except ImportError:
            logger.warning("pywin32 not installed; cannot use Microsoft Word COM fallback.")
            return

        pythoncom.CoInitialize()
        word = None
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0
            for mini in mini_paths:
                doc = None
                try:
                    doc = word.Documents.Open(str(mini.resolve()), ReadOnly=True)
                    doc.SaveAs(str(mini.with_suffix(".pdf").resolve()), FileFormat=17)
                except Exception as exc:
                    logger.warning("Word COM failed to render %s: %s", mini.name, exc)
                finally:
                    if doc is not None:
                        try:
                            doc.Close(False)
                        except Exception:
                            pass
        except Exception as exc:
            logger.warning("Microsoft Word COM unavailable: %s", exc)
        finally:
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()

    @staticmethod
    def _pdf_to_cropped_png(pdf_path, out_png, logger, dpi=300):
        """Rasterize the object's page losslessly and crop to the object."""
        from app.utils import pdf_tools
        from app.utils.media_convert import _autocrop_png
        import tempfile
        try:
            with tempfile.TemporaryDirectory() as tmp:
                pages = pdf_tools.render_pdf_to_images(pdf_path, Path(tmp), dpi=dpi)
                if not pages:
                    return False
                # The isolated document holds a single object: page 1 only.
                import shutil as _shutil
                _shutil.move(str(pages[0]), str(out_png))  # move works across drives
            _autocrop_png(out_png, padding=8)
            return out_png.exists()
        except Exception as exc:
            logger.warning("Rasterizing %s failed: %s", pdf_path, exc)
            return False
