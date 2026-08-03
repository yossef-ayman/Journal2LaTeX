import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Loader2,
  AlertCircle,
  Sparkles,
  ChevronLeft,
  Users,
  LayoutList,
  List,
  Images,
  Table2,
  Sigma,
  Mail,
  MapPin,
  FileText,
  Tag,
  Info,
  ShieldAlert,
} from "lucide-react";
import { cn } from "@/utils/cn";
import type {
  AnalyzeResult,
  PluginDescription,
  SectionNode,
} from "@/types/documentEngine";

const STATS = [
  {
    key: "authors" as const,
    icon: Users,
    label: "Authors",
    color: "from-blue-500 to-cyan-500",
    bg: "bg-blue-50 text-blue-600",
  },
  {
    key: "sections" as const,
    icon: LayoutList,
    label: "Sections",
    color: "from-violet-500 to-purple-500",
    bg: "bg-violet-50 text-violet-600",
  },
  {
    key: "references" as const,
    icon: List,
    label: "References",
    color: "from-amber-500 to-orange-500",
    bg: "bg-amber-50 text-amber-600",
  },
  {
    key: "figures" as const,
    icon: Images,
    label: "Figures",
    color: "from-pink-500 to-rose-500",
    bg: "bg-pink-50 text-pink-600",
  },
  {
    key: "tables" as const,
    icon: Table2,
    label: "Tables",
    color: "from-teal-500 to-emerald-500",
    bg: "bg-teal-50 text-teal-600",
  },
  {
    key: "equations" as const,
    icon: Sigma,
    label: "Equations",
    color: "from-indigo-500 to-blue-500",
    bg: "bg-indigo-50 text-indigo-600",
  },
];

function sectionText(section: SectionNode): string {
  return section.content
    .map((block) => (block.item && block.item.text ? block.item.text : ""))
    .filter(Boolean)
    .join("\n");
}

function ConfidencePill({ confidence }: { confidence: number }) {
  const tone =
    confidence >= 0.8
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : confidence >= 0.5
        ? "bg-amber-50 text-amber-700 border-amber-200"
        : "bg-red-50 text-red-700 border-red-200";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold",
        tone,
      )}
      title={`Extraction confidence: ${confidence}`}
    >
      {Math.round(confidence * 100)}%
    </span>
  );
}

function Field({
  icon: Icon,
  label,
  children,
}: {
  icon: React.ElementType;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
        <Icon size={12} />
        {label}
      </div>
      <div className="text-sm text-gray-800 leading-relaxed">{children}</div>
    </div>
  );
}

interface MetadataPluginsStepProps {
  analysis: AnalyzeResult;
  plugins: PluginDescription[];
  selectedPlugins: string[];
  onSelectedPluginsChange: (next: string[]) => void;
  suggesting: boolean;
  error: string | null;
  onBack: () => void;
  onRun: () => void;
}

