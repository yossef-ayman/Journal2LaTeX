"""Layer 2.5: the assistant.

Layer 0 reads the file, Layer 1 says what it means, Layer 2 writes accepted
edits back.  This layer sits between 1 and 2 and does exactly one thing: it
*proposes*.  It has no path to the bytes -- the only object it produces is a
:class:`~document_engine.edit.suggestions.Suggestion`, and only the existing
:class:`~document_engine.edit.writer.WordWriter` can turn one of those into a
change, and only after a person has accepted it.

That is the whole security model of the assistant, and it is structural rather
than procedural: a plugin cannot write to the document because it is never
handed anything that can.
"""

from __future__ import annotations

from document_engine.assist.assistant import (
    AssistantProvider,
    DocumentAssistant,
    NullProvider,
    PluginRun,
    ProviderPlugin,
    Review,
)
from document_engine.assist.plugin import (
    Context,
    Note,
    PluginResult,
    Registry,
    SuggestionPlugin,
)
from document_engine.assist.plugins import all_plugins


def default_registry() -> Registry:
    """A registry holding one fresh instance of every shipped plugin."""
    return Registry(all_plugins())


__all__ = [
    "AssistantProvider",
    "Context",
    "DocumentAssistant",
    "Note",
    "NullProvider",
    "PluginResult",
    "PluginRun",
    "ProviderPlugin",
    "Registry",
    "Review",
    "SuggestionPlugin",
    "all_plugins",
    "default_registry",
]
