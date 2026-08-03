import { useCallback, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { PageContainer } from "@/components/PageContainer";
import { SectionTitle } from "@/components/SectionTitle";
import { EmptyState } from "@/components/EmptyState";
import { useToast } from "@/components/Toast";
import { Button } from "@/components/ui/button";
import {
  analyzeDocument,
  applyDocument,
  getEngineStatus,
  listEnginePlugins,
  previewDocument,
  readErrorDetail,
  suggestDocument,
} from "@/services/documentEngine";
import type {
  AnalyzeResult,
  Note,
  PluginDescription,
  PreviewResult,
  Suggestion,
} from "@/types/documentEngine";
import { StepIndicator } from "./components/StepIndicator";
import { UploadAnalyzeStep } from "./components/UploadAnalyzeStep";
import { MetadataPluginsStep } from "./components/MetadataPluginsStep";
import { SuggestionReviewStep } from "./components/SuggestionReviewStep";
import { PreviewApplyStep } from "./components/PreviewApplyStep";
import { ServerCrash, Sparkles } from "lucide-react";
import axios from "axios";

type Step = 0 | 1 | 2 | 3;

function errorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

const STEPS = [
  { label: "Upload & Analyze" },
  { label: "Metadata & Plugins" },
  { label: "Review Suggestions" },
  { label: "Preview & Apply" },
];

export default function DocumentEnginePage() {
  const { toast } = useToast();
  const [step, setStep] = useState<Step>(0);
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null);
  const [selectedPlugins, setSelectedPlugins] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [pluginRunErrors, setPluginRunErrors] = useState<string[]>([]);
  const [preview, setPreview] = useState<PreviewResult | null>(null);

  const status = useQuery({
    queryKey: ["document-engine", "status"],
    queryFn: getEngineStatus,
    staleTime: 60_000,
  });

  const plugins = useQuery({
    queryKey: ["document-engine", "plugins"],
    queryFn: listEnginePlugins,
    staleTime: 60_000,
  });

  const pluginDescriptions: PluginDescription[] = plugins.data ?? [];

  const analyzeMutation = useMutation({
    mutationFn: (f: File) => analyzeDocument(f),
    onSuccess: (result) => {
      setAnalysis(result);
      setSuggestions([]);
      setNotes([]);
      setPreview(null);
      setStep(1);
      toast({
        type: "success",
        title: "Document analyzed",
        message: `Extracted ${result.metadata.authors.length} author(s) and ${result.sections.length} section(s).`,
      });
    },
    onError: (error) =>
      toast({
        type: "error",
        title: "Analysis failed",
        message: errorMessage(error, "The document could not be analyzed."),
      }),
  });

  const suggestMutation = useMutation({
    mutationFn: (f: File) => suggestDocument(f, selectedPlugins),
    onSuccess: (result) => {
      setSuggestions(result.suggestions);
      setNotes(result.notes);
      setPluginRunErrors(
        result.plugins.filter((p) => p.error).map((p) => `${p.title}: ${p.error}`),
      );
      setPreview(null);
      setStep(2);
      toast({
        type: "success",
        title: "Suggestions ready",
        message: `${result.suggestions.length} suggestion(s) across ${result.plugins.filter((p) => p.suggestions > 0).length} plugin(s).`,
      });
    },
    onError: (error) =>
      toast({
        type: "error",
        title: "Suggestions failed",
        message: errorMessage(error, "The plugins could not be run."),
      }),
  });

  const previewMutation = useMutation({
    mutationFn: (f: File) => previewDocument(f, suggestions),
    onSuccess: (result) => {
      setPreview(result);
      setStep(3);
      toast({
        type: "info",
        title: "Preview generated",
        message: `${result.counts.applied} edit(s) would be applied, ${result.counts.refused} refused.`,
      });
    },
    onError: (error) =>
      toast({
        type: "error",
        title: "Preview failed",
        message: errorMessage(error, "The preview could not be generated."),
      }),
  });

  const applyMutation = useMutation({
    mutationFn: (f: File) => applyDocument(f, suggestions),
    onSuccess: (outcome) => {
      const url = URL.createObjectURL(outcome.blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = outcome.fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);

      const refusedCount = outcome.refused.length;
      toast({
        type: refusedCount > 0 ? "warning" : "success",
        title: "Document downloaded",
        message:
          `${outcome.applied} edit(s) applied` +
          (refusedCount > 0 ? `, ${refusedCount} refused` : "") +
          ` · ${outcome.fileName}`,
      });
    },
    onError: async (error) => {
      const detail = await readErrorDetail(error);
      toast({
        type: "error",
        title: "Apply failed",
        message: detail ?? errorMessage(error, "The document could not be written."),
      });
    },
  });

  const acceptedCount = useMemo(
    () => suggestions.filter((s) => s.status === "accepted").length,
    [suggestions],
  );

  const resetAll = useCallback(() => {
    setFile(null);
    setAnalysis(null);
    setSuggestions([]);
    setNotes([]);
    setPreview(null);
    setSelectedPlugins([]);
    setStep(0);
  }, []);

  const onSelectedPluginsChange = (next: string[]) => {
    setSelectedPlugins(next);
    // A different plugin set means the current suggestions no longer describe
    // it, so they are cleared and the user is asked to re-run.
    setSuggestions([]);
    setPreview(null);
  };

  const moduleMissing =
    axios.isAxiosError(status.error) && status.error.response?.status === 404;
  const engineDisabled = status.data?.available === false;

  return (
    <PageContainer>
      <SectionTitle
        title="Document Engine"
        description="Analyze a .docx manuscript, review machine-suggested edits, and download the edited document with only the changes you accept."
      />

      {status.isLoading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-24 rounded-2xl border border-gray-100 bg-white" />
          <div className="h-72 rounded-2xl border border-gray-100 bg-white" />
        </div>
      ) : moduleMissing ? (
        <EmptyState
          icon={<ServerCrash size={28} strokeWidth={1.5} />}
          title="The Document Engine is not available"
          description="The module is not enabled on the server. The Word to LaTeX converter is unaffected."
        />
      ) : engineDisabled ? (
        <EmptyState
          icon={<ServerCrash size={28} strokeWidth={1.5} />}
          title="The Document Engine is offline"
          description="The server reports the engine is not available right now. Try again later."
        />
      ) : (
        <div className="space-y-8">
          <StepIndicator current={step} steps={STEPS} />

          {step === 0 && (
            <UploadAnalyzeStep
              file={file}
              setFile={(f) => {
                setFile(f);
                setAnalysis(null);
                setSuggestions([]);
                setPreview(null);
              }}
              analyzing={analyzeMutation.isPending}
              error={
                analyzeMutation.isError
                  ? errorMessage(analyzeMutation.error, "Analysis failed.")
                  : null
              }
              onAnalyze={() => file && analyzeMutation.mutate(file)}
            />
          )}

          {step === 1 && analysis && (
            <MetadataPluginsStep
              analysis={analysis}
              plugins={pluginDescriptions}
              selectedPlugins={selectedPlugins}
              onSelectedPluginsChange={onSelectedPluginsChange}
              suggesting={suggestMutation.isPending}
              error={
                suggestMutation.isError
                  ? errorMessage(suggestMutation.error, "Suggestions failed.")
                  : null
              }
              onBack={() => setStep(0)}
              onRun={() => file && suggestMutation.mutate(file)}
            />
          )}

          {step === 2 && (
            <SuggestionReviewStep
              suggestions={suggestions}
              notes={notes}
              pluginRunErrors={pluginRunErrors}
              onUpdate={(id, patch) =>
                setSuggestions((prev) =>
                  prev.map((s) => (s.id === id ? { ...s, ...patch } : s)),
                )
              }
              onBack={() => setStep(1)}
              onPreview={() => file && previewMutation.mutate(file)}
              previewing={previewMutation.isPending}
              error={
                previewMutation.isError
                  ? errorMessage(previewMutation.error, "Preview failed.")
                  : null
              }
            />
          )}

          {step === 3 && (
            <PreviewApplyStep
              suggestions={suggestions}
              preview={preview}
              previewing={previewMutation.isPending}
              applying={applyMutation.isPending}
              error={
                previewMutation.isError
                  ? errorMessage(previewMutation.error, "Preview failed.")
                  : null
              }
              onBack={() => setStep(2)}
              onPreview={() => file && previewMutation.mutate(file)}
              onApply={() => file && applyMutation.mutate(file)}
            />
          )}

          {file && step > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-gray-100 bg-white px-5 py-4 shadow-sm">
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                  <Sparkles size={15} />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-gray-900">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-400">
                    {acceptedCount} of {suggestions.length} suggestion(s) accepted
                    {preview ? ` · preview ready` : ""}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={resetAll}
                className="h-8 text-xs"
              >
                Start over
              </Button>
            </div>
          )}
        </div>
      )}
    </PageContainer>
  );
}
