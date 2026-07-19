import { cn } from "@/utils/cn";

interface SkeletonLineProps {
  className?: string;
  width?: string;
}

export function SkeletonLine({ className, width = "100%" }: SkeletonLineProps) {
  return (
    <div
      className={cn("h-4 animate-pulse rounded-md bg-muted", className)}
      style={{ width }}
    />
  );
}

interface SkeletonCardProps {
  className?: string;
  lines?: number;
}

export function SkeletonCard({ className, lines = 4 }: SkeletonCardProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-5 space-y-3", className)}>
      <SkeletonLine width="40%" />
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonLine key={i} width={i === lines - 1 ? "60%" : "100%"} />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="rounded-lg border bg-card">
      <div className="border-b px-4 py-3">
        <SkeletonLine width="30%" />
      </div>
      <div className="divide-y">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3">
            <SkeletonLine width="35%" />
            <SkeletonLine width="20%" />
            <SkeletonLine width="15%" />
            <SkeletonLine width="15%" />
            <SkeletonLine width="8%" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonBadge({ className }: { className?: string }) {
  return (
    <div className={cn("h-5 w-16 animate-pulse rounded-full bg-muted", className)} />
  );
}
