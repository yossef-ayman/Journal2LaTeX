# The Document Engine — architecture and migration plan

**Status:** design for approval. No implementation code has been written.
**Scope:** an AI-powered Document Understanding and Editing Engine that parses an
arbitrary research manuscript in `.docx`, extracts its semantic structure, lets the
operator edit that structure, and writes the changes back into *the same file*
without disturbing anything else in it.

Three decisions you already made are the load-bearing constraints of everything
below, so they are stated once here and then assumed throughout:

* **Deterministic first, AI later.** Phase 1 ships rule-based checks behind an LLM
  interface that is stubbed. AI plugs in with no rework.
* **The placeholder generator stays permanently, side by side.** It does a
  different job — batch letters from master templates — that the new editor does
  not replace. It is not migrated, not refactored and not touched.
* **The target document is the manuscript itself**, not a template.

---

## 1. The idea the whole design rests on

Everything difficult about this project reduces to a single sentence in your
directive: *"Do NOT regenerate the document from scratch. Instead, modify the
existing DOCX."*

Almost every DOCX library on earth does the opposite. It reads a package into an
object tree, you mutate the tree, and it serialises the tree back out. That
round-trip is where documents die: attribute order changes, namespace declarations
move, `standalone="yes"` disappears, `<w:t/>` becomes `<w:t></w:t>`, and Word — far
stricter on PDF export than on open — reports *"The file appears to be corrupted."*
We have already lived through exactly this failure and fixed it.

The fix is the asset the new engine is built on. `ooxml_bytes.py` parses a part with
`expat` **purely to record byte offsets**, and then splices only the changed byte
ranges back into the original bytes. A part with no changes is returned as *the same
object*. Fidelity is not something the writer tries to achieve; it is the arithmetic
default, because untouched bytes are never rewritten.

So the design principle is:

> **Every semantic object the engine extracts holds a byte-range anchor back into
> the original part. Extraction never copies text away from the document; it
> *points at* it. Editing rewrites the pointed-at range and nothing else.**

This is what makes "preserve styles, tables, images, headers, footers, bookmarks,
fields, section breaks, page breaks, TOC, cross references, numbering, formatting"
a property of the architecture rather than a checklist the writer has to satisfy
item by item. Those things are preserved because their bytes are never touched.

It also explains, up front, why the existing `DocumentAnalyzer` cannot be the parser
for this engine, which is the single most important reuse judgement in this document
and is argued in full in §4.

---

## 2. Two layers

### Layer 0 — the physical model (`document_engine/ooxml/`)

An anchored, read-mostly view of the actual package. It knows about OOXML and
nothing about research papers.

Today `ooxml_bytes` models exactly two things: text nodes and the paragraphs that
contain them, with counts for tables, text boxes, runs, drawings and hyperlinks. That
was sufficient for replacing field values. It is not sufficient for understanding a
document, because a heading is recognised by *formatting*, and formatting currently
is not in the model at all.

Layer 0 therefore extends the same offset-recording pass — one pass, same expat
scan, same discipline — to record:

| Recorded | Why the semantic layer needs it |
| --- | --- |
| `w:pPr` — style id, `outlineLvl`, `jc`, `spacing`, `ind`, `keepNext`, `numPr` | the heading cascade; list detection |
| `w:rPr` per run — `b`, `i`, `sz`, `rFonts`, `caps`, `smallCaps`, `vertAlign` | prominence scoring; superscript affiliation markers |
| `w:tbl` / `w:tr` / `w:tc` tree with `gridSpan`, `vMerge` | tables as structures, not counts |
| `w:drawing`, `w:pict`, `wp:docPr`, `a:blip` r:embed | figures and their relationship targets |
| `w:bookmarkStart/End`, `w:fldSimple`, `w:instrText`, `w:hyperlink` | cross references and fields |
| `w:sectPr`, `w:br type="page"`, `w:lastRenderedPageBreak` | section and page structure |
| `w:footnoteReference` + the footnotes part | footnotes |
| `styles.xml` resolved chain, `numbering.xml`, `theme` fonts | the *effective* formatting of a run, not just its direct formatting |

The last row matters more than it looks. Word formatting is inherited: docDefaults →
style → paragraph style → direct. A heading may carry no direct bold at all. A
`StyleResolver` that computes effective properties is a prerequisite for any
formatting-based heuristic being trustworthy, and it is the thing the current
analyzer's raw-XML side channels approximate by reading direct properties only.

