import re
import json
from pathlib import Path
from typing import Any, Dict, Tuple

class CitationMapper:
    """Service to automatically map, match, and translate in-text citations to bibliography items."""

    def map_citations(self, doc_model: Any, content_tex: str, report_dir: Path) -> Tuple[str, Dict[str, Any]]:
        """Map in-text citations to bibliography keys.

        Args:
            doc_model: Parsed DocumentModel with references.
            content_tex: Rendered body LaTeX.
            report_dir: Directory where citation_report.json is written
                (the job's intermediate directory).
        """
        report = {
            "total_citations": 0,
            "mapped_citations": 0,
            "broken_citations": 0,
            "unused_bibliography": [],
            "duplicated_bibliography": [],
            "missing_bibliography": [],
            "citation_style_detected": "Unknown"
        }

        # 1. Extract Bibliography Entries and key mappings
        # Mapped keys: e.g. ref1 -> bibliography text, or parsed author-year to ref key
        bib_keys = {}
        author_year_map = {}
        duplicates = []
        seen_refs = set()

        for idx, ref in enumerate(doc_model.references):
            ref_cleaned = ref.strip()
            key = f"ref{idx+1}"
            
            # Check duplicates
            if ref_cleaned in seen_refs:
                duplicates.append(ref_cleaned)
            seen_refs.add(ref_cleaned)
            
            bib_keys[key] = ref_cleaned
            
            # Try parsing Author and Year for APA style
            # e.g., "Almahaireh, A. (2023)."
            author_match = re.match(r'^([A-Z][a-zA-Z\s\-\u00c0-\u017f]+),\s*[A-Z]\.', ref_cleaned)
            year_match = re.search(r'\((19\d{2}|20\d{2})\)', ref_cleaned)
            
            if author_match and year_match:
                author_name = author_match.group(1).split()[-1].lower() # Last name
                year = year_match.group(1)
                author_year_map[(author_name, year)] = key

        report["duplicated_bibliography"] = duplicates

        # Detect citation style from content
        has_numbered = re.search(r'\[[0-9]+', content_tex) is not None
        has_author_year = re.search(r'\([A-Z][a-z]+,\s*(?:19|20)\d{2}\)', content_tex) is not None
        
        if has_numbered and has_author_year:
            report["citation_style_detected"] = "Mixed"
        elif has_numbered:
            report["citation_style_detected"] = "Numbered (IEEE/Vancouver)"
        elif has_author_year:
            report["citation_style_detected"] = "Author-Date (APA/Harvard)"
        else:
            report["citation_style_detected"] = "Numbered (Default fallback)"

        # 2. Map and replace Numbered citations: [1], [1, 2], [1-5], [1–5]
        def replace_numbered(match):
            citation_str = match.group(1)
            parts = re.split(r'[,\s]+', citation_str)
            keys = []
            
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                # Handle range like 1-5 or 1–5
                range_match = re.match(r'(\d+)[\-\u2013\u2014](\d+)', part)
                if range_match:
                    start = int(range_match.group(1))
                    end = int(range_match.group(2))
                    for i in range(start, end + 1):
                        keys.append(f"ref{i}")
                elif part.isdigit():
                    keys.append(f"ref{part}")
                    
            valid_keys = [k for k in keys if k in bib_keys]
            if valid_keys:
                report["total_citations"] += 1
                report["mapped_citations"] += 1
                return "\\cite{" + ", ".join(valid_keys) + "}"
            else:
                report["total_citations"] += 1
                report["broken_citations"] += 1
                return match.group(0) # Keep original if unresolved

        # Replace numbered brackets
        content_tex = re.sub(r'\[([0-9\s,\-\u2013\u2014]+)\]', replace_numbered, content_tex)

        # 3. Map and replace Author-Date citations: (Author, 2020)
        def replace_author_date(match):
            citation_str = match.group(1)
            # Parse components e.g. "Almahaireh, 2023"
            parts = [p.strip() for p in citation_str.split(",")]
            if len(parts) >= 2:
                author = parts[0].lower()
                year = parts[-1]
                if year.isdigit() and len(year) == 4:
                    key = author_year_map.get((author, year))
                    if key:
                        report["total_citations"] += 1
                        report["mapped_citations"] += 1
                        return "\\citep{" + key + "}"
                    
            report["total_citations"] += 1
            report["broken_citations"] += 1
            return match.group(0) # Keep original if unresolved

        content_tex = re.sub(r'\(([^)]+,\s*(?:19|20)\d{2})\)', replace_author_date, content_tex)

        # 4. Map and replace Inline Author-Date citations: Author (2020)
        def replace_inline_author_date(match):
            author = match.group(1).lower()
            year = match.group(2)
            key = author_year_map.get((author, year))
            if key:
                report["total_citations"] += 1
                report["mapped_citations"] += 1
                return "\\citet{" + key + "}"
            return match.group(0)

        content_tex = re.sub(r'([A-Z][a-zA-Z\u00c0-\u017f]+)\s*\(((?:19|20)\d{2})\)', replace_inline_author_date, content_tex)

        # Find uncited bib items
        used_keys = set(re.findall(r'\\cite[a-z]*\{([^}]+)\}', content_tex))
        flat_used_keys = set()
        for k in used_keys:
            for single_key in k.split(','):
                flat_used_keys.add(single_key.strip())
                
        report["unused_bibliography"] = [k for k in bib_keys if k not in flat_used_keys]
        report["missing_bibliography"] = list(flat_used_keys - set(bib_keys.keys()))

        # Save report
        report_path = report_dir / "citation_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        return content_tex, report
