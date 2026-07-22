import hashlib
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from app.core.config import settings
from app.models.conversion import CompilationResult
from app.compiler.compat_layer import apply_compatibility_layer
from app.utils.logger import get_job_logger

# Extensions whose files are template resources that must travel with the
# document (as opposed to being provided by the global TeX installation).
_RESOURCE_EXTS = {
    ".cls": "document class",
    ".sty": "package / style",
    ".bst": "bibliography style",
    ".bib": "bibliography database",
    ".eps": "graphic (EPS)",
    ".pdf": "graphic (PDF)",
    ".png": "graphic (PNG)",
    ".jpg": "graphic (JPEG)",
    ".jpeg": "graphic (JPEG)",
    ".svg": "graphic (SVG)",
    ".ttf": "font",
    ".otf": "font",
    ".tex": "included source",
}
# Candidate extensions probed for \includegraphics references given without one.
_GRAPHIC_EXTS = (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg", ".mps")


@lru_cache(maxsize=None)
def _kpsewhich(name: str) -> bool:
    """True when *name* is resolvable in the global TeX installation."""
    try:
        res = subprocess.run(
            ["kpsewhich", name], capture_output=True, text=True, check=False, timeout=15
        )
        return res.returncode == 0 and bool(res.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


class LatexCompilerException(Exception):
    """Base exception for LaTeX compiler errors."""
    pass


class LatexCompilationError(LatexCompilerException):
    """Exception raised when compilation fails."""

    def __init__(self, message: str, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


class LatexCompiler:
    """Service to handle compilation of LaTeX documents using pdflatex or latexmk."""

    _latexmk_probe_result = None  # cached across compilations

    MAX_PDFLATEX_PASSES = 3

    def _run_pdflatex(self, tex_path: Path, working_dir: Path, job_id: str) -> subprocess.CompletedProcess:
        """Run a single pdflatex pass."""
        cmd = [
            settings.PDFLATEX_PATH,
            "-interaction=nonstopmode",
            "-file-line-error",
            str(tex_path)
        ]
        logger = get_job_logger(job_id, "compiler")
        logger.debug("Executing pdflatex pass: %s in directory: %s", " ".join(cmd), working_dir)
        return subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=settings.COMPILE_TIMEOUT,
        )

    def _file_hash(self, path: Path) -> Optional[str]:
        """Return MD5 hex digest of a file, or None if it doesn't exist."""
        if not path.exists():
            return None
        return hashlib.md5(path.read_bytes()).hexdigest()

    def _latexmk_available(self, logger) -> bool:
        """Probe for latexmk once per process and cache the result."""
        cls = type(self)
        if cls._latexmk_probe_result is None:
            available = False
            if settings.LATEXMK_PATH:
                try:
                    check_res = subprocess.run(
                        [settings.LATEXMK_PATH, "-v"],
                        capture_output=True, text=True, check=False, timeout=30,
                    )
                    available = check_res.returncode == 0
                except (FileNotFoundError, OSError, subprocess.SubprocessError):
                    logger.warning("latexmk not found; falling back to pdflatex.")
            cls._latexmk_probe_result = available
        return cls._latexmk_probe_result

    # ------------------------------------------------------------------ #
    # Pre-flight dependency verification
    # ------------------------------------------------------------------ #

    def _preflight(self, tex_path: Path, working_dir: Path, job_id: str, logger) -> None:
        """Log the workspace tree and a template-resource manifest, then verify
        every referenced dependency resolves.  Raises LatexCompilationError
        before pdflatex runs if a template-local resource is missing.

        System packages provided by the TeX installation (article.cls,
        graphicx.sty, ...) are considered resolved via kpsewhich; only
        resources the template is expected to ship (its own .cls/.sty/.bst and
        graphics referenced by relative path) are treated as required-local.
        """
        # 1. Workspace tree (requirement: show the rendered dir before compile).
        logger.info("Rendered working directory tree before compilation:\n%s",
                    self._tree(working_dir))

        # 2. Manifest of every resource present in the workspace, with reason.
        manifest = self._resource_manifest(working_dir)
        lines = [f"  {rel:<40} {reason}" for rel, reason in manifest]
        logger.info("Template resource manifest (%d files):\n%s",
                    len(manifest), "\n".join(lines) if lines else "  (none)")

        # 3. Resolve dependencies referenced by the document.
        source = tex_path.read_text(encoding="utf-8", errors="replace")
        deps = self._extract_dependencies(source)
        resolved: List[str] = []
        missing: List[str] = []
        optional_missing: List[str] = []
        for kind, target in deps:
            status = self._resolve_dependency(kind, target, working_dir)
            resolved.append(f"  [{status.upper():<7}] {kind:<15} {target}")
            if status == "missing":
                # A missing package is non-fatal: the compatibility layer guards
                # every preamble \usepackage with \IfFileExists so an absent
                # optional package is skipped (with a fallback) at compile time
                # rather than aborting.  Genuinely required resources -- the
                # document class and template-shipped files -- remain fatal.
                if kind in ("usepackage", "requirepackage"):
                    optional_missing.append(f"{kind} -> {target}")
                else:
                    missing.append(f"{kind} -> {target}")
        logger.info("Dependency resolution (%d references):\n%s",
                    len(deps), "\n".join(resolved) if resolved else "  (none)")
        if optional_missing:
            logger.warning(
                "Optional package(s) not installed; skipped via compatibility "
                "layer, compilation continues:\n  - %s",
                "\n  - ".join(optional_missing),
            )

        if missing:
            msg = (
                "Template is missing required local resource(s); aborting before "
                "pdflatex. Ensure the template package ships these files:\n  - "
                + "\n  - ".join(missing)
            )
            logger.error(msg)
            raise LatexCompilationError(msg)

    @staticmethod
    def _tree(root: Path) -> str:
        """Render a compact recursive listing of *root*."""
        entries = []
        for p in sorted(root.rglob("*")):
            if any(part.startswith(".") for part in p.relative_to(root).parts):
                continue
            depth = len(p.relative_to(root).parts) - 1
            marker = "/" if p.is_dir() else ""
            entries.append(f"  {'  ' * depth}{p.name}{marker}")
        return "\n".join(entries) if entries else "  (empty)"

    @staticmethod
    def _resource_manifest(working_dir: Path) -> List[Tuple[str, str]]:
        """List template resources in the workspace with a per-file reason.

        Renderer-generated media (under ``media/``) and LaTeX build artefacts
        (main.aux/.log/.pdf/...) are labelled as such so the manifest clearly
        separates shipped template files from generated ones.
        """
        build_exts = {".aux", ".log", ".out", ".fls", ".fdb_latexmk", ".toc",
                      ".lof", ".lot", ".bbl", ".blg", ".synctex", ".gz"}
        manifest = []
        for p in sorted(working_dir.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(working_dir)
            if any(part.startswith(".") for part in rel.parts):
                continue
            ext = p.suffix.lower()
            if rel.parts and rel.parts[0] == "media":
                reason = "renderer-generated media"
            elif p.stem == "main" or ext in build_exts:
                reason = "generated document / build artefact"
            elif ext in _RESOURCE_EXTS:
                reason = f"template resource ({_RESOURCE_EXTS[ext]})"
            elif p.name in ("template.json",):
                reason = "template metadata"
            else:
                reason = "template resource"
            manifest.append((str(rel), reason))
        return manifest

    @staticmethod
    def _extract_dependencies(source: str) -> List[Tuple[str, str]]:
        """Extract (kind, target) dependency references from LaTeX source.

        Comment lines are stripped first so commented-out references are
        ignored.  Multi-item \\usepackage{a,b,c} lists are split.
        """
        # Strip comments (unescaped %) line by line.
        clean_lines = []
        for line in source.splitlines():
            idx = 0
            out = []
            while idx < len(line):
                ch = line[idx]
                if ch == "\\" and idx + 1 < len(line):
                    out.append(line[idx:idx + 2]); idx += 2; continue
                if ch == "%":
                    break
                out.append(ch); idx += 1
            clean_lines.append("".join(out))
        text = "\n".join(clean_lines)

        deps: List[Tuple[str, str]] = []

        def add_multi(kind, arg):
            for name in arg.split(","):
                name = name.strip()
                if name:
                    deps.append((kind, name))

        for m in re.finditer(r"\\documentclass\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}", text):
            deps.append(("documentclass", m.group(1).strip()))
        for m in re.finditer(r"\\(?:usepackage|RequirePackage)\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}", text):
            add_multi("usepackage", m.group(1))
        for m in re.finditer(r"\\bibliographystyle\s*\{([^}]*)\}", text):
            deps.append(("bibliographystyle", m.group(1).strip()))
        for m in re.finditer(r"\\bibliography\s*\{([^}]*)\}", text):
            add_multi("bibliography", m.group(1))
        for m in re.finditer(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}", text):
            deps.append(("includegraphics", m.group(1).strip()))
        for m in re.finditer(r"\\(?:input|include)\s*\{([^}]*)\}", text):
            deps.append(("input", m.group(1).strip()))
        # De-duplicate, preserving order.
        seen = set()
        unique = []
        for d in deps:
            if d not in seen:
                seen.add(d); unique.append(d)
        return unique

    @staticmethod
    def _resolve_dependency(kind: str, target: str, working_dir: Path) -> str:
        """Return 'local', 'system', 'dynamic', or 'missing' for one dependency."""
        # Targets containing a macro (\\) or parameter (#) or grouping are
        # resolved by TeX at run time (e.g. \\includegraphics{\\psfig@file}
        # inside a macro body); they cannot be checked statically.
        if any(ch in target for ch in ("\\", "#", "{", "}")):
            return "dynamic"

        def local_exists(candidates) -> bool:
            # pdflatex resolves \documentclass/\usepackage from the working
            # directory root (or TEXMF); \includegraphics/\input from a path
            # relative to main.tex.  Both cases are exact root-relative lookups
            # -- a resource buried in a subdirectory is NOT found, so we do not
            # rglob for a basename match (which would mask a real miss).
            for cand in candidates:
                if (working_dir / cand.lstrip("./")).is_file():
                    return True
            return False

        if kind == "documentclass":
            fn = f"{target}.cls"
            if local_exists([fn]):
                return "local"
            return "system" if _kpsewhich(fn) else "missing"

        if kind == "usepackage":
            fn = f"{target}.sty"
            if local_exists([fn]):
                return "local"
            return "system" if _kpsewhich(fn) else "missing"

        if kind == "bibliographystyle":
            fn = f"{target}.bst"
            if local_exists([fn]):
                return "local"
            return "system" if _kpsewhich(fn) else "missing"

        if kind == "bibliography":
            return "local" if local_exists([f"{target}.bib", target]) else "missing"

        if kind == "includegraphics":
            has_ext = Path(target).suffix.lower() in _GRAPHIC_EXTS
            candidates = [target] if has_ext else [target + e for e in _GRAPHIC_EXTS]
            return "local" if local_exists(candidates) else "missing"

        if kind == "input":
            candidates = [target, f"{target}.tex"]
            if local_exists(candidates):
                return "local"
            return "system" if _kpsewhich(target) or _kpsewhich(f"{target}.tex") else "missing"

        return "local"

    def compile_tex(self, tex_path: Path, output_dir: Path, job_id: str) -> CompilationResult:
        """Compile the LaTeX file into a PDF.

        Tries using latexmk if configured/available, otherwise falls back to pdflatex
        with multiple passes to resolve cross-references.

        Args:
            tex_path: Path to the .tex file.
            output_dir: Directory where the final PDF should be saved.
            job_id: The job ID for logging.

        Returns:
            A CompilationResult object.

        Raises:
            LatexCompilationError: If compilation fails.
        """
        logger = get_job_logger(job_id, "compiler")
        logger.info("Starting LaTeX compilation for: %s", tex_path)

        if not tex_path.exists():
            msg = f"LaTeX file not found: {tex_path}"
            logger.error(msg)
            raise LatexCompilationError(msg)

        working_dir = tex_path.parent

        # Generic template compatibility layer: guard optional packages behind
        # \IfFileExists (+ internal fall-backs), ensure named colours resolve
        # regardless of the local xcolor palette, and nudge the body font size.
        # Applied to the final main.tex so it works for any template -- built-in
        # or uploaded -- and never lets an absent package/colour abort the build.
        try:
            original = tex_path.read_text(encoding="utf-8", errors="replace")
            # Also scan the template's own class/style files so named colours
            # used *inside* the class get a fallback too (the class is not edited).
            resource_texts: List[str] = []
            for res in sorted(working_dir.glob("*.cls")) + sorted(working_dir.glob("*.sty")):
                try:
                    resource_texts.append(res.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    continue
            patched = apply_compatibility_layer(original, resource_texts)
            if patched != original:
                tex_path.write_text(patched, encoding="utf-8")
                logger.info("Applied template compatibility layer to %s", tex_path.name)
        except Exception as exc:  # never let the safety layer itself break a build
            logger.warning("Compatibility layer skipped (%s): %s", type(exc).__name__, exc)

        # Pre-flight: log the workspace tree + a manifest of template resources,
        # verify every dependency referenced by the document resolves either
        # locally or in the global TeX tree, and fail early (before pdflatex)
        # with a clear message if a template-local resource is missing.
        self._preflight(tex_path, working_dir, job_id, logger)

        # Output dir setup
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = working_dir / tex_path.with_suffix(".pdf").name
        log_path = tex_path.with_suffix(".log")
        aux_path = tex_path.with_suffix(".aux")

        stdout_combined = ""
        stderr_combined = ""

        # Remove any stale PDF from a previous pass so a failed compile is not
        # masked by an old artifact still sitting in the working directory.
        try:
            if pdf_path.exists():
                pdf_path.unlink()
        except OSError:
            logger.warning("Could not remove stale PDF before compilation: %s", pdf_path)

        use_latexmk = self._latexmk_available(logger)

        try:
            if use_latexmk:
                logger.info("Using latexmk compiler.")
                cmd = [
                    settings.LATEXMK_PATH,
                    "-pdf",
                    "-g",  # force processing: we delete the old PDF ourselves,
                           # and latexmk's up-to-date check otherwise refuses to
                           # rebuild after a previous failed invocation
                    "-interaction=nonstopmode",
                    "-file-line-error",
                    str(tex_path)
                ]
                result = subprocess.run(
                    cmd,
                    cwd=working_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                    encoding="utf-8",
                    errors="replace",
                    timeout=settings.COMPILE_TIMEOUT,
                )
                stdout_combined = result.stdout or ""
                stderr_combined = result.stderr or ""
            else:
                logger.info("Using pdflatex compiler (up to %d passes).", self.MAX_PDFLATEX_PASSES)
                prev_aux_hash = None
                for pass_num in range(1, self.MAX_PDFLATEX_PASSES + 1):
                    logger.info("pdflatex pass %d/%d", pass_num, self.MAX_PDFLATEX_PASSES)
                    result = self._run_pdflatex(tex_path, working_dir, job_id)
                    if result.stdout:
                        stdout_combined += f"\n--- Pass {pass_num} ---\n" + result.stdout
                    if result.stderr:
                        stderr_combined += f"\n--- Pass {pass_num} ---\n" + result.stderr

                    # Check if aux file has stabilized
                    new_hash = self._file_hash(aux_path)
                    if prev_aux_hash is not None and new_hash == prev_aux_hash:
                        logger.info("References stable after pass %d.", pass_num)
                        break
                    prev_aux_hash = new_hash

            # Collect output
            stdout_content = stdout_combined
            stderr_content = stderr_combined

            success = pdf_path.exists()

            # Write compiler output to job logs
            job_logs_dir = working_dir.parent / "logs"
            job_logs_dir.mkdir(parents=True, exist_ok=True)
            compiler_raw_log = job_logs_dir / "compiler_raw.log"
            compiler_raw_log.write_text(f"STDOUT:\n{stdout_content}\n\nSTDERR:\n{stderr_content}", encoding="utf-8")

            if not success:
                msg = f"LaTeX compilation failed. PDF not generated."
                logger.error("%s Check raw logs for details.", msg)
                raise LatexCompilationError(msg, stdout_content, stderr_content)

            # Copy PDF to output folder
            dest_pdf_path = output_dir / "paper.pdf"
            shutil.copy2(pdf_path, dest_pdf_path)

            # Copy standard log to output
            dest_log_path = output_dir / log_path.name
            if log_path.exists():
                shutil.copy2(log_path, dest_log_path)

            logger.info("Compilation completed successfully. PDF generated at: %s", dest_pdf_path)

            return CompilationResult(
                success=True,
                pdf_path=dest_pdf_path,
                log_path=dest_log_path,
                stdout=stdout_content,
                stderr=stderr_content
            )

        except subprocess.SubprocessError as e:
            msg = f"Subprocess error running compiler: {str(e)}"
            logger.exception(msg)
            raise LatexCompilationError(msg)
        except Exception as e:
            if not isinstance(e, LatexCompilerException):
                msg = f"Unexpected error during compilation: {str(e)}"
                logger.exception(msg)
                raise LatexCompilationError(msg)
            raise
