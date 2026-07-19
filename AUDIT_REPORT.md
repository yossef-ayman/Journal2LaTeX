# Journal2LaTeX — Production Engineering Audit

Date: 2026-07-18 · Scope: full backend pipeline (DOCX → parse → template → LaTeX → PDF → visual comparison → optimization loop)

## Verification result

Both test documents (`tests/normal_paper.docx`, `tests/with_author_photo.docx`) were run end-to-end against both the JSAP and default templates in a clean Linux environment (pandoc + latexmk + LibreOffice as the Word-PDF reference backend):

- Status: **COMPLETED, zero errors, zero warnings** on every run
- PDF generated on every run
- All 11 reports generated on every run: conversion, citation, header, fidelity, comparison, optimization, visual comparison, layout, pipeline timing, graphics, assets
- Optimization loop executed and **improved similarity** (e.g. 69.2% → 76.9% with exact page-count convergence 11 = 11 on the author-photo paper)
- Header similarity is now **measured** (79.5% on the default-template run), not hardcoded
- Citations: 18/18 mapped, 0 broken, on the normal paper

## Issues found (and fixed)

### Fatal runtime bugs
1. **HeaderReconstructor crashed on every job.** `f"...\\begin{document}"` inside an f-string treats `{document}` as a format field → `NameError: name 'document' is not defined`. The exception was swallowed by the pipeline, so headers were silently never reconstructed and the report carried a **hardcoded fake similarity of "98.50%"**. Module fully redesigned (see below).
2. **LayoutOptimizer generated invalid LaTeX.** It inserted `\usepackage[margin=…]{geometry}` *before* `\documentclass`, which cannot compile. Combined with:
3. **Stale-PDF masking.** The compiler treated any leftover `main.pdf` from a previous pass as success, so broken optimizer iterations reported "success" with an old PDF. The compiler now deletes the stale PDF before each build.
4. **latexmk error-state deadlock.** After one failed build, latexmk's dependency cache reported "up to date" and refused to rebuild even though we had deleted the PDF — every subsequent optimizer iteration then failed. Fixed with `-g` (force processing).
5. **`rend_pages` unbound variable** in the optimizer when compilation failed on iteration 1 → `NameError` at report writing.
6. **Windows-only VisualComparator.** Top-level `import pythoncom` → `ImportError` on any non-Windows host; on Windows, `CoInitialize` was called twice but `CoUninitialize` once, `word.Quit()` was skipped on exceptions (orphaned WINWORD.EXE processes), and failures fell through to a bare `print`. Rewritten with proper backend selection (Word COM on Windows with balanced COM init/teardown in `finally`, LibreOffice headless elsewhere, graceful degradation with `reference_available: false` in the report when neither exists).
7. **Windows job-cleanup failure.** Job log `FileHandler`s were cached forever and never closed, so `logs/*.log` stayed locked and `DELETE /job/{id}` (rmtree) fails on Windows. Added `close_job_loggers(job_id)`, called before cleanup; also fixes the unbounded handler/memory leak.

### Correctness / robustness
8. **Non-atomic metadata writes + races.** `metadata.json` was rewritten read-modify-write from multiple request handlers with no locking. Now: atomic write (temp file + `os.replace`) plus a process-wide per-job lock around every mutation.
9. **`add_error` always flipped jobs to FAILED**, even for advisory problems; `check_fidelity` then unconditionally set COMPLETED, so a failed job could end "COMPLETED". `add_error(fatal=…)` added; COMPLETED is only set when the job isn't FAILED; optimizer recompiles use a `quiet` mode that records warnings instead of fatal errors.
10. **/compile with a stale FAILED status** never recovered; the endpoint now resets the status alongside clearing errors, and its duplicated fidelity-check block was replaced by a shared `load_document_model()` helper.
11. **Fragile path hack** in CitationMapper and HeaderReconstructor: recovering the job root by string-splitting the path on `"/rendered"` (breaks for any path containing "rendered"). Both now receive the intermediate directory explicitly.
12. **No subprocess timeouts** anywhere (pandoc, pdflatex, latexmk, soffice) — a hung tool hung the job forever. All calls now have configurable timeouts; latexmk availability is probed once per process instead of per compile.
13. **Pandoc media-extraction dummy file** leaked on error paths (now removed in `finally`); Template upload wrote its temp zip into the server CWD (now `tempfile.gettempdir()`).
14. **requirements.txt was missing most actual dependencies** (Pillow, PyMuPDF, charset-normalizer, pywin32). Fixed with platform markers; additionally the code now degrades gracefully: PyMuPDF → poppler (`pdftoppm`/`pdfinfo`) fallback for rasterization, pydantic-settings → env-var fallback in `config.py`.
15. **Hardcoded fake metadata defaults** in the renderer ("Vol. 11", "25 Nov. 2022" etc. — sample-paper values stamped onto every document). Defaults now come from each template's `template.json` `"defaults"` block; JSAP's file was updated accordingly.
16. Duplicate `template.json` loading and a shadowed `import json` in the renderer removed.

