"""Shared LaTeX text helpers."""

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
}


def escape_latex(text: str) -> str:
    """Escape LaTeX special characters in plain text (no math awareness)."""
    return "".join(_LATEX_ESCAPES.get(ch, ch) for ch in text or "")


def escape_latex_keep_math(text: str) -> str:
    """Escape LaTeX specials outside ``$...$`` spans; keep math content raw."""
    if not text:
        return ""
    parts = text.split("$")
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            out.append(escape_latex(part))
        else:
            out.append(f"${part}$")
    return "".join(out)
