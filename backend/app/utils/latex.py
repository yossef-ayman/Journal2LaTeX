"""Shared LaTeX text helpers."""

import re
import unicodedata

# Math spans embedded in extracted text.  The analyzer carries display math as
# \[...\] and inline math as \(...\).  The $-delimited forms are deliberately
# NOT recognised: a bare "$" is far more often a currency amount than a math
# delimiter, and any rule that treats it as one mis-parses "costs $5m, up $2m"
# as an equation.  The \( \) form has no such ambiguity.
_MATH_SPAN_RE = re.compile(
    r"\\\[(?:.|\n)*?\\\]"       # \[ ... \]  display
    r"|\\\((?:.|\n)*?\\\)"      # \( ... \)  inline
)

_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    # Without these, the default font renders `<`/`>` as inverted punctuation
    # (¡ / ¿) -- e.g. a "< .001" p-value came out as "¡ .001".
    "<": r"\textless{}",
    ">": r"\textgreater{}",
}


# Word and Pandoc introduce characters that occupy no space on the page and
# that pdfLaTeX has no glyph for.  Reaching the compiler, each one raises
# "Unicode character (U+200B) not set up for use with LaTeX" and stops the
# build -- a document that is visually identical to one that compiles fails
# because of something nobody can see in Word.
#
# The rule is the Unicode category rather than a hand-written list.  Every
# character the specification calls a *format* character (Cf) is invisible by
# definition: that is precisely U+200B, U+200C, U+200D, U+FEFF, the word
# joiner, the soft hyphen, the bidi marks and isolates, and everything of that
# kind added in any future Unicode revision.  A list would have to be extended
# every time Word learns a new one; the category never will.
_STRIPPABLE_CATEGORIES = frozenset(("Cf", "Cc"))

# Tab, newline and carriage return are controls (Cc) that carry the document's
# line structure, so they are the one exception.
_KEEP_CONTROLS = frozenset("\t\n\r")

# The two format characters that are not decoration.  In Arabic, Persian,
# Indic and other joining scripts a zero-width joiner or non-joiner changes
# which glyph is drawn -- removing one is a spelling error, not a cleanup.  In
# Latin text the same character is invariably a stray from a copy-paste.  The
# distinction is made by looking at what sits next to it, so the rule needs no
# list of scripts and covers every joining script equally.
_CONTEXTUAL_JOINERS = frozenset("‌‍")

# Categories of the characters whose rendering a joiner can legitimately
# affect: other letters (the joining scripts' letters are all Lo) and the
# combining marks that attach to them.
_JOINING_CATEGORIES = frozenset(("Lo", "Mn", "Mc"))


def strip_invisible(text: str) -> str:
    """Remove invisible characters that pdfLaTeX cannot typeset.

    Applied to *everything*, prose and mathematics alike: a zero-width space
    inside an equation stops the compiler exactly as one in a sentence does.
    Nothing visible is touched -- no letter, no punctuation mark, no space that
    occupies width -- so the text a reader would see is unchanged by
    construction.

    A zero-width joiner or non-joiner is kept when a neighbouring character
    belongs to a script whose glyphs it selects, and removed otherwise.
    """
    if not text:
        return ""
    out = []
    for index, ch in enumerate(text):
        if ch in _KEEP_CONTROLS:
            out.append(ch)
            continue
        if unicodedata.category(ch) not in _STRIPPABLE_CATEGORIES:
            out.append(ch)
            continue
        if ch in _CONTEXTUAL_JOINERS and _joins_script(text, index):
            out.append(ch)
    return "".join(out)


def _joins_script(text: str, index: int) -> bool:
    """Whether the joiner at ``index`` sits against a script that uses one."""
    for neighbour in (text[index - 1] if index else "",
                      text[index + 1] if index + 1 < len(text) else ""):
        if neighbour and unicodedata.category(neighbour) in _JOINING_CATEGORIES:
            return True
    return False


