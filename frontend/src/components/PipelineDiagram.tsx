import { cn } from "@/utils/cn";
import type { JobStatus } from "@/types";
import {
  Upload,
  FileSearch,
  FileText,
  Image,
  LayoutTemplate,
  Code,
  FileDown,
  ShieldCheck,
  CheckCircle,
  Loader2,
  XCircle,
} from "lucide-react";

interface Stage {
  key: string;
  label: string;
  activeLabel: string;
  completedLabel: string;
  icon: React.ReactNode;
}

const stages: Stage[] = [
  { key: "UPLOAD", label: "Upload", activeLabel: "Uploading manuscript", completedLabel: "✓ Upload completed", icon: <Upload size={15} /> },
  { key: "VALIDATING", label: "Parsing", activeLabel: "Parsing document structure", completedLabel: "✓ Parsing document", icon: <FileSearch size={15} /> },
  { key: "ANALYZING_DOCUMENT", label: "Analysis", activeLabel: "Analyzing sections & metadata", completedLabel: "✓ Document analysis", icon: <FileText size={15} /> },
  { key: "EXTRACTING_ASSETS", label: "Figures & Tables", activeLabel: "Extracting figures & tables", completedLabel: "✓ Extracting figures & tables", icon: <Image size={15} /> },
  { key: "LOADING_TEMPLATE", label: "Template", activeLabel: "Loading target LaTeX template", completedLabel: "✓ Template loaded", icon: <LayoutTemplate size={15} /> },
  { key: "RENDERING_LATEX", label: "LaTeX Generation", activeLabel: "Generating LaTeX source code", completedLabel: "✓ Generating LaTeX", icon: <Code size={15} /> },
  { key: "COMPILING", label: "Compilation", activeLabel: "Compiling PDF via TeX engine", completedLabel: "✓ Compiling PDF", icon: <FileDown size={15} /> },
  { key: "COMPLETED", label: "Finished", activeLabel: "Finalizing & verifying output", completedLabel: "✓ Finished", icon: <ShieldCheck size={15} /> },
];

const stageOrder = stages.map((s) => s.key);

function getActiveIndex(status: JobStatus): number {
  const idx = stageOrder.indexOf(status);
  if (idx >= 0) return idx;
  if (status === "CREATED") return 0;
  if (status === "FAILED") return stageOrder.length - 1;
  return -1;
}

interface PipelineDiagramProps {
  status: JobStatus;
  progress: number;
  className?: string;
}

export function PipelineDiagram({ status, progress, className }: PipelineDiagramProps) {
  const activeIdx = getActiveIndex(status);
  const isFailed = status === "FAILED";
  const isCompleted = status === "COMPLETED";

  return (
    <div className={cn("space-y-6", className)}>
      {/* Modern Top Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold text-zinc-700">
          <span>Overall Conversion Progress</span>
          <span className="font-mono text-zinc-900">{isCompleted ? 100 : progress}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-100 border border-zinc-200/60">
          <div
            className={cn(
              "h-full transition-all duration-500 ease-out rounded-full",
              isCompleted ? "bg-emerald-500" : isFailed ? "bg-red-500" : "bg-zinc-900"
            )}
            style={{ width: `${isCompleted ? 100 : progress}%` }}
          />
        </div>
      </div>

      {/* Step checklist */}
      <div className="space-y-0" role="list" aria-label="Conversion pipeline stages">
        {stages.map((stage, i) => {
          const isPast = i < activeIdx || (isCompleted && i <= stages.length - 1);
          const isCurrent = i === activeIdx && !isCompleted && !isFailed;
          const isFailedStage = isFailed && i === activeIdx;

          return (
            <div key={stage.key} className="flex items-start gap-3.5" role="listitem">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full border text-xs transition-all duration-300",
                    isPast
                      ? "border-emerald-200 bg-emerald-50 text-emerald-600"
                      : isCurrent
                        ? "border-zinc-900 bg-zinc-900 text-white shadow-xs animate-pulse-soft"
                        : isFailedStage
                          ? "border-red-200 bg-red-50 text-red-600"
                          : "border-zinc-200 bg-zinc-50 text-zinc-400",
                  )}
                  aria-current={isCurrent ? "step" : undefined}
                >
                  {isPast ? (
                    <CheckCircle size={14} className="animate-scale-in" />
                  ) : isCurrent ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : isFailedStage ? (
                    <XCircle size={14} />
                  ) : (
                    stage.icon
                  )}
                </div>
                {i < stages.length - 1 && (
                  <div
                    className={cn(
                      "h-7 w-0.5 transition-colors duration-300",
                      isPast ? "bg-emerald-300" : "bg-zinc-200",
                    )}
                  />
                )}
              </div>
              <div className="flex flex-col justify-center pb-4 pt-1 min-w-0">
                <span
                  className={cn(
                    "text-xs font-semibold transition-colors flex items-center gap-2",
                    isPast
                      ? "text-emerald-700"
                      : isCurrent
                        ? "text-zinc-900"
                        : isFailedStage
                          ? "text-red-600"
                          : "text-zinc-400",
                  )}
                >
                  {isPast ? stage.completedLabel : isCurrent ? stage.activeLabel : stage.label}
                  {isCurrent && (
                    <span className="inline-flex items-center rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-mono text-zinc-600">
                      In progress
                    </span>
                  )}
                </span>
                {isCurrent && (
                  <span className="text-[11px] text-zinc-500 mt-0.5 animate-fade-in">
                    Processing step ({progress}% complete)
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
