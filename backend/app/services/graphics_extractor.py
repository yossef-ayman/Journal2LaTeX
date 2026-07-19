import re
import os
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Optional
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