Layer 0's public shape:

```
Package            parts, content types, relationships, styles, numbering, theme
  Part             bytes + node/offset index          (existing, extended)
    Block          Paragraph | Table | ... with anchor + effective properties
      Run          anchor + effective run properties + text
Anchor             (part_name, start_byte, end_byte, node_ids)
StyleResolver      effective_paragraph_props(block), effective_run_props(run)
```

**Invariant:** Layer 0 objects are anchors and derived facts. They never hold a
mutated copy of anything.

### Layer 1 — the semantic model (`document_engine/model/`)

Typed objects that *reference* Layer-0 anchors. This is the model your directive
enumerates. Sections are nested here, not flat, because "fix heading hierarchy" is
one of your AI features and a flat list with a level integer cannot express the
defect being fixed.

```
Document
  Metadata      title, subtitle, running_head, doi, dates, volume, issue, journal
  Authors[]     name, given, family, markers[], affiliation_refs[], email,
                is_corresponding, anchor
  Affiliations[] marker, text, normalised, anchor
  Abstract      paragraphs[], anchor
  Keywords[]    term, anchor
  Sections[]    heading, level, children[Section], blocks[], anchor   (nested)
  Blocks        Paragraph | List | Table | Figure | Equation | Caption
  References[]  raw, parsed{authors,year,title,venue,doi}, style_guess, anchor
  Footnotes[]   id, blocks[], anchor
  Headers/Footers[] section_ref, blocks[], page_number_fields[]
  Bookmarks[]   name, anchor        CrossRefs[] target_bookmark, kind, anchor
  Styles        the resolved catalogue
```

Every object carries `anchor` and `formatting` (the effective properties that made
it recognisable). Formatting metadata is preserved by construction: it is read from
the anchor on demand, not copied and risked going stale.

---

## 3. The sixteen modules

Your list, mapped onto the two layers, each with one responsibility and a stated
boundary. Package root: `document_engine/`.

| Module | Responsibility | Explicitly not its job |
| --- | --- | --- |
| **DocumentParser** | `ooxml/` — Layer 0. Package → anchored physical blocks + resolved styles. | Any notion of "title", "abstract", "section". |
| **DocumentModel** | `model/` — the Layer-1 dataclasses and their invariants. | Extraction, editing, serialisation. |
| **SemanticExtractor** | `extract/orchestrator.py`. Runs the specialised extractors in order, resolves conflicts, records confidence. | Any individual extraction rule. |
| **MetadataExtractor** | Title, subtitle, authors, affiliations, emails, corresponding author, abstract, keywords, dates, DOI. | Body structure. |
| **SectionExtractor** | The heading cascade (§5) and the nested section tree. | Recognising captions or lists. |
| **TableExtractor** | Table structure, header rows, merges, caption binding. | Rendering. |
| **FigureExtractor** | Drawings, VML, charts, embedded objects, caption binding, image relationship targets. | Rasterising. |
| **EquationExtractor** | OMML (`m:oMath`) → structured form; inline vs display; numbering. | LaTeX emission for the converter. |
| **ReferenceExtractor** | Reference list detection, per-entry splitting, field parsing, style inference, in-text citation linking. | Reformatting entries. |
| **AIEditor** | The provider interface + the deterministic implementation. One method: `propose(kind, target, context) -> Suggestion[]`. | Deciding what the operator sees. |
| **SuggestionEngine** | Runs the rule set (and later the LLM) across the model, dedupes, ranks, groups. | Computing text diffs. |
| **DiffEngine** | Given original and proposed text for one anchor, produce a word-level diff and the changed sub-ranges. | Deciding what to propose. |
| **WordWriter** | Applies **accepted** edits only, via `rewrite_spans`, optionally emitting `w:ins`/`w:del`. | Validation, PDF. |
| **PreviewEngine** | Renders original and modified to PDF/images and maps anchors → changed regions for highlighting. | Comparing pixels. |
| **ExportEngine** | Validation gate, then final artefact + download. | Editing. |
| **ValidationEngine** *(added)* | Package/XML/structure validation of the written file. | — |

`ValidationEngine` is a sixteenth module you did not list; it exists because the
"file appears to be corrupted" incident proved that writing without an export gate
is not safe. It is not new work — `document_generator/services/validation.py` already
does exactly this and is reused (§4).

**Dependency direction is strictly one-way:**

```
ooxml → model → extract → suggest → diff → write → validate → preview → export
```

