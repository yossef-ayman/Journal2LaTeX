import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { WordDiff } from "./WordDiff";
import {
  Check,
  X,
  Pencil,
  RotateCcw,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Info,
  AlertTriangle,
  Loader2,
  CheckCheck,
  CircleX,
} from "lucide-react";
import { cn } from "@/utils/cn";
import type { Suggestion, Note } from "@/types/documentEngine";

type Status = Suggestion["status"];

function StatusPill({ status }: { status: Status }) {
  if (status === "accepted") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[10px] font-bold text-emerald-700">
        <Check size={10} strokeWidth={3} />
        Accepted
      </span>
    );
  }
  if (status === "rejected") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2.5 py-0.5 text-[10px] font-bold text-red-600">
        <X size={10} strokeWidth={3} />
        Rejected
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-gray-50 px-2.5 py-0.5 text-[10px] font-bold text-gray-500">
      Pending
    </span>
  );
}

interface SuggestionCardProps {
  suggestion: Suggestion;
  onUpdate: (id: string, patch: Partial<Suggestion>) => void;
}

function SuggestionCard({ suggestion, onUpdate }: SuggestionCardProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(suggestion.suggested);

  const openEditor = () => {
    setDraft(suggestion.suggested);
    setEditing(true);
  };

  const saveEdit = () => {
    if (!draft.trim()) return;
    onUpdate(suggestion.id, {
      status: "accepted",
      user_text: draft,
      source: "user",
    });
    setEditing(false);
  };

  const isAccepted = suggestion.status === "accepted";
  const isRejected = suggestion.status === "rejected";

  return (
    <div
      className={cn(
        "rounded-2xl border bg-white p-4 shadow-sm transition-colors",
        isAccepted
          ? "border-emerald-200 bg-emerald-50/40"
          : isRejected
            ? "border-red-100 bg-red-50/30 opacity-80"
            : "border-gray-100",
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <div
            className={cn(
              "flex h-6 w-6 shrink-0 items-center justify-center rounded-lg",
              isAccepted
                ? "bg-emerald-100 text-emerald-700"
                : isRejected
                  ? "bg-red-100 text-red-600"
                  : "bg-gray-100 text-gray-400",
            )}
          >
            <Sparkles size={12} />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-gray-900 leading-tight">
              {suggestion.reason || "Suggested edit"}
            </p>
            <p className="mt-0.5 text-[11px] text-gray-400">
              {suggestion.kind} · confidence {Math.round(suggestion.confidence * 100)}%
              {suggestion.source === "user" ? " · manually edited" : ""}
            </p>
          </div>
        </div>
        <StatusPill status={suggestion.status} />
      </div>

      {editing ? (
        <div className="space-y-2.5">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={3}
            autoFocus
            aria-label="Edited replacement text"
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 leading-relaxed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:border-emerald-400"
          />
          <div className="flex items-center justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={() => setEditing(false)} className="h-8 text-xs">
              Cancel
            </Button>
            <Button size="sm" onClick={saveEdit} disabled={!draft.trim()} className="h-8 text-xs gap-1.5">
              <Check size={13} />
              Save edit
            </Button>
          </div>
        </div>
      ) : (
        <WordDiff
          original={suggestion.original}
          suggested={suggestion.user_text ?? suggestion.suggested}
        />
      )}

      {!editing && (
        <div className="mt-3 flex items-center justify-between gap-2 border-t border-gray-50 pt-3">
          <div className="flex items-center gap-1.5">
            {!isRejected && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => onUpdate(suggestion.id, { status: "accepted", user_text: null, source: suggestion.source })}
                aria-label="Accept suggestion"
                title="Accept"
                className={cn(
                  "text-gray-400 hover:bg-emerald-50 hover:text-emerald-700",
                  isAccepted && "text-emerald-600 bg-emerald-50",
                )}
              >
                <Check size={15} />
              </Button>
            )}
            {!isAccepted && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => onUpdate(suggestion.id, { status: "rejected", user_text: null, source: suggestion.source })}
                aria-label="Reject suggestion"
                title="Reject"
                className={cn(
                  "text-gray-400 hover:bg-red-50 hover:text-red-600",
                  isRejected && "text-red-500 bg-red-50",
                )}
              >
                <X size={15} />
              </Button>
            )}
            {!isAccepted && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={openEditor}
                aria-label="Edit and accept suggestion"
                title="Edit then accept"
                className="text-gray-400 hover:bg-blue-50 hover:text-blue-600"
              >
                <Pencil size={14} />
              </Button>
            )}
            {(isAccepted || isRejected) && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => onUpdate(suggestion.id, { status: "pending", user_text: null, source: suggestion.source })}
                aria-label="Reset decision"
                title="Reset"
                className="text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              >
                <RotateCcw size={13} />
              </Button>
            )}
          </div>
          {suggestion.source === "user" && (
            <span className="text-[10px] text-blue-500 font-medium">
              Custom wording
            </span>
          )}
        </div>
      )}
    </div>
  );
}

