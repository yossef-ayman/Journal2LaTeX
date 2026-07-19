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
  icon: React.ReactNode;
}

const stages: Stage[] = [
  { key: "UPLOAD", label: "Upload", icon: <Upload size={16} /> },
  { key: "VALIDATING", label: "Validation", icon: <FileSearch size={16} /> },
  { key: "ANALYZING_DOCUMENT", label: "Document Analysis", icon: <FileText size={16} /> },
  { key: "EXTRACTING_ASSETS", label: "Asset Extraction", icon: <Image size={16} /> },
  { key: "LOADING_TEMPLATE", label: "Template Loading", icon: <LayoutTemplate size={16} /> },
  { key: "RENDERING_LATEX", label: "LaTeX Rendering", icon: <Code size={16} /> },
  { key: "COMPILING", label: "Compilation", icon: <FileDown size={16} /> },
  { key: "COMPLETED", label: "Fidelity Check", icon: <ShieldCheck size={16} /> },
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
    <div className={cn("space-y-0", className)} role="list" aria-label="Conversion pipeline stages">
      {stages.map((stage, i) => {
        const isPast = i < activeIdx || (isCompleted && i < stages.length - 1);
        const isCurrent = i === activeIdx && !isCompleted && !isFailed;
        const isFailedStage = isFailed && i === activeIdx;
        const isPending = !isPast && !isCurrent && !isFailedStage;

        return (
          <div key={stage.key} className="flex items-start gap-4" role="listitem">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all duration-500",
                  isPast
                    ? "border-emerald-500 bg-emerald-50 text-emerald-600 shadow-sm"
                    : isCurrent
                      ? "border-primary bg-primary/10 text-primary shadow-sm animate-pulse-soft"
                      : isFailedStage
                        ? "border-destructive bg-destructive/10 text-destructive shadow-sm"
                        : "border-muted-foreground/20 bg-muted text-muted-foreground/50",
                )}
                aria-current={isCurrent ? "step" : undefined}
              >
                {isPast ? (
                  <CheckCircle size={18} className="animate-scale-in" />
                ) : isCurrent ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : isFailedStage ? (
                  <XCircle size={18} />
                ) : (
                  stage.icon
                )}
              </div>
              {i < stages.length - 1 && (
                <div
                  className={cn(
                    "h-10 w-0.5 transition-colors duration-500",
                    isPast ? "bg-emerald-300" : isPending ? "bg-border" : "bg-border",
                  )}
                />
              )}
            </div>
            <div className="flex flex-col justify-center pb-6 pt-1.5 min-w-0">
              <span
                className={cn(
                  "text-sm font-medium transition-colors",
                  isPast
                    ? "text-emerald-700"
                    : isCurrent
                      ? "text-primary"
                      : isFailedStage
                        ? "text-destructive"
                        : "text-muted-foreground",
                )}
              >
                {stage.label}
              </span>
              {isCurrent && (
                <span className="text-xs text-muted-foreground animate-fade-in">
                  {progress}% complete
                </span>
              )}
              {isPast && i === activeIdx - 1 && (
                <span className="text-xs text-emerald-600 animate-fade-in">Complete</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