No module imports anything downstream of it. `AIEditor` sits behind `suggest` as a
provider interface, so swapping deterministic for LLM changes one constructor
argument.

---

## 4. What we reuse — audited against the actual files

Line counts are real, taken from the repository.

### Bucket A — reused as-is, imported not copied

| File | Lines | Role in the new engine |
| --- | --- | --- |
| `document_generator/services/ooxml_bytes.py` | 429 | **The foundation.** Byte-exact splicing, proven. Promoted to `document_engine/ooxml/bytes.py`; a one-line re-export is left at the old path so the generator's imports are unchanged. |
| `document_generator/services/validation.py` | 370 | The export gate, verbatim. `validate_docx` is document-agnostic. `compare_to_template` becomes `compare_to_original` — same code, the "template" is now the manuscript before editing. |
| `document_generator/services/author_names.py` | 245 | Author/affiliation discrimination. Already generic, already hardened against the real front-matter you sent. Feeds `MetadataExtractor` directly. |
| `document_generator/pdf/converter.py` | — | Both sides of the preview. |
| `document_generator/services/packaging.py` | 49 | ZIP export. |

### Bucket B — extended

| File | Lines | Extension |
| --- | --- | --- |
| `ooxml_bytes.py` | 429 | Layer 0's table above. This is the largest single piece of new work and it is *additive* to a module whose existing behaviour is covered by the generator's tests. |
| `document_generator/services/document_inspector.py` | 281 | Its segment model — paragraph identity across body/header/footer/text-box, innermost-paragraph attribution, duplicate `mc:AlternateContent` branches — is exactly the traversal the editor needs. Generalised into `ooxml/traverse.py`. |
| `document_generator/services/template_store.py` | 352 | Its on-disk pattern (permanent storage, archived versions, atomic replace) becomes the document/session store. Pattern reused, code not shared. |

### Bucket C — read for its rules, never imported, never modified

`app/services/document_analyzer.py` (**2303 lines**) is the most valuable body of
knowledge in the repository and simultaneously unusable as this engine's parser.

Why unusable, concretely:

1. It shells out to **Pandoc** and works from Pandoc's JSON AST. That AST has no byte
   offsets into `word/document.xml`. There is no path from a Pandoc node back to the
   bytes we must rewrite — which is the one thing this engine exists to do.
2. `_stringify_inlines` **flattens every paragraph to plain text**. Bold, italic,
   superscript and font size are gone by the time anything semantic runs. The five
   raw-XML side channels (`_extract_heading_formats`, `_extract_table_styles`,
   `_extract_text_width_in`, `_extract_drawing_placement`, `_extract_corresponding_email`)
   exist precisely to smuggle back the formatting Pandoc discarded — which is an
   admission that the AST is the wrong substrate for this job.
3. Its `DocumentModel` sections are a **flat list with a level integer**, and
   `content` is an untyped `dict`. Neither survives contact with "fix the heading
   hierarchy" or "edit each item independently".

And it is, by your standing instruction, part of the stable Word → LaTeX module that
must remain untouched. So: **frozen, read-only, referenced.** What we lift is the
*reasoning*, re-implemented over anchored nodes:

| Analyzer asset | Line | Re-implemented as |
| --- | --- | --- |
| `_extract_heading_formats` | 1533 | the style/outline/size/bold/caps/keepNext signal set, now over *effective* properties |
| `_semantic_heading_level` | 1837 | the prominence score: `bold + ≥1.12× body size + all-caps + keepNext + ≥6pt spacing` |
| `_looks_like_prose` | 1804 | the negative test that stops a long sentence being read as a heading |
| `_numbering_depth`, `_detect_manual_heading` | 1780, 1913 | manual/roman/letter/word numbering depth |
| `_promote_semantic_headings`, `_front_matter_end` | 1372, 1323 | front-matter boundary and heading promotion |
| `_caption_kind`, `_attach_captions`, `_strip_caption_label` | 1180, 1237, 1196 | caption binding |
| the regex battery | — | `_MANUAL_HEADING_RE`, `_ROMAN_HEADING_RE`, `_ABSTRACT_LABEL_RE`, `_KEYWORD_LABEL_RE`, `_EMAIL_RE`, `_FURNITURE_RE`, `_CAPTION_RE` — carried over verbatim |

Same treatment, same reason: `graphics_extractor.py` (480, DrawingML/VML/SmartArt/chart
handling), `header_reconstructor.py` (499, header/footer semantics), `citation_mapper.py`
(153, in-text citation linking).

