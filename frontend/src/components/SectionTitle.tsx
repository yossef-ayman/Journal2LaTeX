import { cn } from "@/utils/cn";

interface SectionTitleProps {
  title: string;
  description?: string;
  className?: string;
  action?: React.ReactNode;
}

export function SectionTitle({
  title,
  description,
  className,
  action,
}: SectionTitleProps) {
  return (
    <div className={cn("flex items-start justify-between gap-4 mb-6", className)}>
      <div className="space-y-1">
        <h2 className="text-2xl font-bold tracking-tight text-gray-900 leading-tight">
          {title}
        </h2>
        {description && (
          <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
