"""Iterative layout optimization of the rendered LaTeX document.

Tunes a full set of layout parameters -- margins, font size, line spacing,
paragraph/section spacing, float and caption spacing, bibliography spacing,
and widow/orphan penalties -- to make the compiled PDF match the reference
Word PDF as closely as possible.

All tuned values are injected as a single managed block between
``% J2L-OPT-BEGIN`` / ``% J2L-OPT-END`` markers immediately before
``\\begin{document}``.  The block is regenerated from scratch each iteration,
so no fragile incremental regex edits accumulate in the source.
"""

import json
import math
import re
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.header_reconstructor import HeaderReconstructor
from app.services.visual_comparator import VisualComparator
from app.utils.logger import get_job_logger

_BLOCK_RE = re.compile(r"% J2L-OPT-BEGIN.*?% J2L-OPT-END\n?", re.DOTALL)


@dataclass(frozen=True)
class LayoutParams:
    """Complete set of tunable layout parameters (all clamped to sane ranges)."""

    font_size_pt: float = 10.0        # 8 .. 12
    line_spacing: float = 1.0         # 0.85 .. 1.35
    par_skip_pt: float = 4.0          # 0 .. 12
    margin_in: float = 1.0            # 0.5 .. 1.5
    section_space_ex: float = 2.0     # 0.5 .. 4  (space above sections)
    float_sep_pt: float = 12.0        # 4 .. 24   (\floatsep / \textfloatsep)
    caption_skip_pt: float = 6.0      # 0 .. 14
    bib_item_sep_pt: float = 3.0      # 0 .. 10
    head_sep_pt: float = 12.0         # 4 .. 24
    title_skip_pt: float = 18.0       # 6 .. 36   (space after \maketitle region)

    def clamped(self) -> "LayoutParams":
        def clamp(v, lo, hi):
            return max(lo, min(hi, v))

        return LayoutParams(
            font_size_pt=clamp(self.font_size_pt, 8.0, 12.0),
            line_spacing=clamp(self.line_spacing, 0.85, 1.35),
            par_skip_pt=clamp(self.par_skip_pt, 0.0, 12.0),
            margin_in=clamp(self.margin_in, 0.5, 1.5),
            section_space_ex=clamp(self.section_space_ex, 0.5, 4.0),
            float_sep_pt=clamp(self.float_sep_pt, 4.0, 24.0),
            caption_skip_pt=clamp(self.caption_skip_pt, 0.0, 14.0),
            bib_item_sep_pt=clamp(self.bib_item_sep_pt, 0.0, 10.0),
            head_sep_pt=clamp(self.head_sep_pt, 4.0, 24.0),
            title_skip_pt=clamp(self.title_skip_pt, 6.0, 36.0),
        )


