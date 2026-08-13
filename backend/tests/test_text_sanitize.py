"""Tests for text sanitization and LaTeX escaping.

The bug these pin down is a document that is visually identical to one that
compiles and fails anyway, because Word left a character in it that occupies no
space on the page.  pdfLaTeX stops with "Unicode character (U+200B) not set up
for use with LaTeX", and nothing in the manuscript shows the author why.

Every test names the specific way that can happen, or the specific way an
over-eager cleanup would damage a document that was fine.
"""

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.latex import (  # noqa: E402
    escape_latex, escape_latex_keep_math, normalize_prose, strip_invisible,
)


#: The characters the failure was reported against, plus the rest of the class.
_INVISIBLE = {
    "\u200b": "ZERO WIDTH SPACE",
    "\u200c": "ZERO WIDTH NON-JOINER",
    "\u200d": "ZERO WIDTH JOINER",
    "\ufeff": "ZERO WIDTH NO-BREAK SPACE / BOM",
    "\u2060": "WORD JOINER",
    "\u00ad": "SOFT HYPHEN",
    "\u200e": "LEFT-TO-RIGHT MARK",
    "\u200f": "RIGHT-TO-LEFT MARK",
    "\u061c": "ARABIC LETTER MARK",
    "\u2066": "LEFT-TO-RIGHT ISOLATE",
}


# --------------------------------------------------------------------- #
# Removal
# --------------------------------------------------------------------- #

def test_no_invisible_character_survives_escaping():
    """The end-to-end guarantee: none of them can reach the compiler."""
    for ch, name in _INVISIBLE.items():
        out = escape_latex_keep_math(f"before{ch}after")
        assert ch not in out, name
        assert "before" in out and "after" in out, name


def test_the_reported_sentences_come_out_clean():
    """The two phrases from the production failure.

    Kept verbatim as a shape -- prose with a zero-width space beside a
    parenthesis, which is where Word puts them -- not because this manuscript
    is special.
    """
    for sentence in (
        "thinking style\u200b (rapid thinking versus analytical thinking)\u200b "
        "on the effectiveness",
        "professional and personal\u200c values that\ufeff determine",
    ):
        out = escape_latex_keep_math(sentence)
        assert not any(c in out for c in _INVISIBLE)
        assert "thinking" in out or "professional" in out


def test_the_rule_is_the_unicode_category_not_a_list():
    """A hand-written list has to be extended every time Word learns a new
    character; the category never will.  Any format character is removed."""
    for cp in range(0x110000):
        if cp in (0x200c, 0x200d):
            continue  # contextual, covered by their own tests
        ch = chr(cp)
        if unicodedata.category(ch) == "Cf":
            assert ch not in strip_invisible(f"a{ch}b"), hex(cp)


def test_control_characters_go_but_line_structure_stays():
    assert strip_invisible("a\x00\x07b") == "ab"
    assert strip_invisible("a\tb\nc\r") == "a\tb\nc\r"


# --------------------------------------------------------------------- #
# Preservation -- the other half of the requirement
# --------------------------------------------------------------------- #

def test_ordinary_unicode_text_is_untouched():
    """Removing legitimate characters would be a worse bug than the one being
    fixed: it is silent, and it changes what the paper says."""
    for text in ("Ali Akgül", "Emad A. Az-Zo'bi", "Straße", "naïve café",
                 "Ωμέγα", "Привет", "日本語", "α + β = γ"):
        assert strip_invisible(text) == text


def test_arabic_and_other_non_latin_text_is_preserved():
    assert strip_invisible("بسم الله") == "بسم الله"
    assert strip_invisible("नमस्ते") == "नमस्ते"


def test_a_joiner_inside_a_joining_script_is_kept():
    """In Arabic, Persian and the Indic scripts a zero-width joiner selects
    which glyph is drawn.  Removing one is a spelling error, not a cleanup."""
    assert "\u200d" in strip_invisible("ب\u200dس")
    assert "\u200c" in strip_invisible("क\u200cष")


