import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { WordDiff } from "./WordDiff";
import {
  Eye,
  Download,
  Loader2,
  AlertCircle,
  ChevronLeft,
  CheckCheck,
  CircleX,
  FileBox,
  CheckCircle2,
  Layers,
  Sparkles,
} from "lucide-react";
import { cn } from "@/utils/cn";
import type { PreviewResult, Suggestion } from "@/types/documentEngine";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface PreviewApplyStepProps {
  suggestions: Suggestion[];
  preview: PreviewResult | null;
  previewing: boolean;
  applying: boolean;
  error: string | null;
  onBack: () => void;
  onPreview: () => void;
  onApply: () => void;
}

export function PreviewApplyStep({
  suggestions,
  preview,
  previewing,
  applying,
  error,
  onBack,
  onPreview,
  onApply,
}: PreviewApplyStepProps) {
  const accepted = useMemo(
    () => suggestions.filter((s) => s.status === "accepted"),
    [suggestions],
  );

  if (!preview) {
    return (
      <div className="space-y-5">
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-4 py-16 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-50 to-emerald-100 text-emerald-500">
              <Eye size={24} />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-gray-900">
                Preview before you write
              </h3>
              <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
                Generate a report of exactly what accepting {accepted.length}{" "}
                accepted suggestion(s) would do — every applied edit, every
                refusal, and which parts of the file would change. Nothing is
                written until you download.
              </p>
            </div>
            {error && (
              <div className="animate-fade-in flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <AlertCircle size={16} className="shrink-0" />
                <span>{error}</span>
              </div>
            )}
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={onBack} className="gap-1.5">
                <ChevronLeft size={14} />
                Back
              </Button>
              <Button
                onClick={onPreview}
                disabled={previewing || accepted.length === 0}
                size="sm"
                className="gap-2"
              >
                {previewing ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Eye size={14} />
                )}
                {previewing ? "Generating preview..." : "Generate Preview"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { counts, package: pkg } = preview;
  const totalDelta = preview.impact.reduce((sum, p) => sum + p.delta, 0);

  return (
    <div className="space-y-6">
      {/* Outcome summary */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-emerald-100 bg-gradient-to-br from-emerald-50 to-white p-4">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-emerald-600">
            <CheckCircle2 size={13} />
            Applied
          </div>
          <p className="mt-2 text-2xl font-bold text-gray-900">{counts.applied}</p>
          <p className="text-xs text-gray-500">edits written</p>
        </div>
        <div
          className={cn(
            "rounded-2xl border p-4",
            counts.refused > 0
              ? "border-red-100 bg-red-50/40"
              : "border-gray-100 bg-white",
          )}
        >
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-red-500">
            <CircleX size={13} />
            Refused
          </div>
          <p className="mt-2 text-2xl font-bold text-gray-900">{counts.refused}</p>
          <p className="text-xs text-gray-500">
            {counts.refused === 0
              ? "nothing refused"
              : "edits that could not be applied safely"}
          </p>
        </div>
        <div className="rounded-2xl border border-gray-100 bg-white p-4">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-gray-500">
            <Layers size={13} />
            Package
          </div>
          <p className="mt-2 text-2xl font-bold text-gray-900">{pkg.parts_rewritten}</p>
          <p className="text-xs text-gray-500">
            of {pkg.parts_total} parts rewritten ({totalDelta >= 0 ? "+" : ""}
            {formatBytes(totalDelta)})
          </p>
        </div>
      </div>

      {/* Refusals */}
      {preview.refused.length > 0 && (
        <Card className="border-red-100">
          <CardHeader className="pb-3 border-b border-gray-50">
            <CardTitle className="text-sm font-semibold text-red-700 flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-red-100">
                <CircleX size={13} />
              </div>
              Refused edits
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 space-y-2">
            {preview.refused.map((refusal, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700"
              >
                <AlertCircle size={14} className="shrink-0 mt-0.5" />
                <div>
                  <p className="leading-relaxed">{refusal.reason}</p>
                  <p className="mt-0.5 font-mono text-[11px] text-red-500">
                    {refusal.suggestion_id} · {refusal.node_id}
                  </p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Applied edits */}
      {preview.applied.length > 0 && (
        <Card>
          <CardHeader className="pb-3 border-b border-gray-50">
            <CardTitle className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-100">
                <CheckCheck size={13} className="text-emerald-700" />
              </div>
              Applied edits
              <Badge variant="secondary" className="text-[10px] px-2 py-0.5">
                {preview.applied.length}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 space-y-3">
            {preview.applied.map((edit) => (
              <div
                key={edit.suggestion_id}
                className="rounded-xl border border-gray-100 bg-gray-50/40 p-3.5"
              >
                <div className="mb-2 flex items-center justify-between gap-3">
                  <p className="text-xs text-gray-400 font-mono">
                    {edit.part} · span {edit.span[0]}–{edit.span[1]}
                  </p>
                  <Badge variant="success" className="text-[10px] px-2 py-0.5">
                    +{edit.diff.words_added} −{edit.diff.words_removed}
                  </Badge>
                </div>
                <WordDiff
                  original={edit.original}
                  suggested={edit.replacement}
                />
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Impact detail */}
      {preview.impact.length > 0 && (
        <Card>
          <CardHeader className="pb-3 border-b border-gray-50">
            <CardTitle className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-blue-100">
                <FileBox size={13} className="text-blue-700" />
              </div>
              Parts that would change
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wider text-gray-400 border-b border-gray-100">
                    <th className="pb-2 pr-4 font-semibold">Part</th>
                    <th className="pb-2 pr-4 font-semibold text-right">Before</th>
                    <th className="pb-2 pr-4 font-semibold text-right">After</th>
                    <th className="pb-2 font-semibold text-right">Delta</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {preview.impact.map((part) => (
                    <tr key={part.name}>
                      <td className="py-2 pr-4 font-mono text-xs text-gray-700">
                        {part.name}
                      </td>
                      <td className="py-2 pr-4 text-right font-mono text-xs text-gray-500">
                        {formatBytes(part.original_bytes)}
                      </td>
                      <td className="py-2 pr-4 text-right font-mono text-xs text-gray-500">
                        {formatBytes(part.new_bytes)}
                      </td>
                      <td
                        className={cn(
                          "py-2 text-right font-mono text-xs font-semibold",
                          part.delta > 0
                            ? "text-emerald-600"
                            : part.delta < 0
                              ? "text-red-500"
                              : "text-gray-400",
                        )}
                      >
                        {part.delta > 0 ? "+" : ""}
                        {formatBytes(part.delta)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {error && (
        <div className="animate-fade-in flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gray-100 bg-white px-5 py-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
            <Sparkles size={15} />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">
              {counts.applied} edit(s) ready to write
            </p>
            <p className="text-xs text-gray-500">
              The original file is never modified — you download a new copy.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={onBack} className="h-9 gap-1.5">
            <ChevronLeft size={14} />
            Back
          </Button>
          <Button variant="outline" size="sm" onClick={onPreview} disabled={previewing} className="h-9 gap-1.5">
            {previewing ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Eye size={14} />
            )}
            Re-preview
          </Button>
          <Button onClick={onApply} disabled={applying} size="sm" className="h-9 px-6 gap-2">
            {applying ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Download size={14} />
            )}
            {applying ? "Writing..." : "Apply & Download"}
          </Button>
        </div>
      </div>
    </div>
  );
}