**`app/fidelity/` is not consulted at all.** Per your instruction it is not modified,
not imported, and not extended. The preview highlights changed regions from *anchors*
— it knows where the edits are, so it does not need to look at pixels to find them.

### Bucket D — genuinely new

`StyleResolver`; the nested section tree; OMML parsing; reference field parsing;
`DiffEngine`; `SuggestionEngine`; `WordWriter`'s track-changes emission; `PreviewEngine`;
the editor UI; the session store.

### What we deliberately do not touch

`app/` (the Word → LaTeX converter) — read-only, always. `app/fidelity/` — out of
scope entirely. The placeholder generator's `mapping_engine`, `placeholder_engine`,
`generator_service`, `reference_numbers`, `metadata_extractor`, its routes and its UI —
kept permanently, unchanged, side by side.

---

## 5. Parsing without style names — what the real papers actually show

You said: do not rely on paragraph indexes, templates, journal layouts or style names.
The four real production papers make that instruction not merely principled but
*mandatory*, and it is worth showing why:

| Paper | Heading styles | `w:outlineLvl` | tables | drawings | OMML | numPr | sectPr |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 01 normal | Heading1 ×2 | **0** | 0 | 10 | 0 | 19 | 2 |
| 02 the role | Heading1 ×1 | **0** | 24 | 12 | 0 | 0 | 2 |
| 03 author photo | Heading1 ×1, ListParagraph ×24 | **0** | 7 | 13 | 0 | 24 | 2 |
| 04 charts | Heading1 ×3, Title ×1 | **0** | 0 | 4 | 0 | 0 | 1 |

Real manuscripts use **one or two heading styles for an entire paper** and **zero
`w:outlineLvl` anywhere**. A parser that trusts style names would find two headings in
a twenty-heading paper. So the cascade has to fall through to visual prominence in
practice, not as a fallback for exotic files:

1. **Explicit style** — `w:pStyle` matching `heading\s*(\d)`. Correct when present; present rarely.
2. **Outline level** — `w:outlineLvl`. Authoritative; absent in all four papers.
3. **Numbering** — `numPr` depth, or manual `1.` / `1.1` / `I.` / `A.` numbering in the text.
4. **Visual prominence** — the score above, computed against the document's **modal
   body size** rather than an absolute point size, so a 10pt journal and a 12pt thesis
   are judged on the same scale.
5. **Positional/lexical** — front-matter boundary, `_FURNITURE_RE`, abstract/keyword labels.

Each level records *which signal fired* and a confidence. That is not decoration: the
editor shows low-confidence extractions differently, and an operator correcting one is
the cheapest possible ground truth. Nothing in the cascade names a journal.

Equations deserve a flag: **all four papers have zero `m:oMath`**, so their equations
are images or plain text. OMML parsing is still built (Springer/IEEE submissions use
it heavily), but equation *editing* will be a no-op on documents like these, and the
UI should say so rather than appear broken.

---

## 6. Edits, suggestions and diffs

An edit is a small immutable record:

```
Edit(id, anchor, original_text, suggested_text, source, rationale, confidence, status)
    source  = operator | rule:<name> | ai:<model>
    status  = proposed | accepted | rejected | modified
```

Nothing is applied when it is proposed. The operator's own typing in the editor also
produces an `Edit` with `source=operator, status=accepted` — one path to the writer,
not two, so there is no route by which a change reaches the document without passing
the same validation.

`DiffEngine` uses `difflib.SequenceMatcher` at word granularity and returns changed
sub-ranges *relative to the anchor*, which is simultaneously the diff shown in the UI
and the highlight map used by the preview.

`WordWriter` applies only accepted edits, grouped by part, in a single
`rewrite_spans` call per part, using the same one-logical-field rule proven in the
generator: the whole replacement goes into the first node the span touches, the rest
are emptied, and multi-line values emit `</w:t><w:br/><w:t xml:space="preserve">`
inside the same run. Track-changes emission (`w:ins`/`w:del` with author and date) is a
writer *mode*, off by default, because the Track Changes requirement is about Word
being able to consume our output — not about us needing it internally.

---

## 7. Migration plan

Seven phases. Each is independently shippable, each leaves the existing generator and
the existing converter working, and no phase requires the next one to exist. Phases 1–3
ship no user-visible behaviour change at all, which is the safest possible way to
build the risky part.

