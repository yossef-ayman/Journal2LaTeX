import { cn } from "@/utils/cn";

interface SectionTitleProps {
  title: string;
  description?: string;
  className?: string;
}

export function SectionTitle({
  title,
  description,
  className,
}: SectionTitleProps) {
  return (
    <div className={cn("space-y-1 mb-6", className)}>
      <h2 className="text-xl font-bold tracking-tight text-zinc-900">
        {title}
      </h2>
      {description && (
        <p className="text-xs text-zinc-500">{description}</p>
      )}
    </div>
  );
}
