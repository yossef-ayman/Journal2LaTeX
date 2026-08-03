"""The section tree, built from the heading verdicts.

Two jobs.  First, turn a flat run of headings and content into a tree, which is
only interesting because real documents skip levels -- a level 1 followed by a
level 3 is common, and the tree has to stay well-formed anyway.  Second, name
the sections that mean something structural: the abstract, the keywords line and
the bibliography.

That naming is by role, not by title.  A references section is one whose content
is a run of similarly-shaped entries at the end of the document; the word
"References" raises confidence but is not required, because the word is
different in every language and absent in plenty of theses.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence

from document_engine.extract.objects import parse_caption
from document_engine.extract.signals import DocumentSignals, _size_pt
from document_engine.model.nodes import Block, ListItem, Section, TextNode
from document_engine.ooxml.blocks import Paragraph, Table

_ABSTRACT = re.compile(r"^\s*(abstract|summary|résumé|resumen)\b", re.I)
_KEYWORDS = re.compile(r"^\s*key\s?words?\b", re.I)
_REFERENCES = re.compile(
    r"^\s*(references?|bibliograph\w*|works\s+cited|literature\s+cited)\b", re.I
)
_ACKNOWLEDGE = re.compile(r"^\s*acknowledge?ment", re.I)


def _kind_of(title: str) -> str:
    if _ABSTRACT.match(title):
        return "abstract"
    if _KEYWORDS.match(title):
        return "keywords"
    if _REFERENCES.match(title):
        return "references"
    if _ACKNOWLEDGE.match(title):
        return "acknowledgements"
    return "body"


def _strip_number(title: str) -> str:
    return re.sub(r"^\s*(?:\d+(?:\s*\.\s*\d+)*|[IVXLC]{1,6}|[A-Z])\s*[.)\]]?\s+", "", title)


class SectionBuilder:
    """Turns classified blocks into a tree of :class:`Section`."""

    def __init__(self, signals: DocumentSignals, resolver=None) -> None:
        self.signals = signals
        # Optional: with it, a bulleted list is told apart from a numbered one
        # by reading numbering.xml.  Without it, lists are assumed ordered and
        # say so in their evidence rather than pretending to know.
        self.resolver = resolver

    def build(self, blocks: Sequence[object]) -> tuple:
        """Return ``(front_matter_paragraphs, sections)``.

        Front matter is everything before the first heading that starts the
        body.  The title itself is a heading by every visual measure, so the
        boundary is the *second* structural heading when the first one is the
        title -- which the metadata extractor decides.  Rather than guess twice,
        this returns every pre-body paragraph and lets the metadata extractor
        pick the title out of it.
        """
        first = self._body_start(blocks)
        front = [b for b in blocks[:first] if isinstance(b, Paragraph) and not b.in_fallback]
        sections = self._tree(blocks[first:])
        return front, sections

    def _body_start(self, blocks: Sequence[object]) -> int:
        """Where the front matter ends.

        The first heading that is not the document's own title: either one whose
        text names a known structural section, or one carrying a section number,
        or -- failing both -- the second heading in the document.
        """
        headings = [
            (index, block)
            for index, block in enumerate(blocks)
            if isinstance(block, Paragraph)
            and not block.in_fallback
            and self.signals.classify(block).is_heading
        ]
        if not headings:
            return 0
        if len(headings) == 1:
            return headings[0][0]

        # The title, if it is one of the headings, is the most prominent of
        # them and comes first.  Both conditions have to hold: a document whose
        # first heading is an ordinary section (because the title was never
        # styled as a heading) must not lose that section.
        first_index, first_block = headings[0]
        most_prominent = max(headings, key=lambda h: self.signals._prominence(h[1]))
        # Either measure can identify it, and they disagree in real documents:
        # a 26pt Title style is not bold, so a 14pt bold Heading 1 can out-score
        # it on prominence while being obviously smaller.  Size settles that.
        sizes = [(_size_pt(b) or 0.0) for _, b in headings]
        biggest = sizes[0] >= max(sizes)
        looks_like_a_title = (
            not self.signals.classify(first_block).number
            and _kind_of(first_block.text().strip()) == "body"
        )
        first_is_title = looks_like_a_title and (
            biggest or most_prominent[0] == first_index
        )
        return headings[1][0] if first_is_title else first_index

    def _tree(self, blocks: Sequence[object]) -> List[Section]:
        root = Section(id="root", title="", level=0)
        stack: List[Section] = [root]

        for index, block in enumerate(blocks):
            if isinstance(block, Paragraph) and block.in_fallback:
                continue
            if isinstance(block, Paragraph) and block.table_depth:
                continue  # cell content belongs to its table, not the section
            if isinstance(block, Table) and block.table_depth:
                continue

            if isinstance(block, Paragraph):
                verdict = self.signals.classify(block)
                if verdict.is_heading:
                    title = block.text().strip()
                    section = Section(
                        id=f"section:{block.anchor.start}" if block.anchor else f"s{index}",
                        anchor=block.anchor,
                        title=_strip_number(title) or title,
                        level=max(verdict.level, 1),
                        number=verdict.number,
                        kind=_kind_of(title),
                        heading_block=block,
                        confidence=verdict.confidence,
                        evidence=list(verdict.evidence),
                    )
                    # Skipped levels are normal; the tree stays well-formed by
                    # attaching to the nearest shallower ancestor.
                    while len(stack) > 1 and stack[-1].level >= section.level:
                        stack.pop()
                    stack[-1].children.append(section)
                    stack.append(section)
                    continue

            item = self._content(block, index)
            if item is not None:
                stack[-1].content.append(item)

        return root.children

    def _content(self, block: object, index: int) -> Optional[Block]:
        if isinstance(block, Table):
            return Block(
                id=f"block:table:{block.anchor.start}" if block.anchor else f"b{index}",
                anchor=block.anchor,
                kind="table",
            )
        if not isinstance(block, Paragraph):
            return None
        text = block.text().strip()
        if not text and not block.drawings:
            return None

        anchor_id = block.anchor.start if block.anchor else index
        if block.drawings:
            return Block(id=f"block:figure:{anchor_id}", anchor=block.anchor, kind="figure")
        caption = parse_caption(block)
        if caption is not None:
            return Block(
                id=f"block:caption:{anchor_id}",
                anchor=block.anchor,
                kind="caption",
                item=caption,
            )
        if block.equation_count:
            return Block(id=f"block:equation:{anchor_id}", anchor=block.anchor, kind="equation")

        props = block.effective or block.props
        if props is not None and props.is_numbered:
            ordered = True
            marker_format = None
            evidence = ["numPr, but numbering.xml was not available"]
            if self.resolver is not None:
                definition = self.resolver.numbering_level(props)
                if definition is not None:
                    ordered = not definition.is_bullet
                    marker_format = definition.fmt
                    evidence = [f"numbering format {definition.fmt!r}"]
            return Block(
                id=f"block:list:{anchor_id}",
                anchor=block.anchor,
                kind="list_item",
                item=ListItem(
                    id=f"list:{anchor_id}",
                    anchor=block.anchor,
                    text=text,
                    block=block,
                    level=props.numbering_level or 0,
                    ordered=ordered,
                    marker_format=marker_format,
                    evidence=evidence,
                ),
            )
        return Block(
            id=f"block:paragraph:{anchor_id}",
            anchor=block.anchor,
            kind="paragraph",
            item=TextNode(
                id=f"paragraph:{anchor_id}",
                anchor=block.anchor,
                text=text,
                block=block,
            ),
        )


__all__ = ["SectionBuilder", "_kind_of"]
