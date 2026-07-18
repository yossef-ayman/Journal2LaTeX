import json
import shutil
from pathlib import Path
from typing import List, Optional
from app.core.config import settings
from app.utils.filesystem import normalize_path


class TemplateManagerError(Exception):
    """Exception raised when template management operations fail."""
    pass


class TemplateManager:
    """Service to discover, list, and prepare journal templates for rendering workspaces."""

    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        """Initialize TemplateManager.

        Args:
            templates_dir: The directory containing templates. Defaults to backend/templates/journals.
        """
        if templates_dir:
            self.templates_root = normalize_path(templates_dir)
        else:
            # Resolved relative to backend folder
            self.templates_root = normalize_path(Path(__file__).resolve().parent.parent.parent / "templates" / "journals")

    def list_templates(self) -> List[str]:
        """List all discovered template names.

        Returns:
            A list of template directory names.
        """
        if not self.templates_root.exists() or not self.templates_root.is_dir():
            return []

        templates = []
        for path in self.templates_root.iterdir():
            if path.is_dir() and not path.name.startswith("."):
                # Basic validation: check if template.tex or a class file exists
                if (path / "template.tex").exists():
                    templates.append(path.name)
        return templates

    def get_template_path(self, template_name: str) -> Path:
        """Get the directory path for a specific template.

        Args:
            template_name: The name of the template.

        Returns:
            The Path to the template directory.
        """
        template_dir = self.templates_root / template_name
        if not template_dir.exists() or not template_dir.is_dir():
            raise TemplateManagerError(f"Template '{template_name}' not found under {self.templates_root}")
        return template_dir

    def prepare_workspace(self, template_name: str, dest_dir: Path) -> None:
        """Copy all files from a template directory into the job workspace.

        Args:
            template_name: The name of the template to prepare.
            dest_dir: The target workspace directory.
        """
        template_dir = self.get_template_path(template_name)
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

    def get_template_metadata(self, template_name: str) -> dict:
        """Load and return template.json metadata.

        Args:
            template_name: The name of the template.

        Returns:
            The parsed metadata dict from template.json.
        """
        template_dir = self.get_template_path(template_name)
        metadata_file = template_dir / "template.json"
        
        if not metadata_file.exists():
            return {
                "name": template_name,
                "version": "unknown",
                "journal_title": template_name,
                "publisher": "unknown",
                "doi_prefix": "",
                "class_file": "",
                "supported_features": {}
            }
            
        try:
            return json.loads(metadata_file.read_text(encoding="utf-8"))
        except Exception as e:
            raise TemplateManagerError(f"Failed to read template metadata: {str(e)}")
