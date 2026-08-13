"""Batch generation orchestration.

One call produces, for every uploaded paper, one document per registered type in
both DOCX and PDF, laid out as::

    <batch>/Output/Paper 1/Acceptance.docx
                          /Acceptance.pdf
                          /Invoice.docx
                          /Invoice.pdf
            /Output/Paper 2/...
            /Documents.zip

Error handling is per paper and per document, never per batch: an operator
uploading twenty papers wants the nineteen that worked, plus a clear note about
the one that did not.  A batch therefore always finishes, and its summary carries
the failures alongside the successes.
"""

from __future__ import annotations

import logging
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from document_generator import config
from document_generator.models.schemas import (
    BatchGenerationRequest,
    BatchSummary,
    DocumentValidation,
    GeneratedArtifact,
    GeneratedDocumentSet,
    PaperMetadata,
)
from document_generator.pdf import converter as pdf_converter
from document_generator.services import (
    document_types,
    metadata_extractor,
    reference_numbers,
    validation as validation_service,
)
from document_generator.services.context_builder import build_context
from document_generator.services.packaging import ZIP_NAME, PackagingError, build_batch_zip
from document_generator.services.mapping_engine import MappingEngineError, render as render_document
from document_generator.services.template_store import TemplateStore

logger = logging.getLogger("document_generator.generator")

OUTPUT_DIR_NAME = "Output"
PAPERS_DIR_NAME = "papers"
SUMMARY_FILE_NAME = "batch.json"

# Characters a filesystem or a browser download header may object to.
_UNSAFE_NAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class GenerationError(Exception):
    """Raised when a batch cannot be started at all."""


def _safe_filename(name: str) -> str:
    cleaned = _UNSAFE_NAME_RE.sub("_", (name or "").strip()) or "document"
    return cleaned[:150]


def batch_dir(batch_id: str) -> Path:
    """Directory of one batch.

    The identifier is validated rather than trusted: it arrives from a URL, and
    joining an unchecked value onto a path is how directory traversal happens.
    """
    if not re.fullmatch(r"[A-Za-z0-9_-]{4,64}", batch_id or ""):
        raise GenerationError("Invalid batch identifier.")
    return config.BATCHES_DIR / batch_id