export function MetadataPluginsStep({
  analysis,
  plugins,
  selectedPlugins,
  onSelectedPluginsChange,
  suggesting,
  error,
  onBack,
  onRun,
}: MetadataPluginsStepProps) {
  const meta = analysis.metadata;

  const stats = useMemo(
    () =>
      STATS.map((s) => ({
        ...s,
        value:
          s.key === "authors"
            ? meta.authors.length
            : s.key === "sections"
              ? analysis.sections.length
              : s.key === "references"
                ? analysis.references.length
                : s.key === "figures"
                  ? analysis.figures.length
                  : s.key === "tables"
                    ? analysis.tables.length
                    : analysis.equations.length,
      })),
    [analysis, meta],
  );

  const togglePlugin = (name: string) => {
    const next = selectedPlugins.includes(name)
      ? selectedPlugins.filter((n) => n !== name)
      : [...selectedPlugins, name];
    onSelectedPluginsChange(next);
  };

  return (
    <div className="space-y-6">
      {/* Extracted metadata */}
      <Card>
        <CardHeader className="pb-4 border-b border-gray-50">
          <CardTitle className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-blue-100">
              <FileText size={13} className="text-blue-700" />
            </div>
            Extracted Metadata
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6 pt-5">
          {/* Stats row */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {stats.map((s) => (
              <div
                key={s.key}
                className="flex flex-col items-center gap-2 rounded-2xl border border-gray-100 bg-white p-4 text-center shadow-sm"
              >
                <div
                  className={cn(
                    "flex h-9 w-9 items-center justify-center rounded-xl",
                    s.bg,
                  )}
                >
                  <s.icon size={16} />
                </div>
                <div>
                  <p className="text-xl font-bold text-gray-900 leading-none">
                    {s.value}
                  </p>
                  <p className="mt-1 text-[11px] text-gray-400">{s.label}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Title / subtitle */}
          {(meta.title || meta.subtitle) && (
            <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 space-y-4">
              {meta.title && (
                <Field icon={FileText} label="Title">
                  <span className="font-semibold">
                    {meta.title.text}
                    <ConfidencePill confidence={meta.title.confidence} />
                  </span>
                </Field>
              )}
              {meta.subtitle && (
                <Field icon={FileText} label="Subtitle">
                  {meta.subtitle.text}
                  <ConfidencePill confidence={meta.subtitle.confidence} />
                </Field>
              )}
            </div>
          )}

          {/* Authors */}
          {meta.authors.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                <Users size={12} />
                Authors
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {meta.authors.map((author) => (
                  <div
                    key={author.id}
                    className="flex items-start justify-between gap-3 rounded-xl border border-gray-100 bg-white p-3.5"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900 truncate">
                        {author.name}
                        {author.is_corresponding && (
                          <span
                            className="ml-2 text-[10px] font-bold text-blue-600"
                            title="Corresponding author"
                          >
                            CORR
                          </span>
                        )}
                      </p>
                      {author.email && (
                        <p className="mt-0.5 flex items-center gap-1 text-xs text-gray-500 truncate">
                          <Mail size={11} />
                          {author.email}
                        </p>
                      )}
                    </div>
                    <ConfidencePill confidence={author.confidence} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Affiliations */}
          {meta.affiliations.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                <MapPin size={12} />
                Affiliations
              </div>
              {meta.affiliations.map((a) => (
                <div
                  key={a.id}
                  className="flex items-start gap-2 rounded-xl border border-gray-100 bg-white p-3.5 text-sm text-gray-700"
                >
                  <span className="shrink-0 font-mono text-xs font-bold text-emerald-600 bg-emerald-50 rounded px-1.5 py-0.5">
                    {a.marker || "•"}
                  </span>
                  <span className="min-w-0 flex-1">{a.text}</span>
                  <ConfidencePill confidence={a.confidence} />
                </div>
              ))}
            </div>
          )}

          {/* Abstract */}
          {meta.abstract && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                <FileText size={12} />
                Abstract
              </div>
              <div className="rounded-xl border border-gray-100 bg-white p-4 text-sm text-gray-800 leading-relaxed">
                {sectionText(meta.abstract) || (
                  <span className="text-gray-400 italic">No paragraph text.</span>
                )}
              </div>
            </div>
          )}

          {/* Keywords */}
          {meta.keywords.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                <Tag size={12} />
                Keywords
              </div>
              <div className="flex flex-wrap gap-2">
                {meta.keywords.map((k, i) => (
                  <span
                    key={`${k}-${i}`}
                    className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700"
                  >
                    {k}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* DOI / dates */}
          {(meta.doi || meta.received || meta.accepted || meta.published) && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {meta.doi && (
                <Field icon={FileText} label="DOI">
                  <span className="font-mono text-xs">{meta.doi}</span>
                </Field>
              )}
              {meta.received && (
                <Field icon={Info} label="Received">
                  {meta.received}
                </Field>
              )}
              {meta.accepted && (
                <Field icon={Info} label="Accepted">
                  {meta.accepted}
                </Field>
              )}
              {meta.published && (
                <Field icon={Info} label="Published">
                  {meta.published}
                </Field>
              )}
            </div>
          )}

          {/* Warnings */}
          {analysis.warnings.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-amber-600">
                <ShieldAlert size={12} />
                Extraction warnings
              </div>
              {analysis.warnings.map((w, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-800"
                >
                  <AlertCircle size={13} className="shrink-0 mt-0.5" />
                  {w}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Plugin selection */}
      <Card>
        <CardHeader className="pb-4 border-b border-gray-50">
          <CardTitle className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-violet-100">
              <Sparkles size={13} className="text-violet-700" />
            </div>
            Suggestion Plugins
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-5 space-y-4">
          <p className="text-xs text-gray-500 leading-relaxed">
            Select which checks to run against the manuscript. Unchecked plugins
            are skipped entirely; an empty selection runs every plugin that is on
            by default. Suggestions are proposals only — nothing changes until you
            accept an edit and download the result.
          </p>

          {plugins.length === 0 ? (
            <p className="text-sm text-gray-400 italic">
              No plugins reported by the server.
            </p>
          ) : (
            <div className="grid gap-2.5 sm:grid-cols-2">
              {plugins.map((plugin) => {
                const selected = selectedPlugins.includes(plugin.name);
                return (
                  <button
                    key={plugin.name}
                    type="button"
                    role="checkbox"
                    aria-checked={selected}
                    onClick={() => togglePlugin(plugin.name)}
                    className={cn(
                      "flex items-start gap-3 rounded-xl border p-3.5 text-left transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500",
                      selected
                        ? "border-emerald-300 bg-emerald-50/60"
                        : "border-gray-100 bg-white hover:border-emerald-200 hover:bg-emerald-50/30",
                    )}
                  >
                    <div
                      className={cn(
                        "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors",
                        selected
                          ? "border-emerald-500 bg-emerald-500"
                          : "border-gray-300 bg-white",
                      )}
                    >
                      {selected && (
                        <svg
                          width="10"
                          height="10"
                          viewBox="0 0 10 10"
                          fill="none"
                          className="text-white"
                        >
                          <path
                            d="M1 5.5L3.5 8L9 2"
                            stroke="currentColor"
                            strokeWidth="1.8"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900">
                        {plugin.title}
                      </p>
                      <p className="mt-0.5 text-xs text-gray-500 leading-relaxed">
                        {plugin.description || "No description."}
                      </p>
                      <p className="mt-1 text-[10px] text-gray-400">
                        {plugin.enabled_by_default ? "On by default" : "Opt-in"}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {error && (
            <div className="animate-fade-in flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle size={16} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex justify-between gap-2.5 pt-2 border-t border-gray-100">
            <Button variant="ghost" size="sm" onClick={onBack} className="h-9">
              <ChevronLeft size={14} />
              Back
            </Button>
            <Button
              onClick={onRun}
              disabled={suggesting}
              size="sm"
              className="h-9 px-6 gap-2"
            >
              {suggesting ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Sparkles size={14} />
              )}
              {suggesting ? "Running..." : "Generate Suggestions"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {meta.authors.length === 0 &&
        !meta.title &&
        !meta.abstract &&
        analysis.sections.length === 0 && (
          <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <Info size={16} className="shrink-0 mt-0.5" />
            <span>
              Very little was recognized in this document. It may not be a
              research manuscript, or its structure may be unusual. Suggestions
              will still run, but results will be limited.
            </span>
          </div>
        )}
    </div>
  );
}