# Characters Word inserts that are visible but that TeX has its own spelling
# for.  Substituting the TeX construct rather than passing the character
# through is what makes the output typographically correct instead of merely
# compilable: an en dash typed as a character sets at the font's width, whereas
# "--" sets at the width the document class chose.
#
# Applied to prose only, and only after escaping, because every replacement on
# the right-hand side is LaTeX markup that the escaper would otherwise turn
# into literal text.
_PROSE_SUBSTITUTIONS = (
    (" ", "~"),            # no-break space -> TeX's own unbreakable space
    (" ", "\\,"),          # narrow no-break space -> thin space
    (" ", "\\,"),          # thin space
    (" ", "~"),            # figure space
    ("–", "--"),           # en dash
    ("—", "---"),          # em dash
    # A true minus sign (U+2212) is not a dash and must not be set as one:
    # "--" is an en dash, which is narrower, sits at a different height, and
    # reads as a range rather than a negation.  Papers put signed values in
    # running prose constantly ("eigenvalues of -0.1003"), so this is set in
    # math mode, where TeX draws the minus it is -- a minus sign is
    # mathematical by definition, not prose punctuation.
    ("−", "$-$"),
    # Word writes three different hyphens.  Only the ASCII one has a glyph in
    # the T1 encoding; the other two stop the compiler, and they are the most
    # common unmapped characters in real manuscripts because Word inserts the
    # non-breaking form automatically inside hyphenated compounds.
    ("‐", "-"),            # U+2010 HYPHEN
    ("‑", "-"),            # U+2011 NON-BREAKING HYPHEN
    # Typographic ligatures that Word substitutes for the letters themselves.
    # TeX forms its own ligatures from the letters, so restoring the letters is
    # both what compiles and what a spell-checker or a text search expects.
    ("ﬀ", "ff"), ("ﬁ", "fi"), ("ﬂ", "fl"), ("ﬃ", "ffi"), ("ﬄ", "ffl"),
    ("‘", "`"), ("’", "'"),
    ("“", "``"), ("”", "''"),
    ("‚", ","), ("„", ",,"),
    ("…", "\\dots{}"),
    ("′", "'"), ("″", "''"),
    ("·", "\\textperiodcentered{}"),
    ("•", "\\textbullet{}"),
)


def normalize_prose(text: str) -> str:
    """Replace Word's typographic characters with their TeX equivalents.

    Prose only.  The same characters inside mathematics mean different things
    -- a minus sign is an operator, not a dash -- and rewriting them there
    would change the mathematics.
    """
    if not text:
        return ""
    for source, replacement in _PROSE_SUBSTITUTIONS:
        if source in text:
            text = text.replace(source, replacement)
    return text


def escape_latex(text: str) -> str:
    """Escape LaTeX special characters in plain text (no math awareness)."""
    return "".join(_LATEX_ESCAPES.get(ch, ch) for ch in text or "")


def escape_latex_keep_math(text: str) -> str:
    """Escape LaTeX specials outside math spans; keep math content raw.

    Math spans are located by scanning for *balanced* delimiters rather than by
    splitting on ``$`` and alternating.  The alternating approach silently
    inverted itself on the first unpaired ``$`` in the text -- a currency amount
    such as "$5 million" made every following real equation be escaped as prose
    (``$\\alpha_1$`` came out as literal ``\\textbackslash{}alpha\\_1``) while
    the prose after it was emitted unescaped.  Anything that is not part of a
    balanced span, including a lone ``$``, is treated as ordinary text.

    This is the single funnel every rendered string passes through, so it is
    also where text is made safe for the compiler.  The order of the three
    operations is load-bearing:

    * invisible characters are stripped from the *whole* string first, before
      the math spans are located, because a zero-width space inside an equation
      breaks the build just as one in a sentence does -- and because a stray
      format character sitting between ``\\`` and ``[`` would otherwise hide the
      delimiter from the scan below and turn an equation into escaped prose;
    * each prose run is then escaped, which is what protects ``%``, ``&`` and
      the rest;
    * and only then are Word's typographic characters replaced, because every
      replacement is LaTeX markup and escaping it afterwards would emit the
      markup literally.

    Math spans are passed through untouched after the first step, so no
    escaping and no substitution can alter an equation.
    """
    if not text:
        return ""
    text = strip_invisible(text)
    out = []
    pos = 0
    for m in _MATH_SPAN_RE.finditer(text):
        out.append(normalize_prose(escape_latex(text[pos:m.start()])))
        out.append(m.group(0))
        pos = m.end()
    out.append(normalize_prose(escape_latex(text[pos:])))
    return "".join(out)