**Phase 0 — isolation scaffold.**
Create `document_engine/` as a top-level package with its own router, mounted in
`app/main.py` with the same guarded, additive `try/except` the generator already uses
(lines 73–80) — so deleting the package removes the feature and nothing else changes.
Promote `ooxml_bytes` to `document_engine/ooxml/bytes.py` and leave a re-export shim at
`document_generator/services/ooxml_bytes.py`. *Exit criterion: the generator's full
batch over the four real papers still produces 16 documents with 0 validation failures.*

**Phase 1 — Layer 0.**
Extend the offset pass to the full block model; build `StyleResolver`. No semantics.
*Exit criterion: for every one of the four real papers, parse → serialise with zero
edits returns a byte-identical package, and every part object is identity-unchanged.*

**Phase 2 — Layer 1 and the extractors.**
`DocumentModel`, `SemanticExtractor` and the six specialised extractors, with the
heading cascade of §5. Read-only: an API that returns the extracted model as JSON.
*Exit criterion: a per-paper extraction report over the four real papers, reviewed by
you, with the heading tree and author list correct.*

**Phase 3 — the writer.**
`WordWriter` + the validation gate. Still no UI. *Exit criterion: apply a synthetic edit
to each real paper; validation passes; the file opens in Word **and exports to PDF
without a repair dialog** — the check only your machine can perform.*

**Phase 4 — the editor UI and the diff system.**
The structured editor, `DiffEngine`, `SuggestionEngine` with the deterministic rule set
(email validation, heading hierarchy, reference formatting, consistency, affiliation
normalisation) and the accept/reject/edit flow. The `AIEditor` interface exists with a
deterministic implementation; no model is called. *Exit criterion: end-to-end edit of a
real paper through the UI.*

**Phase 5 — preview and export.**
Side-by-side original/modified with anchor-derived highlighting; the export gate; download.

**Phase 6 — AI.**
Implement `AIEditor` against a real model for grammar, rewriting, abstract refinement,
keyword and caption improvement. Every suggestion still lands in the same ledger, still
requires acceptance, still passes the same validation. This is a swap of one
implementation behind an interface that has been in production since Phase 4.

Throughout: the placeholder generator remains mounted and unmodified, and both features
live under the Document Generator section of the UI as separate tools.

---

## 8. Risks, honestly

**The heading cascade is the whole game.** If it is wrong, every downstream feature is
wrong, and the evidence above says style names will not save us. Mitigation: confidence
scores surfaced in the UI, operator corrections as ground truth, and Phase 2 gated on
your review of real extraction output rather than on my own judgement.

**Layer 0 is a large extension of a module that currently works perfectly.** Mitigation:
purely additive, existing API untouched, and the Phase 1 exit criterion is byte-identity
on real files.

**Nested sections from flat evidence.** Level assignment can be locally right and
globally inconsistent (a level 3 under a level 1). Mitigation: a normalisation pass, and
"fix heading hierarchy" is itself one of your listed features — so the defect and the
feature that repairs it are the same code.

**Reference parsing is genuinely hard** across Springer/IEEE/Elsevier/APA. Mitigation:
we detect and split entries reliably, parse fields best-effort, and never rewrite an
entry we could not parse with confidence.

**Equation editing will look inert** on documents whose equations are images — which is
all four of your current papers. Mitigation: say so in the UI.

**Sandbox limits, unchanged:** `npm` is blocked here so the frontend cannot be built or
typechecked in this environment, and Word's own PDF export can only be confirmed on your
machine. Both are Phase 3 and Phase 4 exit criteria on your side, not mine.

---

## 9. Extension points reserved for later

None of the following is implemented now. Each is a place where the core architecture
is shaped so the feature can arrive later without the core changing. The cost of
reserving them now is close to zero; the cost of retrofitting them is a rewrite.

### 9.1 A plugin system for analysis capabilities

Grammar, Citation, Journal Rules, Consistency and Math are not five different kinds of
thing. Each one reads the document model and returns suggestions. That is one contract:

```
class AnalysisPlugin(Protocol):
    id: str                      # "grammar", "citation", "journal.ieee", "math"
    label: str
    requires: frozenset[str]     # model capabilities it needs, e.g. {"sections", "references"}

    def analyse(self, doc: Document, ctx: PluginContext) -> Iterable[Suggestion]: ...
```

