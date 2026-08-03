"""The deterministic plugins shipped with the engine.

The order of :data:`PLUGINS` is the order the user reviews suggestions in, so it
runs from the smallest, most certain edits to the ones that need judgement:
mechanical text first, then document-wide consistency, then the front matter.
A model-backed plugin, when one exists, is registered after all of these --
deliberately last, so a user scrolling the list reads the checkable findings
before the guessed ones.
"""

from __future__ import annotations

from typing import List

from document_engine.assist.plugin import SuggestionPlugin
from document_engine.assist.plugins.abstract import AbstractPlugin
from document_engine.assist.plugins.academic import AcademicPlugin
from document_engine.assist.plugins.citations import CitationPlugin
from document_engine.assist.plugins.consistency import ConsistencyPlugin
from document_engine.assist.plugins.equations import EquationPlugin
from document_engine.assist.plugins.grammar import GrammarPlugin
from document_engine.assist.plugins.journal import JournalStylePlugin
from document_engine.assist.plugins.keywords import KeywordPlugin
from document_engine.assist.plugins.terminology import TerminologyPlugin
from document_engine.assist.plugins.title import TitlePlugin


def all_plugins() -> List[SuggestionPlugin]:
    """A fresh instance of every shipped plugin, in review order.

    Fresh instances rather than module-level singletons: a plugin is allowed to
    keep per-run state on ``self`` one day, and two documents reviewed
    concurrently must not share it.
    """
    return [
        GrammarPlugin(),
        AcademicPlugin(),
        ConsistencyPlugin(),
        CitationPlugin(),
        TerminologyPlugin(),
        JournalStylePlugin(),
        EquationPlugin(),
        TitlePlugin(),
        AbstractPlugin(),
        KeywordPlugin(),
    ]


__all__ = [
    "AbstractPlugin",
    "AcademicPlugin",
    "CitationPlugin",
    "ConsistencyPlugin",
    "EquationPlugin",
    "GrammarPlugin",
    "JournalStylePlugin",
    "KeywordPlugin",
    "TerminologyPlugin",
    "TitlePlugin",
    "all_plugins",
]
