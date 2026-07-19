# Journal2LaTeX — Verification & Debugging Pass

Date: 2026-07-19 · Method: every audit claim re-tested, fresh end-to-end runs on both real documents against both real templates, manual page-by-page visual inspection of rendered vs. Word-reference pages (not metrics alone), full code sweep.

## What verification found (all fixed)

The audit's fixes all held up under re-testing, but distrusting the metrics and inspecting the actual pages exposed seven further defects the first pass had missed:

1. **26 silently broken figures (WMF).** `normal_paper.docx` stores its equations and drawings as 86 WMF files; pdflatex cannot read WMF, so 26 `\includegraphics` calls produced 26 "Unknown graphics extension" errors inside a "successful" compile. Fixed with a new conversion stage (`app/utils/media_convert.py`): LibreOffice batch-converts WMF/EMF/SVG to PNG at extraction time, with Pillow auto-cropping of the A4 canvas LibreOffice puts around vectors, and the renderer references the PNG siblings. JSAP similarity rose 36% → 60% and page count 7 → 12 (target 14) from this fix alone.
2. **The entire bibliography was empty.** Reference list items arrive from pandoc wrapped in `BlockQuote` nodes the parser didn't handle — 14 `\bibitem`s rendered with no text (citation numbers resolved, so nothing "failed"). `_stringify_blocks` now handles BlockQuote/Div/LineBlock; both papers now render complete, correct bibliographies (14 and 20 entries, verified in the PDF text).
3. **Superscripted citation markers were deleted from body text.** `_stringify_inlines` had no Superscript/Subscript/SmallCaps/Underline/Span branches, so in-text citations like "[2]" (superscript runs in Word) vanished — `with_author_photo.docx` showed 0 in-text citations. After the fix: 21/21 mapped, verified visible in the PDF ("governmental hospital [2].").
4. **The default template pushed all content to page 2.** `article`'s `\maketitle` issues `\newpage` when preceded by content; page 1 contained only the header and fake "Journal2LaTeX Open Document Series" branding. The template now renders the title block inline and the fabricated branding was removed (the real header comes from the DOCX reconstruction). Page 1 now mirrors the Word page 1: title, authors, affiliations, abstract, keywords, first section.
5. **Footers were not reconstructed at all** (audit claim was header-only). `HeaderReconstructor` now parses `word/footer*.xml` identically to headers — text, alignment, fonts, images — and injects `\fancyfoot`. The NSP copyright block and corresponding-author line now appear in the rendered footer matching Word.
6. **JSAP banner rendered as a black box.** NSP1.cls defines its banner via dvips *named* colors that were undefined at class load, and LaTeX's error recovery painted the banner black; separately the EPS journal logo could not be embedded without ghostscript. Fixed by defining the colors explicitly (matched to the Word original's orange), pre-converting EPS logos when ghostscript is absent, and adding a `\shortjournalname` hook to the vendored class so the running header reads "J. Stat. Appl. Pro." instead of the class's hard-coded "Appl. Math. Inf. Sci.".
7. **Front-matter regressions surfaced by fix #3, then repaired:** author names carried affiliation digits ("Almahaireh1"), affiliations lost their index mapping, dates truncated at abbreviation periods ("27Aug" for "27 Aug. 2025"), and a trailing blank paragraph produced an empty `[21]` bibliography entry. All four fixed; the rendered front matter now lists three/five authors with correct superscripts, indexed affiliations, and full dates.

Also fixed in the sweep: duplicated RMS-similarity and LaTeX-escaping code extracted into `app/utils/imaging.py` and `app/utils/latex.py` (used by renderer, header reconstructor, and comparator); ten unused imports removed; hyperref link boxes hidden in the default class to match Word's plain text.

## Requirement-by-requirement verification

