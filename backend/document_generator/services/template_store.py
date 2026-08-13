"""Permanent storage for the master Word templates.

The templates are uploaded once and reused for every generation from then on.
That makes their storage the module's most important durability guarantee, so:

* each document type owns a fixed slot path (``templates/<key>.docx``), which
  means a generation run never has to search for "the current" template;
* replacing a template archives the previous file rather than deleting it, so a
  bad upload is always recoverable;
* writes go through a temporary file and an atomic replace, so an interrupted
  upload can never leave a half-written template in the active slot;
* an upload is validated as a real Word document *before* it is allowed to
  supersede a working template.
"""

from __future__ import annotations

import json
import logging
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from document_generator import config
from document_generator.models.schemas import FieldMapping, TemplateInfo, TemplateMapping
from document_generator.services import document_types, template_fields
from document_generator.services.document_inspector import count_occurrences
from document_generator.services.placeholder_engine import discover_placeholders

logger = logging.getLogger("document_generator.template_store")

# Marker entries every .docx contains.  Checking for them rejects a renamed PDF
# or a .doc binary at upload time instead of at generation time, when it would
# fail a whole batch.
_REQUIRED_DOCX_ENTRIES = ("word/document.xml", "[Content_Types].xml")


class TemplateStoreError(Exception):
    """Raised when a template cannot be stored or read."""


