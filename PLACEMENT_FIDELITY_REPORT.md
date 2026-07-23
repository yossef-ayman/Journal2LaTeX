# Hybrid Placement Engine — Fidelity Report

Each figure and table is scored on DOCX signals — Word inline-vs-floating,
object width vs the text column, native aspect / rendered height (page-break
risk), caption length, and two-column fit — and assigned the placement that
best balances reading-order fidelity with LaTeX layout quality. No strategy
is globally forced; floats are used where appropriate.

## Strategy distribution
- **inline_span** (10): inline, full-width spanning (cuted strip) — exact position, caption attached
- **float_h** (3): figure[H]/table[H] — pinned in place at column width, caption attached

## Per-object decisions (in document order)

| # | Object | Strategy | Why |
|---|--------|----------|-----|
| 1 | table | `inline_span` | wide table (table width 92% of text), short (~2.9in) -> inline spanning both columns to hold its exact reading-order position |
| 2 | figure | `float_h` | wide figure (image 100% of text width) but tall/near-square (~5.5in at full width) -> pinned in place at column width ([H]) so it stays in order without overflowing the page |
| 3 | figure | `inline_span` | wide figure (image 100% of text width), short banner shape (~3.0in) -> inline spanning both columns, exact position |
| 4 | figure | `float_h` | wide figure (image 92% of text width) but tall/near-square (~5.5in at full width) -> pinned in place at column width ([H]) so it stays in order without overflowing the page |
| 5 | table | `inline_span` | wide table (table width 100% of text), short (~1.9in) -> inline spanning both columns to hold its exact reading-order position |
| 6 | table | `inline_span` | wide table (table width 100% of text), short (~0.5in) -> inline spanning both columns to hold its exact reading-order position |
| 7 | table | `inline_span` | wide table (table width 97% of text), short (~3.1in) -> inline spanning both columns to hold its exact reading-order position |
| 8 | table | `inline_span` | wide table (table width 81% of text), short (~1.9in) -> inline spanning both columns to hold its exact reading-order position |
| 9 | figure | `float_h` | wide figure (image 88% of text width) but tall/near-square (~5.5in at full width) -> pinned in place at column width ([H]) so it stays in order without overflowing the page |
| 10 | table | `inline_span` | wide table (table width 95% of text), short (~1.0in) -> inline spanning both columns to hold its exact reading-order position |
| 11 | table | `inline_span` | wide table (table width 100% of text), short (~1.0in) -> inline spanning both columns to hold its exact reading-order position |
| 12 | table | `inline_span` | wide table (table width 95% of text), short (~1.0in) -> inline spanning both columns to hold its exact reading-order position |
| 13 | table | `inline_span` | wide table (table width 94% of text), short (~0.7in) -> inline spanning both columns to hold its exact reading-order position |

## Ordering differences
- Objects placed order-preserving (inline / [H]): **13/13**
- Objects handed to LaTeX float optimisation (may shift within/near a page): **0/13**
- On this document every object keeps its exact DOCX reading-order position;
  none can appear before the paragraph that introduces it.

## Page flow
- Generated pages: **20**
- Forced page breaks inserted by the placement engine: **0** (no blank pages)

## Before / after
- **Before:** every figure/table was a LaTeX float (`figure[htbp]`, `table*`),
  so LaTeX reordered them — figures appeared before their introducing paragraph,
  captions detached, wide tables jumped pages.
- **After (hybrid):** wide short charts span full width inline in place; tall or
  near-square figures are pinned at column width ([H]); tables span full width
  inline; anything Word floats (or that would overflow) is left as a proper float.
