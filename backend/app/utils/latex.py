"""Shared LaTeX text helpers."""

import re

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
    """
    if not text:
        return ""
    out = []
    pos = 0
    for m in _MATH_SPAN_RE.finditer(text):
        out.append(escape_latex(text[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(escape_latex(text[pos:]))
    return "".join(out)