interface SuggestionReviewStepProps {
  suggestions: Suggestion[];
  notes: Note[];
  pluginRunErrors: string[];
  onUpdate: (id: string, patch: Partial<Suggestion>) => void;
  onBack: () => void;
  onPreview: () => void;
  previewing: boolean;
  error: string | null;
}

export function SuggestionReviewStep({
  suggestions,
  notes,
  pluginRunErrors,
  onUpdate,
  onBack,
  onPreview,
  previewing,
  error,
}: SuggestionReviewStepProps) {
  const grouped = useMemo(() => {
    const map = new Map<string, Suggestion[]>();
    for (const s of suggestions) {
      const list = map.get(s.source) ?? [];
      list.push(s);
      map.set(s.source, list);
    }
    return Array.from(map.entries());
  }, [suggestions]);

  const acceptedCount = suggestions.filter((s) => s.status === "accepted").length;

  const acceptAll = () => {
    for (const s of suggestions) {
      onUpdate(s.id, { status: "accepted", user_text: null, source: s.source });
    }
  };

  const rejectAll = () => {
    for (const s of suggestions) {
      onUpdate(s.id, { status: "rejected", user_text: null, source: s.source });
    }
  };

  if (suggestions.length === 0 && notes.length === 0) {
    return (
      <div className="space-y-5">
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-4 py-16 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-gray-100 to-gray-50 text-gray-400">
              <Sparkles size={24} />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-gray-900">
                No suggestions found
              </h3>
              <p className="text-sm text-gray-500 max-w-sm">
                The plugins found nothing to change in this document. Go back and
                try a different set of plugins, or use the document as-is.
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={onBack} className="gap-1.5">
              <ChevronLeft size={14} />
              Back to plugins
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      <Card className="border-emerald-100 bg-gradient-to-br from-emerald-50 to-white">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm shadow-emerald-200">
              <CheckCheck size={17} />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">
                {acceptedCount} of {suggestions.length} suggestion(s) accepted
              </p>
              <p className="text-xs text-gray-500">
                Only accepted edits will be applied to the document.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={acceptAll} className="h-8 text-xs gap-1.5">
              <Check size={13} />
              Accept all
            </Button>
            <Button variant="outline" size="sm" onClick={rejectAll} className="h-8 text-xs gap-1.5">
              <CircleX size={13} />
              Reject all
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Notes */}
      {notes.length > 0 && (
        <Card>
          <CardHeader className="pb-3 border-b border-gray-50">
            <CardTitle className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-amber-100">
                <Info size={13} className="text-amber-700" />
              </div>
              Findings without edits
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 space-y-2">
            {notes.map((note, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 rounded-xl border border-gray-100 bg-gray-50/50 px-4 py-3 text-sm text-gray-700"
              >
                {note.severity === "warning" ? (
                  <AlertTriangle size={14} className="shrink-0 mt-0.5 text-amber-500" />
                ) : (
                  <Info size={14} className="shrink-0 mt-0.5 text-blue-500" />
                )}
                <div>
                  <p className="leading-relaxed">{note.message}</p>
                  <p className="mt-0.5 text-[11px] text-gray-400">{note.plugin}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Plugin errors */}
      {pluginRunErrors.length > 0 && (
        <Card className="border-red-100">
          <CardHeader className="pb-3 border-b border-gray-50">
            <CardTitle className="text-sm font-semibold text-red-700 flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-red-100">
                <AlertCircle size={13} />
              </div>
              Plugins that failed
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 space-y-2">
            {pluginRunErrors.map((message, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 rounded-xl border border-red-100 bg-red-50 px-4 py-2.5 text-xs text-red-700"
              >
                <AlertCircle size={13} className="shrink-0 mt-0.5" />
                {message}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Grouped suggestions */}
      {grouped.map(([source, items]) => (
        <section key={source} className="space-y-3">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-bold text-gray-900 capitalize">
              {source.replace(/[_-]+/g, " ")}
            </h2>
            <Badge variant="secondary" className="text-[10px] px-2 py-0.5">
              {items.length}
            </Badge>
            <div className="flex-1 h-px bg-gray-100" />
          </div>
          <div className="grid gap-3">
            {items.map((s) => (
              <SuggestionCard key={s.id} suggestion={s} onUpdate={onUpdate} />
            ))}
          </div>
        </section>
      ))}

      {error && (
        <div className="animate-fade-in flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex justify-between gap-2.5">
        <Button variant="ghost" size="sm" onClick={onBack} className="h-9">
          <ChevronLeft size={14} />
          Back
        </Button>
        <Button
          onClick={onPreview}
          disabled={previewing || suggestions.length === 0}
          size="sm"
          className="h-9 px-6 gap-2"
        >
          {previewing ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <ChevronRight size={14} />
          )}
          {previewing ? "Previewing..." : "Preview Document"}
        </Button>
      </div>
    </div>
  );
}
