"""Resolving formatting the way Word does, not the way the XML reads.

A paragraph's appearance is almost never written on the paragraph.  Word layers
it: document defaults, then the paragraph's style, then every style that one is
``basedOn``, then whatever the author applied directly.  Runs add two more
layers on top -- the paragraph style's character formatting, then the run's own
character style chain, then direct ``w:rPr``.

This is the difference between a parser that works on one template and one that
works on a manuscript.  A Springer heading is bold because ``Heading1`` is bold;
its ``w:r`` says nothing at all.  Reading the run and stopping there sees plain
12pt text and files the heading as a body paragraph -- silently, and on every
document from that publisher.

:class:`StyleResolver` owns that cascade and nothing else.  It answers "what
does this actually look like", never "is this a title".

Numbering is read here too, for a narrower reason: ``w:numPr`` tells you a
paragraph is numbered but not *how*.  Whether a list is decimal-with-dots or
bulleted is what separates "1.2 Methods" the heading from "1." the list item,
and that lives in ``word/numbering.xml``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence
from xml.parsers import expat

from document_engine.ooxml.blocks import (
    Block,
    Paragraph,
    Run,
    Table,
    TextBox,
    W_NS,
    iter_paragraphs,
)
from document_engine.ooxml.builder import (
    _int,
    _on_off,
    _split,
    _w,
    read_paragraph_property,
    read_run_property,
)
from document_engine.ooxml.props import ParagraphProps, RunProps

# How deep a basedOn chain may go before we call it a cycle.  Word's own limit is
# smaller; this is a guard against a malformed file, not a real constraint.
_MAX_CHAIN = 24


@dataclass
class Style:
    """One ``w:style``: what it says, and what it is based on."""

    style_id: str
    type: str = "paragraph"
    name: str = ""
    based_on: Optional[str] = None
    next_style: Optional[str] = None
    is_default: bool = False
    paragraph: ParagraphProps = field(default_factory=ParagraphProps)
    run: RunProps = field(default_factory=RunProps)
    # Style-level numbering, which is how most heading styles get their numbers.
    numbering_id: Optional[int] = None


@dataclass
class NumberingLevel:
    """One level of a list definition."""

    level: int
    fmt: Optional[str] = None
    text: Optional[str] = None
    start: Optional[int] = None
    style_id: Optional[str] = None
    indent_left_twips: Optional[int] = None

    @property
    def is_bullet(self) -> bool:
        return self.fmt == "bullet"


class StyleResolver:
    """The formatting cascade for one package."""

    def __init__(
        self,
        styles_xml: Optional[bytes] = None,
        numbering_xml: Optional[bytes] = None,
    ) -> None:
        self.styles: Dict[str, Style] = {}
        self.default_paragraph_style: Optional[str] = None
        self.default_character_style: Optional[str] = None
        self.doc_defaults_paragraph = ParagraphProps()
        self.doc_defaults_run = RunProps()
        # numId -> abstractNumId, and abstractNumId -> {level: NumberingLevel}
        self.num_to_abstract: Dict[int, int] = {}
        self.abstract_levels: Dict[int, Dict[int, NumberingLevel]] = {}

        self._paragraph_cache: Dict[str, ParagraphProps] = {}
        self._run_cache: Dict[str, RunProps] = {}

        if styles_xml:
            self._read_styles(styles_xml)
        if numbering_xml:
            self._read_numbering(numbering_xml)

    # -- construction ----------------------------------------------------

    @classmethod
    def from_zip(cls, archive) -> "StyleResolver":
        """Build from an open :class:`zipfile.ZipFile` of a .docx.

        Missing parts are normal -- a document with no lists has no
        ``numbering.xml`` -- and produce an emptier resolver, not an error.
        """

        def read(name: str) -> Optional[bytes]:
            try:
                return archive.read(name)
            except KeyError:
                return None

        return cls(read("word/styles.xml"), read("word/numbering.xml"))

    # -- style chain -----------------------------------------------------

    def _chain(self, style_id: Optional[str]) -> List[Style]:
        """A style and its ancestors, nearest first."""
        chain: List[Style] = []
        seen = set()
        current = style_id
        while current and current not in seen and len(chain) < _MAX_CHAIN:
            seen.add(current)
            style = self.styles.get(current)
            if style is None:
                break
            chain.append(style)
            current = style.based_on
        return chain

    def paragraph_style_props(self, style_id: Optional[str]) -> ParagraphProps:
        """Paragraph formatting contributed by a style chain plus doc defaults."""
        key = style_id or ""
        cached = self._paragraph_cache.get(key)
        if cached is not None:
            return cached
        resolved = self.doc_defaults_paragraph
        # Walk the chain from the *root* outwards so nearer styles layer on top.
        for style in reversed(self._chain(style_id or self.default_paragraph_style)):
            resolved = style.paragraph.over(resolved)
        self._paragraph_cache[key] = resolved
        return resolved

    def run_style_props(self, style_id: Optional[str]) -> RunProps:
        """Character formatting contributed by a style chain plus doc defaults."""
        key = style_id or ""
        cached = self._run_cache.get(key)
        if cached is not None:
            return cached
        resolved = self.doc_defaults_run
        for style in reversed(self._chain(style_id)):
            resolved = style.run.over(resolved)
        self._run_cache[key] = resolved
        return resolved

    # -- the public questions --------------------------------------------

    def effective_paragraph_props(self, paragraph: Paragraph) -> ParagraphProps:
        """What this paragraph's formatting resolves to.

        Direct formatting over the style chain over the document defaults.  A
        paragraph style may itself carry numbering, which is why the style's
        ``numbering_id`` is folded in rather than read from ``w:numPr`` alone.
        """
        base = self.paragraph_style_props(paragraph.props.style_id)
        style = self.styles.get(paragraph.props.style_id or "")
        if style is not None and style.numbering_id is not None:
            base = ParagraphProps(numbering_id=style.numbering_id).over(base)
        return paragraph.props.over(base)

    def effective_run_props(self, run: Run, paragraph: Optional[Paragraph]) -> RunProps:
        """What this run's character formatting resolves to.

        Order: document defaults, then the *paragraph* style's ``w:rPr`` (this is
        the layer that makes an entire heading bold with no run saying so), then
        the run's own character style chain, then direct ``w:rPr``.
        """
        base = self.doc_defaults_run
        if paragraph is not None:
            paragraph_style_id = paragraph.props.style_id or self.default_paragraph_style
            for style in reversed(self._chain(paragraph_style_id)):
                base = style.run.over(base)
        if run.props.style_id:
            for style in reversed(self._chain(run.props.style_id)):
                base = style.run.over(base)
        elif self.default_character_style:
            for style in reversed(self._chain(self.default_character_style)):
                base = style.run.over(base)
        return run.props.over(base)

    def numbering_level(self, props: ParagraphProps) -> Optional[NumberingLevel]:
        """The list definition a paragraph's ``w:numPr`` points at, if any."""
        if not props.is_numbered:
            return None
        abstract = self.num_to_abstract.get(int(props.numbering_id or 0))
        if abstract is None:
            return None
        levels = self.abstract_levels.get(abstract) or {}
        return levels.get(int(props.numbering_level or 0))

    def resolve(self, blocks: Sequence[Block]) -> None:
        """Fill in ``effective`` on every paragraph and run in a block tree.

        Done in place and only once: :attr:`Paragraph.props` keeps saying what
        the *file* says, which is what a writer must preserve, while
        ``effective`` says what the reader should judge by.
        """
        for paragraph in iter_paragraphs(blocks, skip_fallback=False):
            paragraph.effective = self.effective_paragraph_props(paragraph)
            for run in paragraph.runs:
                run.effective = self.effective_run_props(run, paragraph)

    # -- reading styles.xml ----------------------------------------------

    def _read_styles(self, data: bytes) -> None:
        parser = expat.ParserCreate(namespace_separator=" ")
        state: Dict[str, object] = {
            "style": None,
            "ctx": [],
            "p_pending": {},
            "r_pending": {},
            "defaults": None,
        }

        def context() -> List[str]:
            return state["ctx"]  # type: ignore[return-value]

        def start(name: str, attrs: Dict[str, str]) -> None:
            uri, local = _split(name)
            if uri != W_NS:
                return
            ctx = context()
            if local == "docDefaults":
                state["defaults"] = True
                return
            if local == "style":
                state["style"] = Style(
                    style_id=_w(attrs, "styleId") or "",
                    type=_w(attrs, "type") or "paragraph",
                    is_default=_on_off(attrs) if _w(attrs, "default") else False,
                )
                state["p_pending"] = {}
                state["r_pending"] = {}
                return
            if local in ("pPr", "rPr", "numPr", "pPrDefault", "rPrDefault", "rFonts", "tabs", "pBdr"):
                ctx.append(local)
                if local not in ("rFonts",):
                    return
            if local == "name" and state["style"] is not None:
                state["style"].name = _w(attrs, "val") or ""  # type: ignore[union-attr]
                return
            if local == "basedOn" and state["style"] is not None:
                state["style"].based_on = _w(attrs, "val")  # type: ignore[union-attr]
                return
            if local == "next" and state["style"] is not None:
                state["style"].next_style = _w(attrs, "val")  # type: ignore[union-attr]
                return
            if not ctx:
                return
            # Inside w:pPr but not inside its w:rPr -> paragraph formatting.
            in_rpr = "rPr" in ctx
            in_ppr = "pPr" in ctx or "pPrDefault" in ctx
            if local == "numId" and in_ppr and not in_rpr:
                value = _int(_w(attrs, "val"))
                if state["style"] is not None and value:
                    state["style"].numbering_id = value  # type: ignore[union-attr]
                read_paragraph_property(state["p_pending"], local, attrs)  # type: ignore[arg-type]
            elif in_rpr:
                read_run_property(state["r_pending"], local, attrs)  # type: ignore[arg-type]
            elif in_ppr:
                read_paragraph_property(state["p_pending"], local, attrs)  # type: ignore[arg-type]

        def end(name: str) -> None:
            uri, local = _split(name)
            if uri != W_NS:
                return
            ctx = context()
            if ctx and ctx[-1] == local:
                ctx.pop()
            if local == "style" and state["style"] is not None:
                style: Style = state["style"]  # type: ignore[assignment]
                style.paragraph = ParagraphProps(**state["p_pending"])  # type: ignore[arg-type]
                style.run = RunProps(**state["r_pending"])  # type: ignore[arg-type]
                if style.style_id:
                    self.styles[style.style_id] = style
                    if style.is_default and style.type == "paragraph":
                        self.default_paragraph_style = style.style_id
                    elif style.is_default and style.type == "character":
                        self.default_character_style = style.style_id
                state["style"] = None
                state["p_pending"] = {}
                state["r_pending"] = {}
            elif local == "docDefaults":
                self.doc_defaults_paragraph = ParagraphProps(**state["p_pending"])  # type: ignore[arg-type]
                self.doc_defaults_run = RunProps(**state["r_pending"])  # type: ignore[arg-type]
                state["defaults"] = None
                state["p_pending"] = {}
                state["r_pending"] = {}

        parser.StartElementHandler = start
        parser.EndElementHandler = end
        parser.buffer_text = False
        try:
            parser.Parse(data, True)
        except expat.ExpatError:  # pragma: no cover - malformed styles part
            pass

    # -- reading numbering.xml -------------------------------------------

    def _read_numbering(self, data: bytes) -> None:
        parser = expat.ParserCreate(namespace_separator=" ")
        state: Dict[str, object] = {
            "abstract": None,
            "level": None,
            "num": None,
            "in_lvl_ppr": False,
        }

        def start(name: str, attrs: Dict[str, str]) -> None:
            uri, local = _split(name)
            if uri != W_NS:
                return
            if local == "abstractNum":
                abstract = _int(_w(attrs, "abstractNumId"))
                state["abstract"] = abstract
                if abstract is not None:
                    self.abstract_levels.setdefault(abstract, {})
            elif local == "lvl":
                level = _int(_w(attrs, "ilvl")) or 0
                state["level"] = NumberingLevel(level=level)
            elif local == "pPr":
                state["in_lvl_ppr"] = True
            elif state["level"] is not None:
                lvl: NumberingLevel = state["level"]  # type: ignore[assignment]
                if local == "numFmt":
                    lvl.fmt = _w(attrs, "val")
                elif local == "lvlText":
                    lvl.text = _w(attrs, "val")
                elif local == "start":
                    lvl.start = _int(_w(attrs, "val"))
                elif local == "pStyle":
                    lvl.style_id = _w(attrs, "val")
                elif local == "ind" and state["in_lvl_ppr"]:
                    lvl.indent_left_twips = _int(_w(attrs, "left") or _w(attrs, "start"))
            if local == "num":
                state["num"] = _int(_w(attrs, "numId"))
            elif local == "abstractNumId" and state["num"] is not None:
                target = _int(_w(attrs, "val"))
                if target is not None:
                    self.num_to_abstract[int(state["num"])] = target  # type: ignore[arg-type]

        def end(name: str) -> None:
            uri, local = _split(name)
            if uri != W_NS:
                return
            if local == "lvl" and state["level"] is not None:
                abstract = state["abstract"]
                lvl: NumberingLevel = state["level"]  # type: ignore[assignment]
                if abstract is not None:
                    self.abstract_levels.setdefault(int(abstract), {})[lvl.level] = lvl
                state["level"] = None
            elif local == "pPr":
                state["in_lvl_ppr"] = False
            elif local == "abstractNum":
                state["abstract"] = None
            elif local == "num":
                state["num"] = None

        parser.StartElementHandler = start
        parser.EndElementHandler = end
        parser.buffer_text = False
        try:
            parser.Parse(data, True)
        except expat.ExpatError:  # pragma: no cover - malformed numbering part
            pass


__all__ = ["NumberingLevel", "Style", "StyleResolver"]
