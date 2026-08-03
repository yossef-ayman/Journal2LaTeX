/**
 * Template Mapping Wizard.
 *
 * The operator uploads the real acceptance letter and the real invoice — ordinary
 * Word files with real values already in them — and points at the parts that
 * change from paper to paper. Nothing is edited in Word, and no
 * `{{PLACEHOLDER}}` is ever typed.
 *
 * Two decisions shape the interaction:
 *
 * * **Selection is by text, not by paragraph.** One line of an invoice often
 *   carries the title, the reference number and the authors at once, so the
 *   operator can select just part of a line; clicking a line with nothing
 *   selected takes the whole line, which is the common case.
 * * **A first guess is pre-filled.** The backend suggests a value for each field
 *   from generic label and value shapes, so the usual path is reading four rows
 *   and pressing Save rather than hunting through the document.
 *
 * Once saved, the mapping is permanent: every later generation reuses it and the
 * operator is never asked to map the same template again.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import type { MouseEvent } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";
import {
  AlertCircle,
  Check,
  Loader2,
  MousePointerClick,
  Sparkles,
  Wand2,
  X,
} from "lucide-react";
import type {
  TemplateInspection,
  TemplateFieldInfo,
} from "@/services/documentGenerator";

interface MappingWizardProps {
  open: boolean;
  label: string;
  inspection: TemplateInspection | null;
  loading?: boolean;
  saving?: boolean;
  error?: string | null;
  onSave: (mappings: Array<{ field: string; text: string }>) => void;
  onClose: () => void;
}

/** Field key → the literal text in the document that stands for it. */
type Selections = Record<string, string>;

function initialSelections(inspection: TemplateInspection | null): Selections {
  if (!inspection) return {};
  const selections: Selections = {};
  // A saved mapping is the operator's own work and always wins over a guess.
  for (const suggestion of inspection.suggestions) {
    selections[suggestion.field] = suggestion.text;
  }
  for (const mapping of inspection.mapping?.mappings ?? []) {
    selections[mapping.field] = mapping.text;
  }
  return selections;
}

/** The text the operator has highlighted inside `element`, if any. */
function highlightedText(element: HTMLElement): string {
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return "";
  const range = selection.getRangeAt(0);
  if (!element.contains(range.commonAncestorContainer)) return "";
  return selection.toString().trim();
}

