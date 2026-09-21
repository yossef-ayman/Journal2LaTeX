import datetime
import json
import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import List, Optional
from app.utils.filesystem import (
    UnsafePathError,
    is_safe_component,
    is_within,
    normalize_path,
    read_text_file,
    safe_join,
)
from app.utils.zip_utils import (
    UnsafeArchiveError,
    extract_zip as safe_extract_zip,
    validate_archive_members,
    zip_directory,
)


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
        # The template ID arrives straight from the URL and from request bodies,
        # so it is validated as a single safe component before it is ever joined
        # to a root: "../../etc" (or its percent-encoded form) must not resolve.
        if not is_safe_component(template_id):
            raise TemplateManagerError(f"Template with ID '{template_id}' not found.")

        for root in (self.uploaded_root, self.built_in_root):
            try:
                candidate = safe_join(root, template_id)
            except UnsafePathError:
                continue
            # A symlinked template directory would still point elsewhere.
            if candidate.is_dir() and not candidate.is_symlink() \
                    and is_within(root, candidate.resolve()):
                return candidate

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
            # 1. Structural safety: traversal, absolute paths, symlinks, special
            #    files and size bombs are all rejected here, before extraction.
            #    (The previous string-prefix containment test also accepted a
            #    sibling directory whose name merely started with the target's.)
            try:
                validate_archive_members(zip_file_path, extract_dir)
            except UnsafeArchiveError as exc:
                raise TemplateManagerError(f"Security alert: {exc}")

            # 2. Policy: no executable/script payloads inside a template.
            with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                for member in zip_ref.infolist():
                    if self._is_forbidden_file(member.filename):
                        raise TemplateManagerError(
                            f"Security alert: File {member.filename} is a forbidden "
                            "executable or configuration payload."
                        )

            # 3. All checks passed -- extract member by member (never extractall).
            safe_extract_zip(zip_file_path, extract_dir)

            # Users routinely zip the template FOLDER rather than its contents,
            # producing a single wrapper directory ("MyTemplate/...").  Flatten
            # it (repeatedly, for nested wrappers) so template files sit at the
            # template root where the compiler expects them.
            self._flatten_single_wrapper(extract_dir)

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
                entry_file_path = self._choose_entry_file(extract_dir, primary_candidates)
            elif secondary_candidates:
                entry_file_path = self._choose_entry_file(extract_dir, secondary_candidates)
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

    @staticmethod
    def _choose_entry_file(extract_dir: Path, candidates: List[Path]) -> Path:
        """Pick the manuscript entry point out of several compilable .tex files.

        Journal packages routinely ship more than one compilable file: the
        manuscript skeleton the author is meant to fill in, plus class
        documentation, style guides and worked examples.  Choosing by filename
        alone fails whenever the publisher uses its own naming ("ijca.tex",
        "sample-sigconf.tex"), so the decision is made from the *structure* of
        each file and the filename only breaks ties.

        Signals, in the order they matter:
          * files that another candidate \\input or \\include are components,
            never the entry point;
          * the entry point carries manuscript front matter (\\maketitle, a
            title/author block, an abstract) and body sectioning;
          * package documentation is recognised by its own markers (\\DocInput,
            \\OnlyDescription, ltxdoc/doc) and rejected;
          * shallower paths beat files buried in doc/ or examples/.
        """
        texts = {}
        for path in candidates:
            try:
                texts[path] = read_text_file(path)
            except Exception:
                texts[path] = ""

        # Files pulled in by another candidate are components of it.
        included = set()
        for path, content in texts.items():
            for other in candidates:
                if other == path:
                    continue
                stem = other.stem
                if f"{{{stem}}}" in content and (
                    "\\input" in content or "\\include" in content
                ):
                    included.add(other)

        def score(path: Path) -> tuple:
            rel = path.relative_to(extract_dir)
            content = texts.get(path, "")
            lowered = content.lower()
            points = 0
            if path in included:
                points -= 60
            if any(
                marker in content
                for marker in ("\\DocInput", "\\OnlyDescription", "\\DocumentMetadata")
            ) or "documentclass{ltxdoc}" in content.replace(" ", ""):
                points -= 50
            for part in rel.parts[:-1]:
                if part.lower() in {"doc", "docs", "documentation", "example", "examples", "sample", "samples"}:
                    points -= 25
            for marker, weight in (
                ("\\maketitle", 12),
                ("\\title", 10),
                ("\\author", 8),
                ("\\begin{abstract}", 8),
                ("\\bibliography", 4),
                ("\\keywords", 3),
            ):
                if marker in content:
                    points += weight
            # Placeholder-style templates are unambiguous entry points.
            if "__CONTENT__" in content or "__TITLE__" in content:
                points += 20
            # A fully written-out body marks a worked example paper shipped
            # alongside the blank skeleton; the skeleton is what a manuscript
            # should be rendered into.  \section is deliberately *not* a positive
            # signal for the same reason -- a blank template has none.
            if content.count("\\section") >= 3:
                points -= 8
            if "lipsum" in lowered or "your text here" in lowered:
                points += 2
            points -= 3 * (len(rel.parts) - 1)
            # Filename is the final tiebreaker only.
            preferred = {"template.tex", "main.tex", "paper.tex", "manuscript.tex", "bare_jrnl.tex"}
            name_bonus = 1 if rel.name.lower() in preferred else 0
            return (points, name_bonus, -len(rel.as_posix()))

        return max(candidates, key=score)

    @staticmethod
    def _flatten_single_wrapper(extract_dir: Path) -> None:
        """Hoist contents when the archive extracted to one wrapper directory.

        Applied repeatedly so double-zipped archives also flatten.  A root that
        already contains files (or several entries) is left untouched, so a
        legitimate multi-entry layout with subfolders is preserved.
        """
        for _ in range(5):  # bounded: no realistic archive nests deeper
            entries = [p for p in extract_dir.iterdir() if not p.name.startswith(".")]
            if len(entries) != 1 or not entries[0].is_dir():
                return
            wrapper = entries[0]
            for item in wrapper.iterdir():
                shutil.move(str(item), str(extract_dir / item.name))
            wrapper.rmdir()

    # ------------------------------------------------------------------ #
    # Template file management (browse / preview / edit / add / delete /
    # download / validate) -- the ZIP Template Editor backend.
    # ------------------------------------------------------------------ #

    #: extensions never accepted inside a template
    FORBIDDEN_EXTENSIONS = {
        ".sh", ".bat", ".cmd", ".ps1", ".vbs", ".vbe", ".wsf", ".wsh",
        ".pif", ".com", ".scr", ".msi", ".dll", ".so", ".dylib", ".jar",
        ".rb", ".exe", ".py", ".pl", ".php", ".js", ".reg", ".hta",
    }
    #: specific dangerous filenames never accepted inside a template
    FORBIDDEN_NAMES = {
        "latexmkrc", ".latexmkrc", ".bashrc", ".bash_profile", ".profile",
        ".zshrc", ".env", ".git", ".gitconfig", ".htaccess", "web.config",
    }
    #: extensions treated as editable text
    TEXT_EXTENSIONS = {
        ".tex", ".cls", ".sty", ".bst", ".bib", ".txt", ".md", ".json",
        ".cfg", ".def", ".clo", ".ins", ".dtx", ".csv", ".log",
    }

    @classmethod
    def _is_forbidden_file(cls, filename: str) -> bool:
        """Check if a file has a forbidden executable/script extension or name."""
        p = Path(filename)
        name_lower = p.name.lower()
        suffix_lower = p.suffix.lower()
        if name_lower in cls.FORBIDDEN_NAMES:
            return True
        if suffix_lower in cls.FORBIDDEN_EXTENSIONS:
            return True
        # Check all suffixes for compound extensions like .tar.gz or malicious doubles
        for s in p.suffixes:
            if s.lower() in cls.FORBIDDEN_EXTENSIONS:
                return True
        return False

    def _resolve_member(self, template_id: str, rel_path: str,
                        must_exist: bool = True) -> Path:
        """Resolve *rel_path* inside the template dir, rejecting traversal."""
        template_dir = self.get_template_path(template_id)
        candidate = (template_dir / rel_path).resolve()
        root = template_dir.resolve()
        if root != candidate and root not in candidate.parents:
            raise TemplateManagerError("Invalid path: escapes the template directory.")
        if must_exist and not candidate.exists():
            raise TemplateManagerError(f"File not found in template: {rel_path}")
        return candidate

    def _require_uploaded(self, template_id: str) -> Path:
        """Return the template dir, ensuring it is an uploaded (editable) one."""
        template_dir = self.get_template_path(template_id)
        if self.uploaded_root.resolve() not in template_dir.resolve().parents:
            raise TemplateManagerError(
                "Built-in templates are read-only; upload a copy to edit it."
            )
        return template_dir

    def list_files(self, template_id: str) -> List[dict]:
        """Recursive file listing of a template: path, size, kind, editability."""
        template_dir = self.get_template_path(template_id)
        entries: List[dict] = []
        for path in sorted(template_dir.rglob("*")):
            if any(part.startswith(".") for part in path.relative_to(template_dir).parts):
                continue
            rel = path.relative_to(template_dir).as_posix()
            if path.is_dir():
                entries.append({"path": rel, "type": "dir", "size": None})
            else:
                suffix = path.suffix.lower()
                entries.append({
                    "path": rel,
                    "type": "file",
                    "size": path.stat().st_size,
                    "is_text": suffix in self.TEXT_EXTENSIONS,
                })
        return entries

    def read_file(self, template_id: str, rel_path: str) -> dict:
        """Preview one template file.  Text files return their content; binary
        files return base64 so images can still be previewed client-side."""
        path = self._resolve_member(template_id, rel_path)
        if path.is_dir():
            raise TemplateManagerError(f"'{rel_path}' is a directory, not a file.")
        suffix = path.suffix.lower()
        size = path.stat().st_size
        if suffix in self.TEXT_EXTENSIONS:
            return {
                "path": rel_path, "encoding": "text", "size": size,
                "content": read_text_file(path),
            }
        import base64
        if size > 10 * 1024 * 1024:
            raise TemplateManagerError("File too large to preview (limit 10 MB).")
        return {
            "path": rel_path, "encoding": "base64", "size": size,
            "content": base64.b64encode(path.read_bytes()).decode("ascii"),
        }

    def write_file(self, template_id: str, rel_path: str, content: str,
                   encoding: str = "text") -> dict:
        """Create or replace one file in an uploaded template.

        ``encoding='text'`` writes UTF-8 text; ``'base64'`` decodes and writes
        bytes (for replacing images/logos).  Parent directories are created.
        """
        self._require_uploaded(template_id)
        if self._is_forbidden_file(rel_path):
            raise TemplateManagerError(
                f"File '{rel_path}' is not allowed in templates due to security restrictions."
            )
        path = self._resolve_member(template_id, rel_path, must_exist=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if encoding == "base64":
                import base64
                path.write_bytes(base64.b64decode(content))
            else:
                path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise TemplateManagerError(f"Failed to write '{rel_path}': {e}")
        return {"path": rel_path, "size": path.stat().st_size}

    def delete_file(self, template_id: str, rel_path: str) -> None:
        """Delete one file (or empty directory) from an uploaded template."""
        self._require_uploaded(template_id)
        if Path(rel_path).as_posix() == "template.json":
            raise TemplateManagerError("template.json is managed by the system and cannot be deleted.")
        path = self._resolve_member(template_id, rel_path)
        try:
            if path.is_dir():
                # Only empty directories -- deleting a tree must be deliberate.
                path.rmdir()
            else:
                path.unlink()
        except OSError as e:
            raise TemplateManagerError(f"Failed to delete '{rel_path}': {e}")

    def export_zip(self, template_id: str, dest_dir: Path) -> Path:
        """Package a template directory (built-in or uploaded, including any
        edits) into a fresh zip for download.  Returns the zip path."""
        # get_template_path has already validated template_id as a single safe
        # component, so it is safe to use in the archive's own file name.
        template_dir = self.get_template_path(template_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        zip_path = dest_dir / f"{template_id}.zip"
        try:
            # Uses the shared hardened packer: symlinks are skipped rather than
            # followed, and entry count / total size are bounded.
            zip_directory(template_dir, zip_path)
        except Exception as e:
            raise TemplateManagerError(f"Failed to package template: {e}")
        return zip_path

    def validate_template(self, template_id: str) -> dict:
        """Static validation of a template before conversion.

        Checks the entry file exists and is a compilable document, that every
        locally-referenced resource (class/style/graphics/inputs) is present
        either in the template or the TeX installation, and reports missing
        required files.  Returns {'valid', 'errors', 'warnings', 'checks'}.
        """
        errors: List[str] = []
        warnings: List[str] = []
        checks: List[dict] = []

        def check(name: str, ok: bool, detail: str, fatal: bool = True):
            checks.append({"name": name, "ok": bool(ok), "detail": detail})
            if not ok:
                (errors if fatal else warnings).append(f"{name}: {detail}")

        try:
            template_dir = self.get_template_path(template_id)
        except TemplateManagerError as e:
            return {"valid": False, "errors": [str(e)], "warnings": [], "checks": []}

        meta = self.get_template_metadata(template_id)
        entry_rel = meta.get("entry_file") or "template.tex"
        entry = template_dir / entry_rel
        check("entry_file_exists", entry.is_file(),
              f"entry file '{entry_rel}'" + ("" if entry.is_file() else " is missing"))

        source = ""
        if entry.is_file():
            try:
                source = read_text_file(entry)
            except Exception as e:
                check("entry_file_readable", False, f"cannot read '{entry_rel}': {e}")
        if source:
            check("has_documentclass",
                  "\\documentclass" in source or "\\documentstyle" in source,
                  "\\documentclass declaration present"
                  if "\\documentclass" in source else "no \\documentclass found")
            check("has_begin_document", "\\begin{document}" in source,
                  "\\begin{document} present" if "\\begin{document}" in source
                  else "no \\begin{document} found")

            # Resolve every dependency the entry file references, using the
            # compiler's own resolution rules (local file, TeX tree, missing).
            from app.compiler.latex_compiler import LatexCompiler
            missing_local: List[str] = []
            missing_packages: List[str] = []
            for kind, target in LatexCompiler._extract_dependencies(source):
                status = LatexCompiler._resolve_dependency(kind, target, template_dir)
                if status == "missing":
                    if kind in ("usepackage", "requirepackage"):
                        missing_packages.append(target)
                    else:
                        missing_local.append(f"{kind} -> {target}")
            check("required_resources_present", not missing_local,
                  "all referenced local resources found" if not missing_local
                  else "missing: " + ", ".join(missing_local))
            check("optional_packages_available", not missing_packages,
                  "all packages available" if not missing_packages
                  else "not installed (skipped at compile time via the "
                       "compatibility layer): " + ", ".join(missing_packages),
                  fatal=False)

        class_file = meta.get("class_file")
        if class_file:
            check("class_file_present", (template_dir / class_file).is_file(),
                  f"class file '{class_file}'"
                  + ("" if (template_dir / class_file).is_file() else " is missing"),
                  fatal=False)

        forbidden = [
            p.relative_to(template_dir).as_posix()
            for p in template_dir.rglob("*")
            if p.is_file() and self._is_forbidden_file(p.name)
        ]
        check("no_forbidden_files", not forbidden,
              "no forbidden file types" if not forbidden
              else "forbidden files present: " + ", ".join(forbidden))

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "checks": checks,
        }

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
