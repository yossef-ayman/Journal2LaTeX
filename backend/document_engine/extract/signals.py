"""Deciding what a paragraph *is*, from the document itself.

No style name, journal template or paragraph index appears anywhere in this
module.  A document that calls its headings ``Ttulo1``, or that has no styles at
all and makes headings by setting 14pt bold, must come out the same way -- so
every threshold here is measured against the rest of *this* document rather than
carried in from another one.

The signals are ordered by how much they are worth, and the first one that
speaks decides:

1. **An explicit outline level.**  ``w:outlineLvl`` is Word's own answer to the
   question and is what its navigation pane reads.  It may arrive through the
   style chain, which is why this runs on resolved properties.
2. **A style that behaves like a heading elsewhere.**  Not by name: a style is a
   heading style if the paragraphs wearing it are consistently short, visually
   prominent, and followed by prose.  The evidence is pooled across the whole
   document, so one ambiguous line is judged by its hundred siblings.
3. **Visual prominence.**  Bigger than the modal body size, or bold or caps at
   body size, plus the corroborating hints Word writers actually leave:
   ``keepNext``, space before, a short line that does not end in a full stop.
4. **A section number.**  ``3.2`` or ``IV.`` at the head of a short line is a
   heading almost wherever it appears, and its depth is the nesting depth.

Anything that clears the bar is returned with the evidence that got it there, so
a wrong answer can be explained instead of merely observed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from document_engine.ooxml.blocks import Paragraph, modal_body_size_pt
from document_engine.ooxml.props import ParagraphProps, RunProps

# A leading section number: "3", "3.2", "3.2.1", "IV", "A." -- with the depth
# readable from it.  Deliberately not anchored to any particular numbering
# style, because documents disagree about all of them.
_NUMBER = re.compile(
    r"^\s*(?:"
    # Spaces are tolerated around the dots: real documents contain "2. 1".
    r"(?P<arabic>\d+(?:\s*\.\s*\d+)*)"
    r"|(?P<roman>[IVXLC]{1,6})"
    r"|(?P<letter>[A-Z])"
    r")\s*[.)\]]?\s+(?P<rest>\S.*)$"
)

# Terminal punctuation a heading almost never ends with.  A colon is allowed:
# run-in headings ("Methods:") are common and real.
_SENTENCE_END = ".!?;,"

# Long enough that it is a sentence rather than a label.  Measured in words so
# it does not depend on language density as much as a character count would.
_MAX_HEADING_WORDS = 18


@dataclass
class Verdict:
    """What a paragraph appears to be, and why."""

    kind: str = "body"          # "heading" | "body" | "list_item" | "caption"
    level: int = 0              # 1-based for headings, 0 otherwise
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    number: Optional[str] = None

    @property
    def is_heading(self) -> bool:
        return self.kind == "heading"


def _props(paragraph: Paragraph) -> ParagraphProps:
    return paragraph.effective or paragraph.props or ParagraphProps()


def _run_props(paragraph: Paragraph) -> List[RunProps]:
    out = []
    for run in paragraph.runs:
        props = run.effective or run.props
        if props is not None and (run.text or "").strip():
            out.append(props)
    return out


def _size_pt(paragraph: Paragraph) -> Optional[float]:
    """The dominant size of the paragraph's *visible* text.

    Weighted by characters, so a stray 8pt footnote marker cannot make a 16pt
    heading look like body text.
    """
    weights: Dict[float, int] = {}
    for run in paragraph.runs:
        props = run.effective or run.props
        text = (run.text or "").strip()
        if not text or props is None or props.size_pt is None:
            continue
        weights[props.size_pt] = weights.get(props.size_pt, 0) + len(text)
    if not weights:
        return None
    return max(weights.items(), key=lambda kv: (kv[1], -kv[0]))[0]


def _mostly(paragraph: Paragraph, attribute: str) -> bool:
    """True when most of the paragraph's characters carry the attribute.

    "Most" rather than "all" because a heading with an italic species name in it
    is still a bold heading.
    """
    on = off = 0
    for run in paragraph.runs:
        props = run.effective or run.props
        text = (run.text or "").strip()
        if not text or props is None:
            continue
        if getattr(props, attribute):
            on += len(text)
        else:
            off += len(text)
    return on > off and on > 0


def _looks_like_prose(text: str) -> bool:
    """Sentences, not a label.  The single most useful negative signal."""
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped.split()) > _MAX_HEADING_WORDS:
        return True
    return stripped[-1] in _SENTENCE_END and stripped[-1] != ":"


def _leading_number(text: str):
    """``("3.2", 2, "Results")`` -- the number, its depth, and what follows."""
    match = _NUMBER.match(text)
    if match is None:
        return None
    rest = match.group("rest")
    if match.group("arabic"):
        number = re.sub(r"\s+", "", match.group("arabic"))
        return number, number.count(".") + 1, rest
    if match.group("roman"):
        return match.group("roman"), 1, rest
    return match.group("letter"), 1, rest


class DocumentSignals:
    """Everything measured about one document, and the verdicts that follow.

    Constructed once per document because every threshold is relative: the modal
    body size, which sizes count as prominent, and which style ids turned out to
    behave like headings are all facts about this file.
    """

    def __init__(self, paragraphs: Sequence[Paragraph]) -> None:
        self.paragraphs: List[Paragraph] = [p for p in paragraphs if not p.in_fallback]
        self.body_size_pt = modal_body_size_pt(self.paragraphs)
        self._sizes = self._size_histogram()
        self.heading_styles: Dict[str, int] = self._learn_heading_styles()
        self._verdicts: Dict[int, Verdict] = {}

    # -- measurement ------------------------------------------------------

    def _size_histogram(self) -> Dict[float, int]:
        sizes: Dict[float, int] = {}
        for paragraph in self.paragraphs:
            size = _size_pt(paragraph)
            if size is not None:
                sizes[size] = sizes.get(size, 0) + len(paragraph.text().strip())
        return sizes

    def _learn_heading_styles(self) -> Dict[str, int]:
        """Which style ids act like headings here, and at what depth.

        A style qualifies on behaviour, never on its name.  If every paragraph
        wearing it is short, non-prose and prominent, it is a heading style even
        if it is called ``Style17``; if most paragraphs wearing it are prose it
        is not one even if it is called ``Heading 1``.
        """
        stats: Dict[str, Dict[str, object]] = {}
        for paragraph in self.paragraphs:
            props = _props(paragraph)
            text = paragraph.text().strip()
            if not props.style_id or not text:
                continue
            entry = stats.setdefault(
                props.style_id,
                {"n": 0, "shortish": 0, "prominent": 0, "outline": None, "sizes": []},
            )
            entry["n"] = int(entry["n"]) + 1
            if not _looks_like_prose(text):
                entry["shortish"] = int(entry["shortish"]) + 1
            if self._prominence(paragraph) > 0:
                entry["prominent"] = int(entry["prominent"]) + 1
            if props.outline_level is not None and entry["outline"] is None:
                entry["outline"] = props.outline_level
            size = _size_pt(paragraph)
            if size is not None:
                entry["sizes"].append(size)  # type: ignore[union-attr]

        learned: Dict[str, int] = {}
        for style_id, entry in stats.items():
            count = int(entry["n"])
            short = int(entry["shortish"])
            prominent = int(entry["prominent"])
            outline = entry["outline"]
            if outline is not None:
                learned[style_id] = int(outline) + 1
                continue
            # Unanimously short and mostly prominent.  One prose paragraph is
            # enough to disqualify a style: heading styles do not hold prose.
            if count and short == count and prominent * 2 >= count:
                learned[style_id] = 0  # depth decided later, by size rank
        # Depth for the styles that had no outline level: rank by their typical
        # size, largest first, so the biggest learned heading style is level 1.
        undecided = [s for s, level in learned.items() if level == 0]
        by_size = sorted(
            undecided,
            key=lambda s: -(max(stats[s]["sizes"]) if stats[s]["sizes"] else 0),  # type: ignore[arg-type]
        )
        seen: List[float] = []
        for style_id in by_size:
            sizes = stats[style_id]["sizes"]  # type: ignore[index]
            size = max(sizes) if sizes else 0.0  # type: ignore[arg-type]
            if size not in seen:
                seen.append(size)
            learned[style_id] = seen.index(size) + 1
        return learned

    def _prominence(self, paragraph: Paragraph) -> float:
        """How much this paragraph stands out from body text, in [0, 1]."""
        score = 0.0
        size = _size_pt(paragraph)
        if size is not None and self.body_size_pt:
            ratio = size / self.body_size_pt
            if ratio >= 1.4:
                score += 0.5
            elif ratio >= 1.15:
                score += 0.35
            elif ratio >= 1.05:
                score += 0.15
        if _mostly(paragraph, "is_bold"):
            score += 0.3
        if _mostly(paragraph, "is_caps"):
            score += 0.2
        props = _props(paragraph)
        if props.keep_next:
            score += 0.15
        if props.space_before_pt and props.space_before_pt >= 6:
            score += 0.1
        return min(score, 1.0)

    # -- classification ---------------------------------------------------

    def classify(self, paragraph: Paragraph) -> Verdict:
        key = id(paragraph)
        cached = self._verdicts.get(key)
        if cached is not None:
            return cached
        verdict = self._classify(paragraph)
        self._verdicts[key] = verdict
        return verdict

    def _classify(self, paragraph: Paragraph) -> Verdict:
        text = paragraph.text().strip()
        props = _props(paragraph)
        if not text:
            return Verdict(kind="body", confidence=1.0, evidence=["empty"])

        # Text inside a table cell belongs to the table.  A bold, prominent
        # column header looks exactly like a heading and is never one; the
        # containing table is the structure, not the cell.
        if paragraph.table_depth:
            return Verdict(
                kind="body", confidence=0.95, evidence=["inside a table cell"]
            )

        # A numbered or bulleted paragraph is a list item unless Word also calls
        # it an outline heading -- numbered headings are numbered too.
        if props.is_numbered and props.outline_level is None:
            style_level = self.heading_styles.get(props.style_id or "")
            if style_level is None:
                return Verdict(
                    kind="list_item",
                    level=(props.numbering_level or 0),
                    confidence=0.85,
                    evidence=[f"numPr numId={props.numbering_id}"],
                )

        # 1. Word's own answer.
        if props.outline_level is not None and props.outline_level < 9:
            if not _looks_like_prose(text):
                return Verdict(
                    kind="heading",
                    level=props.outline_level + 1,
                    confidence=0.97,
                    evidence=[f"outlineLvl={props.outline_level}"],
                    number=self._number_of(text),
                )

        # 2. A style that behaves like a heading throughout this document.
        style_level = self.heading_styles.get(props.style_id or "")
        if style_level and not _looks_like_prose(text):
            return Verdict(
                kind="heading",
                level=style_level,
                confidence=0.9,
                evidence=[f"style {props.style_id!r} behaves as a heading here"],
                number=self._number_of(text),
            )

        if _looks_like_prose(text):
            return Verdict(kind="body", confidence=0.9, evidence=["reads as prose"])

        # 3 and 4. Visual prominence, corroborated by a section number.
        prominence = self._prominence(paragraph)
        numbered = _leading_number(text)
        evidence = []
        if prominence:
            evidence.append(f"prominence={prominence:.2f} vs body {self.body_size_pt}pt")
        if numbered:
            evidence.append(f"leading section number {numbered[0]!r}")

        # A lone short acronym -- "BDDS", "QOL" -- is bold and capitalised for
        # the same reasons a heading is, and is almost never a heading.  It has
        # to be bigger than body text, not merely emphasised, to count.
        lone_acronym = (
            numbered is None
            and len(text.split()) == 1
            and text.isupper()
            and len(text) <= 6
        )
        bar = 0.65 if lone_acronym else 0.45
        if lone_acronym:
            evidence.append("lone acronym: held to a higher bar")

        if prominence >= bar or (numbered and prominence >= 0.15):
            level = numbered[1] if numbered else self._level_from_size(paragraph)
            return Verdict(
                kind="heading",
                level=level,
                confidence=min(0.5 + prominence / 2, 0.85),
                evidence=evidence,
                number=numbered[0] if numbered else None,
            )

        return Verdict(kind="body", confidence=0.6, evidence=evidence or ["no signal"])

    def _number_of(self, text: str) -> Optional[str]:
        found = _leading_number(text)
        return found[0] if found else None

    def _level_from_size(self, paragraph: Paragraph) -> int:
        """Rank a heading among the other heading-sized text in the document."""
        size = _size_pt(paragraph)
        if size is None or not self.body_size_pt:
            return 1
        bigger = sorted(
            {s for s in self._sizes if s > self.body_size_pt * 1.02}, reverse=True
        )
        if size in bigger:
            return bigger.index(size) + 1
        return len(bigger) + 1 if bigger else 1

    # -- reporting --------------------------------------------------------

    def observations(self) -> Dict[str, object]:
        """What was measured, for the ``Document.observations`` field."""
        return {
            "body_size_pt": self.body_size_pt,
            "size_histogram": {str(k): v for k, v in sorted(self._sizes.items())},
            "heading_styles": dict(sorted(self.heading_styles.items())),
            "paragraphs": len(self.paragraphs),
        }


__all__ = ["DocumentSignals", "Verdict"]
