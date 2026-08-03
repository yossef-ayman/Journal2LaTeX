# document_generator/templates

This folder is the module's template area. It is intentionally **empty of Word
files**: the master templates an operator uploads are user data, not source
code, so they are stored outside the package tree under the module's data root:

```
<DOCUMENT_GENERATOR_DATA>/templates/acceptance.docx
<DOCUMENT_GENERATOR_DATA>/templates/invoice.docx
<DOCUMENT_GENERATOR_DATA>/templates/archive/<key>__<timestamp>.docx
```

`DOCUMENT_GENERATOR_DATA` defaults to `document_generator_data/` next to the
backend and is set in `document_generator/config.py`. Keeping uploads out of the
package means a code deployment never overwrites the operator's stored
templates, and the archive of previous versions survives upgrades.

Use this folder for template *assets that ship with the module* — a starter
letterhead, a sample invoice shipped as a default, or documentation of the
placeholder vocabulary. Anything placed here is version-controlled with the
code.

## Field mapping (the normal way to make a template)

A master template is an **ordinary Word document** — the real acceptance letter
or invoice, with a real title, real authors and a real reference number already
in it. Nothing has to be edited in Word and no `{{PLACEHOLDER}}` has to be
inserted.

On the first upload the UI opens the Template Mapping Wizard. It shows the
document's lines (reassembled across Word's runs) and the operator points at the
text that changes per paper: the title, the authors, the acceptance date, the
reference number, the deadline. `document_generator/services/document_inspector.py`
pre-fills a guess for each field from generic label and value shapes, so the
usual action is a confirmation.

Confirming stores the mapping permanently beside the template:

```
<DOCUMENT_GENERATOR_DATA>/templates/<key>.mapping.json
```

Every later generation reuses it — the operator is never asked to map the same
template again. Replacing a template does not discard the mapping: each saved
literal is re-counted against the new file, and only fields whose text has
genuinely gone are marked stale for re-mapping.

At generation time `document_generator/services/mapping_engine.py` replaces
**every** occurrence of each mapped literal, across the body, headers, footers,
footnotes, endnotes and both branches of Word's `mc:AlternateContent` text
boxes, longest literal first. Mapped literals and `{{PLACEHOLDER}}` markers are
applied in the same pass, so a template may use either mechanism or both.

### Why the generated file is byte-identical apart from its values

The engine never re-serialises the document. `document_generator/services/ooxml_bytes.py`
parses each XML part only to record *byte offsets*, and writing splices the new
text into the original bytes; an untouched part is returned as the very same
object it was read as. This matters because re-serialising an OOXML part — even
with a correct XML writer — moves namespace declarations, reorders attributes,
drops `standalone="yes"` and rewrites `<w:t/>` as `<w:t></w:t>`. LibreOffice
tolerates all of that; Word does not, and reports *"The file appears to be
corrupted"* when exporting such a file to PDF. Splicing bytes is what removes
that failure at the root rather than per template, and it is also why no
paragraph shifts, spacing changes or reflowed tables can occur.

A mapped value is **one logical field**: the whole replacement is written into
the first run the mapped text touches and the remaining fragments are emptied,
so an author list Word had split across nine runs comes back as one contiguous
block in that run's own formatting. A multi-line value stays inside that run,
using `<w:br/>` between its lines rather than new paragraphs.

### Validation before export

`document_generator/services/validation.py` checks every generated document
before it is handed to a PDF converter, and a document that fails is never
converted. It answers two questions: is the package one Word will open *and*
export (zip integrity, required parts, every XML part well-formed, content types
and relationships consistent), and is it still the template (every non-text part
byte-identical; paragraph, table, row, cell, text-box, run, drawing, hyperlink,
header and footer counts unchanged; each dynamic value present and each replaced
template literal gone). The report reaches the operator per document in the UI
and is stored in the batch summary.

The mappable field vocabulary lives in
`document_generator/services/template_fields.py`; its keys are the same keys the
placeholder context uses, and `register_field()` adds one without touching
anything else.

## Reference numbers

Reference numbers follow `<JournalCode><MMDDYY><BatchOrder><Suffix>`, e.g.
`JSAP07302601A`. The journal code and the suffix are both settings
(`journal_code`, `reference_suffix`) and either can be overridden for a single
batch, because one installation routinely serves several journals. The code is a
*component of the number*, not a label: whatever wording the template puts in
front of it — `Ref. ` and so on — belongs to the template and is never generated.

## Placeholder vocabulary

Placeholders are written `{{NAME}}` in the Word file and matched
case-insensitively. `document_generator/services/context_builder.py` is the
single place their meanings are defined; add a key there to add a placeholder.

Currently supplied: `TITLE`, `PAPER_TITLE`, `AUTHORS`, `AUTHOR_LIST`,
`AUTHOR_COUNT`, `FIRST_AUTHOR`, `CORRESPONDING_AUTHOR`, `AUTHOR_SURNAME`,
`REFERENCE_NUMBER`, `REFERENCE_NO`, `REF_NUMBER`, `MANUSCRIPT_ID`,
`ACCEPT_DATE`, `ACCEPTANCE_DATE`, `DATE`, `DEADLINE`, `PAYMENT_DEADLINE`,
`DUE_DATE`, `EDITOR`, `EDITOR_NAME`, `JOURNAL`, `JOURNAL_NAME`, `PAPER_NUMBER`,
`PAPER_INDEX`, `SOURCE_FILENAME`, `DOCUMENT_TYPE`, `TODAY`, `YEAR`.

Any other placeholder can be supplied per-batch (`extra_placeholders`) or stored
permanently in the module settings (`custom_placeholders`) without a code change.

## Adding a document type

Call `register_document_type()` from
`document_generator/services/document_types.py` with a new key, label and output
basename. Templates, generation, output folders, the ZIP and the frontend all
iterate the registry, so certificates, review letters or copyright forms need no
other change.
