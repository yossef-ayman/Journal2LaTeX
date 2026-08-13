"""In-text citation mapping.

This service keeps the interface it has always had -- the renderer calls
``map_citations`` and receives rewritten LaTeX and a report -- but the work is
now done by :class:`app.engines.citation_engine.CitationEngine`.

The reason for the change is not tidiness.  This module and the engine had each
grown their own answer to the same three questions: which shapes in the text are
citations, which reference each one names, and what LaTeX to write for it.  Two
answers to one question is one answer too many -- the two disagreed about
ranges, about bare years, about superscripts, and most seriously about how a
citation key is spelled, which is the one thing that has to match the
bibliography exactly.  So the logic lives in the engine, and this module is the
adapter that keeps every existing caller working unchanged.

What the engine adds over what was here: superscript and hyperlinked citations,
citations already rendered as commands, the guards that stop a page range or a
bare year becoming a citation, validation of the reference numbering itself, and
citation commands chosen by the journal's rules instead of hard-coded.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.engines.citation_engine import CitationEngine
from app.engines.journal_rules import JournalRules, JournalRulesResolver


class CitationMapper:
    """Service to automatically map, match, and translate in-text citations to bibliography items."""

    #: Style names kept in the shape the previous implementation reported them,
    #: so anything reading ``citation_report.json`` -- the frontend, a saved
    #: report from an earlier run -- still recognises the value.
    _STYLE_NAMES = {
        "numeric": "Numbered (IEEE/Vancouver)",
        "superscript": "Numbered (Superscript)",
        "author_year": "Author-Date (APA/Harvard)",
        "mixed": "Mixed",
        "rendered": "Numbered (Already rendered)",
        "none": "Numbered (Default fallback)",
    }

    def __init__(self, engine: Optional[CitationEngine] = None,
                 rules_resolver: Optional[JournalRulesResolver] = None) -> None:
        self._engine = engine or CitationEngine()
        self._rules_resolver = rules_resolver or JournalRulesResolver()

    def map_citations(self, doc_model: Any, content_tex: str, report_dir: Path,
                      rules: Optional[JournalRules] = None
                      ) -> Tuple[str, Dict[str, Any]]:
        """Map in-text citations to bibliography keys.

        Args:
            doc_model: Parsed DocumentModel with references.
            content_tex: Rendered body LaTeX.
            report_dir: Directory where citation_report.json is written
                (the job's intermediate directory).
            rules: Resolved journal rules.  Optional so the three-argument
                calls that exist today keep working; when the caller has
                already resolved the rules it passes them, which is what
                guarantees that the keys written here are the same keys the
                renderer writes into ``\\bibitem``.
        """
        if rules is None:
            rules = self._rules_resolver.resolve({})

        references = list(getattr(doc_model, "references", None) or [])
        analysis = self._engine.analyse(references, content_tex, rules)
        content_tex = self._engine.render(content_tex, analysis, rules)

        report = self._build_report(analysis)

        report_path = report_dir / "citation_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        return content_tex, report

    def _build_report(self, analysis) -> Dict[str, Any]:
        """The report, in the shape callers already expect.

        Every key the previous implementation produced is still produced, with
        the same meaning, so no consumer needs changing.  The engine's richer
        findings are added alongside rather than replacing them -- a caller that
        wants the detail can read ``issues``, and one that only wants the
        counts is unaffected.
        """
        resolved = [c for c in analysis.citations if c.resolved]
        broken = [c for c in analysis.citations if not c.resolved]
        cited_keys = {k for c in analysis.citations for k in c.keys}

        duplicated = [i.detail.get("number") for i in analysis.issues
                      if i.kind == "duplicate_numbering"]
        missing = sorted({u for c in analysis.citations for u in c.unresolved})

        return {
            "total_citations": len(analysis.citations),
            "mapped_citations": len(resolved),
            "broken_citations": len(broken),
            "unused_bibliography": [e.key for e in analysis.entries
                                    if e.key not in cited_keys],
            "duplicated_bibliography": duplicated,
            "missing_bibliography": missing,
            "citation_style_detected": self._STYLE_NAMES.get(
                analysis.detected_style, "Unknown"),
            # Added by the engine; no existing consumer depends on these, and
            # they are what make a citation problem diagnosable rather than
            # merely countable.
            "issues": [i.to_dict() for i in analysis.issues],
            "bibliography_keys": [
                {"key": e.key, "source_number": e.number,
                 "text": e.raw[:160]} for e in analysis.entries
            ],
        }
