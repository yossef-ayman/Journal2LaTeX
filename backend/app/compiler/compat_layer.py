"""Generic LaTeX template compatibility layer.

Journal templates (built-in or uploaded) target a wide range of TeX
installations.  A document that compiles on one machine can fail on another
purely because an *optional* package is absent, because the template loads the
old ``color`` package instead of ``xcolor``, or because it references a named
colour the local palette does not define.  This module rewrites the final
``main.tex`` just before compilation so those environment gaps never abort the
build.  It is deliberately template-agnostic: nothing here is keyed to NSP,
JSAP or any specific journal, and no journal class is edited -- only the
generated preamble.

Transformations applied:

1. Colour compatibility -- ``xcolor`` (with the ``dvipsnames``/``svgnames``/
   ``x11names`` palettes) is force-loaded before the class, and a template that
   asks for the plain ``color`` package transparently receives ``xcolor``
   (a superset).  So ``\\providecolor``, ``\\definecolor{..}{named}{..}`` and the
   standard named colours always resolve, whichever package the template loads.

2. Missing named colours -- every colour name referenced by the document *or its
   class/style files* is guarded with ``\\providecolor`` (a no-op when already
   defined), so a name no palette supplies degrades to a neutral grey instead
   of raising ``Undefined color``.

3. Missing packages -- every preamble ``\\usepackage``/``\\RequirePackage`` is
   wrapped in ``\\IfFileExists`` (the in-LaTeX equivalent of ``kpsewhich``);
   absent packages are skipped, with a lightweight internal fallback where one
   exists (e.g. ``newunicodechar``).

4. Body text size -- only ``\\normalsize`` running text is scaled up ~5%;
   titles, banners, headings, captions and references are left at their original
   size, and margins/page layout are untouched.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence

# Body-text magnification (normal paragraph text only).  ~5% brings a 10pt
# journal body closer to Word without materially changing pagination.
_BODY_SCALE = 1.05

# Internal fall-backs for optional packages that might be absent on the
# compiling machine.  Each value is LaTeX emitted in place of the package so
# later uses of its commands still compile.  Anything not listed degrades to a
# plain "skip loading".
_PACKAGE_FALLBACKS: Dict[str, str] = {
    "newunicodechar": (
        "\\makeatletter\\providecommand\\newunicodechar[2]{%\n"
        "  \\begingroup\\lccode`\\~=`#1\\lowercase{\\endgroup\\def~}{#2}%\n"
        "  \\catcode`#1=\\active}\\makeatother"
    ),
    "multirow": "\\providecommand\\multirow[3]{#3}",
    "booktabs": (
        "\\providecommand\\toprule{\\hline}\\providecommand\\midrule{\\hline}"
        "\\providecommand\\bottomrule{\\hline}"
    ),
    # cuted's \begin{strip} places full-width inline content; if it is absent,
    # fall back to a plain full-line-width block so the document still compiles
    # (content stays in reading order, just within the current column width).
    "cuted": (
        "\\newenvironment{strip}"
        "{\\par\\medskip\\noindent\\begin{minipage}{\\linewidth}}"
        "{\\end{minipage}\\par\\medskip}"
    ),
    # capt-of / caption supply \captionof for non-floating captions; a minimal
    # fallback keeps the numbered label attached without a float.
    "capt-of": (
        "\\providecommand\\captionof[2]{\\par\\refstepcounter{#1}%\n"
        "  \\textbf{\\csname #1name\\endcsname\\ \\csname the#1\\endcsname:}\\ #2\\par}"
    ),
}

# Neutral grey stand-in for a colour name nothing defines, so an unknown name
# degrades to a harmless value instead of aborting the build.
#
# There is deliberately no table of per-name RGB values here.  One used to
# exist, listing twenty dvips colours, but every name in it is already defined
# by the dvipsnames/svgnames/x11names palettes that this module force-loads a
# few lines above -- so \providecolor found the colour present and the
# hardcoded value never took effect.  It was twenty hardcoded constants that
# could only ever drift away from the real palette.
_DEFAULT_RGB = "128,128,128"

_DOCUMENTCLASS_RE = re.compile(r"\\documentclass\b[^\n]*\n")
_BEGIN_DOC_RE = re.compile(r"\\begin\{document\}")
_USEPACKAGE_RE = re.compile(
    r"\\(usepackage|RequirePackage)\s*(\[[^\]]*\])?\s*\{([^}]*)\}"
)
# Colour references across the common entry points.  Forms carrying an explicit
# model option (\cellcolor[HTML]{DDD9C3}, \textcolor[rgb]{...}) are intentionally
# not matched: those name a value, not a palette colour.
_COLOR_REF_RES = [
    re.compile(r"\\(?:text|page|cell|row|column)?color(?!\s*\[)\s*\{([^}]*)\}"),
    re.compile(r"\\colorbox(?!\s*\[)\s*\{([^}]*)\}"),
    re.compile(r"\\fcolorbox(?!\s*\[)\s*\{([^}]*)\}\{([^}]*)\}"),
    re.compile(r"\\definecolor\s*\{[^}]*\}\s*\{named\}\s*\{([^}]*)\}"),
    re.compile(r"\\colorlet\s*\{[^}]*\}\s*\{([^}!]*)"),
]
_ALWAYS_KEEP = {"inputenc", "fontenc", "babel", "geometry"}
# Base colours xcolor always defines -- never need a fallback.
_BASE_COLORS = {
    "black", "white", "red", "green", "blue", "cyan", "magenta", "yellow",
    "gray", "grey", "darkgray", "lightgray", "brown", "lime", "olive",
    "orange", "pink", "purple", "teal", "violet",
}


def apply_compatibility_layer(
    source: str, resource_texts: Optional[Sequence[str]] = None
) -> str:
    """Rewrite *source* with the generic compatibility transforms.

    ``resource_texts`` are the contents of the template's class/style files
    (``.cls``/``.sty``); they are scanned so named colours used *inside* the
    class also get a fallback, even though the class itself is never edited.

    Idempotent: the pipeline may compile the same ``main.tex`` several times
    (e.g. via the layout-optimizer loop), so a document that has already been
    patched is returned unchanged -- guards must never nest or duplicate.
    """
    if not source or "\\documentclass" not in source:
        return source
    if "% >>> j2l compat: xcolor" in source:
        return source
    color_names = _referenced_colors(source, resource_texts or [])
    source = _force_xcolor_preamble(source, color_names)
    source = _guard_preamble_packages(source)
    source = _inject_body_font_scale(source)
    return source


def _referenced_colors(source: str, resource_texts: Sequence[str]) -> List[str]:
    """Collect every palette colour name referenced by the document or its
    class/style files (base colours and model-qualified values excluded)."""
    names: "set[str]" = set()
    for blob in [source, *resource_texts]:
        for rex in _COLOR_REF_RES:
            for match in rex.finditer(blob):
                for grp in match.groups():
                    if not grp:
                        continue
                    for token in grp.split(","):
                        token = token.split("!")[0].strip()
                        if token and re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", token):
                            if token.lower() not in _BASE_COLORS:
                                names.add(token)
    return sorted(names)


def _force_xcolor_preamble(source: str, color_names: Sequence[str]) -> str:
    """Force-load xcolor (with the named palettes) before the class, redirect a
    ``color`` request to xcolor, and provide fallbacks for every named colour."""
    if "% >>> j2l compat: xcolor" in source:
        return source
    head = [
        "% >>> j2l compat: xcolor / named-colour compatibility",
        # Steer palettes into whichever colour package ends up loading.
        "\\PassOptionsToPackage{dvipsnames}{color}",
        "\\PassOptionsToPackage{dvipsnames,svgnames,x11names,table}{xcolor}",
        # Load the superset now so \providecolor and the palettes exist, and
        # mark color.sty as already provided so a class \RequirePackage{color}
        # transparently resolves to xcolor instead of clashing.
        "\\RequirePackage{xcolor}",
        "\\makeatletter\\@namedef{ver@color.sty}{2021/01/01}\\makeatother",
    ]
    if color_names:
        head.append("\\makeatletter\\@ifundefined{providecolor}{}{%")
        for name in color_names:
            head.append(f"  \\providecolor{{{name}}}{{RGB}}{{{_DEFAULT_RGB}}}")
        head.append("}\\makeatother")
    head.append("% <<< j2l compat")
    block = "\n".join(head) + "\n"
    m = _DOCUMENTCLASS_RE.search(source)
    if not m:
        return block + source
    # Everything above must precede \documentclass so the class sees xcolor and
    # the named colours already in place while it loads.
    return source[: m.start()] + block + source[m.start():]


def _guard_preamble_packages(source: str) -> str:
    """Wrap each preamble package load in \\IfFileExists, with a fallback."""
    m = _DOCUMENTCLASS_RE.search(source)
    b = _BEGIN_DOC_RE.search(source)
    if not m or not b:
        return source
    pre_start, pre_end = m.end(), b.start()
    preamble = source[pre_start:pre_end]

    def guard(match: "re.Match") -> str:
        cmd, opts, names = match.group(1), match.group(2) or "", match.group(3)
        pkgs = [p.strip() for p in names.split(",") if p.strip()]
        out: List[str] = []
        for pkg in pkgs:
            if pkg in _ALWAYS_KEEP:
                out.append(f"\\{cmd}{opts}{{{pkg}}}")
                continue
            fallback = _PACKAGE_FALLBACKS.get(pkg, "")
            out.append(
                f"\\IfFileExists{{{pkg}.sty}}"
                f"{{\\{cmd}{opts}{{{pkg}}}}}"
                f"{{{fallback}}}"
            )
        return "\n".join(out)

    guarded = _USEPACKAGE_RE.sub(guard, preamble)
    return source[:pre_start] + guarded + source[pre_end:]


def _inject_body_font_scale(source: str) -> str:
    """Scale only \\normalsize running text by ``_BODY_SCALE``.

    Titles, banners and headings use their own size commands (\\Large, ...) and
    are unaffected.  Captions and the bibliography are explicitly reset to the
    *original* \\normalsize so they stay exactly as the template intends -- only
    normal paragraph text grows.
    """
    b = _BEGIN_DOC_RE.search(source)
    if not b:
        return source
    scale = f"{_BODY_SCALE:.3f}"
    pct = int(round((_BODY_SCALE - 1) * 100))
    # Scaling the body by a non-integer factor asks for sizes such as
    # 10.50003pt.  Computer Modern only ships a fixed set of design sizes, so
    # without type1cm/fix-cm every such request produces a
    # "Font shape ... in size <10.50003> not available" warning and is
    # silently rounded.  Loading them makes the scalable Type 1 CM fonts
    # available at arbitrary sizes: the requested size is honoured exactly and
    # the warnings disappear.  Guarded, so a TeX tree without them still
    # compiles.
    preamble = (
        "\n% >>> j2l compat: scalable Computer Modern (arbitrary font sizes)\n"
        "\\IfFileExists{type1cm.sty}{\\usepackage{type1cm}}{}\n"
        "\\IfFileExists{fix-cm.sty}{\\usepackage{fix-cm}}{}\n"
        "% <<< j2l compat\n"
    )
    if "j2l compat: scalable Computer Modern" not in source:
        source = source[: b.start()] + preamble + source[b.start():]
        b = _BEGIN_DOC_RE.search(source)

    block = (
        f"\n% >>> j2l compat: body-text size (+{pct}%)\n"
        "\\makeatletter\n"
        # Capture the template's original body size/leading *before* scaling, so
        # captions and references can be pinned back to it exactly.
        "\\edef\\JLTXbasesize{\\f@size}\n"
        "\\@tempdimb=1.2\\dimexpr\\f@size pt\\relax\\edef\\JLTXbaseskip{\\strip@pt\\@tempdimb}\n"
        f"\\def\\JLTXbodyscale{{{scale}}}\n"
        "\\let\\JLTX@normalsize\\normalsize\n"
        # Scale only \normalsize running text; \Large/\large/\small size commands
        # (titles, banner, headings, small print) are untouched.
        "\\renewcommand\\normalsize{%\n"
        "  \\JLTX@normalsize\n"
        "  \\@tempdima=\\JLTXbodyscale\\dimexpr\\f@size pt\\relax\n"
        "  \\@tempdimb=1.2\\@tempdima\n"
        "  \\fontsize{\\strip@pt\\@tempdima}{\\strip@pt\\@tempdimb}\\selectfont}%\n"
        # This block sits just after \begin{document}, so every package is
        # already loaded -- the final \@makecaption / thebibliography (whatever
        # the class or caption package installed) is wrapped so it emits at the
        # captured base size.  This is package-agnostic and works even when the
        # caption package cannot adapt to an unknown journal class.
        # Captions: force the original size around the installed \@makecaption.
        "\\@ifundefined{@makecaption}{}{%\n"
        "  \\let\\JLTX@makecaption\\@makecaption\n"
        "  \\long\\def\\@makecaption#1#2{%\n"
        "    \\begingroup\\fontsize{\\JLTXbasesize}{\\JLTXbaseskip}\\selectfont\n"
        "    \\let\\normalsize\\JLTX@normalsize\n"
        "    \\JLTX@makecaption{#1}{#2}\\endgroup}}%\n"
        # References: pin the bibliography back to the original size.
        "\\@ifundefined{thebibliography}{}{%\n"
        "  \\let\\JLTX@thebibliography\\thebibliography\n"
        "  \\def\\thebibliography{%\n"
        "    \\fontsize{\\JLTXbasesize}{\\JLTXbaseskip}\\selectfont\\JLTX@thebibliography}}%\n"
        "\\makeatother\n"
        "\\normalsize\n"
        "% <<< j2l compat\n"
    )
    insert = b.end()
    return source[:insert] + block + source[insert:]
