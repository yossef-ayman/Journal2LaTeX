"""Configuration and on-disk layout for the Document Generator module.

Every path this module touches lives under a single root
(``document_generator_data/``) so the feature owns its storage outright and can
be removed, backed up or relocated without reaching into the converter's
directories.

Operator-editable values (the reference-number suffix, the default editor and
journal names) are persisted as JSON rather than being read from the
environment: they are changed from the module's own settings screen at runtime,
so they have to survive a restart without anyone editing a ``.env`` file.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("document_generator.config")

# Root of the module's storage.  Overridable so a deployment can point it at a
# mounted volume, and so tests can run against a scratch directory.
DATA_ROOT = Path(
    os.environ.get("DOCUMENT_GENERATOR_DATA", "document_generator_data")
).resolve()

# Master templates: uploaded once, reused for every generation, replaced only
# on an explicit upload.
TEMPLATES_DIR = DATA_ROOT / "templates"
# Superseded templates, kept so a replacement is never a destructive act.
TEMPLATE_ARCHIVE_DIR = DATA_ROOT / "templates_archive"
# One directory per generation batch, holding Output/<paper>/... and the ZIP.
BATCHES_DIR = DATA_ROOT / "batches"
# Scratch space for uploads being inspected before they are accepted.
STAGING_DIR = DATA_ROOT / "staging"

SETTINGS_FILE = DATA_ROOT / "settings.json"

# Defaults for the persisted settings.  Nothing here is specific to any
# particular template: they are the values the placeholder context falls back to
# when a generation request does not override them.
DEFAULT_SETTINGS: Dict[str, Any] = {
    # The journal's short code -- JSAP, IJM, JNS -- and the leading component of
    # every reference number.  Configurable because one installation commonly
    # serves several journals, and because a future journal must need no code
    # change to be numbered correctly.
    "journal_code": "",
    # The suffix in <JournalCode><MMDDYY><BatchOrder><Suffix>.
    "reference_suffix": "A",
    # Filled into {{EDITOR}} / {{JOURNAL}} when the request omits them.
    "editor_name": "",
    "journal_name": "",
    # Extra placeholder values applied to every document, e.g. bank details on
    # an invoice.  Keys are placeholder names without the braces.
    "custom_placeholders": {},
    # Produce a PDF alongside every DOCX.
    "generate_pdf": True,
}

_settings_lock = threading.Lock()


def ensure_directories() -> None:
    """Create the module's storage tree.  Idempotent."""
    for directory in (
        DATA_ROOT,
        TEMPLATES_DIR,
        TEMPLATE_ARCHIVE_DIR,
        BATCHES_DIR,
        STAGING_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def load_settings() -> Dict[str, Any]:
    """Return the persisted settings merged over the defaults.

    Merged rather than replaced so a settings file written by an older version
    gains new keys with sensible values instead of raising ``KeyError`` deep
    inside a generation run.
    """
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))  # deep copy
    if not SETTINGS_FILE.exists():
        return settings
    try:
        stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        # A corrupt settings file must not take the module down: the defaults
        # are always usable, and the operator can re-save from the UI.
        logger.warning("Ignoring unreadable settings file %s: %s", SETTINGS_FILE, exc)
        return settings
    if isinstance(stored, dict):
        settings.update({k: v for k, v in stored.items() if k in settings})
    return settings


def save_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Persist ``updates`` over the current settings and return the result.

    Only known keys are written, so a malformed request cannot inject arbitrary
    state into the settings file.
    """
    ensure_directories()
    with _settings_lock:
        settings = load_settings()
        for key, value in updates.items():
            if key in DEFAULT_SETTINGS and value is not None:
                settings[key] = value
        tmp = SETTINGS_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        # Atomic replace: a crash mid-write must never leave a truncated file.
        tmp.replace(SETTINGS_FILE)
    logger.info("Document Generator settings updated: %s", sorted(updates))
    return settings


def soffice_binary() -> str | None:
    """Locate LibreOffice, honouring the application's configured path.

    Read-only reuse of the converter's configuration: the binary is a machine
    property, and having two places that disagree about where it lives would be
    a maintenance trap.  Falls back to the conventional names when the shared
    configuration is unavailable, so this module never hard-depends on it.
    """
    candidates = []
    try:
        from app.core.config import settings as app_settings

        candidates.append(getattr(app_settings, "SOFFICE_PATH", "soffice"))
    except Exception:  # pragma: no cover - defensive: module must stand alone
        pass
    candidates += ["soffice", "libreoffice"]
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    return None