export function MappingWizard({
  open,
  label,
  inspection,
  loading = false,
  saving = false,
  error = null,
  onSave,
  onClose,
}: MappingWizardProps) {
  const [active, setActive] = useState<string | null>(null);
  const [selections, setSelections] = useState<Selections>({});
  const [touched, setTouched] = useState(false);

  const fields = useMemo<TemplateFieldInfo[]>(
    () => inspection?.fields ?? [],
    [inspection],
  );

  // Re-seed whenever a different template is inspected.
  useEffect(() => {
    setSelections(initialSelections(inspection));
    setTouched(false);
    setActive(inspection?.fields?.[0]?.key ?? null);
  }, [inspection]);

  const close = useCallback(() => {
    if (!saving) onClose();
  }, [onClose, saving]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close]);

  if (!open) return null;

  const assign = (field: string, text: string) => {
    const cleaned = text.trim();
    if (!cleaned) return;
    setSelections((current) => ({ ...current, [field]: cleaned }));
    setTouched(true);
    // Move to the next unmapped field so mapping is one pass down the list.
    const remaining = fields
      .map((f) => f.key)
      .filter((key) => key !== field && !selections[key]);
    setActive(remaining[0] ?? field);
  };

  const clear = (field: string) => {
    setSelections((current) => {
      const next = { ...current };
      delete next[field];
      return next;
    });
    setTouched(true);
    setActive(field);
  };

  const handleSegmentClick = (
    event: MouseEvent<HTMLButtonElement>,
    text: string,
  ) => {
    if (!active) return;
    assign(active, highlightedText(event.currentTarget) || text);
  };

  const suggestionFor = (field: string) =>
    inspection?.suggestions.find((s) => s.field === field);

  const missingRequired = fields
    .filter((field) => field.required && !selections[field.key])
    .map((field) => field.label);

  const payload = Object.entries(selections)
    .filter(([, text]) => text.trim().length > 0)
    .map(([field, text]) => ({ field, text }));

  const mappedCount = payload.length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="fixed inset-0 bg-black/30 backdrop-blur-sm"
        onClick={close}
        aria-hidden="true"
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="mapping-wizard-title"
        className="relative z-50 flex h-[min(46rem,92vh)] w-full max-w-5xl flex-col overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-2xl shadow-black/10 animate-scale-in"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-5">
          <div className="flex items-start gap-3 min-w-0">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
              <Wand2 size={18} />
            </div>
            <div className="min-w-0">
              <h2
                id="mapping-wizard-title"
                className="text-base font-bold leading-tight text-gray-900"
              >
                Map the fields in {label}
              </h2>
              <p className="mt-1 text-sm leading-relaxed text-gray-500">
                Pick a field on the left, then click the text in the document that
                should change for each paper. Select part of a line to map just that
                part. Saved once — every later batch reuses it.
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={close}
            disabled={saving}
            aria-label="Close"
            className="h-8 w-8 shrink-0 p-0"
          >
            <X size={16} />
          </Button>
        </div>

        {/* Body */}
        {loading ? (
          <div className="flex flex-1 items-center justify-center gap-2 text-sm text-gray-500">
            <Loader2 size={16} className="animate-spin" />
            Reading the document…
          </div>
        ) : !inspection ? (
          <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-gray-500">
            {error ?? "The document could not be read."}
          </div>
        ) : (
          <div className="grid flex-1 grid-cols-1 overflow-hidden md:grid-cols-[22rem_1fr]">
            {/* Fields */}
            <div className="overflow-y-auto border-b border-gray-100 md:border-b-0 md:border-r">
              <ul className="divide-y divide-gray-50">
                {fields.map((field) => {
                  const value = selections[field.key];
                  const isActive = active === field.key;
                  const suggested =
                    value !== undefined && value === suggestionFor(field.key)?.text;
                  return (
                    <li key={field.key}>
                      <button
                        type="button"
                        onClick={() => setActive(field.key)}
                        className={cn(
                          "w-full px-5 py-3.5 text-left transition-colors",
                          isActive ? "bg-emerald-50/60" : "hover:bg-gray-50",
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-gray-900">
                            {field.label}
                          </span>
                          {field.required && !value && (
                            <Badge variant="warning" className="shrink-0">
                              Required
                            </Badge>
                          )}
                          {value && (
                            <Check size={14} className="shrink-0 text-emerald-600" />
                          )}
                        </div>
                        {value ? (
                          <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-gray-600">
                            {value}
                          </p>
                        ) : (
                          <p className="mt-1 text-xs text-gray-400">
                            {isActive
                              ? "Click the text in the document →"
                              : field.description || "Not mapped"}
                          </p>
                        )}
                        <div className="mt-1.5 flex items-center gap-3">
                          {suggested && (
                            <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700">
                              <Sparkles size={11} /> Suggested
                            </span>
                          )}
                          {value && (
                            <span
                              role="button"
                              tabIndex={0}
                              onClick={(event) => {
                                event.stopPropagation();
                                clear(field.key);
                              }}
                              onKeyDown={(event) => {
                                if (event.key === "Enter" || event.key === " ") {
                                  event.stopPropagation();
                                  clear(field.key);
                                }
                              }}
                              className="text-[11px] text-gray-400 underline-offset-2 hover:text-gray-600 hover:underline"
                            >
                              Clear
                            </span>
                          )}
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>

            {/* Document */}
            <div className="overflow-y-auto bg-gray-50/60 px-5 py-4">
              <p className="mb-3 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-gray-400">
                <MousePointerClick size={12} />
                {active
                  ? `Click the text that is the ${
                      fields.find((f) => f.key === active)?.label ?? "value"
                    }`
                  : "Choose a field first"}
              </p>
              <div className="space-y-1.5">
                {inspection.segments.map((segment) => {
                  const mappedTo = fields.find(
                    (field) =>
                      selections[field.key] &&
                      segment.text.includes(selections[field.key]),
                  );
                  return (
                    <button
                      key={segment.id}
                      type="button"
                      disabled={!active}
                      onClick={(event) => handleSegmentClick(event, segment.text)}
                      className={cn(
                        "w-full rounded-xl border px-3.5 py-2.5 text-left text-sm leading-relaxed transition-colors",
                        mappedTo
                          ? "border-emerald-200 bg-emerald-50/70 text-gray-800"
                          : "border-gray-100 bg-white text-gray-700 hover:border-gray-200 hover:bg-white",
                        !active && "cursor-default opacity-70",
                      )}
                    >
                      <span className="block whitespace-pre-wrap break-words">
                        {segment.text}
                      </span>
                      <span className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-gray-400">
                        {segment.location !== "body" && (
                          <span className="capitalize">{segment.location}</span>
                        )}
                        {segment.in_table && <span>In a table</span>}
                        {segment.occurrences > 1 && (
                          <span>Appears {segment.occurrences} times</span>
                        )}
                        {mappedTo && (
                          <span className="font-medium text-emerald-700">
                            {mappedTo.label}
                          </span>
                        )}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 px-6 py-4">
          <div className="min-w-0 text-xs text-gray-500">
            {error ? (
              <span className="flex items-start gap-1.5 text-red-600">
                <AlertCircle size={13} className="mt-0.5 shrink-0" />
                {error}
              </span>
            ) : missingRequired.length > 0 ? (
              <span className="flex items-start gap-1.5 text-amber-700">
                <AlertCircle size={13} className="mt-0.5 shrink-0" />
                Still to map: {missingRequired.join(", ")}
              </span>
            ) : (
              <span>
                {mappedCount} field{mappedCount === 1 ? "" : "s"} mapped
                {touched ? " · not saved yet" : ""}
              </span>
            )}
          </div>
          <div className="flex gap-2.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={close}
              disabled={saving}
              className="h-9"
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              className="h-9"
              disabled={saving || loading || mappedCount === 0}
              onClick={() => onSave(payload)}
            >
              {saving ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Saving
                </>
              ) : (
                <>
                  <Check size={14} /> Save mapping
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
