"""Regression tests for the front-matter boundary and inline stringification.

These cover the three defects that let a manuscript's entire body be parsed as
front matter (and therefore rendered into ``\\author{}``):

1. The front-matter split trusted the *first* ``Header`` block unconditionally,
   even when that heading sat near the end of the document.
2. Headings numbered with Word's list numbering are folded by pandoc into an
   ``OrderedList`` block and could never be recognised as headings.
3. ``_stringify_inlines`` read a pandoc ``Link``'s target instead of its label,
   silently dropping every hyperlink's visible text.

All fixtures are synthetic pandoc ASTs, so the tests need no .docx fixture and
assert behaviour rather than any document-specific value.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.document_analyzer import DocumentAnalyzer  # noqa: E402


def _para(text):
    words = text.split(" ")
    inlines = []
    for i, w in enumerate(words):
        if i:
            inlines.append({"t": "Space"})
        inlines.append({"t": "Str", "c": w})
    return {"t": "Para", "c": inlines}


def _header(level, text):
    return {"t": "Header", "c": [level, ["", [], []], [{"t": "Str", "c": text}]]}


def _ordered(items):
    return {"t": "OrderedList", "c": [[1, {"t": "Decimal"}, {"t": "Period"}],
                                      [[_para(t)] for t in items]]}


# --------------------------------------------------------------------- #
# 1. Front-matter boundary
# --------------------------------------------------------------------- #

def test_label_boundary_is_reported_as_label_derived():
    an = DocumentAnalyzer()
    blocks = [_para("A Title"), _para("Jane Doe1"), _para("1 Some University"),
              _para("Abstract"), _para("We show that things work."),
              _para("Keywords: one; two"), _para("Body starts here.")]
    end, from_label = an._front_matter_end(blocks)
    assert from_label is True
    assert end == 6


def test_prose_fallback_is_not_label_derived():
    an = DocumentAnalyzer()
    long_prose = ("This is a long running paragraph of body prose. " * 6)
    blocks = [_para("A Title"), _para(long_prose)]
    end, from_label = an._front_matter_end(blocks)
    assert from_label is False
    assert end == 1


def test_no_boundary_found_returns_document_length():
    an = DocumentAnalyzer()
    blocks = [_para("A Title"), _para("Jane Doe")]
    end, from_label = an._front_matter_end(blocks)
    assert from_label is False
    assert end == len(blocks)


def test_label_boundary_precedes_a_late_first_header():
    """The core regression: a document whose only Header is near the end.

    The label-derived boundary must win, otherwise everything before that late
    heading is read as front matter and the body is lost.
    """
    an = DocumentAnalyzer()
    blocks = [_para("A Title"), _para("Jane Doe1"), _para("Abstract"),
              _para("We show that things work."), _para("Keywords: one; two")]
    blocks += [_para("Body paragraph %d." % i) for i in range(30)]
    blocks.append(_header(1, "Conclusions"))
    end, from_label = an._front_matter_end(blocks)
    assert from_label is True
    # The boundary is the keywords label, not the Conclusions heading.
    assert end == 5
    assert end < len(blocks) - 1


# --------------------------------------------------------------------- #
# 2. Headings hidden inside a numbered list
# --------------------------------------------------------------------- #

def test_list_headings_are_lifted_out_of_the_list():
    an = DocumentAnalyzer()
    formats = {"introduction": {"level": 1}, "methods": {"level": 1}}
    block = _ordered(["Introduction", "Methods"])
    out, lifted = an._lift_list_headings(block, formats)
    assert lifted == 2
    assert [b["t"] for b in out] == ["Header", "Header"]


def test_genuine_enumeration_is_left_untouched():
    an = DocumentAnalyzer()
    block = _ordered(["First point", "Second point", "Third point"])
    out, lifted = an._lift_list_headings(block, {"introduction": {"level": 1}})
    assert lifted == 0
    assert out == [block]


def test_mixed_list_keeps_non_heading_items_in_order():
    an = DocumentAnalyzer()
    formats = {"results": {"level": 2}}
    block = _ordered(["First point", "Results", "Second point"])
    out, lifted = an._lift_list_headings(block, formats)
    assert lifted == 1
    assert [b["t"] for b in out] == ["OrderedList", "Header", "OrderedList"]
    assert out[1]["c"][0] == 2


def test_bullet_list_is_handled_too():
    an = DocumentAnalyzer()
    block = {"t": "BulletList", "c": [[_para("Discussion")], [_para("a point")]]}
    out, lifted = an._lift_list_headings(block, {"discussion": {"level": 1}})
    assert lifted == 1
    assert out[0]["t"] == "Header"
    assert out[1]["t"] == "BulletList"


# --------------------------------------------------------------------- #
# 3. Hyperlink text
# --------------------------------------------------------------------- #

def test_link_label_is_kept_not_the_target():
    an = DocumentAnalyzer()
    link = {"t": "Link", "c": [["", [], []],
                               [{"t": "Str", "c": "jane@example.org"}],
                               ["mailto:jane@example.org", ""]]}
    assert an._stringify_inlines([link]) == "jane@example.org"


def test_link_inside_a_formatting_wrapper_survives():
    an = DocumentAnalyzer()
    link = {"t": "Link", "c": [["", [], []],
                               [{"t": "Str", "c": "jane@example.org"}],
                               ["mailto:jane@example.org", ""]]}
    wrapped = {"t": "Underline", "c": [link]}
    text = an._stringify_inlines([{"t": "Str", "c": "Email:"},
                                  {"t": "Space"}, wrapped])
    assert "jane@example.org" in text


def test_unlabelled_link_falls_back_to_its_url():
    an = DocumentAnalyzer()
    link = {"t": "Link", "c": [["", [], []], [], ["https://example.org/x", ""]]}
    assert an._stringify_inlines([link]) == "https://example.org/x"


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                passed += 1
                print("PASS", name)
            except AssertionError as exc:
                failed += 1
                print("FAIL", name, exc)
    print("\n%d passed, %d failed" % (passed, failed))
    sys.exit(1 if failed else 0)
