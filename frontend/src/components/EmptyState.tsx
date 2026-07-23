import type { ReactNode } from "react";
import { cn } from "@/utils/cn";
import { Inbox } from "lucide-react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-zinc-200 bg-white px-6 py-12 text-center",
        className,
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-zinc-100 text-zinc-400">
        {icon ?? <Inbox size={22} />}
      </div>
      <div className="space-y-1">
        <h3 className="text-xs font-semibold text-zinc-900">{title}</h3>
        {description && (
          <p className="text-xs text-zinc-500 max-w-sm leading-relaxed">
            {description}
          </p>
        )}
      </div>
      {action && <div className="pt-1">{action}</div>}
    </div>
  );
}
