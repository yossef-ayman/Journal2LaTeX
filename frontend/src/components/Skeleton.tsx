import { cn } from "@/utils/cn";

interface SkeletonLineProps {
  className?: string;
  width?: string;
}

export function SkeletonLine({ className, width = "100%" }: SkeletonLineProps) {
  return (
    <div
      className={cn("h-3.5 rounded-lg skeleton-shimmer", className)}
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
    <div className={cn("rounded-2xl border border-gray-100 bg-white p-6 space-y-4 shadow-sm", className)}>
      <SkeletonLine width="35%" className="h-5" />
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonLine
          key={i}
          width={i === lines - 1 ? "55%" : i % 3 === 0 ? "85%" : "100%"}
        />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-gray-50 px-5 py-3.5">
        <SkeletonLine width="25%" className="h-4" />
      </div>
      <div className="divide-y divide-gray-50">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-5 px-5 py-4">
            <div className="h-8 w-8 rounded-lg skeleton-shimmer shrink-0" />
            <SkeletonLine width="30%" />
            <SkeletonLine width="18%" />
            <SkeletonLine width="14%" />
            <SkeletonLine width="10%" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonBadge({ className }: { className?: string }) {
  return (
    <div className={cn("h-6 w-20 rounded-full skeleton-shimmer", className)} />
  );
}