class GeneratorService:
    """Produces the documents for a batch of papers."""

    def __init__(self, store: Optional[TemplateStore] = None) -> None:
        config.ensure_directories()
        self.store = store or TemplateStore()

    # ------------------------------------------------------------------ #
    # Planning
    # ------------------------------------------------------------------ #

    def _resolve_document_types(self, requested: Optional[Sequence[str]], journal_code: Optional[str] = None) -> List[str]:
        """Which document types this batch will produce."""
        available = self.store.available_types(journal_code)
        if not available:
            raise GenerationError(
                "No master templates have been uploaded yet. Upload the acceptance "
                "letter and invoice templates before generating documents."
            )
        if not requested:
            return available

        unknown = [k for k in requested if not document_types.is_known(k)]
        if unknown:
            raise GenerationError(f"Unknown document type(s): {', '.join(unknown)}")
        missing = [k for k in requested if k not in available]
        if missing:
            labels = ", ".join(document_types.get_document_type(k).label for k in missing)
            raise GenerationError(f"No template has been uploaded for: {labels}")
        return [k for k in available if k in requested]

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #

    def generate_batch(
        self,
        papers: Sequence[Tuple[str, Path]],
        request: BatchGenerationRequest,
    ) -> BatchSummary:
        """Generate every document for papers."""
        if not papers:
            raise GenerationError("No papers were uploaded.")

        settings = config.load_settings()
        suffix = (
            request.reference_suffix
            if request.reference_suffix is not None
            else settings["reference_suffix"]
        )
        journal_code = (
            request.journal_code
            if request.journal_code is not None
            else settings.get("journal_code", "")
        )
        selected_types = self._resolve_document_types(request.document_types, journal_code)
        editor = request.editor if request.editor is not None else settings["editor_name"]
        journal = request.journal if request.journal is not None else settings["journal_name"]
        want_pdf = (
            request.generate_pdf
            if request.generate_pdf is not None
            else bool(settings["generate_pdf"])
        )
        # The MMDDYY component follows the acceptance date the operator entered,
        # falling back to today when it is blank or in a format we cannot read.
        ref_date = reference_numbers.parse_reference_date(request.acceptance_date)

        batch_id = uuid.uuid4().hex[:16]
        root = batch_dir(batch_id)
        output_root = root / OUTPUT_DIR_NAME
        papers_dir = root / PAPERS_DIR_NAME
        output_root.mkdir(parents=True, exist_ok=True)
        papers_dir.mkdir(parents=True, exist_ok=True)

        warnings: List[str] = []
        pdf_backend = pdf_converter.backend_name()
        if want_pdf and pdf_backend is None:
            want_pdf = False
            warnings.append(
                "PDF export is unavailable on this server (LibreOffice was not "
                "found), so only DOCX files were produced."
            )
        if not ref_date and request.acceptance_date.strip():
            warnings.append(
                f"The acceptance date '{request.acceptance_date}' was used verbatim in "
                "the documents, but its format was not recognised, so today's date "
                "was used for the reference numbers."
            )

        logger.info(
            "Batch %s: %d paper(s), types=%s, pdf=%s",
            batch_id,
            len(papers),
            ",".join(selected_types),
            want_pdf,
        )

        document_sets: List[GeneratedDocumentSet] = []
        for index, (original_name, staged_path) in enumerate(papers, start=1):
            document_sets.append(
                self._generate_for_paper(
                    batch_id=batch_id,
                    index=index,
                    original_name=original_name,
                    staged_path=staged_path,
                    papers_dir=papers_dir,
                    output_root=output_root,
                    selected_types=selected_types,
                    request=request,
                    suffix=suffix,
                    journal_code=journal_code,
                    editor=editor,
                    journal=journal,
                    ref_date=ref_date,
                    want_pdf=want_pdf,
                    custom=settings["custom_placeholders"],
                )
            )

        zip_available = False
        try:
            build_batch_zip(output_root, root / ZIP_NAME)
            zip_available = True
        except PackagingError as exc:
            warnings.append(str(exc))

        document_count = sum(len(d.artifacts) for d in document_sets)
        validation_failures = sum(
            1 for d in document_sets for v in d.validations if not v.valid
        )
        if validation_failures:
            warnings.append(
                f"{validation_failures} generated document(s) did not match their "
                "template and were not converted to PDF. Their validation reports "
                "list what differed."
            )
        summary = BatchSummary(
            batch_id=batch_id,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            paper_count=len(document_sets),
            document_count=document_count,
            documents=document_sets,
            zip_available=zip_available,
            zip_download_url=(
                f"/document-generator/download/{batch_id}?path={OUTPUT_DIR_NAME}.zip"
                if zip_available
                else None
            ),
            pdf_backend=pdf_backend if want_pdf else None,
            warnings=warnings,
            validation_failures=validation_failures,
        )
        # Persisted so a batch survives a restart and can be re-downloaded
        # without regenerating it.
        try:
            (root / SUMMARY_FILE_NAME).write_text(
                summary.model_dump_json(indent=2), encoding="utf-8"
            )
        except OSError as exc:
            logger.warning("Could not persist the summary of batch %s: %s", batch_id, exc)

        logger.info(
            "Batch %s complete: %d document(s) across %d paper(s)",
            batch_id,
            document_count,
            len(document_sets),
        )
        return summary

    def _generate_for_paper(
        self,
        *,
        batch_id: str,
        index: int,
        original_name: str,
        staged_path: Path,
        papers_dir: Path,
        output_root: Path,
        selected_types: Sequence[str],
        request: BatchGenerationRequest,
        suffix: str,
        journal_code: str,
        editor: str,
        journal: str,
        ref_date,
        want_pdf: bool,
        custom: Dict[str, str],
    ) -> GeneratedDocumentSet:
        """Produce every selected document for one paper."""
        settings = config.load_settings()
        folder_name = f"Paper {index}"
        paper_folder = output_root / folder_name
        paper_folder.mkdir(parents=True, exist_ok=True)
        errors: List[str] = []

        # Keep the source alongside the output: an operator questioning a letter
        # needs the paper it came from, and the staged upload is transient.
        kept_source = papers_dir / f"{index:02d}_{_safe_filename(original_name)}"
        try:
            shutil.copyfile(staged_path, kept_source)
        except OSError as exc:
            logger.warning("Could not retain the source of %s: %s", original_name, exc)

        title, authors, meta_warnings = metadata_extractor.extract(
            staged_path, f"docgen-{batch_id}-{index:02d}"
        )
        auto_ref = reference_numbers.build_reference_number(
            index,
            ref_date,
            suffix=suffix,
            prefix=request.reference_prefix,
            journal_code=journal_code,
        )

        override = next(
            (ov for ov in (request.paper_overrides or []) if ov.index == index), None
        )
        if override:
            if override.title and override.title.strip():
                title = override.title.strip()
            if override.authors:
                if isinstance(override.authors, list):
                    authors = [a for a in override.authors if a.strip()]
                elif isinstance(override.authors, str):
                    authors = [a.strip() for a in override.authors.split(",") if a.strip()]
            if override.reference_number and override.reference_number.strip():
                auto_ref = override.reference_number.strip()

        paper_extra = dict(request.extra_placeholders or {})
        fee_val = (
            override.fee.strip()
            if (override and override.fee)
            else (request.fee or settings.get("default_fee") or "$2100").strip()
        )
        currency_val = (request.currency or settings.get("default_currency") or "$").strip()
        bank_val = (request.bank_details or settings.get("bank_details") or "").strip()
        inv_num_val = (request.invoice_number or f"INV-{auto_ref}").strip()
        paper_acceptance_date = (
            override.acceptance_date.strip()
            if (override and override.acceptance_date and override.acceptance_date.strip())
            else request.acceptance_date
        )
        paper_deadline = (
            override.deadline.strip()
            if (override and override.deadline and override.deadline.strip())
            else request.deadline
        )
        inv_date_val = (request.invoice_date or paper_acceptance_date or "").strip()

        discount_val = (override.discount if override and override.discount else "$0").strip()
        total_val = (override.total_charge if override and override.total_charge else fee_val).strip()

        paper_extra["FEE"] = fee_val
        paper_extra["TOTAL_CHARGE_USD"] = fee_val
        paper_extra["DISCOUNT"] = discount_val
        paper_extra["TOTAL_CHARGE"] = total_val

        paper = PaperMetadata(
            index=index,
            source_filename=original_name,
            title=title,
            authors=authors,
            reference_number=auto_ref,
            warnings=meta_warnings,
        )

        artifacts: List[GeneratedArtifact] = []
        validations: List[DocumentValidation] = []
        for type_key in selected_types:
            info = document_types.get_document_type(type_key)
            template = self.store.template_path(type_key, journal_code)
            docx_out = paper_folder / f"{info.output_basename}.docx"
            context = build_context(
                paper,
                acceptance_date=paper_acceptance_date,
                deadline=paper_deadline,
                editor=editor,
                journal=journal,
                document_type=info.label,
                fee=fee_val,
                currency=currency_val,
                bank_details=bank_val,
                invoice_number=inv_num_val,
                invoice_date=inv_date_val,
                custom=custom,
                extra=paper_extra,
            )

            mapping = self.store.load_mapping(type_key, journal_code)
            mappings = list(mapping.mappings) if mapping else []
            try:
                report = render_document(template, docx_out, context, mappings)
            except MappingEngineError as exc:
                errors.append(f"{info.label}: {exc}")
                logger.error("Batch %s paper %d %s failed: %s", batch_id, index, type_key, exc)
                continue

            unmatched = report.get("unmatched_fields") or []
            if unmatched:
                paper.warnings.append(
                    f"{info.label}: the mapped text for "
                    f"{', '.join(str(u) for u in unmatched)} was not found in the "
                    "template, so those values were not filled in. Re-map the "
                    "template to fix this."
                )
            if not mappings and not report.get("substitutions"):
                paper.warnings.append(
                    f"{info.label} was copied out unchanged: its fields have not "
                    "been mapped yet. Open the template and map its fields."
                )

            unresolved = report.get("unresolved") or []
            if unresolved:
                paper.warnings.append(
                    f"{info.label} uses placeholders with no value: "
                    f"{', '.join(str(u) for u in unresolved)}."
                )
            artifacts.append(
                self._artifact(batch_id, type_key, "docx", docx_out, output_root)
            )

            # Every generated document is checked against the template it came
            # from *before* it is handed to a PDF converter.  Word is stricter
            # when exporting than when opening, so a package with inconsistent
            # XML opens fine and then fails export with "the file appears to be
            # corrupted"; the point of this gate is that such a file never
            # reaches that stage, and the operator is told why.
            check = validation_service.validate_generated(
                template,
                docx_out,
                expected_values={
                    m.field: context.get(m.field.upper(), "") for m in mappings
                },
                original_literals={m.field: m.text for m in mappings},
            )
            report_dict = check.as_dict()
            validations.append(
                DocumentValidation(
                    document_type=type_key,
                    document=str(report_dict["document"]),
                    valid=check.valid,
                    checks=check.checks,
                    errors=check.errors,
                    fields_replaced=check.fields_replaced,
                    fields_missing=check.fields_missing,
                )
            )
            if not check.valid:
                errors.append(
                    f"{info.label}: the generated document did not match its "
                    f"template ({'; '.join(check.errors)}). No PDF was produced "
                    "for it."
                )
                logger.error(
                    "Batch %s paper %d %s failed validation: %s",
                    batch_id,
                    index,
                    type_key,
                    "; ".join(check.errors),
                )
                continue

            if not want_pdf:
                continue
            pdf_out = paper_folder / f"{info.output_basename}.pdf"
            try:
                pdf_converter.convert_to_pdf(docx_out, pdf_out)
                artifacts.append(
                    self._artifact(batch_id, type_key, "pdf", pdf_out, output_root)
                )
            except pdf_converter.PdfConversionError as exc:
                # The DOCX is already produced and usable; the batch keeps going.
                errors.append(f"{info.label} PDF: {exc}")
                logger.error("Batch %s paper %d %s PDF failed: %s", batch_id, index, type_key, exc)

        return GeneratedDocumentSet(
            paper=paper,
            folder=folder_name,
            artifacts=artifacts,
            errors=errors,
            validations=validations,
        )

    @staticmethod
    def _artifact(
        batch_id: str, type_key: str, fmt: str, path: Path, output_root: Path
    ) -> GeneratedArtifact:
        relative = path.relative_to(output_root).as_posix()
        return GeneratedArtifact(
            document_type=type_key,
            format=fmt,
            filename=path.name,
            relative_path=relative,
            size_bytes=path.stat().st_size if path.exists() else 0,
            download_url=f"/document-generator/download/{batch_id}?path={relative}",
        )

    # ------------------------------------------------------------------ #
    # Retrieval
    # ------------------------------------------------------------------ #

    @staticmethod
    def load_summary(batch_id: str) -> Optional[BatchSummary]:
        path = batch_dir(batch_id) / SUMMARY_FILE_NAME
        if not path.is_file():
            return None
        try:
            return BatchSummary.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - a stale summary is not fatal
            logger.warning("Could not read the summary of batch %s: %s", batch_id, exc)
            return None

    @staticmethod
    def resolve_download(batch_id: str, relative_path: str) -> Path:
        root = batch_dir(batch_id)
        if not root.is_dir():
            raise GenerationError("Unknown batch.")

        requested = (relative_path or "").strip().lstrip("/")
        if not requested:
            raise GenerationError("No file was requested.")

        if requested == f"{OUTPUT_DIR_NAME}.zip":
            candidate = root / ZIP_NAME
        else:
            candidate = root / OUTPUT_DIR_NAME / requested

        try:
            resolved = candidate.resolve()
            resolved.relative_to(root.resolve())
        except (OSError, ValueError) as exc:
            raise GenerationError("Invalid file path.") from exc

        if not resolved.is_file():
            raise GenerationError("The requested file does not exist in this batch.")
        return resolved
