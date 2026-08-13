"""Journal rules: every decision a journal makes, in one resolved object.

The conversion engine has exactly one legitimate reason to behave differently
for two journals, and it is that the two journals ask for different things.
That difference belongs in data, declared once per template, not in the code
that walks a document.  A test like ``"NSP" in class_file`` scattered through a
renderer is the same decision written in the worst possible place: invisible to
whoever adds the next template, impossible to override, and silently wrong for
every journal whose class file happens to share a substring.

So this module defines what a journal may decide, and resolves those decisions
for a given template from three sources, in order of authority:

1. the ``rules`` block of the template's own ``template.json`` -- the explicit,
   per-journal answer, and the only place a human should ever have to write one;
2. what the template's LaTeX actually provides -- if its class defines
   ``\\citep`` then author-year citation commands are available, and if it
   defines a biography environment then that layout is on the table.  This is
   inference from the template, not from its name, so it stays correct when a
   template is renamed, forked or vendored;
3. conventions shared by essentially all of scientific publishing, used only
   when neither of the above says anything.

Nothing here names a journal.  Adding support for a new one means writing a
``rules`` block, never editing this file.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


# --------------------------------------------------------------------------- #
# Vocabularies
# --------------------------------------------------------------------------- #

#: How a journal wants citations to appear in the body text.
#:
#: ``numeric``      -- [1], [2-4]; the citation is a number in brackets.
#: ``author_year``  -- (Roe, 2021) and Roe (2021); the citation names people.
#: ``superscript``  -- ¹; the citation is a raised number with no brackets.
CITATION_STYLES = ("numeric", "author_year", "superscript")

#: How the bibliography itself is produced.
#:
#: ``inline`` -- a hand-built ``thebibliography`` environment, which is what a
#:               Word manuscript naturally yields: the reference list is already
#:               formatted prose and re-parsing it into BibTeX fields would
#:               invent data the source does not contain.
#: ``bibtex`` -- a ``.bib`` file plus ``\\bibliography``; only usable when the
#:               references have been parsed into structured entries.
BIBLIOGRAPHY_MODES = ("inline", "bibtex")

#: Layouts an author biography may be rendered with, in the order the engine
#: should try them.  Each is a LaTeX construct with different failure modes:
#: ``wrapfigure`` and ``floatingfigure`` wrap text around the photo and are the
#: most attractive but collide with floats and with page breaks; ``minipage``
#: cannot collide with anything but does not wrap; ``plain`` is the fallback
#: that always typesets.
BIOGRAPHY_LAYOUTS = ("journal_env", "wrapfigure", "floatingfigure",
                     "minipage", "plain")


# --------------------------------------------------------------------------- #
# The rules object
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CitationRules:
    """How this journal wants citations written."""

    style: str = "numeric"
    #: Command for a plain citation.  ``\\cite`` is near-universal; a journal
    #: class that defines its own takes precedence.
    command: str = "cite"
    #: Commands for the two author-year shapes.  ``parenthetical`` is the
    #: "(Roe, 2021)" form, ``textual`` the "Roe (2021)" form.  Both are natbib
    #: spellings by default because natbib is what most classes load, but a
    #: class that provides different names overrides them.
    parenthetical_command: str = "citep"
    textual_command: str = "citet"
    #: True when several adjacent citations should be emitted as one command
    #: with a key list -- ``\\cite{a,b,c}`` -- rather than as separate commands.
    #: Grouping is what lets the class collapse "[1,2,3]" into "[1-3]"; a class
    #: that cannot do that wants them separate.
    group_multiple: bool = True
    #: Name of a command the rendered citation is wrapped in, used by journals
    #: that print citations raised or in a distinguishing font.  Stored as a
    #: bare command name ("textsuperscript") rather than a format string,
    #: because a format string in a config file is one escaping mistake away
    #: from emitting LaTeX that does not compile.
    wrapper: Optional[str] = None


@dataclass(frozen=True)
class BibliographyRules:
    """How this journal wants the reference list produced."""

    mode: str = "inline"
    #: BibTeX style name, meaningful only when ``mode == "bibtex"``.
    style: str = ""
    #: The widest label the list will contain, which sets its indentation.
    #: "99" is right for any list under a hundred entries and is what a Word
    #: manuscript almost always has; templates with longer lists override it.
    widest_label: str = "99"
    #: Prefix for generated citation keys.  Empty by default, so a reference
    #: list numbered 1, 2, 3 produces ``\\cite{1}`` against ``\\bibitem{1}`` --
    #: the citation in the LaTeX reads the same as the citation in the
    #: manuscript, which is what makes generated source reviewable by the
    #: author.  A template that needs alphabetic keys (because its class or its
    #: .bst requires them, or because a human maintains the .bib) sets a prefix
    #: here and everything downstream follows.
    key_prefix: str = ""

    def key_for(self, position: int) -> str:
        """The citation key for the reference at ``position`` (1-based).

        **This is the single definition of a citation key.**  It exists as one
        function, on the rules, precisely because the key is written in two
        distant places -- the ``\\cite`` in the body and the ``\\bibitem`` in
        the reference list -- and those two must agree in every document.
        Before this, each place computed the key with its own copy of the same
        expression, in different modules; the two agreed only by coincidence,
        and any change to one silently produced a document whose every citation
        pointed at nothing.

        The key is derived from *position in the reference list*, never from
        the number the source document happened to print.  A manuscript whose
        list is numbered 1, 2, 3, 6 still typesets as four consecutive entries,
        so the fourth entry's key must be 4 -- matching where ``\\bibitem`` will
        actually put it.  Resolving a citation that says "[6]" to that entry is
        a separate step, and belongs to the engine that reads the numbering.
        """
        return f"{self.key_prefix}{int(position)}"


@dataclass(frozen=True)
class BiographyRules:
    """How this journal wants author biographies laid out."""

    #: Candidate layouts, most preferred first.  The engine tries the first and
    #: falls back down the list when the compilation log shows the layout did
    #: not typeset cleanly, which is why this is a sequence and not a value.
    layouts: Tuple[str, ...] = ("minipage", "plain")
    #: Name of the journal class's own biography environment, when it has one.
    #: Only consulted for the ``journal_env`` layout.
    environment: str = ""
    #: Variant environment that also takes a photograph path.
    photo_environment: str = ""
    #: Photograph box, in inches.  A biography photo is a fixed-size box in
    #: every journal that prints one; only the size differs.
    photo_width_in: float = 1.0
    photo_height_in: float = 1.25


#: How an author's photograph is set.  These are *layout mechanisms*, not
#: journals: each is a different LaTeX construct with different behaviour, and
#: a template picks the one its class supports.
#:
#: ``floatingfigure`` -- text wraps around the photo (floatflt package)
#: ``wrapfigure``     -- text wraps around the photo (wrapfig package)
#: ``figure``         -- an ordinary non-floating box, no wrapping, no package
#: ``none``           -- the journal does not print author photographs
AUTHOR_PHOTO_MODES = ("floatingfigure", "wrapfigure", "figure", "none")

#: The package each mode needs.  Injected only when the resolved mode is
#: actually used, so a document with no author photograph never loads a
#: package it does not need -- and a template whose TeX installation lacks
#: floatflt is unaffected unless it asks for that mode.
_AUTHOR_PHOTO_PACKAGES = {
    "floatingfigure": "floatflt",
    "wrapfigure": "wrapfig",
    "figure": "",
    "none": "",
}


@dataclass(frozen=True)
class AuthorPhotoRules:
    """How this journal sets an author's photograph.

    An author photograph is not a manuscript figure.  It illustrates a person,
    not a result; it carries no caption, takes no figure number, and belongs in
    no list of figures.  Numbering one as a figure shifts every real figure
    number in the paper by one and puts a portrait in the List of Figures --
    which is why this is a separate rules section rather than a variation on
    the figure rules.
    """

    mode: str = "floatingfigure"
    #: Environment name.  Separate from ``mode`` so a class that provides the
    #: same mechanism under its own name can be used without code changes.
    environment: str = ""
    #: Float placement specifier, without brackets.
    placement: str = "h"
    #: Width of the column the text wraps around.
    column_width: str = "3.5cm"
    #: Size of the photograph itself.
    image_width: str = "3cm"
    image_height: str = "3.4cm"
    #: Whether to add ``keepaspectratio``.  Off by default: a journal that
    #: specifies both dimensions wants that exact box, and keeping the aspect
    #: ratio would silently produce a different one.
    keep_aspect: bool = False

    def resolved_environment(self) -> str:
        return self.environment or self.mode

    def package(self) -> str:
        """The package this mode requires, or "" if none."""
        return _AUTHOR_PHOTO_PACKAGES.get(self.mode, "")

    def render(self, image_path: str) -> str:
        """The LaTeX for one author photograph.

        Every dimension and every name comes from this object, so the output is
        whatever the template declared and nothing is spelled into the
        renderer.  The path is the only part that varies per document.
        """
        if self.mode == "none" or not image_path:
            return ""
        options = f"width={self.image_width},height={self.image_height}"
        if self.keep_aspect:
            options += ",keepaspectratio"
        include = f"\\includegraphics[{options}]{{{image_path}}}"
        env = self.resolved_environment()
        if self.mode == "figure":
            return ("\\noindent\\begin{minipage}{" + self.column_width + "}%\n"
                    "\\centering\n" + include + "\n\\end{minipage}%\n")
        # floatingfigure and wrapfigure share a signature: an optional
        # placement, then the width of the wrapped column.
        return (f"\\begin{{{env}}}[{self.placement}]{{{self.column_width}}}\n"
                f"\\centering\n{include}\n\\end{{{env}}}\n")


@dataclass(frozen=True)
class PlacementRules:
    """How this journal wants floats placed."""

    #: Float specifier for an in-column float and for a full-width one.
    column_spec: str = "[htbp]"
    span_spec: str = "[tp]"
    #: Fraction of the text width beyond which an object is treated as needing
    #: the full width rather than one column.
    span_threshold: float = 0.55
    #: True when the journal wants floats pinned where they appear in the
    #: source rather than allowed to migrate.
    pin_in_place: bool = False


@dataclass(frozen=True)
class LabelRules:
    """Label prefixes, so every reference in the document is namespaced."""

    figure: str = "fig:"
    table: str = "tab:"
    equation: str = "eq:"
    section: str = "sec:"
    appendix: str = "app:"
    algorithm: str = "alg:"

    def prefix_for(self, kind: str) -> str:
        return getattr(self, kind, f"{kind}:")


@dataclass(frozen=True)
class JournalRules:
    """The complete set of decisions a journal makes about a manuscript."""

    template_id: str = ""
    citation: CitationRules = field(default_factory=CitationRules)
    bibliography: BibliographyRules = field(default_factory=BibliographyRules)
    biography: BiographyRules = field(default_factory=BiographyRules)
    author_photo: AuthorPhotoRules = field(default_factory=AuthorPhotoRules)
    placement: PlacementRules = field(default_factory=PlacementRules)
    labels: LabelRules = field(default_factory=LabelRules)
    #: Caption style hook: the command a caption is emitted with.  Journals that
    #: want captions above tables and below figures differ only in ordering,
    #: which the renderer handles; those that want a different command set it
    #: here.
    caption_command: str = "caption"
    caption_above_tables: bool = True
    #: Where the resolved values came from, per section, for the report.  A
    #: rule that was inferred rather than declared is worth knowing about when
    #: output looks wrong.
    provenance: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """A plain-data view, for the validation report and the API."""
        return {
            "template_id": self.template_id,
            "citation": vars(self.citation).copy(),
            "bibliography": vars(self.bibliography).copy(),
            "biography": {**vars(self.biography),
                          "layouts": list(self.biography.layouts)},
            "author_photo": vars(self.author_photo).copy(),
            "placement": vars(self.placement).copy(),
            "labels": vars(self.labels).copy(),
            "caption_command": self.caption_command,
            "caption_above_tables": self.caption_above_tables,
            "provenance": dict(self.provenance),
        }


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #

# A class or style file announces what it provides by defining it.  These are
# the definition forms LaTeX offers; matching all of them is what makes the
# probe reliable across hand-written classes, generated ones and packages that
# patch each other.
_DEFINES_RE_CACHE: Dict[str, "re.Pattern[str]"] = {}


def _defines_command(text: str, name: str) -> bool:
    """True when the LaTeX source defines the named command."""
    pattern = _DEFINES_RE_CACHE.get(name)
    if pattern is None:
        escaped = re.escape(name)
        pattern = re.compile(
            r"\\(?:def|newcommand|renewcommand|providecommand|DeclareRobustCommand)"
            r"\s*\*?\s*\{?\\" + escaped + r"\}?[\s\[{]",
            re.MULTILINE,
        )
        _DEFINES_RE_CACHE[name] = pattern
    return bool(pattern.search(text))


def _defines_environment(text: str, name: str) -> bool:
    """True when the LaTeX source defines the named environment.

    Two forms count, and both must, because real journal classes use both.
    ``\\newenvironment{x}`` is the LaTeX way.  The plain-TeX way is a pair of
    macros, ``\\def\\x`` and ``\\def\\endx``, which is what an environment
    actually *is* underneath -- and it is what the publisher classes in this
    project use.  Recognising only the LaTeX form would report that a class
    which plainly provides a biography environment provides nothing, and any
    decision made on that answer would strip the journal's own layout from
    every document it typesets.
    """
    escaped = re.escape(name)
    if re.search(r"\\(?:newenvironment|renewenvironment)\s*\*?\s*\{" + escaped + r"\}",
                 text, re.MULTILINE):
        return True
    # The \def pair.  Both halves are required: a lone \def\x is an ordinary
    # command, and treating it as an environment would emit \begin{x}...\end{x}
    # around content the macro never expected.
    return bool(
        re.search(r"\\def\s*\\" + escaped + r"(?![a-zA-Z])", text)
        and re.search(r"\\def\s*\\end" + escaped + r"(?![a-zA-Z])", text)
    )


class JournalRulesResolver:
    """Resolves the rules for a template from its metadata and its LaTeX.

    The resolver is deliberately total: it always returns a usable
    ``JournalRules``, because a template with no ``rules`` block is the normal
    case for every template that exists today and must keep working unchanged.
    What it never does is guess from a journal's *name*.
    """

    #: Files worth reading when probing what a template provides.  Reading the
    #: whole tree would be wasteful and would pick up sample documents; the
    #: class and style files are where capabilities are declared.
    _PROBE_SUFFIXES = (".cls", ".sty")
    #: A probe reads at most this much of any one file.  Definitions live in
    #: the preamble of a class file; a multi-megabyte vendored package should
    #: not be read in full on every job.
    _PROBE_BYTES = 400_000

    def resolve(self, metadata: Optional[Dict[str, Any]] = None,
                workspace_dir: Optional[Path] = None) -> JournalRules:
        """The rules for one template.

        ``metadata`` is the parsed ``template.json``; ``workspace_dir`` is the
        prepared LaTeX project, used only to probe what the template's own
        class and style files define.  Both are optional -- with neither, the
        result is the shared conventions, which is a correct answer for a
        generic article template.
        """
        metadata = metadata or {}
        rules = JournalRules(
            template_id=str(metadata.get("template_id") or ""),
            provenance={"citation": "default", "bibliography": "default",
                        "biography": "default", "author_photo": "default",
                        "placement": "default", "labels": "default"},
        )
        # Precedence, lowest authority first, each layer overwriting only what
        # it actually declares:
        #
        #   1. built-in safe defaults   -- already in ``rules`` above
        #   2. probe of the template's own LaTeX -- an inference
        #   3. the ``rules`` block of template.json -- declared by a human
        #   4. rules.json               -- declared, and wins over everything
        #
        # Declared always beats inferred, because the point of declaring is to
        # correct an inference.  rules.json beats the template.json block so a
        # template can carry its original publisher metadata untouched and keep
        # its conversion rules in a separate, reviewable file.
        if workspace_dir is not None:
            rules = self._apply_probe(rules, self.probe(workspace_dir))
        declared = metadata.get("rules")
        if isinstance(declared, dict):
            rules = self._apply_declared(rules, declared)
        if workspace_dir is not None:
            external = self._read_rules_file(Path(workspace_dir))
            if external:
                rules = self._apply_declared(rules, external)
        return rules

    @staticmethod
    def _read_rules_file(directory: Path) -> Dict[str, Any]:
        """The template's ``rules.json``, or an empty mapping.

        A malformed file is ignored rather than fatal.  A template whose rules
        file has a stray comma should still convert -- with the defaults, which
        are safe -- rather than failing every job for that journal until
        somebody notices.  The file may hold the rule sections at its top level
        or nested under a ``rules`` key; both are accepted, because both are
        what people write.
        """
        path = directory / "rules.json"
        if not path.is_file():
            return {}
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(loaded, dict):
            return {}
        nested = loaded.get("rules")
        return nested if isinstance(nested, dict) else loaded

    # -- source 2: what the template's LaTeX provides ----------------------- #

    def probe(self, workspace_dir: Path) -> Dict[str, Any]:
        """What the template's class and style files declare they provide.

        Reading the template is how a rule can be inferred without naming a
        journal: a class that defines ``\\biographyps`` provides a photo
        biography environment, whatever it is called on the cover of the
        journal.  A probe failure is not an error -- it simply means nothing
        was inferred, and the declared rules and the defaults still apply.
        """
        found: Dict[str, Any] = {}
        if not workspace_dir or not Path(workspace_dir).is_dir():
            return found
        text_parts = []
        for path in sorted(Path(workspace_dir).rglob("*")):
            if not path.is_file() or path.suffix.lower() not in self._PROBE_SUFFIXES:
                continue
            try:
                text_parts.append(path.read_text(encoding="utf-8",
                                                 errors="replace")[:self._PROBE_BYTES])
            except OSError:
                continue
        if not text_parts:
            return found
        text = "\n".join(text_parts)

        # Citation commands.  natbib and biblatex both provide \citep/\citet,
        # so loading either is as good as defining them.
        loads_natbib = bool(re.search(r"\\(?:usepackage|RequirePackage)"
                                      r"\s*(?:\[[^\]]*\])?\s*\{[^}]*\b(?:natbib|biblatex)\b",
                                      text))
        if loads_natbib or _defines_command(text, "citep"):
            found["author_year_commands"] = True
        for name in ("citenum", "citeauthor", "citeyear", "onlinecite",
                     "supercite"):
            if _defines_command(text, name):
                found.setdefault("extra_cite_commands", []).append(name)

        # Biography environments, the layout question this engine most needs an
        # answer to and the one that was previously answered by a substring
        # test on the class file's name.
        for env in ("biographyps", "IEEEbiography", "biographynophoto",
                    "IEEEbiographynophoto", "biography", "bio"):
            if _defines_environment(text, env):
                if "ps" in env.lower() or env in ("IEEEbiography",):
                    found.setdefault("photo_environment", env)
                else:
                    found.setdefault("biography_environment", env)

        # Wrapping packages: a layout the template cannot load is not a
        # candidate, and offering it would produce a document that fails to
        # compile for a reason no log message explains well.
        for pkg, key in (("wrapfig", "wrapfigure"), ("floatflt", "floatingfigure"),
                         ("picinpar", "picinpar")):
            if re.search(r"\\(?:usepackage|RequirePackage)"
                         r"\s*(?:\[[^\]]*\])?\s*\{[^}]*\b" + pkg + r"\b", text):
                found.setdefault("available_layouts", []).append(key)

        if re.search(r"\\(?:usepackage|RequirePackage)"
                     r"\s*(?:\[[^\]]*\])?\s*\{[^}]*\bsuperscript\b", text) \
                or _defines_command(text, "supercite"):
            found["superscript_citations"] = True

        if re.search(r"\\bibliographystyle\s*\{([^}]*)\}", text):
            found["bibliography_style"] = re.search(
                r"\\bibliographystyle\s*\{([^}]*)\}", text).group(1).strip()
        return found

    def _apply_probe(self, rules: JournalRules,
                     probe: Dict[str, Any]) -> JournalRules:
        if not probe:
            return rules
        provenance = dict(rules.provenance)

        citation = rules.citation
        if probe.get("superscript_citations"):
            citation = replace(citation, style="superscript")
            provenance["citation"] = "probed"
        if probe.get("author_year_commands"):
            provenance["citation"] = "probed"

        biography = rules.biography
        env = probe.get("biography_environment", "")
        photo_env = probe.get("photo_environment", "")
        if env or photo_env:
            # A journal that ships its own biography environment means that
            # environment, and nothing this engine composes can be closer to
            # what the journal wants.  It goes to the front of the list; the
            # generic layouts stay behind it as fallbacks for when it does not
            # typeset cleanly.
            biography = replace(biography, environment=env,
                                photo_environment=photo_env,
                                layouts=("journal_env",) + biography.layouts)
            provenance["biography"] = "probed"
        available = probe.get("available_layouts") or []
        if available:
            extra = tuple(l for l in available if l not in biography.layouts)
            if extra:
                # Insert wrapping layouts ahead of minipage: they are what a
                # journal loading wrapfig or floatflt is asking for.
                head = tuple(l for l in biography.layouts if l == "journal_env")
                tail = tuple(l for l in biography.layouts if l != "journal_env")
                biography = replace(biography, layouts=head + extra + tail)
                provenance["biography"] = "probed"

        bibliography = rules.bibliography
        if probe.get("bibliography_style"):
            bibliography = replace(bibliography,
                                   style=probe["bibliography_style"])
            provenance["bibliography"] = "probed"

        return replace(rules, citation=citation, biography=biography,
                       bibliography=bibliography, provenance=provenance)

    # -- source 1: what the template declares -------------------------------- #

    def _apply_declared(self, rules: JournalRules,
                        declared: Dict[str, Any]) -> JournalRules:
        """Overlay the template's own ``rules`` block.

        Declared values win over everything: they are a human's explicit answer
        for this journal, and the whole point of the block is that it can
        correct an inference the probe got wrong.  Unknown keys are ignored
        rather than rejected, so a ``rules`` block written against a later
        version of this engine still loads.
        """
        provenance = dict(rules.provenance)

        citation = rules.citation
        block = declared.get("citation")
        if isinstance(block, dict):
            style = str(block.get("style") or citation.style)
            citation = replace(
                citation,
                style=style if style in CITATION_STYLES else citation.style,
                command=str(block.get("command") or citation.command),
                parenthetical_command=str(block.get("parenthetical_command")
                                          or citation.parenthetical_command),
                textual_command=str(block.get("textual_command")
                                    or citation.textual_command),
                group_multiple=bool(block.get("group_multiple",
                                              citation.group_multiple)),
                wrapper=block.get("wrapper") or citation.wrapper,
            )
            provenance["citation"] = "declared"

        bibliography = rules.bibliography
        block = declared.get("bibliography")
        if isinstance(block, dict):
            mode = str(block.get("mode") or bibliography.mode)
            bibliography = replace(
                bibliography,
                mode=mode if mode in BIBLIOGRAPHY_MODES else bibliography.mode,
                style=str(block.get("style") or bibliography.style),
                widest_label=str(block.get("widest_label")
                                 or bibliography.widest_label),
                key_prefix=str(block.get("key_prefix")
                               or bibliography.key_prefix),
            )
            provenance["bibliography"] = "declared"

        biography = rules.biography
        block = declared.get("biography")
        if isinstance(block, dict):
            layouts = block.get("layouts")
            if isinstance(layouts, (list, tuple)) and layouts:
                valid = tuple(str(l) for l in layouts if str(l) in BIOGRAPHY_LAYOUTS)
                # "plain" always terminates the list: a layout chain that can
                # run out leaves a biography unrendered, and a biography that
                # is merely plain is better than one that is missing.
                if valid and "plain" not in valid:
                    valid = valid + ("plain",)
                if valid:
                    biography = replace(biography, layouts=valid)
            biography = replace(
                biography,
                environment=str(block.get("environment") or biography.environment),
                photo_environment=str(block.get("photo_environment")
                                      or biography.photo_environment),
                photo_width_in=float(block.get("photo_width_in")
                                     or biography.photo_width_in),
                photo_height_in=float(block.get("photo_height_in")
                                      or biography.photo_height_in),
            )
            provenance["biography"] = "declared"

        author_photo = rules.author_photo
        block = declared.get("author_photo")
        if isinstance(block, dict):
            mode = str(block.get("mode") or author_photo.mode)
            author_photo = replace(
                author_photo,
                mode=mode if mode in AUTHOR_PHOTO_MODES else author_photo.mode,
                environment=str(block.get("environment")
                                or author_photo.environment),
                placement=str(block.get("placement") or author_photo.placement),
                column_width=str(block.get("column_width")
                                 or author_photo.column_width),
                image_width=str(block.get("image_width")
                                or author_photo.image_width),
                image_height=str(block.get("image_height")
                                 or author_photo.image_height),
                keep_aspect=bool(block.get("keep_aspect",
                                           author_photo.keep_aspect)),
            )
            provenance["author_photo"] = "declared"

        placement = rules.placement
        block = declared.get("placement")
        if isinstance(block, dict):
            placement = replace(
                placement,
                column_spec=str(block.get("column_spec") or placement.column_spec),
                span_spec=str(block.get("span_spec") or placement.span_spec),
                span_threshold=float(block.get("span_threshold")
                                     or placement.span_threshold),
                pin_in_place=bool(block.get("pin_in_place",
                                            placement.pin_in_place)),
            )
            provenance["placement"] = "declared"

        labels = rules.labels
        block = declared.get("labels")
        if isinstance(block, dict):
            labels = replace(labels, **{
                k: str(v) for k, v in block.items()
                if k in vars(labels) and isinstance(v, str)
            })
            provenance["labels"] = "declared"

        return replace(
            rules,
            citation=citation, bibliography=bibliography, biography=biography,
            author_photo=author_photo, placement=placement, labels=labels,
            caption_command=str(declared.get("caption_command")
                                or rules.caption_command),
            caption_above_tables=bool(declared.get("caption_above_tables",
                                                   rules.caption_above_tables)),
            provenance=provenance,
        )

    # -- convenience --------------------------------------------------------- #

    def for_workspace(self, workspace_dir: Path) -> JournalRules:
        """Rules for a prepared job workspace, reading its own ``template.json``."""
        metadata: Dict[str, Any] = {}
        meta_file = Path(workspace_dir) / "template.json"
        if meta_file.is_file():
            try:
                loaded = json.loads(meta_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    metadata = loaded
            except (OSError, json.JSONDecodeError):
                pass
        return self.resolve(metadata, Path(workspace_dir))
