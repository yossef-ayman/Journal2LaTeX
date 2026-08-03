"""The front matter: title, authors, affiliations, abstract, keywords.

This is the part of a paper with the least structure and the most variation.
Springer puts affiliations in superscript-marked lines under the authors; IEEE
puts them in a table; a thesis may have neither and a plain Word file may have
nothing but a big line at the top.  So nothing here requires a marker, a label
or an order -- each field is found by its own evidence, and every field records
how confident the engine is that it found the right thing.

The one structural assumption is that front matter comes before the body, which
is true of every document that has front matter at all.  Where the body starts
is measured (the first paragraph the signals call a numbered or well-known
section heading), not assumed.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from document_engine.extract.signals import DocumentSignals, _props, _size_pt
from document_engine.model.nodes import Affiliation, Author, Metadata, TextNode
from document_engine.ooxml.blocks import Paragraph

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_DOI = re.compile(r"\b(?:doi:\s*|https?://(?:dx\.)?doi\.org/)(10\.\d{4,9}/\S+)", re.I)

# Labels are a *hint*, never a requirement, and are matched loosely because
# documents write them a dozen ways.
_ABSTRACT = re.compile(r"^\s*abstract\b\s*[:.—-]?\s*", re.I)
_KEYWORDS = re.compile(r"^\s*key\s?words?\b\s*[:.—-]?\s*", re.I)
_CORRESPONDING = re.compile(r"correspond", re.I)
_RECEIVED = re.compile(r"^\s*received\b\s*[:.]?\s*(.+)$", re.I)
_ACCEPTED = re.compile(r"^\s*accepted\b\s*[:.]?\s*(.+)$", re.I)
_PUBLISHED = re.compile(r"^\s*published\b\s*[:.]?\s*(.+)$", re.I)

# The markers that tie an author to an affiliation.  Digits, daggers, stars and
# letters all appear in the wild; what matters is that the same glyph shows up
# on both sides.
_MARKER_CHARS = "0123456789*†‡§¶#abcdefghijklmnop"
_MARKER = re.compile(r"^[\s,;]*([" + re.escape(_MARKER_CHARS) + r"]{1,3})[\s,;.)]*")

# Words that mean a line is describing an institution rather than naming a
# person.  Generic on purpose: no journal, city or university from any real
# document appears here.
_AFFILIATION_WORDS = (
    "university",
    "universit",
    "institute",
    "institut",
    "college",
    "school",
    "faculty",
    "department",
    "dept",
    "laboratory",
    "lab",
    "centre",
    "center",
    "academy",
    "hospital",
    "clinic",
    "ministry",
    "college",
    "company",
    "corporation",
    "inc.",
    "ltd",
    "gmbh",
    "campus",
    "p.o. box",
    "po box",
)

_TITLE_WORDS = ("dr", "prof", "professor", "mr", "mrs", "ms", "phd", "msc", "eng")

_SEPARATORS = re.compile(r"\s*(?:,|;|\band\b|&)\s*", re.I)


def _looks_like_affiliation(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in _AFFILIATION_WORDS)


def _looks_like_person(text: str) -> bool:
    """A name is two-to-four capitalised words and no institution vocabulary."""
    stripped = text.strip().strip(",;")
    if not stripped or _looks_like_affiliation(stripped):
        return False
    if _EMAIL.search(stripped):
        return False
    words = [w for w in re.split(r"\s+", stripped) if w]
    if not 1 < len(words) <= 5:
        return False
    capitalised = sum(1 for w in words if w[:1].isupper())
    return capitalised >= max(2, len(words) - 1)


def _strip_markers(text: str) -> Tuple[str, List[str]]:
    """Split ``"Jane Doe1,*"`` into ``("Jane Doe", ["1", "*"])``.

    Only trailing markers are taken, and only when what remains still looks like
    a name -- otherwise ``"3D Printing"`` would lose its 3.
    """
    markers: List[str] = []
    remainder = text.strip()
    while remainder:
        match = re.search(r"[\s,]*([0-9*†‡§#])+\s*$", remainder)
        if not match:
            break
        candidate = remainder[: match.start()].strip()
        if not candidate or not candidate[-1:].isalpha():
            break
        markers[:0] = list(match.group(0).strip(" ,"))
        remainder = candidate
    for word in _TITLE_WORDS:
        remainder = re.sub(rf"^\s*{word}\.?\s+", "", remainder, flags=re.I)
    return remainder.strip(), markers


def _superscript_markers(paragraph: Paragraph) -> List[str]:
    """Markers Word set as real superscripts rather than as plain characters."""
    out: List[str] = []
    for run in paragraph.runs:
        props = run.effective or run.props
        text = (run.text or "").strip()
        if not text or props is None or props.vert_align != "superscript":
            continue
        # Split on separators, not into characters: "10" is one marker and
        # "1,2" is two.  Splitting per character turns affiliation 10 into 1.
        out.extend(t for t in re.split(r"[\s,;]+", text) if t)
    return out


class MetadataExtractor:
    """Reads the front matter of one document."""

    def __init__(self, signals: DocumentSignals) -> None:
        self.signals = signals

    def extract(self, front: Sequence[Paragraph]) -> Metadata:
        meta = Metadata(id="metadata")
        front = [p for p in front if p.text().strip()]
        if not front:
            meta.note("no front matter found before the first section heading")
            meta.confidence = 0.0
            return meta

        title_index = self._title(front, meta)
        rest = front[title_index + 1 :] if title_index is not None else front

        self._subtitle(rest, meta, title_index is not None)
        self._people(rest, meta)
        self._dates_and_identifiers(front, meta)
        self._keywords(front, meta)
        self._abstract(front, meta)
        self._link_authors_to_affiliations(meta)
        return meta

    def _abstract(self, front: Sequence[Paragraph], meta: Metadata) -> None:
        """The abstract as it usually appears: front matter, not a section.

        Most journals set "Abstract" as a bold run at the head of the paragraph
        rather than as a heading, so the section builder never sees it.  It is
        found here by its label and runs until the keywords line or the end of
        the front matter.
        """
        from document_engine.model.nodes import Block, Section, TextNode as _T

        start = None
        for index, paragraph in enumerate(front):
            if _ABSTRACT.match(paragraph.text().strip()):
                start = index
                break
        if start is None:
            return

        section = Section(
            id=f"abstract:{front[start].anchor.start}" if front[start].anchor else "abstract",
            anchor=front[start].anchor,
            title="Abstract",
            level=1,
            kind="abstract",
            heading_block=front[start],
            confidence=0.9,
            evidence=["a front-matter paragraph labelled as the abstract"],
        )
        for paragraph in front[start:]:
            text = paragraph.text().strip()
            if not text:
                continue
            if paragraph is not front[start] and _KEYWORDS.match(text):
                break
            if paragraph is front[start]:
                text = _ABSTRACT.sub("", text, count=1).strip()
                if not text:
                    continue
            anchor = paragraph.anchor
            section.content.append(
                Block(
                    id=f"block:abstract:{anchor.start if anchor else 0}",
                    anchor=anchor,
                    kind="paragraph",
                    item=_T(
                        id=f"paragraph:{anchor.start if anchor else 0}",
                        anchor=anchor,
                        text=text,
                        block=paragraph,
                    ),
                )
            )
        meta.abstract = section

    # -- title ------------------------------------------------------------

    def _title(self, front: Sequence[Paragraph], meta: Metadata) -> Optional[int]:
        """The most prominent line in the front matter, earliest wins ties.

        Not "the first paragraph": documents begin with running heads, journal
        banners and blank lines.  Not "the Title style" either -- plenty of
        documents have no such style.  Prominence, measured against this
        document's own body size, is what actually identifies it.
        """
        best_index: Optional[int] = None
        best_score = -1.0
        for index, paragraph in enumerate(front):
            text = paragraph.text().strip()
            if len(text) < 8 or _EMAIL.search(text) or _looks_like_affiliation(text):
                continue
            score = self.signals._prominence(paragraph)
            size = _size_pt(paragraph)
            if size and self.signals.body_size_pt:
                score += (size / self.signals.body_size_pt - 1.0) * 0.5
            # Earlier is better, gently: a title is near the top but rarely at
            # the very first line.
            score -= index * 0.01
            if score > best_score:
                best_score, best_index = score, index

        if best_index is None:
            meta.note("no candidate title in the front matter")
            return None

        paragraph = front[best_index]
        meta.title = TextNode(
            id=f"title:{paragraph.anchor.start}" if paragraph.anchor else "title",
            anchor=paragraph.anchor,
            text=paragraph.text().strip(),
            block=paragraph,
            confidence=min(0.55 + best_score / 2, 0.95),
            evidence=[f"most prominent front-matter line (score {best_score:.2f})"],
        )
        return best_index

    def _subtitle(
        self, rest: Sequence[Paragraph], meta: Metadata, had_title: bool
    ) -> None:
        """A second prominent line immediately under the title, if there is one."""
        if not had_title or not rest:
            return
        paragraph = rest[0]
        text = paragraph.text().strip()
        if not text or _looks_like_person(text) or _looks_like_affiliation(text):
            return
        if _EMAIL.search(text):
            return
        prominence = self.signals._prominence(paragraph)
        if prominence < 0.2:
            return
        meta.subtitle = TextNode(
            id=f"subtitle:{paragraph.anchor.start}" if paragraph.anchor else "subtitle",
            anchor=paragraph.anchor,
            text=text,
            block=paragraph,
            confidence=0.5 + prominence / 3,
            evidence=["prominent line directly under the title"],
        )

    # -- people -----------------------------------------------------------

    def _people(self, rest: Sequence[Paragraph], meta: Metadata) -> None:
        for paragraph in rest:
            text = paragraph.text().strip()
            if not text:
                continue
            if _ABSTRACT.match(text):
                break  # the abstract ends the author block, always

            for address in _EMAIL.findall(text):
                if address not in meta.emails:
                    meta.emails.append(address)

            if _looks_like_affiliation(text):
                self._add_affiliation(paragraph, meta)
                continue

            names = self._names_in(paragraph)
            if names:
                superscripts = _superscript_markers(paragraph)
                for name, markers in names:
                    if not markers and len(names) == 1:
                        markers = superscripts
                    self._add_author(paragraph, meta, name, markers, text)

    def _names_in(self, paragraph: Paragraph) -> List[Tuple[str, List[str]]]:
        """Split one line into the people named on it, if any."""
        text = paragraph.text().strip()
        if len(text) > 300:
            return []
        found: List[Tuple[str, List[str]]] = []
        for chunk in _SEPARATORS.split(text):
            chunk = chunk.strip()
            if not chunk:
                continue
            name, markers = _strip_markers(chunk)
            if _looks_like_person(name):
                found.append((name, markers))
        # One unsplittable chunk that is not a person means the line is not an
        # author line at all -- do not take half of it.
        return found

    def _add_author(
        self,
        paragraph: Paragraph,
        meta: Metadata,
        name: str,
        markers: List[str],
        line: str,
    ) -> None:
        if any(a.name == name for a in meta.authors):
            return
        author = Author(
            id=f"author:{len(meta.authors)}:{paragraph.anchor.start if paragraph.anchor else 0}",
            anchor=paragraph.anchor,
            name=name,
            markers=markers,
            block=paragraph,
            confidence=0.8 if markers else 0.7,
            evidence=["reads as a personal name in the front matter"],
        )
        emails = _EMAIL.findall(line)
        if len(emails) == 1:
            author.email = emails[0]
            author.note("the only email address on the same line")
        if _CORRESPONDING.search(line) or "*" in markers:
            author.is_corresponding = True
            author.note("marked as corresponding")
            meta.corresponding.append(author)
        meta.authors.append(author)

    def _add_affiliation(self, paragraph: Paragraph, meta: Metadata) -> None:
        text = paragraph.text().strip()
        if any(a.text == text for a in meta.affiliations):
            return
        marker = ""
        superscripts = _superscript_markers(paragraph)
        if superscripts:
            marker = superscripts[0]
        else:
            match = _MARKER.match(text)
            if match and not text[: match.end()].strip().isalpha():
                marker = match.group(1)
                text = text[match.end() :].strip()
        meta.affiliations.append(
            Affiliation(
                id=f"affiliation:{len(meta.affiliations)}",
                anchor=paragraph.anchor,
                text=text,
                marker=marker,
                block=paragraph,
                confidence=0.85,
                evidence=["names an institution"],
            )
        )

    def _link_authors_to_affiliations(self, meta: Metadata) -> None:
        """Tie the two together by shared marker, and only by shared marker.

        When the markers do not line up the engine says nothing rather than
        pairing them by position -- a wrong affiliation is worse than a missing
        one, and the UI can ask.
        """
        by_marker: Dict[str, str] = {
            a.marker: a.id for a in meta.affiliations if a.marker
        }
        if not by_marker:
            if len(meta.affiliations) == 1:
                only = meta.affiliations[0].id
                for author in meta.authors:
                    author.affiliation_ids = [only]
                    author.note("the document has exactly one affiliation")
            return
        for author in meta.authors:
            matched = [by_marker[m] for m in author.markers if m in by_marker]
            if matched:
                author.affiliation_ids = matched
                author.note("matched to affiliations by superscript marker")

    # -- the rest ---------------------------------------------------------

    def _dates_and_identifiers(self, front: Sequence[Paragraph], meta: Metadata) -> None:
        for paragraph in front:
            text = paragraph.text().strip()
            doi = _DOI.search(text)
            if doi and not meta.doi:
                meta.doi = doi.group(1).rstrip(".,;")
            for pattern, attribute in (
                (_RECEIVED, "received"),
                (_ACCEPTED, "accepted"),
                (_PUBLISHED, "published"),
            ):
                match = pattern.match(text)
                if match and getattr(meta, attribute) is None:
                    setattr(meta, attribute, match.group(1).strip())

    def _keywords(self, front: Sequence[Paragraph], meta: Metadata) -> None:
        for paragraph in front:
            text = paragraph.text().strip()
            match = _KEYWORDS.match(text)
            if not match:
                continue
            body = text[match.end() :].strip()
            if not body:
                continue
            parts = [p.strip(" .") for p in re.split(r"[;,•]", body)]
            meta.keywords = [p for p in parts if p]
            meta.keywords_node = TextNode(
                id="keywords",
                anchor=paragraph.anchor,
                text=body,
                block=paragraph,
                confidence=0.9,
                evidence=["a line beginning with a keywords label"],
            )
            return


__all__ = ["MetadataExtractor"]
