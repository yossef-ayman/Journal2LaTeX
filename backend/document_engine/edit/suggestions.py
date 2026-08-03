"""Proposed edits, and the decision the user makes about each one.

The directive is explicit that the editor must not overwrite the document.  It
proposes, the user disposes -- the Google Docs / pull request / track changes
shape.  This module is the data behind that: a :class:`Suggestion` is a
*proposal* against one node, carrying the original text so it can be checked
against the document at the moment it is applied, and a status that starts at
``pending`` and only becomes an actual edit when someone says so.

Three things about the design are deliberate.

**A suggestion names a node, not an offset.**  Offsets move the instant an
earlier edit is applied; a node id is stable across a re-parse of the same
bytes.  The writer resolves the id to bytes at apply time, once, in document
order.

**The original text travels with the suggestion.**  The user may have reloaded
the document, or a different copy of it.  Applying an edit whose ``original`` no
longer matches what is actually in the file is the single most dangerous thing
this engine could do, so it is refused rather than guessed at (see
:mod:`document_engine.edit.writer`).

**A user edit is a first-class outcome.**  "Accept, reject, or edit" means the
third case has to be storable, so :meth:`Suggestion.edit` records the user's own
text and marks the suggestion accepted with the human as its author.  The
machine's proposal is kept either way, because losing what was suggested makes
the accepted result impossible to review afterwards.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional

PENDING = "pending"
ACCEPTED = "accepted"
REJECTED = "rejected"

_STATUSES = (PENDING, ACCEPTED, REJECTED)


class SuggestionError(ValueError):
    """A suggestion was malformed, or a decision was made about an unknown one."""


def _identifier(node_id: str, original: str, suggested: str, kind: str) -> str:
    """A deterministic id for a proposal.

    Deterministic on purpose: the same document analysed twice by the same
    plugins must produce the same ids, or a user's accept/reject decisions
    cannot survive a page reload.  Nothing here uses a counter, a timestamp or
    an address.
    """
    digest = hashlib.sha1(
        "\x00".join((node_id, kind, original, suggested)).encode("utf-8")
    ).hexdigest()
    return f"sug-{digest[:16]}"


@dataclass
class Suggestion:
    """One proposed replacement for the text of one node."""

    node_id: str
    original: str
    suggested: str
    # Free-form and open by design: "grammar", "citation", "journal-rule",
    # "consistency", "manual".  The core never switches on it; a plugin uses it
    # to group its own output, and the UI to label it.
    kind: str = "manual"
    reason: str = ""
    # Which plugin or person proposed this.  "user" once someone has edited it.
    source: str = "engine"
    confidence: float = 1.0
    status: str = PENDING
    # Set only when the user rewrote the proposal rather than accepting it.
    user_text: Optional[str] = None
    id: str = ""

    def __post_init__(self) -> None:
        if not self.node_id:
            raise SuggestionError("a suggestion must name the node it applies to")
        if self.status not in _STATUSES:
            raise SuggestionError(f"unknown status {self.status!r}")
        if not self.id:
            self.id = _identifier(self.node_id, self.original, self.suggested, self.kind)

    # -- the user's decision ---------------------------------------------

    def accept(self) -> "Suggestion":
        self.status = ACCEPTED
        return self

    def reject(self) -> "Suggestion":
        self.status = REJECTED
        self.user_text = None
        return self

    def edit(self, text: str) -> "Suggestion":
        """Accept, but with the user's wording instead of the engine's."""
        self.user_text = text
        self.source = "user"
        self.status = ACCEPTED
        return self

    def reset(self) -> "Suggestion":
        self.status = PENDING
        self.user_text = None
        return self

    # -- what would actually be written ----------------------------------

    @property
    def replacement(self) -> str:
        """The text this suggestion would put in the document if applied."""
        return self.user_text if self.user_text is not None else self.suggested

    @property
    def is_accepted(self) -> bool:
        return self.status == ACCEPTED

    @property
    def is_noop(self) -> bool:
        """Nothing to do -- the proposal matches what is already there."""
        return self.replacement == self.original

    def as_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "kind": self.kind,
            "reason": self.reason,
            "source": self.source,
            "confidence": round(self.confidence, 3),
            "status": self.status,
            "original": self.original,
            "suggested": self.suggested,
            "user_text": self.user_text,
            "replacement": self.replacement,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "Suggestion":
        """Rebuild a suggestion from the wire, tolerating a partial payload."""
        try:
            suggestion = cls(
                node_id=str(payload["node_id"]),
                original=str(payload.get("original", "")),
                suggested=str(payload.get("suggested", "")),
                kind=str(payload.get("kind", "manual")),
                reason=str(payload.get("reason", "")),
                source=str(payload.get("source", "engine")),
                confidence=float(payload.get("confidence", 1.0)),
                status=str(payload.get("status", PENDING)),
                id=str(payload.get("id", "")),
            )
        except KeyError as error:
            raise SuggestionError(f"missing field: {error}") from error
        user_text = payload.get("user_text")
        if user_text is not None:
            suggestion.user_text = str(user_text)
        return suggestion


class SuggestionSet:
    """Every proposal against one document, and the decisions made about them.

    Insertion order is preserved, so a UI that renders the set gets the same
    order twice.  Application order is *not* this order -- the writer sorts by
    document position, because two edits in the same paragraph have to be
    spliced right to left.
    """

    def __init__(self, suggestions: Iterable[Suggestion] = ()) -> None:
        self._by_id: Dict[str, Suggestion] = {}
        for suggestion in suggestions:
            self.add(suggestion)

    # -- collection ------------------------------------------------------

    def add(self, suggestion: Suggestion) -> Suggestion:
        existing = self._by_id.get(suggestion.id)
        if existing is not None:
            # The same proposal offered twice is one proposal.  Two plugins
            # noticing the same typo should not make the user click twice.
            return existing
        self._by_id[suggestion.id] = suggestion
        return suggestion

    def propose(self, node_id: str, original: str, suggested: str, **kwargs) -> Suggestion:
        return self.add(
            Suggestion(node_id=node_id, original=original, suggested=suggested, **kwargs)
        )

    def get(self, suggestion_id: str) -> Suggestion:
        try:
            return self._by_id[suggestion_id]
        except KeyError as error:
            raise SuggestionError(f"no such suggestion: {suggestion_id}") from error

    def __iter__(self) -> Iterator[Suggestion]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, suggestion_id: object) -> bool:
        return suggestion_id in self._by_id

    # -- decisions -------------------------------------------------------

    def accept(self, suggestion_id: str) -> Suggestion:
        return self.get(suggestion_id).accept()

    def reject(self, suggestion_id: str) -> Suggestion:
        return self.get(suggestion_id).reject()

    def edit(self, suggestion_id: str, text: str) -> Suggestion:
        return self.get(suggestion_id).edit(text)

    def accept_all(self) -> "SuggestionSet":
        for suggestion in self:
            suggestion.accept()
        return self

    def reject_all(self) -> "SuggestionSet":
        for suggestion in self:
            suggestion.reject()
        return self

    # -- views -----------------------------------------------------------

    @property
    def accepted(self) -> List[Suggestion]:
        return [s for s in self if s.is_accepted and not s.is_noop]

    @property
    def pending(self) -> List[Suggestion]:
        return [s for s in self if s.status == PENDING]

    @property
    def rejected(self) -> List[Suggestion]:
        return [s for s in self if s.status == REJECTED]

    def counts(self) -> Dict[str, int]:
        return {
            "total": len(self),
            "accepted": len([s for s in self if s.is_accepted]),
            "pending": len(self.pending),
            "rejected": len(self.rejected),
        }

    def as_list(self) -> List[Dict[str, object]]:
        return [s.as_dict() for s in self]

    @classmethod
    def from_list(cls, payload: Iterable[Dict[str, object]]) -> "SuggestionSet":
        return cls(Suggestion.from_dict(item) for item in payload)


__all__ = [
    "ACCEPTED",
    "PENDING",
    "REJECTED",
    "Suggestion",
    "SuggestionError",
    "SuggestionSet",
]
