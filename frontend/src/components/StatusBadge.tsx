import { cn } from "@/utils/cn";
import type { JobStatus } from "@/types";

interface StatusBadgeProps {
  status: JobStatus;
  className?: string;
}

const STATUS_CONFIG: Record<string, { dot: string; bg: string; border: string; text: string; label: string }> = {
  COMPLETED:  { dot: "bg-emerald-500", bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-700", label: "Completed" },
  FAILED:     { dot: "bg-red-500",     bg: "bg-red-50",     border: "border-red-200",     text: "text-red-700",     label: "Failed"    },
  CREATED:    { dot: "bg-gray-400",    bg: "bg-gray-50",    border: "border-gray-200",    text: "text-gray-600",    label: "Created"   },
  COMPILING:  { dot: "bg-blue-500 animate-pulse", bg: "bg-blue-50",  border: "border-blue-200",  text: "text-blue-700",  label: "Compiling" },
  RENDERING_LATEX:      { dot: "bg-violet-500 animate-pulse", bg: "bg-violet-50", border: "border-violet-200", text: "text-violet-700", label: "Rendering" },
  EXTRACTING_ASSETS:    { dot: "bg-amber-500 animate-pulse",  bg: "bg-amber-50",  border: "border-amber-200",  text: "text-amber-700",  label: "Extracting" },
  ANALYZING_DOCUMENT:   { dot: "bg-cyan-500 animate-pulse",   bg: "bg-cyan-50",   border: "border-cyan-200",   text: "text-cyan-700",   label: "Analyzing"  },
  VALIDATING:           { dot: "bg-indigo-500 animate-pulse", bg: "bg-indigo-50", border: "border-indigo-200", text: "text-indigo-700", label: "Validating" },
  LOADING_TEMPLATE:     { dot: "bg-pink-500 animate-pulse",   bg: "bg-pink-50",   border: "border-pink-200",   text: "text-pink-700",   label: "Loading"    },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const cfg = STATUS_CONFIG[status] ?? {
    dot: "bg-gray-400 animate-pulse",
    bg: "bg-gray-50",
    border: "border-gray-200",
    text: "text-gray-600",
    label: status,
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold border tracking-wide",
        cfg.bg, cfg.border, cfg.text,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", cfg.dot)} />
      {cfg.label}
    </span>
  );
}
