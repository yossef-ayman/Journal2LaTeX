"""What a suggestion plugin is, and what it is not allowed to do.

A plugin **reads** the semantic model and **proposes**.  It cannot write: there
is no package on the context object, no writer, no bytes.  Everything a plugin
produces is a :class:`~document_engine.edit.suggestions.Suggestion` that the
existing editing engine may later apply if -- and only if -- a person accepts
it.  That constraint is enforced by what this module hands a plugin rather than
by asking plugins to behave, which is the difference between an architecture and
a convention.

Three design points are worth stating.

**Proposals quote the writer's own idea of the text.**  A suggestion is refused
at apply time if its ``original`` does not match the document character for
character, so :meth:`Context.propose` takes the original from
:func:`document_engine.edit.writer.editable_text` -- the same function the
writer uses -- instead of from whatever the plugin happened to be looking at.  A
plugin therefore cannot author an unapplyable suggestion by accident.

**Not every finding is an edit.**  "Reference 12 is never cited" is worth
telling the user and has no replacement text; forcing it into a suggestion would
mean inventing one.  Those go in :attr:`PluginResult.notes`, which the UI shows
and the writer never sees.

**The AI comes in here, not somewhere else.**  A model-backed plugin implements
the same :class:`SuggestionPlugin` interface as the deterministic ones and is
registered the same way.  Nothing above or below this seam has to change when
one arrives, which is what "deterministic first, AI later" has to mean if it is
to be true later rather than a rewrite.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from document_engine.edit.suggestions import Suggestion
from document_engine.edit.writer import editable_text
from document_engine.model.nodes import Document, Node, Section

# Sentence splitting for the plugins that work below paragraph level.  Kept
# deliberately blunt: an abbreviation followed by a capital will split wrongly,
# and every plugin here treats a sentence as a heuristic unit rather than as a
# fact it acts on.
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[])")

WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")


@dataclass
class Note:
    """A finding with no text to replace: information, not an edit."""

    plugin: str
    message: str
    node_id: Optional[str] = None
    severity: str = "info"   # "info" | "warning"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "plugin": self.plugin,
            "message": self.message,
            "node_id": self.node_id,
            "severity": self.severity,
        }


@dataclass
class PluginResult:
    """Everything one plugin found."""

    suggestions: List[Suggestion] = field(default_factory=list)
    notes: List[Note] = field(default_factory=list)


class Context:
    """Read-only view of the document, plus the only way to propose an edit.

    Held by every plugin for the duration of one run.  It has no reference to
    the package or to the writer, so a plugin has nothing to write *with*.
    """

    def __init__(self, document: Document, plugin_name: str = "") -> None:
        self.document = document
        self.plugin_name = plugin_name
        self._result = PluginResult()

    # -- proposing -------------------------------------------------------

    def propose(
        self,
        node: Node,
        suggested: str,
        reason: str,
        confidence: float = 0.8,
        kind: Optional[str] = None,
    ) -> Optional[Suggestion]:
        """Offer a replacement for a node's text.

        Returns ``None`` -- and proposes nothing -- when the node has no single
        editable string or when the suggestion would change nothing.  Silently
        dropping a no-op is deliberate: a plugin that "finds" fifty things and
        proposes fifty identical strings has found nothing, and the user should
        not have to click through them.
        """
        original = editable_text(node)
        if original is None or suggested == original or not suggested.strip():
            return None
        suggestion = Suggestion(
            node_id=node.id,
            original=original,
            suggested=suggested,
            kind=kind or self.plugin_name,
            reason=reason,
            source=self.plugin_name,
            confidence=max(0.0, min(1.0, confidence)),
        )
        self._result.suggestions.append(suggestion)
        return suggestion

    def note(
        self, message: str, node: Optional[Node] = None, severity: str = "info"
    ) -> Note:
        note = Note(
            plugin=self.plugin_name,
            message=message,
            node_id=node.id if node is not None else None,
            severity=severity,
        )
        self._result.notes.append(note)
        return note

    @property
    def result(self) -> PluginResult:
        return self._result

    # -- reading ---------------------------------------------------------

    def body_sections(self) -> Iterator[Section]:
        """Every section, abstract included, in document order."""
        return self.document.every_section()

    def prose_nodes(self) -> Iterator[Tuple[Node, str]]:
        """Every node whose text is running prose, with that text.

        Headings, captions, references and equations are excluded: they have
        their own plugins, and a grammar rule written for sentences produces
        noise on a bibliography entry.
        """
        for section in self.body_sections():
            if section.kind == "references":
                continue
            for item in section.content:
                if item.kind not in ("paragraph", "list_item"):
                    continue
                node = item.item
                text = getattr(node, "text", "")
                if node is not None and isinstance(text, str) and text.strip():
                    yield node, text

    def all_text_nodes(self) -> Iterator[Tuple[Node, str]]:
        """Every node with an editable string, prose or not."""
        for node in self.document._every_node():
            text = editable_text(node)
            if text and text.strip():
                yield node, text

    def full_text(self) -> str:
        """The document's prose as one string, for document-wide counting."""
        return "\n".join(text for _, text in self.prose_nodes())