`SuggestionEngine` becomes a *host*: it holds a registry, asks each enabled plugin to
analyse, then dedupes, ranks and groups the union. It contains no rule of its own. The
deterministic rules of Phase 4 — email validation, heading hierarchy, reference
formatting, consistency, affiliation normalisation — are written **as plugins from day
one**, against this exact interface. That is the design decision that matters: the
first-party rules are not privileged, so a later third-party plugin is not a special
case, it is the same case.

What this reserves:

* `Suggestion` already carries `source`, so a suggestion knows which plugin produced it
  and the UI can group and filter by plugin without a schema change.
* Plugins receive the model and return suggestions. They **cannot** write to the
  document — only `WordWriter` writes, only accepted edits reach it, and validation
  still gates export. A plugin can therefore never corrupt a package.
* `requires` lets a plugin declare what it needs. A Math plugin on a document with no
  OMML is reported as *not applicable*, not as *found nothing* — the distinction §8
  already flags as a UI honesty problem.
* Registration is a single entry-point function, so first-party plugins ship in-tree and
  external ones can be discovered later without touching the host.

`AnalysisPlugin`, `PluginContext` and the registry are defined in Phase 4 when the first
rules are written. Nothing before Phase 4 needs to know they exist.

### 9.2 The AI layer behind a named interface

The provider interface is `DocumentAssistant`, and it is the *only* place in the engine
that knows a model exists:

```
class DocumentAssistant(Protocol):
    def propose(self, task: AssistantTask, target: TextTarget,
                context: AssistantContext) -> list[Proposal]: ...
    def capabilities(self) -> frozenset[AssistantTask]: ...
```

`AssistantTask` is a closed enum drawn from your feature list — grammar, rewrite,
abstract refinement, keyword improvement, caption improvement, consistency. `TextTarget`
is anchor plus text, never a package or a file path. Deliberate properties:

* **Nothing crosses the boundary but text.** A provider receives strings and returns
  strings. It never sees the package, never touches bytes, never writes. So a cloud API,
  a local model or the deterministic stub are interchangeable at the level of what they
  are *able* to do, not merely what they promise.
* `capabilities()` means a small local model can support rewriting but not journal-style
  suggestion, and the UI adapts rather than failing.
* Providers are selected by configuration and resolved through a small factory, so
  swapping local for cloud is a settings change, not a code change.
* Everything a provider returns is a `Proposal` that becomes a `Suggestion` in the same
  ledger, requiring the same acceptance, passing the same validation. There is no path
  by which a model writes to a document.

Phase 4 ships `DeterministicAssistant`. Phase 6 adds a real provider. §9.1 and §9.2
compose: an AI-backed plugin is a plugin holding a `DocumentAssistant`.

### 9.3 Version history

Reserved by two decisions taken now rather than later:

* Edits are already **immutable records with stable ids**, applied as a set. An
  edit session is therefore already a changeset — history needs to persist it, not
  invent it.
* The document store (Bucket B, from `template_store`'s pattern) already keeps archived
  versions with atomic replace. The engine writes each revision as a new stored version
  rather than overwriting in place, from Phase 3 onwards, because that is no harder than
  overwriting.

So a future history feature is: list revisions, show the changeset between two, restore
one. Diffing two revisions reuses `DiffEngine` unchanged. Restoring is writing a stored
version back — a copy, not a reconstruction. **The one thing this requires of Phase 3 is
that the writer never mutates the operator's original file in place**, and that is how
it will be built.

### 9.4 Semantic search

Reserved by the anchor, which already exists for a different reason.

Every semantic object carries `(part, byte range, node ids)`. That is precisely the
identifier an index entry needs in order to point back at a location in a document. So a
future index is a side table of `(document_id, revision, anchor, text, embedding)` —
built by walking the model, requiring no change to the model, the parser or the writer.
Search results resolve to anchors, and anchors are what the editor and the preview
highlighter already navigate to.

Two small things are done now to keep this open: extraction is a **pure function of the
package** (same input, same model, so an index can be rebuilt deterministically), and
every model object has a stable id derived from its anchor rather than from its position
in a list, so an index entry survives edits elsewhere in the document.

Nothing else is needed. Search is additive infrastructure over data the engine already
produces, which is exactly where a feature of uncertain timing belongs.

---

## 10. What I need from you

Approval of this design, or corrections to it. On approval I begin at Phase 0, which is
scaffold and shim only and changes no behaviour.

Also still outstanding from the previous directive, on your machine: run `npm run build`,
confirm Word's PDF export produces no repair dialog, and delete the now-dead
`document_generator/services/ooxml.py` (the sandbox copy is gone; the device bridge
cannot delete files).