## Header reconstruction (redesigned)

The old implementation ignored the DOCX entirely beyond plain text, injected a generic italic fancyhdr line, and reported a fake score. The new `HeaderReconstructor`:

- Parses **all** `word/header*.xml` parts: text runs with **alignment (w:jc), fonts (w:rFonts), sizes (w:sz), bold/italic**, paragraph bottom borders (→ header rule on/off)
- Resolves **header images through the header relationship files** and copies the real logos into the workspace, with widths/heights converted from EMU to points
- Extracts **header tables** cell-by-cell and page geometry (page size, all margins, header distance) from `sectPr`
- Reconstructs left/center/right fancyhdr fields honoring alignment, font size, logos, and measured `headheight`/`headsep`
- **Skips injection for classes that draw their own header** (NSP1/JSAP — controlled by `class_provides_header` in template.json) instead of fighting them
- Injects inside idempotent `% J2L-HEADER-BEGIN/END` markers and reports a **measured** header similarity

## Layout optimizer (redesigned)

Now tunes ten parameters — margins, line spacing, font size, paragraph spacing, section spacing, float separation (incl. text-float and in-text), above/below caption skips, bibliography item spacing, header separation, title spacing — all clamped to sane ranges. All values are regenerated each iteration into one managed `% J2L-OPT-BEGIN/END` block (no accumulating regex edits), placed correctly after `\documentclass`. Search strategy: page-count error drives global density expansion/compression with decaying step size; once page counts match, it rotates fine single-parameter tweaks. Failed compiles revert the source, count toward patience, and move parameters halfway back to the best-known point. Stops on target similarity, patience, or max iterations (all configurable via env), always restores the best-scoring version, and always writes `optimization_report.json` — even on abort.

## Remaining limitations

- Visual similarity against JSAP tops out around ~36% on the 2-column template because the Word original is single-column: page-by-page pixel comparison penalizes the (intended) reflow. A column-aware or content-based metric would be needed to score that fairly.
- The FastAPI layer could not be exercised over HTTP in the audit sandbox (no package network access there); it was verified by static analysis and byte-compilation only. The endpoints are thin wrappers over the fully tested `PipelineService`.
- MS Word COM path is written per pywin32 best practice but was verified only by review (no Windows/Word in the sandbox); LibreOffice path is verified end-to-end.
- Author/affiliation heuristics in `DocumentAnalyzer` remain heuristic; unusual front-matter layouts can still misclassify author lines.
- Pixel RMS is a coarse similarity proxy; SSIM (scikit-image) would rank layouts more perceptually.

## Suggested future improvements

Move pipeline execution to a background task queue so `/convert` and `/compile` don't block the event loop for the ~1–5 min optimization runs; add SSIM-based scoring and per-region (header/body/floats) metrics to give the optimizer a richer gradient; persist jobs in SQLite instead of scanning metadata.json files; add a scheduled cleaner for the dozens of stale job folders currently in `temp/`; and add a pytest suite around the smoke tests used in this audit (job cleanup, template upload, citation mapping, escape rules, optimizer idempotency).
