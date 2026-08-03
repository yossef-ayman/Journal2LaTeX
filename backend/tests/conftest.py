"""Shared fixtures for the Document Engine regression suite.

Everything here is driven by the four **real production papers** committed
alongside these tests.  That is deliberate: a synthetic .docx written by a test
is a document written by the same assumptions as the parser, so it proves the
parser agrees with itself.  These four came out of Word, from a real journal
template, and between them they cover the cases that actually break parsers --
tables, floating images, charts, footnotes, headers, numbered lists, text boxes
and ``mc:AlternateContent`` duplication.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

TESTS = Path(__file__).resolve().parent

# name -> what it is there to exercise
PAPERS = {
    "normal_paper": "prose, footnotes, headers, numbered lists, no tables",
    "the_role": "24 tables, the heaviest structure of the four",
    "with_author_photo": "a floating image in the author block",
    "with_charts": "charts, and a document whose runs carry no direct sizes",
}


def paper_path(name: str) -> Path:
    path = TESTS / f"{name}.docx"
    if not path.exists():  # pragma: no cover - checkout without the corpus
        pytest.skip(f"production paper {name}.docx is not present")
    return path


@pytest.fixture(params=sorted(PAPERS), ids=sorted(PAPERS))
def paper(request) -> Path:
    """Each real paper in turn."""
    return paper_path(request.param)


@pytest.fixture
def document_bytes(paper: Path) -> bytes:
    with zipfile.ZipFile(paper) as archive:
        return archive.read("word/document.xml")
