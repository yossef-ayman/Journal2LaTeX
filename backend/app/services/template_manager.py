import datetime
import json
import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import List, Optional
from app.utils.filesystem import normalize_path, read_text_file


class TemplateManagerError(Exception):
    """Exception raised when template management operations fail."""
    pass


class TemplateManager:
    """Service to discover, list, and manage both built-in and user-uploaded journal templates."""

    def __init__(self, built_in_dir: Optional[Path] = None, uploaded_dir: Optional[Path] = None) -> None:
        """Initialize TemplateManager with built-in and uploaded template roots."""
        # Built-in root (relative to backend folder by default)
        if built_in_dir:
            self.built_in_root = normalize_path(built_in_dir)
        else:
            self.built_in_root = normalize_path(Path(__file__).resolve().parent.parent.parent / "templates" / "journals")

        # Uploaded templates root
        if uploaded_dir:
            self.uploaded_root = normalize_path(uploaded_dir)
        else:
            self.uploaded_root = normalize_path(Path(__file__).resolve().parent.parent.parent / "templates" / "uploaded")
        
        self.uploaded_root.mkdir(parents=True, exist_ok=True)

    def list_templates(self) -> List[dict]:
        """List all discovered templates (both built-in and uploaded) with their metadata.

        Returns:
            A list of template metadata dictionaries.
        """
        results = []

        # 1. Discover built-in templates
        if self.built_in_root.exists() and self.built_in_root.is_dir():
            for path in self.built_in_root.iterdir():
                if path.is_dir() and not path.name.startswith("."):
                    if (path / "template.tex").exists():
                        meta = self.get_template_metadata(path.name, is_uploaded=False)
                        results.append(meta)

        # 2. Discover uploaded templates
        if self.uploaded_root.exists() and self.uploaded_root.is_dir():
            for path in self.uploaded_root.iterdir():
                if path.is_dir() and not path.name.startswith("."):
                    if (path / "template.tex").exists():
                        meta = self.get_template_metadata(path.name, is_uploaded=True)
                        results.append(meta)

        return results

    def get_template_path(self, template_id: str) -> Path:
        """Resolve a template ID (either built-in name or uploaded UUID) to its directory path.

        Args:
            template_id: The ID of the template.

        Returns:
            The Path to the template directory.
        """
        # First check uploaded root
        uploaded_path = self.uploaded_root / template_id
        if uploaded_path.exists() and uploaded_path.is_dir():
            return uploaded_path

        # Then check built-in root
        built_in_path = self.built_in_root / template_id
        if built_in_path.exists() and built_in_path.is_dir():
            return built_in_path

        raise TemplateManagerError(f"Template with ID '{template_id}' not found.")

    def get_template_metadata(self, template_id: str, is_uploaded: Optional[bool] = None) -> dict:
        """Load and return template metadata.

        Args:
            template_id: The ID of the template.
            is_uploaded: If known, indicates if the template is an uploaded one.

        Returns:
            The parsed metadata dict.
        """
        try:
            template_dir = self.get_template_path(template_id)
        except TemplateManagerError:
            # Fallback or placeholder for missing template
            return {
                "template_id": template_id,
                "display_name": template_id,
                "journal_name": template_id,
                "version": "unknown",
                "upload_date": "",
                "description": "",
                "template_type": "built_in",
                "class_file": "",
                "supported_features": {}
            }

        # Determine type
        if is_uploaded is None:
            is_uploaded = self.uploaded_root in template_dir.parents

        metadata_file = template_dir / "template.json"
        
        # Default fallback structure
        default_meta = {
            "template_id": template_id,
            "display_name": template_id,
            "journal_name": template_id,
            "version": "1.0.0",
            "upload_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
            "description": "Custom user uploaded LaTeX template.",
            "template_type": "uploaded" if is_uploaded else "built_in",
            "class_file": "",
            "entry_file": "template.tex",
            "supported_features": {
                "author_biographies": True,
                "double_column": False,
                "custom_headers": True
            }
        }

        if not metadata_file.exists():
            return default_meta

        try:
            data = json.loads(metadata_file.read_text(encoding="utf-8"))
            # Map old format or fill defaults
            mapped = {
                "template_id": data.get("template_id") or data.get("name") or default_meta["template_id"],
                "display_name": data.get("display_name") or data.get("journal_title") or data.get("name") or default_meta["display_name"],
                "journal_name": data.get("journal_name") or data.get("journal_title") or data.get("name") or default_meta["journal_name"],
                "version": data.get("version") or default_meta["version"],
                "upload_date": data.get("upload_date") or default_meta["upload_date"],
                "description": data.get("description") or default_meta["description"],
                "template_type": default_meta["template_type"],
                "class_file": data.get("class_file") or default_meta["class_file"],
                "entry_file": data.get("entry_file") or default_meta["entry_file"],
                "supported_features": data.get("supported_features") or default_meta["supported_features"],
                "engine": data.get("engine") or "pdflatex"
            }
            return mapped
        except Exception as e:
            # Return defaults on parse failure
            return default_meta

    def save_template_package(self, zip_file_path: Path, max_size_bytes: int = 50 * 1024 * 1024) -> dict:
        """Verify, extract, and register an uploaded template archive safely.

        Args:
            zip_file_path: The Path to the uploaded zip file.
            max_size_bytes: Size limit for safety.

        Returns:
            The registered template metadata.
        """
        # Validate size
        if zip_file_path.stat().st_size > max_size_bytes:
            raise TemplateManagerError("Template package exceeds the maximum size limit.")

        # Validate Zip integrity
        if not zipfile.is_zipfile(zip_file_path):
            raise TemplateManagerError("The uploaded file is not a valid zip archive.")

        template_id = str(uuid.uuid4())
        extract_dir = self.uploaded_root / template_id
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                for member in zip_ref.infolist():
                    # 1. Zip Slip / Traversal Check
                    target_path = Path(os.path.abspath(extract_dir / member.filename))
                    extract_dir_abs = Path(os.path.abspath(extract_dir))
                    if not str(target_path).startswith(str(extract_dir_abs)):
                        raise TemplateManagerError("Security alert: Zip Slip / Directory traversal attempt detected.")

                    # 2. Symlink check
                    if (member.external_attr >> 16) & 0o170000 == 0o120000:
                        raise TemplateManagerError("Security alert: Symbolic links are not allowed in templates.")

                    # 3. Dangerous files check (prevent executing scripts, etc.)
                    bad_extensions = {".sh", ".bat", ".exe", ".py", ".pl", ".php", ".js"}
                    if Path(member.filename).suffix.lower() in bad_extensions:
                        raise TemplateManagerError(f"Security alert: File {member.filename} has a forbidden executable extension.")

                # If all security checks pass, extract the archive
                zip_ref.extractall(extract_dir)

            # Search for entry .tex file using robust heuristics
            tex_files = list(extract_dir.rglob("*.tex"))
            if not tex_files:
                raise TemplateManagerError("Invalid template package: no LaTeX source (.tex) files found.")

            entry_file_path = None
            primary_candidates = []
            secondary_candidates = []

            for tex_path in tex_files:
                try:
                    content = read_text_file(tex_path)
                    has_documentclass = "\\documentclass" in content or "\\documentstyle" in content
                    has_begindocument = "\\begin{document}" in content
                    
                    if has_documentclass and has_begindocument:
                        primary_candidates.append(tex_path)
                    elif has_begindocument:
                        secondary_candidates.append(tex_path)
                except Exception:
                    continue

            if primary_candidates:
                # Prefer common entry point filenames
                preferred_names = {"template.tex", "main.tex", "paper.tex", "bare_jrnl.tex", "manuscript.tex"}
                for p in primary_candidates:
                    if p.name.lower() in preferred_names:
                        entry_file_path = p
                        break
                if not entry_file_path:
                    entry_file_path = primary_candidates[0]
            elif secondary_candidates:
                entry_file_path = secondary_candidates[0]
            else:
                entry_file_path = tex_files[0]

            # Resolve relative path in POSIX style
            entry_file_rel = entry_file_path.relative_to(extract_dir).as_posix()

            # Load or initialize template.json
            metadata_file = extract_dir / "template.json"
            meta_data = {}
            if metadata_file.exists():
                try:
                    meta_data = json.loads(metadata_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            # Write standard metadata
            meta_data["template_id"] = template_id
            meta_data["template_type"] = "uploaded"
            meta_data["upload_date"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
            meta_data["entry_file"] = entry_file_rel
            
            # Map legacy class_file or guess it
            if not meta_data.get("class_file"):
                classes = list(extract_dir.glob("*.cls"))
                if classes:
                    meta_data["class_file"] = classes[0].name

            metadata_file.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")

            return self.get_template_metadata(template_id, is_uploaded=True)

        except Exception as e:
            # Clean up on failure
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            raise TemplateManagerError(f"Failed to process template package: {str(e)}")

    def delete_template(self, template_id: str) -> None:
        """Delete an uploaded template directory.

        Args:
            template_id: The ID of the template to delete.
        """
        template_dir = self.uploaded_root / template_id
        if not template_dir.exists() or not template_dir.is_dir():
            raise TemplateManagerError("Only uploaded templates can be deleted, or template not found.")

        try:
            shutil.rmtree(template_dir)
        except Exception as e:
            raise TemplateManagerError(f"Failed to delete template: {str(e)}")

    def update_template_metadata(self, template_id: str, updates: dict) -> dict:
        """Update template metadata JSON.

        Args:
            template_id: The ID of the template.
            updates: Dict containing fields to update.

        Returns:
            The updated metadata.
        """
        template_dir = self.get_template_path(template_id)
        if self.uploaded_root not in template_dir.parents:
            raise TemplateManagerError("Only uploaded templates can be modified.")

        metadata_file = template_dir / "template.json"
        
        current_meta = self.get_template_metadata(template_id, is_uploaded=True)
        current_meta.update(updates)

        # Remove system-controlled keys from being overwritten by external updates if passed
        current_meta["template_id"] = template_id
        current_meta["template_type"] = "uploaded"

        try:
            metadata_file.write_text(json.dumps(current_meta, indent=2), encoding="utf-8")
            return current_meta
        except Exception as e:
            raise TemplateManagerError(f"Failed to save metadata updates: {str(e)}")

    def prepare_workspace(self, template_id: str, dest_dir: Path) -> None:
        """Copy all files from a template directory into the job workspace.

        Args:
            template_id: The ID of the template to prepare.
            dest_dir: The target workspace directory.
        """
        template_dir = self.get_template_path(template_id)
        dest_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy all files recursively from template folder to dest_dir
            for item in template_dir.iterdir():
                if item.name.startswith("."):
                    continue
                
                dest_path = dest_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest_path)
        except Exception as e:
            raise TemplateManagerError(f"Failed to prepare template workspace: {str(e)}") from e
