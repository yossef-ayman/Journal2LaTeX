import json
import re
from pathlib import Path
from typing import Any, Dict
from app.models.document import DocumentModel, BlockType
from app.utils.logger import get_job_logger


_INCLUDEGRAPHICS_RE = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")

# Extensions probed when \includegraphics is written without one, matching what
# the LaTeX graphics driver itself will try.
_GRAPHIC_EXTS = (".pdf", ".png", ".jpg", ".jpeg", ".eps")


class FidelityChecker:
    """Service to validate LaTeX rendering outputs and calculate fidelity quality scores."""

    @staticmethod
    def _referenced_media(rendered_dir: Path) -> set:
        """Media filenames the generated LaTeX asks for, under ``media/``.

        Only ``media/`` references are considered: a template ships its own
        graphics (a publisher logo, a class ornament) whose presence is the
        template's business, not the converter's.
        """
        names = set()
        for tex in sorted(rendered_dir.glob("*.tex")):
            try:
                source = tex.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for match in _INCLUDEGRAPHICS_RE.finditer(source):
                target = match.group(1).strip().replace("\\", "/")
                if target.startswith("media/"):
                    names.add(target[len("media/"):])
        return names

    @staticmethod
    def _media_present(name: str, rendered_files: set) -> bool:
        """Whether a reference resolves to a file the compiler can actually use.

        Two allowances mirror what happens at compile time: a reference given
        without an extension is satisfied by any graphics format, and a vector
        source (WMF/EMF/SVG) is included through the PNG sibling that
        ``convert_unsupported_media`` produced, so the sibling counts.
        """
        if name in rendered_files:
            return True
        stem = Path(name).stem
        suffix = Path(name).suffix.lower()
        if not suffix:
            return any(f"{stem}{ext}" in rendered_files for ext in _GRAPHIC_EXTS)
        if suffix in (".wmf", ".emf", ".svg"):
            return f"{stem}.png" in rendered_files
        return False

    def generate_fidelity_report(self, job_id: str, doc_model: DocumentModel, temp_folder: Path) -> Dict[str, Any]:
        """Generate a detailed fidelity report comparing inputs and output PDF.

        Args:
            job_id: The UUID of the job.
            doc_model: The extracted DocumentModel.
            temp_folder: The job's temporary workspace directory.

        Returns:
            A dictionary containing the detailed fidelity report.
        """
        logger = get_job_logger(job_id, "system")
        logger.info("Generating advanced fidelity report and scores for job: %s", job_id)

        missing_assets = []
        missing_sections = []
        missing_figures = []
        missing_tables = []
        layout_warnings = []

        rendered_dir = temp_folder / "rendered"
        log_file = rendered_dir / "main.log"

        # Content match calculation
        expected_sections_count = len(doc_model.sections)
        actual_sections_count = 0
        sections = doc_model.sections
        for index, section in enumerate(sections):
            if section.blocks:
                actual_sections_count += 1
                continue
            # A heading whose next sibling is a *deeper* heading is a container
            # ("2. Literature Review" followed immediately by "2.1 ..."), which
            # is normal in academic manuscripts.  Its text lives in the
            # subsections, so nothing has been lost and flagging it as missing
            # content is a false positive.
            nxt = sections[index + 1] if index + 1 < len(sections) else None
            own_level = getattr(section, "level", None) or 1
            next_level = getattr(nxt, "level", None) or 1 if nxt else None
            if nxt is not None and next_level > own_level:
                actual_sections_count += 1
                continue
            missing_sections.append(f"Empty section content: {section.title}")

        if expected_sections_count == 0:
            content_match_score = 100.0
        else:
            content_match_score = (actual_sections_count / expected_sections_count) * 100.0

        # Asset comparison: Original DOCX assets vs. Rendered LaTeX assets
        original_assets_dir = temp_folder / "intermediate" / "original_assets"
        rendered_assets_dir = rendered_dir / "media"

        original_files = set()
        if original_assets_dir.exists():
            original_files = {f.name for f in original_assets_dir.iterdir() if f.is_file()}

        rendered_files = set()
        if rendered_assets_dir.exists():
            rendered_files = {f.name for f in rendered_assets_dir.iterdir() if f.is_file()}

        # Asset match asks one question: does every image the generated
        # document asks for actually resolve in the compilation workspace?
        #
        # Comparing the two directories as sets, which is what this used to do,
        # answered a different and largely meaningless question.  Assets reach
        # the workspace by three independent routes -- pandoc media extraction,
        # the Office-native object renderer, and the header reconstructor, which
        # copies a masthead straight out of word/media at render time -- so the
        # two directories are never expected to be equal.  A chart-only
        # manuscript scored 0% with four correctly rendered charts, purely
        # because pandoc had contributed nothing to the snapshot.  Conversely a
        # source image that the analyzer legitimately turns into real LaTeX (an
        # equation stored as WMF) is not a lost asset, but set difference
        # counted it as one.
        referenced = self._referenced_media(rendered_dir)
        resolved, unresolved = set(), set()
        for name in referenced:
            (resolved if self._media_present(name, rendered_files) else unresolved).add(name)

        # An asset sitting in the workspace that nothing refers to is dead
        # weight, not a defect; it is reported but does not affect the score.
        referenced_stems = {Path(n).stem for n in referenced}
        unused_files = sorted(f for f in rendered_files if Path(f).stem not in referenced_stems)

        missing_files = sorted(unresolved)
        unexpected_files = unused_files

        total_original = len(original_files)
        total_rendered = len(rendered_files)
        matched_count = len(resolved)

        # Asset match score
        if not referenced:
            asset_match_score = 100.0
        else:
            asset_match_score = (matched_count / len(referenced)) * 100.0

        # Document structure figure validation
        for section in doc_model.sections:
            for block in section.blocks:
                if block.type == BlockType.FIGURE:
                    img_path = block.content.get("path", "")
                    img_name = Path(img_path).name
                    # Resolved through the same rules the compiler uses, so a
                    # figure carried as WMF and included via its PNG sibling is
                    # not reported as a missing image.
                    if not self._media_present(img_name, rendered_files):
                        missing_assets.append(f"Figure image missing: {img_name}")
                        missing_figures.append(f"Missing figure caption: {block.content.get('caption')}")
                elif block.type == BlockType.TABLE:
                    if not block.content.get("rows"):
                        missing_tables.append(f"Empty table caption: {block.content.get('caption')}")

        # PDF log-level validation and layout overflow checks
        text_overflow_count = 0
        latex_warnings = []
        empty_pages = False

        if log_file.exists():
            log_content = log_file.read_text(encoding="utf-8", errors="ignore")
            
            # Text/table/caption overflow detection
            overfull_hboxes = re.findall(r"Overfull \\hbox", log_content)
            overfull_vboxes = re.findall(r"Overfull \\vbox", log_content)
            text_overflow_count = len(overfull_hboxes) + len(overfull_vboxes)

            # Biography and image scaling detection
            for match in re.finditer(r"Warning: (.*)", log_content):
                warn_msg = match.group(1).strip()
                if "includegraphics" in warn_msg or "size" in warn_msg:
                    layout_warnings.append(f"Image scaling issue: {warn_msg}")
                elif "biography" in warn_msg:
                    layout_warnings.append(f"Biography overflow/issue: {warn_msg}")

            warnings = re.findall(r"LaTeX Warning: (.*)", log_content)
            for w in warnings:
                if "Marginpar on page" not in w and "float specifier" not in w:
                    # Filter out non-critical compilation reference/label warnings
                    if any(x in w.lower() for x in ["reference", "label(s)", "citation", "undefined", "requested document class"]):
                        continue
                    latex_warnings.append(w.strip())
                    layout_warnings.append(f"LaTeX layout warning: {w.strip()}")

            if "Empty page" in log_content or "No pages of output" in log_content:
                empty_pages = True
        else:
            layout_warnings.append("main.log not found; skipped PDF validations.")

        # Layout match score starts at 100 and decreases for overflows
        layout_match_score = max(0.0, 100.0 - (text_overflow_count * 1.5) - (len(latex_warnings) * 1.0))
        if empty_pages:
            layout_match_score = max(0.0, layout_match_score - 30.0)

        # Weighted overall fidelity score
        overall_fidelity_score = (content_match_score * 0.40) + (asset_match_score * 0.30) + (layout_match_score * 0.30)

        # Determine critical missing sections
        critical_missing_content = len(missing_sections)

        report = {
            "content_match_score": round(content_match_score, 1),
            "asset_match_score": round(asset_match_score, 1),
            "layout_match_score": round(layout_match_score, 1),
            "overall_fidelity_score": round(overall_fidelity_score, 1),
            "critical_missing_content": critical_missing_content,
            "assets_validation": {
                "total_original_assets": total_original,
                "total_rendered_assets": total_rendered,
                "total_referenced_assets": len(referenced),
                "matched_assets": matched_count,
                # References the compiler cannot resolve -- a genuine defect.
                "missing_assets": missing_files,
                # Files shipped into the workspace that nothing refers to.
                "unexpected_assets": unexpected_files
            },
            "missing_assets": missing_assets,
            "missing_sections": missing_sections,
            "missing_figures": missing_figures,
            "missing_tables": missing_tables,
            "layout_warnings": layout_warnings,
            "pdf_validations": {
                "text_overflow_warnings": text_overflow_count,
                "empty_pages_detected": empty_pages,
                "latex_log_warnings": latex_warnings[:15]
            }
        }

        # Write fidelity report
        report_path = temp_folder / "intermediate" / "fidelity_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        logger.info(
            "Fidelity report written to %s. Overall Score: %s%%, Critical missing: %d",
            report_path, report["overall_fidelity_score"], critical_missing_content
        )

        # Generate comparison_report.json
        mismatches = {}
        
        # 1. Header Match
        header_score = 100.0
        header_mismatches = []
        if not doc_model.volume:
            header_mismatches.append({
                "expected": "Journal volume details present",
                "actual": "Missing or generic volume",
                "reason": "Volume not detected in DOCX header",
                "proposed_fix": "Extract volume metadata from first page header"
            })
            header_score -= 20.0
        if not doc_model.received_date:
            header_mismatches.append({
                "expected": "Received/Revised/Accepted dates present",
                "actual": "Missing dates",
                "reason": "Dates not detected in DOCX metadata",
                "proposed_fix": "Extract dates from header blocks"
            })
            header_score -= 20.0
        if not doc_model.doi:
            header_mismatches.append({
                "expected": "DOI identifier present",
                "actual": "Missing DOI",
                "reason": "DOI not detected in DOCX",
                "proposed_fix": "Generate standard DOI prefix in templates"
            })
            header_score -= 20.0
        header_score = max(0.0, header_score)
        if header_mismatches:
            mismatches["header_match"] = header_mismatches

        # 2. Title Match
        title_score = 100.0
        if not doc_model.title or len(doc_model.title.strip()) < 10:
            title_score = 0.0
            mismatches["title_match"] = [{
                "expected": "Valid paper title extracted",
                "actual": doc_model.title or "Empty",
                "reason": "Title block not detected",
                "proposed_fix": "Verify Pandoc metadata title parsing"
            }]

        # 3. Author Match
        author_score = 100.0
        if not doc_model.authors:
            author_score = 0.0
            mismatches["author_match"] = [{
                "expected": "Authors list extracted",
                "actual": "0 authors",
                "reason": "Authors paragraphs not detected",
                "proposed_fix": "Verify author block detection rules before abstract"
            }]

        # 4. Affiliation Match
        affiliation_score = 100.0
        missing_affs = [a.name for a in doc_model.authors if not a.affiliation]
        if missing_affs:
            affiliation_score = max(0.0, 100.0 - (len(missing_affs) * 25.0))
            mismatches["affiliation_match"] = [{
                "expected": "Affiliations for all authors",
                "actual": f"Missing affiliations for: {', '.join(missing_affs)}",
                "reason": "Affiliation paragraphs not grouped with author names",
                "proposed_fix": "Implement proximity grouping in author analyzer"
            }]

        # 5. Abstract Match
        abstract_score = 100.0
        if not doc_model.abstract or len(doc_model.abstract.strip()) < 20:
            abstract_score = 0.0
            mismatches["abstract_match"] = [{
                "expected": "Abstract text extracted",
                "actual": "Empty or short abstract",
                "reason": "Abstract section not found",
                "proposed_fix": "Verify abstract keyword detection"
            }]

        # 6. Keyword Match
        keyword_score = 100.0
        if not doc_model.keywords:
            keyword_score = 0.0
            mismatches["keyword_match"] = [{
                "expected": "Keywords list extracted",
                "actual": "0 keywords",
                "reason": "Keywords paragraph not found",
                "proposed_fix": "Verify keyword prefix detection"
            }]

        # 7. Section Match
        section_score = 100.0
        if not doc_model.sections:
            section_score = 0.0
            mismatches["section_match"] = [{
                "expected": "Document sections extracted",
                "actual": "0 sections",
                "reason": "No section headers detected",
                "proposed_fix": "Verify header block parsing in AST"
            }]

        # 8. Figure Match
        figure_score = max(0.0, 100.0 - (len(missing_figures) * 20.0))
        if missing_figures:
            mismatches["figure_match"] = [{
                "expected": "All figures rendered",
                "actual": f"Missing figures: {len(missing_figures)}",
                "reason": "Figure files not found in media folder",
                "proposed_fix": "Verify figure image extraction path mapping"
            }]

        # 9. Table Match
        table_score = max(0.0, 100.0 - (len(missing_tables) * 25.0))
        if missing_tables:
            mismatches["table_match"] = [{
                "expected": "All tables rendered",
                "actual": f"Missing tables: {len(missing_tables)}",
                "reason": "Empty tables or parser errors",
                "proposed_fix": "Verify table row extraction logic"
            }]

        # 10. Reference Match
        reference_score = 100.0
        if not doc_model.references:
            reference_score = 0.0
            mismatches["reference_match"] = [{
                "expected": "References parsed",
                "actual": "0 references",
                "reason": "References section empty or not detected",
                "proposed_fix": "Verify paragraph check for references transition"
            }]

        # 11. Biography Match
        biography_score = 100.0
        if doc_model.author_biographies:
            missing_bio_photos = [b.author_name for b in doc_model.author_biographies if not b.image_path]
            if missing_bio_photos:
                biography_score = max(0.0, 100.0 - (len(missing_bio_photos) * 25.0))
                mismatches["biography_match"] = [{
                    "expected": "Biography photos for all biographed authors",
                    "actual": f"Missing photos for: {', '.join(missing_bio_photos)}",
                    "reason": "Author photo extraction or table mapping issue",
                    "proposed_fix": "Verify image cell extraction in biography table"
                }]
        else:
            biography_score = 100.0

        # 12. Layout Match
        layout_score = layout_match_score
        if len(layout_warnings) > 0:
            mismatches["layout_match"] = [{
                "expected": "No LaTeX layout warnings or overflows",
                "actual": f"{len(layout_warnings)} layout issues detected",
                "reason": "Hbox/Vbox overflows or bad scaling",
                "proposed_fix": "Verify graphics scaling and table wrapping styles"
            }]

        # 13. Typography Match
        typography_score = max(0.0, 100.0 - (text_overflow_count * 3.0))
        if text_overflow_count > 0:
            mismatches["typography_match"] = [{
                "expected": "Zero text line overflows",
                "actual": f"{text_overflow_count} line overflows",
                "reason": "Long math equation or long table column widths",
                "proposed_fix": "Implement auto-wrapping or auto-resizing styles"
            }]

        # 14. First Page Match
        first_page_score = round(
            (title_score + author_score + affiliation_score + abstract_score + keyword_score + header_score) / 6.0,
            1
        )
        if first_page_score < 95.0:
            mismatches["first_page_match"] = [{
                "expected": "High fidelity first page layout",
                "actual": f"First page match score: {first_page_score}%",
                "reason": "Metadata fields mismatch or generic formatting",
                "proposed_fix": "Override document class metadata macros"
            }]

        # Overall Comparison Score
        overall_score = round(
            (header_score + title_score + author_score + affiliation_score + abstract_score +
             keyword_score + section_score + figure_score + table_score + reference_score +
             biography_score + layout_score + typography_score + first_page_score) / 14.0,
            1
        )

        comparison_report = {
            "header_match": round(header_score, 1),
            "title_match": round(title_score, 1),
            "author_match": round(author_score, 1),
            "affiliation_match": round(affiliation_score, 1),
            "abstract_match": round(abstract_score, 1),
            "keyword_match": round(keyword_score, 1),
            "section_match": round(section_score, 1),
            "figure_match": round(figure_score, 1),
            "table_match": round(table_score, 1),
            "reference_match": round(reference_score, 1),
            "biography_match": round(biography_score, 1),
            "layout_match": round(layout_score, 1),
            "typography_match": round(typography_score, 1),
            "first_page_match": round(first_page_score, 1),
            "overall_score": overall_score,
            "mismatches": mismatches
        }

        # Write comparison_report.json to job directory only
        comp_report_path = temp_folder / "intermediate" / "comparison_report.json"
        comp_report_path.write_text(json.dumps(comparison_report, indent=2), encoding="utf-8")

        return report