class LayoutOptimizer:
    """Iteratively refine LaTeX layout to match the Word reference rendering."""

    def optimize_layout(
        self, pipeline_service: Any, job_id: str, doc_model: Any, job_dir: Path
    ) -> Dict[str, Any]:
        logger = get_job_logger(job_id, "layout_optimizer")
        logger.info("Starting layout optimization loop for job: %s", job_id)

        intermediate_dir = job_dir / "intermediate"
        intermediate_dir.mkdir(parents=True, exist_ok=True)
        main_tex_path = job_dir / "rendered" / "main.tex"
        rendered_pdf_path = job_dir / "output" / "paper.pdf"

        opt_report: Dict[str, Any] = {
            "enabled": True,
            "iterations": [],
            "best_iteration": 0,
            "final_similarity": 0.0,
            "final_page_count": 0,
            "final_parameters": {},
            "stop_reason": "",
            "elapsed_seconds": 0.0,
        }
        started = time.monotonic()

        try:
            self._run_loop(
                pipeline_service, job_id, job_dir, intermediate_dir,
                main_tex_path, rendered_pdf_path, opt_report, logger,
            )
        except Exception as exc:  # never crash the pipeline; always report
            logger.exception("Layout optimization aborted: %s", exc)
            opt_report["stop_reason"] = f"aborted: {exc}"
        finally:
            opt_report["elapsed_seconds"] = round(time.monotonic() - started, 2)
            (intermediate_dir / "optimization_report.json").write_text(
                json.dumps(opt_report, indent=2), encoding="utf-8"
            )
            logger.info(
                "Layout optimization finished (%s). Best similarity: %.2f%%",
                opt_report["stop_reason"], opt_report["final_similarity"] * 100,
            )
        return opt_report

    # ------------------------------------------------------------------ #

    def _run_loop(
        self, pipeline_service, job_id, job_dir, intermediate_dir,
        main_tex_path, rendered_pdf_path, opt_report, logger,
    ) -> None:
        metadata = pipeline_service.job_manager.get_job(job_id)
        if not metadata or not main_tex_path.exists():
            opt_report["enabled"] = False
            opt_report["stop_reason"] = "missing job metadata or main.tex"
            return

        docx_path = job_dir / "input" / metadata.paper_name
        comparator = VisualComparator()
        header_recon = HeaderReconstructor()

        params = LayoutParams()
        best_params = params
        best_sim = -1.0
        best_tex: Optional[str] = None
        best_pages = 0
        non_improve_count = 0
        orig_pages = 0

        max_iters = settings.OPTIMIZER_MAX_ITERATIONS
        target = settings.OPTIMIZER_TARGET_SIMILARITY
        patience = settings.OPTIMIZER_PATIENCE

        for iteration in range(1, max_iters + 1):
            # 1. Apply current parameters and compile.
            source_before = main_tex_path.read_text(encoding="utf-8")
            self._apply_params(main_tex_path, params)
            pdf_path = pipeline_service.compile(job_id, quiet=True)
            if not pdf_path or not pdf_path.exists():
                logger.warning("Iteration %d: compilation failed; reverting parameters.", iteration)
                main_tex_path.write_text(source_before, encoding="utf-8")
                opt_report["iterations"].append({
                    "iteration": iteration,
                    "status": "compile_failed",
                    "parameters": asdict(params),
                })
                if best_tex is None:
                    # Recompile the reverted source so the job still has a PDF.
                    pipeline_service.compile(job_id, quiet=True)
                    opt_report["stop_reason"] = "first compilation with tuned parameters failed"
                    return
                non_improve_count += 1
                if non_improve_count >= patience:
                    opt_report["stop_reason"] = f"no improvement for {patience} iterations"
                    break
                params = self._perturb_towards(params, best_params)
                continue

            # 2. Compare against reference.
            vis_rep, lay_rep = comparator.compare_documents(
                docx_path, rendered_pdf_path, intermediate_dir, job_id
            )
            if not vis_rep.get("reference_available"):
                opt_report["enabled"] = False
                opt_report["stop_reason"] = "reference PDF unavailable; optimization skipped"
                opt_report["final_page_count"] = lay_rep.get("page_count", {}).get("rendered", 0)
                return

            sim = float(vis_rep.get("average_similarity", 0.0))
            orig_pages = lay_rep.get("page_count", {}).get("original", 0)
            rend_pages = lay_rep.get("page_count", {}).get("rendered", 0)

            header_sim = self._header_similarity(header_recon, intermediate_dir)
            rmse = 255.0 * (1.0 - sim)
            psnr = 20 * math.log10(255.0 / rmse) if rmse > 0 else 99.0

            opt_report["iterations"].append({
                "iteration": iteration,
                "status": "ok",
                "similarity_score": f"{sim * 100:.2f}%",
                "psnr": f"{psnr:.2f} dB",
                "rmse": f"{rmse:.2f}",
                "header_similarity": f"{header_sim * 100:.2f}%",
                "page_count": {"original": orig_pages, "rendered": rend_pages},
                "parameters": asdict(params),
                "remaining_differences": lay_rep.get("layout_differences", []),
            })
            logger.info(
                "Iteration %d: similarity %.2f%%, header %.2f%%, pages %d (target %d)",
                iteration, sim * 100, header_sim * 100, rend_pages, orig_pages,
            )

            improved = sim > best_sim + 1e-6
            if improved:
                best_sim = sim
                best_params = params
                best_pages = rend_pages
                best_tex = main_tex_path.read_text(encoding="utf-8")
                opt_report["best_iteration"] = iteration
                non_improve_count = 0
            else:
                non_improve_count += 1

            if sim >= target:
                opt_report["stop_reason"] = f"target similarity {target:.0%} reached"
                break
            if non_improve_count >= patience:
                opt_report["stop_reason"] = f"no improvement for {patience} iterations"
                break
            if iteration == max_iters:
                opt_report["stop_reason"] = "maximum iterations reached"
                break

            # 3. Propose next parameters.
            params = self._next_params(
                params if improved else best_params,
                orig_pages, rend_pages, iteration,
            )

        # Restore the best-performing version.
        if best_tex is not None:
            current = main_tex_path.read_text(encoding="utf-8")
            if current != best_tex:
                main_tex_path.write_text(best_tex, encoding="utf-8")
                pipeline_service.compile(job_id, quiet=True)
        opt_report["final_similarity"] = max(best_sim, 0.0)
        opt_report["final_page_count"] = best_pages
        opt_report["final_parameters"] = asdict(best_params)
        if not opt_report["stop_reason"]:
            opt_report["stop_reason"] = "loop completed"

    # ------------------------------------------------------------------ #
    # Parameter search
    # ------------------------------------------------------------------ #

    @staticmethod
    def _next_params(base: LayoutParams, orig_pages: int, rend_pages: int, iteration: int) -> LayoutParams:
        """Direction-aware proposal: page-count error drives global density;
        later iterations make finer, rotating single-parameter tweaks."""
        step = max(0.3, 1.0 - iteration * 0.08)  # decay step size

        if orig_pages and rend_pages < orig_pages:
            # Too dense: expand.
            return replace(
                base,
                line_spacing=base.line_spacing + 0.04 * step,
                font_size_pt=base.font_size_pt + 0.25 * step,
                par_skip_pt=base.par_skip_pt + 1.0 * step,
                margin_in=base.margin_in + 0.05 * step,
                section_space_ex=base.section_space_ex + 0.25 * step,
            ).clamped()
        if orig_pages and rend_pages > orig_pages:
            # Too sparse: compress.
            return replace(
                base,
                line_spacing=base.line_spacing - 0.04 * step,
                font_size_pt=base.font_size_pt - 0.25 * step,
                par_skip_pt=base.par_skip_pt - 1.0 * step,
                margin_in=base.margin_in - 0.05 * step,
                section_space_ex=base.section_space_ex - 0.25 * step,
            ).clamped()

        # Page counts match: fine-tune one spacing dimension per iteration.
        tweaks = [
            ("caption_skip_pt", 1.5), ("float_sep_pt", 2.0), ("bib_item_sep_pt", 1.0),
            ("head_sep_pt", 2.0), ("title_skip_pt", 3.0), ("par_skip_pt", 0.5),
        ]
        name, delta = tweaks[iteration % len(tweaks)]
        sign = 1 if iteration % 2 else -1
        return replace(base, **{name: getattr(base, name) + sign * delta * step}).clamped()

    @staticmethod
    def _perturb_towards(params: LayoutParams, best: LayoutParams) -> LayoutParams:
        """After a failed compile, move halfway back towards the best-known point."""
        return LayoutParams(**{
            k: (getattr(params, k) + getattr(best, k)) / 2.0
            for k in asdict(params)
        }).clamped()

    # ------------------------------------------------------------------ #
    # LaTeX injection
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_block(p: LayoutParams) -> str:
        baseline = round(p.font_size_pt * 1.2, 2)
        return "\n".join([
            "% J2L-OPT-BEGIN (auto-generated; regenerated every iteration)",
            "\\makeatletter",
            "\\@ifpackageloaded{geometry}{}{\\usepackage{geometry}}",
            f"\\geometry{{margin={p.margin_in:.2f}in}}",
            f"\\renewcommand{{\\baselinestretch}}{{{p.line_spacing:.2f}}}",
            f"\\AtBeginDocument{{\\fontsize{{{p.font_size_pt:.1f}pt}}{{{baseline}pt}}\\selectfont}}",
            f"\\setlength{{\\parskip}}{{{p.par_skip_pt:.1f}pt}}",
            f"\\setlength{{\\floatsep}}{{{p.float_sep_pt:.1f}pt plus 2pt minus 2pt}}",
            f"\\setlength{{\\textfloatsep}}{{{p.float_sep_pt + 4:.1f}pt plus 2pt minus 2pt}}",
            f"\\setlength{{\\intextsep}}{{{p.float_sep_pt:.1f}pt plus 2pt minus 2pt}}",
            f"\\setlength{{\\abovecaptionskip}}{{{p.caption_skip_pt:.1f}pt}}",
            f"\\setlength{{\\belowcaptionskip}}{{{max(0.0, p.caption_skip_pt - 2):.1f}pt}}",
            # Bibliography spacing: honour natbib's \bibsep when present.
            f"\\AtBeginDocument{{\\@ifundefined{{bibsep}}{{}}{{\\setlength{{\\bibsep}}{{{p.bib_item_sep_pt:.1f}pt}}}}}}",
            "\\widowpenalty=10000",
            "\\clubpenalty=10000",
            "\\makeatother",
            "% J2L-OPT-END",
            "",
        ])

    def _apply_params(self, main_tex_path: Path, params: LayoutParams) -> None:
        content = main_tex_path.read_text(encoding="utf-8")
        content = _BLOCK_RE.sub("", content)
        block = self._build_block(params)
        begin_doc = "\\begin{document}"
        if begin_doc in content:
            content = content.replace(begin_doc, block + begin_doc, 1)
        else:
            content = block + content
        main_tex_path.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------ #

    @staticmethod
    def _header_similarity(header_recon: HeaderReconstructor, intermediate_dir: Path) -> float:
        orig_img = intermediate_dir / "orig_pages" / "page_1.png"
        rend_img = intermediate_dir / "rend_pages" / "page_1.png"
        if not (orig_img.exists() and rend_img.exists()):
            return 0.0
        sim = header_recon.compare_headers(orig_img, rend_img)

        header_rep_path = intermediate_dir / "header_report.json"
        if header_rep_path.exists():
            try:
                data = json.loads(header_rep_path.read_text(encoding="utf-8"))
                data["similarity_score_for_header_alone"] = f"{sim * 100:.2f}%"
                header_rep_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except (OSError, json.JSONDecodeError):
                pass
        return sim