def test_the_same_joiner_between_latin_letters_is_removed():
    """There it is invariably a stray from a copy-paste, and pdfLaTeX stops on
    it.  The distinction is made from context, so it needs no list of scripts
    and covers every joining script equally."""
    assert strip_invisible("personal\u200c values") == "personal values"
    assert strip_invisible("a\u200db") == "ab"


def test_meaningful_punctuation_survives():
    for ch in ".,;:!?()[]{}<>/\\-'\"":
        assert ch in strip_invisible(f"a{ch}b"), ch


# --------------------------------------------------------------------- #
# Typography
# --------------------------------------------------------------------- #

def test_word_typography_becomes_tex_typography():
    """An en dash typed as a character sets at the font's width; "--" sets at
    the width the document class chose."""
    out = escape_latex_keep_math("an en–dash, an em—dash, “quotes”, ‘one’, and…")
    assert "--" in out and "---" in out
    assert "``" in out and "''" in out
    assert "\\dots{}" in out


def test_a_no_break_space_becomes_texs_own():
    assert escape_latex_keep_math("Figure\u00a01") == "Figure~1"


def test_substitution_runs_after_escaping_not_before():
    """Every replacement is LaTeX markup.

    Substituting first would leave the escaper to turn "~" into
    \\textasciitilde{} and "--" into literal text, so the dash and the
    unbreakable space would both appear as characters in the PDF.
    """
    out = escape_latex_keep_math("50%\u00a0of x_1 – y")
    assert "\\%" in out and "\\_" in out
    assert "~" in out and "\\textasciitilde" not in out
    assert "--" in out


# --------------------------------------------------------------------- #
# Mathematics must not be damaged
# --------------------------------------------------------------------- #

def test_math_spans_are_not_escaped_or_substituted():
    """A minus sign in mathematics is an operator, not a dash."""
    out = escape_latex_keep_math(r"prose 50% then \(a_1 - b^2\) then more 50%")
    assert r"\(a_1 - b^2\)" in out
    assert out.count("\\%") == 2


def test_display_math_survives_intact():
    out = escape_latex_keep_math("see \\[\\sum_{i=1}^{n} x_i\\] above")
    assert "\\[\\sum_{i=1}^{n} x_i\\]" in out


def test_an_invisible_character_inside_math_is_still_removed():
    """It stops the compiler exactly as one in a sentence does, so stripping
    has to happen before the math spans are protected."""
    out = escape_latex_keep_math("\\(a\u200b+b\\)")
    assert "\u200b" not in out
    assert "\\(a+b\\)" in out


def test_a_format_character_cannot_hide_a_math_delimiter():
    """The reason stripping runs before the span scan rather than after.

    A stray character between the backslash and the bracket would hide the
    delimiter from the scanner, and the whole equation would be escaped as
    prose -- which is how an exponent turns into literal text.
    """
    out = escape_latex_keep_math("\\\u200b(x^2\\)")
    assert "\\textasciicircum" not in out


def test_a_lone_dollar_is_still_treated_as_currency():
    """Pre-existing behaviour that must not regress: the alternating-dollar
    approach used to invert itself on the first unpaired '$'."""
    out = escape_latex_keep_math("costs $5m, up $2m")
    assert out.count("\\$") == 2


# --------------------------------------------------------------------- #
# Escaping, unchanged
# --------------------------------------------------------------------- #

def test_every_latex_special_is_still_escaped():
    out = escape_latex("100% & #1 _x_ {a} $5 ~ ^ < >")
    for expected in ("\\%", "\\&", "\\#", "\\_", "\\{", "\\}", "\\$",
                     "\\textasciitilde{}", "\\textasciicircum{}",
                     "\\textless{}", "\\textgreater{}"):
        assert expected in out, expected


def test_a_backslash_does_not_become_a_command():
    assert escape_latex("a\\b") == "a\\textbackslash{}b"


def test_empty_and_none_are_safe():
    for fn in (strip_invisible, normalize_prose, escape_latex,
               escape_latex_keep_math):
        assert fn("") == ""
        assert fn(None) == ""


if __name__ == "__main__":
    import traceback
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not (name.startswith("test_") and callable(fn)):
            continue
        try:
            fn()
            print(f"PASS {name}")
            passed += 1
        except Exception:
            print(f"FAIL {name}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