class SuggestionPlugin:
    """Base class.  Subclasses implement :meth:`run` and nothing else.

    ``name`` is what the UI groups by and what a user disables, so it is part of
    the contract: renaming one silently discards that plugin's saved decisions,
    because suggestion ids are derived from it.
    """

    name = "plugin"
    title = "Plugin"
    description = ""
    # Plugins that only ever add information, never change meaning, can be
    # defaulted on.  Anything that rewrites an author's sentences should not be.
    enabled_by_default = True

    def run(self, context: Context) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def analyze(self, document: Document) -> PluginResult:
        """Run this plugin over a document and collect what it proposed."""
        context = Context(document, self.name)
        self.run(context)
        return context.result

    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "enabled_by_default": self.enabled_by_default,
        }


class Registry:
    """The set of available plugins, in a fixed order.

    Order is fixed because it decides the order suggestions are reported in, and
    a UI whose list reshuffles between two runs of the same document is a UI
    nobody can review with.
    """

    def __init__(self, plugins: Iterable[SuggestionPlugin] = ()) -> None:
        self._plugins: List[SuggestionPlugin] = []
        for plugin in plugins:
            self.register(plugin)

    def register(self, plugin: SuggestionPlugin) -> SuggestionPlugin:
        if any(existing.name == plugin.name for existing in self._plugins):
            raise ValueError(f"a plugin named {plugin.name!r} is already registered")
        self._plugins.append(plugin)
        return plugin

    def get(self, name: str) -> Optional[SuggestionPlugin]:
        for plugin in self._plugins:
            if plugin.name == name:
                return plugin
        return None

    def select(self, names: Optional[Iterable[str]] = None) -> List[SuggestionPlugin]:
        """The plugins to run: the named ones, or the defaults."""
        if names is None:
            return [p for p in self._plugins if p.enabled_by_default]
        wanted = list(names)
        unknown = [n for n in wanted if self.get(n) is None]
        if unknown:
            raise ValueError(f"unknown plugin(s): {', '.join(sorted(unknown))}")
        return [p for p in self._plugins if p.name in wanted]

    def __iter__(self) -> Iterator[SuggestionPlugin]:
        return iter(self._plugins)

    def __len__(self) -> int:
        return len(self._plugins)

    def describe(self) -> List[Dict[str, Any]]:
        return [plugin.describe() for plugin in self._plugins]


def sentences(text: str) -> List[str]:
    return [part for part in SENTENCE.split(text or "") if part.strip()]


def words(text: str) -> List[str]:
    return WORD.findall(text or "")


__all__ = [
    "Context",
    "Note",
    "PluginResult",
    "Registry",
    "SENTENCE",
    "SuggestionPlugin",
    "sentences",
    "words",
]
