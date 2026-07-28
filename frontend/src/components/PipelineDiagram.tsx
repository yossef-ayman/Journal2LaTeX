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
  color: string;
}

const stages: Stage[] = [
  { key: "UPLOAD", label: "Upload", activeLabel: "Uploading manuscript", completedLabel: "Upload completed", icon: <Upload size={14} />, color: "from-emerald-400 to-emerald-500" },
  { key: "VALIDATING", label: "Parsing", activeLabel: "Parsing document structure", completedLabel: "Document parsed", icon: <FileSearch size={14} />, color: "from-teal-400 to-teal-500" },
  { key: "ANALYZING_DOCUMENT", label: "Analysis", activeLabel: "Analyzing sections & metadata", completedLabel: "Document analyzed", icon: <FileText size={14} />, color: "from-cyan-400 to-cyan-500" },
  { key: "EXTRACTING_ASSETS", label: "Figures & Tables", activeLabel: "Extracting figures & tables", completedLabel: "Assets extracted", icon: <Image size={14} />, color: "from-blue-400 to-blue-500" },
  { key: "LOADING_TEMPLATE", label: "Template", activeLabel: "Loading target LaTeX template", completedLabel: "Template loaded", icon: <LayoutTemplate size={14} />, color: "from-violet-400 to-violet-500" },
  { key: "RENDERING_LATEX", label: "LaTeX Generation", activeLabel: "Generating LaTeX source code", completedLabel: "LaTeX generated", icon: <Code size={14} />, color: "from-purple-400 to-purple-500" },
  { key: "COMPILING", label: "Compilation", activeLabel: "Compiling PDF via TeX engine", completedLabel: "PDF compiled", icon: <FileDown size={14} />, color: "from-pink-400 to-pink-500" },
  { key: "COMPLETED", label: "Finished", activeLabel: "Finalizing & verifying output", completedLabel: "All done!", icon: <ShieldCheck size={14} />, color: "from-emerald-500 to-emerald-600" },
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
  const displayProgress = isCompleted ? 100 : progress;

  return (
    <div className={cn("space-y-5", className)}>
      {/* Step list */}
      <div className="space-y-1" role="list" aria-label="Conversion pipeline stages">
        {stages.map((stage, i) => {
          const isPast = i < activeIdx || isCompleted;
          const isCurrent = i === activeIdx && !isCompleted && !isFailed;
          const isFailedStage = isFailed && i === activeIdx;
          return (
            <div key={stage.key} className="flex items-start gap-3" role="listitem">
              {/* Left: dot + connector */}
              <div className="flex flex-col items-center shrink-0 pt-0.5">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-xl transition-all duration-300",
                    isPast
                      ? `bg-gradient-to-br ${stage.color} text-white shadow-sm`
                      : isCurrent
                        ? "bg-emerald-600 text-white shadow-md shadow-emerald-200 animate-pulse-soft"
                        : isFailedStage
                          ? "bg-red-100 text-red-600 border border-red-200"
                          : "bg-gray-100 text-gray-400 border border-gray-200",
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
                {/* Vertical connector */}
                {i < stages.length - 1 && (
                  <div
                    className={cn(
                      "mt-1 w-0.5 flex-1 min-h-[20px] rounded-full transition-colors duration-300",
                      isPast ? "bg-emerald-200" : "bg-gray-100",
                    )}
                  />
                )}
              </div>

              {/* Right: text */}
              <div className={cn("pb-5 pt-1 min-w-0 flex-1", i === stages.length - 1 && "pb-0")}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={cn(
                      "text-sm font-semibold transition-colors duration-200",
                      isPast ? "text-emerald-700" : isCurrent ? "text-gray-900" : isFailedStage ? "text-red-600" : "text-gray-400",
                    )}
                  >
                    {isPast
                      ? stage.completedLabel
                      : isCurrent
                        ? stage.activeLabel
                        : stage.label}
                  </span>
                  {isCurrent && (
                    <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                      In progress
                    </span>
                  )}
                  {isFailedStage && (
                    <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-600">
                      Failed
                    </span>
                  )}
                </div>
                {isCurrent && (
                  <span className="text-xs text-gray-400 mt-1 block animate-fade-in">
                    {displayProgress}% complete
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
