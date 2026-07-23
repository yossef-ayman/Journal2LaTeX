import { cn } from "@/utils/cn";
import type { JobStatus } from "@/types";

interface StatusBadgeProps {
  status: JobStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const isCompleted = status === "COMPLETED";
  const isFailed = status === "FAILED";
  const isPending = !isCompleted && !isFailed && status !== "CREATED";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors",
        isCompleted && "border-emerald-200 bg-emerald-50 text-emerald-700",
        isFailed && "border-red-200 bg-red-50 text-red-700",
        isPending && "border-blue-200 bg-blue-50 text-blue-700",
        status === "CREATED" && "border-zinc-200 bg-zinc-100 text-zinc-600",
        className,
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          isCompleted && "bg-emerald-500",
          isFailed && "bg-red-500",
          isPending && "bg-blue-500 animate-pulse",
          status === "CREATED" && "bg-zinc-400",
        )}
      />
      {status}
    </span>
  );
}

