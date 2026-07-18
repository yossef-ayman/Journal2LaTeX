import json
import shutil
from pathlib import Path
from typing import Optional
from app.services.job_manager import JobManager
from app.services.pandoc_service import PandocService, PandocException
from app.services.document_analyzer import DocumentAnalyzer, DocumentAnalyzerError
from app.services.asset_analyzer import AssetAnalyzer
from app.services.template_manager import TemplateManager, TemplateManagerError
from app.services.latex_renderer import LatexRenderer, LatexRendererError
from app.services.fidelity_checker import FidelityChecker
from app.compiler.latex_compiler import LatexCompiler, LatexCompilerException
from app.models.job import JobMetadata, JobStatus
from app.models.document import DocumentModel
from app.utils.logger import get_job_logger


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
            logger.info("Assets extracted to: %s", media_dir)
            self.job_manager.update_progress(job_id, 60, "Document assets extracted successfully")
            return True
        except PandocException as e:
            error_msg = f"Asset extraction failed: {str(e)}"
            logger.error(error_msg)
            self.job_manager.add_error(job_id, error_msg)
            return False

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

    def load_template(self, job_id: str, template_name: str) -> bool:
        """Load selected template class/styles and prepare isolated workspace."""
        logger = get_job_logger(job_id, "system")
        logger.info("Loading template %s for job: %s", template_name, job_id)

        self.job_manager.set_status(job_id, JobStatus.LOADING_TEMPLATE)
        self.job_manager.update_progress(job_id, 70, f"Loading template styles: {template_name}")

        job_dir = self.job_manager._get_job_dir(job_id)
        rendered_dir = job_dir / "rendered"

        try:
            # 1. Prepare rendering workspace with template files
            self.template_manager.prepare_workspace(template_name, rendered_dir)
            
            # 2. Copy intermediate media files into rendering workspace under 'media/'
            intermediate_media = job_dir / "intermediate" / "media"
            if intermediate_media.exists() and intermediate_media.is_dir():
                dest_media = rendered_dir / "media"
                shutil.copytree(intermediate_media, dest_media, dirs_exist_ok=True)

            logger.info("Template loaded and workspace prepared at: %s", rendered_dir)
            self.job_manager.update_progress(job_id, 80, "Template workspace initialized")
            return True

        except TemplateManagerError as e:
            error_msg = f"Template loading failed: {str(e)}"
            logger.error(error_msg)
            self.job_manager.add_error(job_id, error_msg)
            return False

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
            self.job_manager.update_progress(job_id, 90, "LaTeX document rendering completed")
            return main_tex_path

        except LatexRendererError as e:
            error_msg = f"LaTeX rendering failed: {str(e)}"
            logger.error(error_msg)
            self.job_manager.add_error(job_id, error_msg)
            return None

    def compile(self, job_id: str) -> Optional[Path]:
        """Compile the rendered main.tex inside workspace into final PDF."""
        logger = get_job_logger(job_id, "system")
        logger.info("Starting document compilation for job: %s", job_id)

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
            self.job_manager.add_error(job_id, error_msg)
            return None

    def check_fidelity(self, job_id: str, doc_model: DocumentModel) -> bool:
        """Run fidelity analysis comparing structural inputs against generated LaTeX results."""
        logger = get_job_logger(job_id, "system")
        logger.info("Running E2E publication fidelity checker for job: %s", job_id)

        job_dir = self.job_manager._get_job_dir(job_id)
        try:
            self.fidelity_checker.generate_fidelity_report(job_id, doc_model, job_dir)
            
            # Transition job status state
            self.job_manager.set_status(job_id, JobStatus.COMPLETED)
            self.job_manager.update_progress(job_id, 100, "Pipeline process completed successfully")
            return True
        except Exception as e:
            error_msg = f"Fidelity checker execution failed: {str(e)}"
            logger.error(error_msg)
            self.job_manager.add_error(job_id, error_msg)
            return False

    def run_full_pipeline(self, job_id: str, docx_filename: str, template_name: str = "default") -> JobMetadata:
        """Run the full end-to-end document conversion, rendering, and compilation pipeline."""
        # Step 1: Validate
        if not self.validate(job_id, docx_filename):
            return self.job_manager.get_job(job_id)

        # Step 2: Analyze
        doc_model = self.analyze(job_id, docx_filename)
        if not doc_model:
            return self.job_manager.get_job(job_id)

        # Step 3: Extract Assets
        if not self.extract_assets(job_id, docx_filename):
            return self.job_manager.get_job(job_id)

        # Step 4: Classify Assets
        if not self.analyze_assets(job_id, doc_model):
            return self.job_manager.get_job(job_id)

        # Step 5: Load Template
        if not self.load_template(job_id, template_name):
            return self.job_manager.get_job(job_id)

        # Step 6: Render LaTeX
        tex_path = self.render_latex(job_id)
        if not tex_path:
            return self.job_manager.get_job(job_id)

        # Step 7: Compile LaTeX to PDF
        pdf_path = self.compile(job_id)
        if not pdf_path:
            return self.job_manager.get_job(job_id)

        # Step 8: Run Fidelity check
        self.check_fidelity(job_id, doc_model)
        
        return self.job_manager.get_job(job_id)
