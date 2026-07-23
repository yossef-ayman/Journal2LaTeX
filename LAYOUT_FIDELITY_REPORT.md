# Layout Fidelity — Comparison Report

Method: figures and tables are emitted **inline** at their exact DOCX position.
Nothing uses a floating environment, so LaTeX cannot reorder content.

## Misplaced figures
- Floating figure environments (could jump pages / reorder): **0**
- Figures pinned in place ([H] float or strip, inline): **4**
- A figure can no longer appear before the paragraph that introduces it.

## Misplaced tables
- Floating table environments: **0**
- Tables placed inline (full-width strip, or in-column): **9**
- Tables stay immediately where they occur in the DOCX flow.

## Detached captions
- Captions rendered outside their figure/table unit: **0**
- Captions bound inside the same unbreakable unit as their content: **10**
- Each image/table + caption share one [H] float or one strip+minipage, so a
  page break can never separate them.

## Ordering differences
- Total floating (reorderable) environments in the body: **0**
- Reading order = source order = DOCX block order, preserved exactly.

## Page-flow differences
- Generated pages: **20** (no \clearpage/\newpage forced by the layer)
- Forced page breaks inserted by placement: **0**  (blank pages are not created)