class TemplateStore:
    """Manages the master template slots."""

    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        config.ensure_directories()
        self.templates_dir = templates_dir or config.TEMPLATES_DIR
        self.archive_dir = config.TEMPLATE_ARCHIVE_DIR
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Paths
    # ------------------------------------------------------------------ #

    def template_path(self, key: str, journal_code: Optional[str] = None) -> Path:
        """Active slot path for a document type, optionally for a specific journal."""
        if not document_types.is_known(key):
            raise TemplateStoreError(f"Unknown document type: {key}")

        if journal_code:
            journal_dir = self.templates_dir / journal_code
            if journal_dir.is_dir():
                target_prefix = "acceptance" if key == "acceptance" else "invoice"
                for f in journal_dir.glob("*.docx"):
                    if not f.name.startswith("~$") and target_prefix in f.name.lower():
                        return f

        default_path = self.templates_dir / f"{key}.docx"
        if not default_path.is_file() and journal_code:
            journal_dir = self.templates_dir / journal_code
            if journal_dir.is_dir():
                target_prefix = "acceptance" if key == "acceptance" else "invoice"
                for f in journal_dir.glob("*.docx"):
                    if not f.name.startswith("~$") and target_prefix in f.name.lower():
                        return f
        return default_path

    def _metadata_path(self, key: str, journal_code: Optional[str] = None) -> Path:
        if journal_code and (self.templates_dir / journal_code).is_dir():
            return self.templates_dir / journal_code / f"{key}.json"
        return self.templates_dir / f"{key}.json"

    def mapping_path(self, key: str, journal_code: Optional[str] = None) -> Path:
        """Where the saved field mapping for a slot lives."""
        if not document_types.is_known(key):
            raise TemplateStoreError(f"Unknown document type: {key}")
        if journal_code and (self.templates_dir / journal_code).is_dir():
            return self.templates_dir / journal_code / f"{key}.mapping.json"
        return self.templates_dir / f"{key}.mapping.json"

    def has_template(self, key: str, journal_code: Optional[str] = None) -> bool:
        return self.template_path(key, journal_code).is_file()

    # ------------------------------------------------------------------ #
    # Reading
    # ------------------------------------------------------------------ #

    def list_journals(self) -> List[Dict[str, Any]]:
        """Discover all journal folders in storage."""
        journals: List[Dict[str, Any]] = []
        if not self.templates_dir.exists():
            return journals

        for child in sorted(self.templates_dir.iterdir()):
            if child.is_dir() and not child.name.startswith((".", "_")):
                acc_path = self.template_path("acceptance", child.name)
                inv_path = self.template_path("invoice", child.name)
                
                # Derive human-readable name from filename if available
                name = child.name
                if acc_path.is_file():
                    stem = acc_path.stem
                    if stem.startswith("Acceptance_"):
                        name = stem[len("Acceptance_"):].replace("_", " ").strip()
                elif inv_path.is_file():
                    stem = inv_path.stem
                    if stem.startswith("Invoice_"):
                        name = stem[len("Invoice_"):].replace("_", " ").strip()

                journals.append({
                    "code": child.name,
                    "name": name or child.name,
                    "has_acceptance": acc_path.is_file(),
                    "has_invoice": inv_path.is_file(),
                    "acceptance_file": acc_path.name if acc_path.is_file() else None,
                    "invoice_file": inv_path.name if inv_path.is_file() else None,
                })
        return journals

    def describe(self, key: str, journal_code: Optional[str] = None) -> TemplateInfo:
        """Current state of one slot, including the placeholders it uses."""
        info = document_types.get_document_type(key)
        path = self.template_path(key, journal_code)
        described = TemplateInfo(key=key, label=info.label, uploaded=path.is_file())
        if not described.uploaded:
            return described

        described.size_bytes = path.stat().st_size
        meta = self._read_metadata(key, journal_code)
        described.original_filename = meta.get("original_filename", path.name)
        described.uploaded_at = meta.get("uploaded_at")
        described.archived_versions = len(list(self.archive_dir.glob(f"{key}__*.docx")))
        try:
            described.placeholders = discover_placeholders(path)
        except Exception as exc:
            logger.warning("Could not read placeholders from %s: %s", path, exc)

        mapping = self.load_mapping(key, journal_code)
        if mapping is not None:
            described.mapped = bool(mapping.mappings)
            described.mapped_fields = [m.field for m in mapping.mappings]
            described.stale_fields = list(mapping.stale_fields)
        described.needs_mapping = not described.mapped and not described.placeholders
        return described

    def describe_all(self, journal_code: Optional[str] = None) -> List[TemplateInfo]:
        return [self.describe(t.key, journal_code) for t in document_types.list_document_types()]

    def available_types(self, journal_code: Optional[str] = None) -> List[str]:
        """Document types that currently have a usable template."""
        return [
            t.key for t in document_types.list_document_types() if self.has_template(t.key, journal_code)
        ]

    def _read_metadata(self, key: str) -> Dict[str, str]:
        path = self._metadata_path(key)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    # ------------------------------------------------------------------ #
    # Writing
    # ------------------------------------------------------------------ #

    @staticmethod
    def validate_docx(path: Path) -> None:
        """Confirm ``path`` is a readable Word document.

        Raises ``TemplateStoreError`` with an operator-facing message otherwise.
        """
        if not path.is_file() or path.stat().st_size == 0:
            raise TemplateStoreError("The uploaded file is empty.")
        try:
            with zipfile.ZipFile(path) as zf:
                names = set(zf.namelist())
                missing = [e for e in _REQUIRED_DOCX_ENTRIES if e not in names]
                if missing:
                    raise TemplateStoreError(
                        "The uploaded file is not a valid .docx template "
                        "(missing Word document structure)."
                    )
                # Surface a corrupt archive here rather than mid-batch.
                bad = zf.testzip()
                if bad is not None:
                    raise TemplateStoreError(
                        f"The uploaded .docx archive is corrupt (bad entry: {bad})."
                    )
        except zipfile.BadZipFile as exc:
            raise TemplateStoreError(
                "The uploaded file is not a .docx document. Word templates saved "
                "as .doc must be re-saved as .docx first."
            ) from exc

    def save_template(
        self, key: str, source: Path, original_filename: str = ""
    ) -> TemplateInfo:
        """Install ``source`` as the master template for ``key``.

        Any template already in the slot is archived first.  Validation happens
        before the existing template is touched, so a rejected upload leaves the
        working template exactly where it was.
        """
        if not document_types.is_known(key):
            raise TemplateStoreError(f"Unknown document type: {key}")
        self.validate_docx(source)

        target = self.template_path(key)
        if target.exists():
            self._archive(key, target)

        tmp = target.with_suffix(".docx.tmp")
        try:
            shutil.copyfile(source, tmp)
            tmp.replace(target)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise TemplateStoreError(f"Could not store the template: {exc}") from exc

        self._metadata_path(key).write_text(
            json.dumps(
                {
                    "original_filename": original_filename or source.name,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        # A replacement usually still contains the same literals, so the saved
        # mapping is re-checked rather than discarded: the operator only redoes
        # the wizard for fields that genuinely moved.
        self.revalidate_mapping(key)
        logger.info(
            "Stored master template '%s' from %s (%d bytes)",
            key,
            original_filename or source.name,
            target.stat().st_size,
        )
        return self.describe(key)

    # ------------------------------------------------------------------ #
    # Field mappings
    # ------------------------------------------------------------------ #

    def load_mapping(self, key: str, journal_code: Optional[str] = None) -> Optional[TemplateMapping]:
        """The saved mapping for a slot, or an auto-detected one if unmapped."""
        path = self.mapping_path(key, journal_code)
        if path.is_file():
            try:
                return TemplateMapping.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                logger.warning("Could not read the saved mapping for '%s': %s", key, exc)
        return self._auto_detect_mapping(key, journal_code)

    def _auto_detect_mapping(self, key: str, journal_code: Optional[str] = None) -> Optional[TemplateMapping]:
        """Auto-detect field mappings for templates using ## placeholders."""
        tmpl_path = self.template_path(key, journal_code)
        if not tmpl_path.is_file():
            return None
        try:
            from document_generator.services import document_inspector
            insp = document_inspector.inspect(tmpl_path, key)
            mappings: List[FieldMapping] = []
            for idx, seg in enumerate(insp.segments):
                txt = seg.text
                if "##" in txt:
                    prev_txt = insp.segments[idx - 1].text if idx > 0 else ""
                    combined = f"{prev_txt} {txt}".lower()
                    field = None
                    if "invoice no" in combined or "invoice number" in combined:
                        field = "INVOICE_NUMBER"
                    elif "ref" in combined:
                        field = "REFERENCE_NUMBER"
                    elif "title" in combined:
                        field = "TITLE"
                    elif "author" in combined:
                        field = "AUTHORS"
                    elif "accepted" in combined or "date" in combined:
                        field = "ACCEPTANCE_DATE"
                    elif "deadline" in combined:
                        field = "DEADLINE"
                    elif "discount" in combined:
                        field = "DISCOUNT"
                    elif "total charge in us dollars" in combined or "total charge in dollars" in combined:
                        field = "TOTAL_CHARGE_USD"
                    elif "total charge" in combined or "fees" in combined or "fee" in combined:
                        field = "TOTAL_CHARGE"

                    if field:
                        mappings.append(FieldMapping(field=field, text=txt, occurrences=1))
            if mappings:
                return TemplateMapping(document_type=key, mappings=mappings)
        except Exception as exc:
            logger.warning("Could not auto-detect mappings for %s: %s", key, exc)
        return None

    def save_mapping(
        self, key: str, mappings: List[FieldMapping], journal_code: Optional[str] = None
    ) -> TemplateMapping:
        """Store the wizard's confirmed mapping permanently."""
        if not self.has_template(key, journal_code):
            raise TemplateStoreError(
                "Upload the template before mapping its fields."
            )
        template = self.template_path(key, journal_code)

        cleaned: List[FieldMapping] = []
        stale: List[str] = []
        seen: set[str] = set()
        for mapping in mappings:
            field = (mapping.field or "").strip().upper()
            literal = mapping.text or ""
            if not field or not literal.strip():
                continue
            if not template_fields.is_known(field):
                raise TemplateStoreError(f"Unknown field: {mapping.field}")
            if field in seen:
                raise TemplateStoreError(
                    f"The field {template_fields.get_field(field).label} was mapped twice."
                )
            seen.add(field)
            occurrences = count_occurrences(template, literal)
            if occurrences == 0:
                stale.append(field)
            cleaned.append(
                FieldMapping(field=field, text=literal, occurrences=occurrences)
            )

        if stale:
            labels = ", ".join(template_fields.get_field(f).label for f in stale)
            raise TemplateStoreError(
                f"This text was not found in the template: {labels}. "
                "Select the text again from the document."
            )

        mapping_record = TemplateMapping(
            document_type=key,
            mappings=cleaned,
            updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self._write_mapping(key, mapping_record, journal_code)
        logger.info(
            "Saved field mapping for '%s': %s",
            key,
            ", ".join(f"{m.field}(x{m.occurrences})" for m in cleaned) or "none",
        )
        return mapping_record

    def _write_mapping(self, key: str, mapping: TemplateMapping, journal_code: Optional[str] = None) -> None:
        path = self.mapping_path(key, journal_code)
        tmp = path.with_suffix(".json.tmp")
        try:
            tmp.write_text(mapping.model_dump_json(indent=2), encoding="utf-8")
            tmp.replace(path)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise TemplateStoreError(f"Could not store the mapping: {exc}") from exc

    def revalidate_mapping(self, key: str, journal_code: Optional[str] = None) -> Optional[TemplateMapping]:
        """Re-check a saved mapping against the template currently in the slot."""
        mapping = self.load_mapping(key, journal_code)
        if mapping is None:
            return None
        template = self.template_path(key, journal_code)
        stale: List[str] = []
        for entry in mapping.mappings:
            entry.occurrences = count_occurrences(template, entry.text)
            if entry.occurrences == 0:
                stale.append(entry.field)
        mapping.stale_fields = stale
        try:
            self._write_mapping(key, mapping, journal_code)
        except TemplateStoreError as exc:
            logger.warning("Could not update the mapping for '%s': %s", key, exc)
        if stale:
            logger.info(
                "Mapping for '%s' no longer matches the template for: %s",
                key,
                ", ".join(stale),
            )
        return mapping

    def _archive_mapping(self, key: str, stamp: str) -> None:
        """Keep a copy of the mapping alongside the archived template."""
        current = self.mapping_path(key)
        if not current.is_file():
            return
        try:
            shutil.copyfile(current, self.archive_dir / f"{key}__{stamp}.mapping.json")
        except OSError as exc:
            logger.warning("Could not archive the mapping for '%s': %s", key, exc)

    def _archive(self, key: str, current: Path) -> None:
        """Move the template currently in a slot into the archive."""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = self.archive_dir / f"{key}__{stamp}.docx"
        self._archive_mapping(key, stamp)
        try:
            shutil.copyfile(current, destination)
            logger.info("Archived previous '%s' template to %s", key, destination.name)
        except OSError as exc:
            # An archiving failure must not block a legitimate replacement, but
            # it is worth knowing about.
            logger.warning("Could not archive previous '%s' template: %s", key, exc)
