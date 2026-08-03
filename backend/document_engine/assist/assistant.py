"""The assistant: run the plugins, collect what they found, change nothing.

This module is a facade and is meant to stay one.  It owns no analysis of its
own -- every finding comes from a plugin -- and it owns no writing, because the
editing engine already does that and doing it twice is how two behaviours drift
apart.  What it adds is the three things a caller genuinely needs and a plugin
should not each solve separately:

* **one run over one document**, with plugin failures isolated so a bug in the
  keyword plugin does not cost the user the grammar suggestions;
* **a stable order**, so the same document reviewed twice presents the same list
  in the same sequence -- reviewing a reshuffling list is not reviewing;
* **deduplication**, because two plugins noticing the same double space should
  cost the user one decision, not two.

:class:`AssistantProvider` is the seam the user's "deterministic first, AI
later" decision lives on.  A model-backed provider implements one method,
becomes a plugin like any other, and nothing above or below it changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from document_engine.assist.plugin import (
    Context,
    Note,
    PluginResult,
    Registry,
    SuggestionPlugin,
)
from document_engine.edit.suggestions import Suggestion, SuggestionSet
from document_engine.model.nodes import Document


@dataclass
class PluginRun:
    """What one plugin contributed, including a failure if it had one."""

    name: str
    title: str
    suggestions: int = 0
    notes: int = 0
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "suggestions": self.suggestions,
            "notes": self.notes,
            "error": self.error,
        }


@dataclass
class Review:
    """Everything the assistant found in one pass over a document."""

    suggestions: SuggestionSet = field(default_factory=SuggestionSet)
    notes: List[Note] = field(default_factory=list)
    plugins: List[PluginRun] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(run.error for run in self.plugins)

    def by_plugin(self) -> Dict[str, List[Suggestion]]:
        grouped: Dict[str, List[Suggestion]] = {}
        for suggestion in self.suggestions:
            grouped.setdefault(suggestion.source, []).append(suggestion)
        return grouped

    def as_dict(self) -> Dict[str, Any]:
        return {
            "suggestions": self.suggestions.as_list(),
            "notes": [note.as_dict() for note in self.notes],
            "plugins": [run.as_dict() for run in self.plugins],
            "counts": {
                "suggestions": len(self.suggestions),
                "notes": len(self.notes),
                "failed_plugins": sum(1 for run in self.plugins if run.error),
            },
        }


class AssistantProvider:
    """The interface a future model-backed assistant implements.

    Kept deliberately narrow: given a document and the deterministic findings so
    far, return more findings.  A provider cannot write, cannot apply, and
    cannot see the package -- exactly the constraints a plugin has, because a
    model is not more trusted than the code around it, only less predictable.
    """

    name = "provider"

    def suggest(self, context: Context) -> None:  # pragma: no cover - abstract
        raise NotImplementedError


class NullProvider(AssistantProvider):
    """The provider in use today.  It finds nothing, on purpose.

    Its existence is the point: the code path that consults a provider is
    exercised on every run, so turning a real one on is a registration rather
    than a new branch nobody has ever executed.
    """

    name = "null"

    def suggest(self, context: Context) -> None:
        return None


class ProviderPlugin(SuggestionPlugin):
    """Adapts a provider into the plugin pipeline."""

    enabled_by_default = False

    def __init__(self, provider: AssistantProvider) -> None:
        self.provider = provider
        self.name = f"ai:{provider.name}"
        self.title = f"AI assistant ({provider.name})"
        self.description = "Suggestions from a model-backed provider."

    def run(self, context: Context) -> None:
        self.provider.suggest(context)


class DocumentAssistant:
    """Runs a registry of plugins over a document and reports what they found."""

    def __init__(
        self,
        registry: Optional[Registry] = None,
        provider: Optional[AssistantProvider] = None,
    ) -> None:
        if registry is None:
            from document_engine.assist import default_registry

            registry = default_registry()
        self.registry = registry
        self.provider = provider
        if provider is not None:
            self.registry.register(ProviderPlugin(provider))

    # -- reviewing -------------------------------------------------------

    def review(
        self,
        document: Document,
        plugins: Optional[Iterable[str]] = None,
    ) -> Review:
        """Run the selected plugins (or the defaults) over one document."""
        review = Review()
        for plugin in self.registry.select(plugins):
            run = PluginRun(name=plugin.name, title=plugin.title)
            try:
                result = plugin.analyze(document)
            except Exception as error:   # noqa: BLE001 - isolation is the point
                # One plugin's bug must not cost the user every other plugin's
                # findings, and must not be silent either.
                run.error = f"{type(error).__name__}: {error}"
                review.plugins.append(run)
                continue
            self._collect(review, result)
            run.suggestions = len(result.suggestions)
            run.notes = len(result.notes)
            review.plugins.append(run)
        return review

    @staticmethod
    def _collect(review: Review, result: PluginResult) -> None:
        for suggestion in result.suggestions:
            # ``add`` deduplicates on the suggestion id, which is derived from
            # (node, original, suggested, kind).  Two plugins proposing the same
            # replacement of the same text therefore cost one decision.
            review.suggestions.add(suggestion)
        review.notes.extend(result.notes)

    def describe(self) -> List[Dict[str, Any]]:
        return self.registry.describe()


__all__ = [
    "AssistantProvider",
    "DocumentAssistant",
    "NullProvider",
    "PluginRun",
    "ProviderPlugin",
    "Review",
]
