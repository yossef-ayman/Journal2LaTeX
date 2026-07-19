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
    <div className={cn("space-y-1", className)}>
      <h2 className="text-2xl font-semibold tracking-tight text-foreground">
        {title}
      </h2>
      {description && (
        <p className="text-sm text-muted-foreground">{description}</p>
      )}
    </div>
  );
}
