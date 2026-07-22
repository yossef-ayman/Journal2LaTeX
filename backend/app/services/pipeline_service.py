import json
import shutil
import time
from pathlib import Path
from typing import Optional
from app.services.job_manager import JobManager
from app.services.pandoc_service import PandocService, PandocException
from app.services.document_analyzer import DocumentAnalyzer, DocumentAnalyzerError
from app.services.asset_analyzer import AssetAnalyzer
from app.services.template_manager import TemplateManager, TemplateManagerError
from app.services.latex_renderer import LatexRenderer, LatexRendererError
from app.services.fidelity_checker import FidelityChecker
from app.services.graphics_extractor import GraphicsExtractor, OfficeObjectExtractor
from app.services.visual_comparator import VisualComparator
from app.services.layout_optimizer import LayoutOptimizer
from app.services.header_reconstructor import HeaderReconstructor
from app.compiler.latex_compiler import LatexCompiler, LatexCompilerException
from app.models.job import JobMetadata, JobStatus
from app.models.document import DocumentModel
from app.utils.logger import get_job_logger
from app.utils.media_convert import convert_unsupported_media


class PipelineService:
    """Service responsible for orchestrating the E2E document conversion, templating, and compilation."""

    def __init__(self) -> None:
        self.job_manager = JobManager()
        self.pandoc_service = PandocService()
        self.document_analyzer = DocumentAnalyzer()
        self.asset_analyzer = AssetAnalyzer()
        self.template_manager = TemplateManager()
        self.latex_renderer = LatexRenderer()
        self.latex_compiler = LatexCompiler()
        self.fidelity_checker = FidelityChecker()
        self.graphics_extractor = GraphicsExtractor()
        self.office_object_extractor = OfficeObjectExtractor()
        self.visual_comparator = VisualComparator()
        self.layout_optimizer = LayoutOptimizer()
        self.header_reconstructor = HeaderReconstructor()

    def validate(self, job_id: str, docx_filename: str) -> bool:
        """Validate the input document."""
        logger = get_job_logger(job_id, "system")
        logger.info("Starting validation for job: %s", job_id)

        self.job_manager.set_status(job_id, JobStatus.VALIDATING)
        self.job_manager.update_progress(job_id, 10, "Validating input Word Document")

        job_dir = self.job_manager._get_job_dir(job_id)
        docx_path = job_dir / "input" / docx_filename

        is_valid = self.pandoc_service.validate_docx(docx_path)
        if not is_valid:
            error_msg = f"Document validation failed. Ensure the uploaded file is a valid DOCX: {docx_filename}"
            logger.error(error_msg)
            self.job_manager.add_error(job_id, error_msg)
            return False

        logger.info("Validation successful.")
        self.job_manager.update_progress(job_id, 20, "Input document validated successfully")
        return True

    def analyze(self, job_id: str, docx_filename: str) -> Optional[DocumentModel]:
        """Analyze the DOCX document and extract its structured model."""
        logger = get_job_logger(job_id, "system")
        logger.info("Starting document analysis for job: %s", job_id)

        self.job_manager.set_status(job_id, JobStatus.ANALYZING_DOCUMENT)
        self.job_manager.update_progress(job_id, 30, "Analyzing document structure and content blocks")

        job_dir = self.job_manager._get_job_dir(job_id)
        docx_path = job_dir / "input" / docx_filename
        intermediate_dir = job_dir / "intermediate"
        structure_json_path = intermediate_dir / "document_structure.json"

        try:
            # Parse document structure
            doc_model, report = self.document_analyzer.analyze_document(docx_path, job_id)
            
            # Save structure to JSON file
            intermediate_dir.mkdir(parents=True, exist_ok=True)
            structure_json_path.write_text(
                doc_model.model_dump_json(indent=2),
                encoding="utf-8"
            )

            # Save conversion report to JSON file
            report_path = intermediate_dir / "conversion_report.json"
            report_path.write_text(
                json.dumps(report, indent=2),
                encoding="utf-8"
            )

            logger.info("Document analysis completed. Saved structure to: %s, report to: %s", structure_json_path, report_path)
            self.job_manager.update_progress(job_id, 45, "Document structure extracted successfully")
            return doc_model

        except DocumentAnalyzerError as e:
            error_msg = f"Document analysis failed: {str(e)}"
            logger.error(error_msg)
            self.job_manager.add_error(job_id, error_msg)
            return None

    def extract_assets(self, job_id: str, docx_filename: str) -> bool:
        """Extract media/assets from the uploaded DOCX document."""
        logger = get_job_logger(job_id, "system")
        logger.info("Starting asset extraction for job: %s", job_id)

        self.job_manager.set_status(job_id, JobStatus.EXTRACTING_ASSETS)
        self.job_manager.update_progress(job_id, 50, "Extracting images and figure assets from document")

        job_dir = self.job_manager._get_job_dir(job_id)
        docx_path = job_dir / "input" / docx_filename
        media_dir = job_dir / "intermediate" / "media"

        try:
            self.pandoc_service.extract_media(docx_path, media_dir, job_id)
            self.graphics_extractor.extract_graphics(docx_path, media_dir, job_id)

            # Office-native objects (charts, SmartArt, shapes, text boxes,
            # groups, OLE) are invisible to pandoc: extract and render each one
            # individually, then splice them into the document model at their
            # original positions.
            office_objects = self.office_object_extractor.extract_objects(
                docx_path, media_dir, job_id
            )
            if office_objects:
                self._merge_office_objects(job_id, office_objects)

            # pdflatex cannot include WMF/EMF/SVG (Word often stores equations
            # and drawings as WMF) -- convert them to PNG siblings up front.
            conv_report = convert_unsupported_media(media_dir, job_id)
            if conv_report["failed"]:
                self.job_manager.add_warning(
                    job_id,
                    f"{len(conv_report['failed'])} vector media files could not be converted to PNG "
                    f"and may be missing from the output.",
                )

            logger.info("Assets extracted to: %s", media_dir)
            self.job_manager.update_progress(job_id, 60, "Document assets extracted successfully")
            return True
        except PandocException as e:
            error_msg = f"Asset extraction failed: {str(e)}"
            logger.error(error_msg)
            self.job_manager.add_error(job_id, error_msg)
            return False

    def _merge_office_objects(self, job_id: str, office_objects: list) -> None:
        """Insert rendered Office objects into the saved document model.

        Each object becomes a FIGURE block placed after the paragraph it
        followed in the source document (matched by anchor text), carrying its
        original size, caption, and a stable label.  The caption paragraph is
        removed from the body so it is not duplicated below the figure.
        """
        logger = get_job_logger(job_id, "system")
        doc_model = self.load_document_model(job_id)
        if not doc_model:
            logger.warning("Cannot merge Office objects: document model unavailable.")
            return

        from app.models.document import BlockType, DocumentBlock

        def norm(text):
            return " ".join((text or "").split()).lower()

        rendered_objects = [o for o in office_objects if o.get("rendered") and o.get("file")]
        report = self.job_manager._get_job_dir(job_id) / "intermediate" / "office_objects.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(office_objects, indent=2), encoding="utf-8")

        for obj in rendered_objects:
            # \caption prints "Figure N:" itself; strip the literal prefix
            # carried in the Word caption text to avoid "Figure 2: Figure 2:".
            import re as _re
            caption_text = _re.sub(
                r"^(figure|fig\.?)\s*\d+\s*[:.\-]?\s*", "",
                obj.get("caption") or "", flags=_re.IGNORECASE,
            )
            figure = DocumentBlock(
                type=BlockType.FIGURE,
                content={
                    "caption": caption_text,
                    "path": obj["file"],
                    "label": obj.get("label"),
                    "width_pt": obj.get("width_pt"),
                    "height_pt": obj.get("height_pt"),
                    "office_object_type": obj.get("type"),
                },
            )
            anchor = norm(obj.get("anchor_text"))[:60]
            placed = False
            for section in doc_model.sections:
                for idx, block in enumerate(section.blocks):
                    if block.type == BlockType.PARAGRAPH and anchor and \
                            norm(block.content.get("text", "")).startswith(anchor):
                        section.blocks.insert(idx + 1, figure)
                        placed = True
                        break
                if placed:
                    break
            if not placed:
                # Anchor text may be a section title rather than a paragraph.
                target = None
                for section in doc_model.sections:
                    if anchor and norm(section.title).startswith(anchor[:40]):
                        target = section
                        break
                (target or doc_model.sections[-1]).blocks.insert(0, figure) \
                    if doc_model.sections else None
                placed = bool(doc_model.sections)
            # Remove the caption paragraph so it is not shown twice.
            caption = norm(obj.get("caption"))
            if caption:
                for section in doc_model.sections:
                    section.blocks = [
                        b for b in section.blocks
                        if not (b.type == BlockType.PARAGRAPH
                                and norm(b.content.get("text", "")) == caption)
                    ]
            logger.info("Office object %s placed=%s", obj.get("label"), placed)

        structure_file = self.job_manager._get_job_dir(job_id) / "intermediate" / "document_structure.json"
        structure_file.write_text(doc_model.model_dump_json(indent=2), encoding="utf-8")

    def analyze_assets(self, job_id: str, doc_model: DocumentModel) -> bool:
        """Run classification on extracted assets and create traceability mappings."""
        logger = get_job_logger(job_id, "system")
        logger.info("Classifying extracted assets for job: %s", job_id)

        job_dir = self.job_manager._get_job_dir(job_id)
        try:
            self.asset_analyzer.analyze_assets(job_id, doc_model, job_dir)
            self.job_manager.update_progress(job_id, 65, "Extracted assets analyzed and mapped successfully")
            return True
        except Exception as e:
            error_msg = f"Asset analysis failed: {str(e)}"
            logger.error(error_msg)
            self.job_manager.add_error(job_id, error_msg)
            return False

    def load_template(self, job_id: str, template_id: str) -> bool:
        """Load selected template class/styles and prepare isolated workspace."""
        logger = get_job_logger(job_id, "system")
        logger.info("Loading template %s for job: %s", template_id, job_id)

        self.job_manager.set_status(job_id, JobStatus.LOADING_TEMPLATE)
        self.job_manager.update_progress(job_id, 70, f"Loading template styles: {template_id}")

        job_dir = self.job_manager._get_job_dir(job_id)
        rendered_dir = job_dir / "rendered"

        try:
            # 1. Prepare rendering workspace with template files
            self.template_manager.prepare_workspace(template_id, rendered_dir)
            
            # 2. Copy intermediate media files into rendering workspace under 'media/'
            intermediate_media = job_dir / "intermediate" / "media"
            if intermediate_media.exists() and intermediate_media.is_dir():
                dest_media = rendered_dir / "media"
                shutil.copytree(intermediate_media, dest_media, dirs_exist_ok=True)

            # Convert template-supplied vector graphics (EPS class logos etc.)
            # that the LaTeX toolchain cannot process on this host.
            convert_unsupported_media(rendered_dir, job_id)

            logger.info("Template loaded and workspace prepared at: %s", rendered_dir)
            self.job_manager.update_progress(job_id, 80, "Template workspace initialized")
            return True

        except TemplateManagerError as e:
            error_msg = f"Template loading failed: {str(e)}"
            logger.error(error_msg)
            self.job_manager.add_error(job_id, error_msg)
            return False

    def load_document_model(self, job_id: str) -> Optional[DocumentModel]:
        """Load the persisted DocumentModel from intermediate/document_structure.json."""
        structure_file = self.job_manager._get_job_dir(job_id) / "intermediate" / "document_structure.json"
        if not structure_file.exists():
            return None
        try:
            data = json.loads(structure_file.read_text(encoding="utf-8"))
            return DocumentModel(**data)
        except Exception as e:
            get_job_logger(job_id, "system").error("Failed to load document model: %s", e)
            return None

    def render_latex(self, job_id: str) -> Optional[Path]:
        """Render the extracted document structure model into main.tex inside the workspace."""
        logger = get_job_logger(job_id, "system")
        logger.info("Starting LaTeX rendering for job: %s", job_id)

        self.job_manager.set_status(job_id, JobStatus.RENDERING_LATEX)
        self.job_manager.update_progress(job_id, 85, "Rendering document content to LaTeX")

        job_dir = self.job_manager._get_job_dir(job_id)
        structure_file = job_dir / "intermediate" / "document_structure.json"
        rendered_dir = job_dir / "rendered"

        if not structure_file.exists():
            error_msg = "Document structure JSON not found. Run analysis stage first."
            logger.error(error_msg)
            self.job_manager.add_error(job_id, error_msg)
            return None

        try:
            # Load DocumentModel
            data = json.loads(structure_file.read_text(encoding="utf-8"))
            doc_model = DocumentModel(**data)

            # Render document to main.tex
            main_tex_path = self.latex_renderer.render_document(doc_model, rendered_dir, job_id)
            
            # Automatically extract and reconstruct publication headers
            try:
                metadata = self.job_manager.get_job(job_id)
                if metadata and metadata.paper_name:
                    docx_path = job_dir / "input" / metadata.paper_name
                    template_meta = {}
                    template_json = rendered_dir / "template.json"
                    if template_json.exists():
                        try:
                            template_meta = json.loads(template_json.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            template_meta = {}
                    self.header_reconstructor.reconstruct_header(
                        docx_path, rendered_dir, job_dir / "intermediate", job_id, template_meta
                    )
                else:
                    logger.warning("Skipping header reconstruction: job metadata unavailable.")
            except Exception as e:
                logger.error("Header reconstruction failed: %s", str(e))
                self.job_manager.add_warning(job_id, f"Header reconstruction failed: {e}")
                
            self.job_manager.update_progress(job_id, 90, "LaTeX document rendering completed")
            return main_tex_path

        except LatexRendererError as e:
            error_msg = f"LaTeX rendering failed: {str(e)}"
            logger.error(error_msg)
            self.job_manager.add_error(job_id, error_msg)
            return None

    def compile(self, job_id: str, quiet: bool = False) -> Optional[Path]:
        """Compile the rendered main.tex inside workspace into the final PDF.

        Args:
            job_id: The job UUID.
            quiet: When True (optimizer recompiles), do not rewrite job
                status/progress and record failures as warnings, not fatal
                errors.
        """
        logger = get_job_logger(job_id, "system")
        logger.info("Starting document compilation for job: %s", job_id)

        if not quiet:
            self.job_manager.set_status(job_id, JobStatus.COMPILING)
            self.job_manager.update_progress(job_id, 92, "Compiling LaTeX source to PDF")

        job_dir = self.job_manager._get_job_dir(job_id)
        tex_path = job_dir / "rendered" / "main.tex"
        output_dir = job_dir / "output"

        try:
            comp_res = self.latex_compiler.compile_tex(tex_path, output_dir, job_id)
            if not comp_res.success:
                return None

            # Update final metadata outcomes
            metadata = self.job_manager.get_job(job_id)
            if metadata:
                metadata.output_pdf = "output/paper.pdf"
                metadata.output_tex = "rendered/main.tex"
                metadata.compile_success = True
                self.job_manager._save_metadata(metadata)

            logger.info("Compilation completed successfully.")
            return comp_res.pdf_path

        except LatexCompilerException as e:
            error_msg = f"LaTeX compilation failed: {str(e)}"
            logger.error(error_msg)
            if quiet:
                self.job_manager.add_warning(job_id, error_msg)
            else:
                self.job_manager.add_error(job_id, error_msg)
            return None

    def check_fidelity(self, job_id: str, doc_model: DocumentModel) -> bool:
        """Run fidelity analysis comparing structural inputs against generated LaTeX results."""
        logger = get_job_logger(job_id, "system")
        logger.info("Running E2E publication fidelity checker for job: %s", job_id)

        job_dir = self.job_manager._get_job_dir(job_id)
        try:
            self.fidelity_checker.generate_fidelity_report(job_id, doc_model, job_dir)
            
            # Run layout optimization loop to iteratively refine visual layout match
            try:
                self.layout_optimizer.optimize_layout(self, job_id, doc_model, job_dir)
            except Exception as e:
                logger.error("Layout optimization failed: %s", str(e))
            
            # Transition job status only if no fatal error occurred meanwhile.
            metadata = self.job_manager.get_job(job_id)
            if metadata and metadata.status != JobStatus.FAILED:
                self.job_manager.set_status(job_id, JobStatus.COMPLETED)
                self.job_manager.update_progress(job_id, 100, "Pipeline process completed successfully")
            return True
        except Exception as e:
            error_msg = f"Fidelity checker execution failed: {str(e)}"
            logger.error(error_msg)
            self.job_manager.add_error(job_id, error_msg)
            return False

    def run_full_pipeline(self, job_id: str, docx_filename: str, template_id: str = "default") -> JobMetadata:
        """Run the full end-to-end conversion, rendering, and compilation pipeline.

        A stage-by-stage timing report is always written to
        ``intermediate/pipeline_timing.json``, including for failed runs.
        """
        timings = {}
        pipeline_started = time.monotonic()

        def timed(stage_name, fn, *args):
            started = time.monotonic()
            try:
                return fn(*args)
            finally:
                timings[stage_name] = round(time.monotonic() - started, 3)

        try:
            if not timed("validate", self.validate, job_id, docx_filename):
                return self.job_manager.get_job(job_id)

            doc_model = timed("analyze", self.analyze, job_id, docx_filename)
            if not doc_model:
                return self.job_manager.get_job(job_id)

            if not timed("extract_assets", self.extract_assets, job_id, docx_filename):
                return self.job_manager.get_job(job_id)

            if not timed("analyze_assets", self.analyze_assets, job_id, doc_model):
                return self.job_manager.get_job(job_id)

            if not timed("load_template", self.load_template, job_id, template_id):
                return self.job_manager.get_job(job_id)

            if not timed("render_latex", self.render_latex, job_id):
                return self.job_manager.get_job(job_id)

            if not timed("compile", self.compile, job_id):
                return self.job_manager.get_job(job_id)

            timed("fidelity_and_optimization", self.check_fidelity, job_id, doc_model)
            return self.job_manager.get_job(job_id)
        finally:
            timings["total"] = round(time.monotonic() - pipeline_started, 3)
            self._write_timing_report(job_id, timings)

    def _write_timing_report(self, job_id: str, timings: dict) -> None:
        """Persist per-stage timings; failures here must never mask pipeline results."""
        try:
            intermediate_dir = self.job_manager._get_job_dir(job_id) / "intermediate"
            intermediate_dir.mkdir(parents=True, exist_ok=True)
            (intermediate_dir / "pipeline_timing.json").write_text(
                json.dumps({"stage_seconds": timings}, indent=2), encoding="utf-8"
            )
        except OSError:
            get_job_logger(job_id, "system").warning("Failed to write pipeline timing report.")