Verified working, with evidence from real runs: header reconstruction (real logos, fonts, alignment; measured 79.5% header-region similarity), footer reconstruction (real NSP footer text), logos and header/footer images (copied from header rels, correct EMU→pt sizing), inline and figure images (10/10 referenced media present), WMF/EMF conversion, tables (6 tabulars rendered; simple merges flattened — see limitations), citations (18/18 and 21/21 mapped, 0 broken), bibliography (full text verified in PDF), page counts (11 vs 11 exact on one paper; 12 vs 14 on the two-column reflow), optimization improving similarity (69.2→76.9% and 36→60% across fixes; loop reverts failed iterations and restores the best version), and every report generated on every run — optimization, header, citation, graphics, visual comparison, layout, fidelity, comparison, conversion, assets, timing — all containing measured values. Grep sweep for TODO/FIXME/HACK/XXX/fake/placeholder/hardcoded: clean (remaining `pass` statements are exception-class bodies and narrow tolerated-failure handlers). Stale-PDF, stale-report, locked-file, subprocess-timeout, COM init/teardown, and atomic-metadata behaviors were each re-tested individually.

Equations: both test papers store equations as WMF images (no OMML), so equation fidelity is carried by the image conversion, which now works. OMML equations would flow through pandoc's Math AST path, which is implemented but not exercised by these documents.

## FastAPI endpoints — honest status

This sandbox has no route to install FastAPI (PyPI, apt, npm, GitHub all blocked), so `/upload /convert /compile /download /job` could not be exercised over HTTP. They were verified statically: routes, request/response models, and every service call they make checked against the actual service signatures (including the new `quiet`, `fatal`, and `load_document_model` contracts), plus byte-compilation. The endpoints are thin wrappers over the fully end-to-end-tested `PipelineService`. **Before release, run one `/upload → /convert → /compile → /download` cycle on your machine** — it is the one path this pass could not execute.

## Remaining bugs / known limitations

- Composite Word drawings (grouped DrawingML shapes, e.g. Fig. 1 in the MANET paper) render as a blank frame: pandoc extracts the group's members as separate media files and no single image represents the whole figure. Charts/SmartArt are detected and reported by GraphicsExtractor but similarly have no vector-to-LaTeX rendering path.
- Merged table cells (vMerge/gridSpan) are flattened — no `\multirow`/`\multicolumn` emission.
- Hyperlink and footnote *text* is preserved; URLs and footnote anchoring are not (`\href`/`\footnote` would need a rich inline renderer — the current text model is plain text + inline math).
- Word's first-page-vs-running header distinction is merged into one fancyhdr style; exact per-run colors/fonts inside body text are not reproduced (document-level fonts/spacing are optimizer-tuned instead).
- Author/affiliation parsing is heuristic; multi-marker authors ("Akgül 1,2,3,4,5,*") keep only a single affiliation link.
- Two-column journal templates intrinsically reflow a single-column Word source, capping pixel-similarity scores (~60%) even when content fidelity is high.

## Technical debt

Front-matter extraction (authors/affiliations/dates) would be more robust reading DOCX styles directly than pandoc AST heuristics. Pixel RMS remains a coarse optimizer signal (SSIM/per-region would rank better). Pipeline runs block the request thread — a task queue is the right production shape. `temp/` has no retention policy (dozens of stale job folders exist in the repo working tree — deletable). No pytest suite yet; the smoke tests from this pass are the seed.

## Verdict

- Files changed this pass: 14 modified, 3 new utils (`media_convert.py`, `imaging.py`, `latex.py`), plus default/JSAP template files and vendored NSP1.cls.
- Final state: repeated fresh end-to-end runs on both documents × both templates finish COMPLETED with zero errors, zero warnings, all reports real and present.
- **Production readiness: 82/100.** Core pipeline: solid. Deductions: API layer unverified over HTTP in this environment (−6), content classes with no rendering path (composite drawings, merged cells, footnote/hyperlink anchoring) (−8), no automated test suite / task queue / retention policy (−4).
- **Confidence: high** on everything exercised end-to-end here (Linux, LibreOffice reference path); **medium** on Windows-specific paths (Word COM, Windows file locking) — written to spec and reviewed, but this sandbox cannot execute them.
- Before release: run the HTTP cycle once on Windows, run one job with MS Word installed to exercise the COM path, install ghostscript alongside LaTeX (or rely on the new LibreOffice EPS fallback), clear old `temp/` job folders, and `pip install -r requirements.txt` (it now lists the real dependencies).
