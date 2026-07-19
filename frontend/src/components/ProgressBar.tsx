import { Progress } from "@/components/ui/progress";
import { cn } from "@/utils/cn";

interface ProgressBarProps {
  value: number;
  className?: string;
}

export function ProgressBar({ value, className }: ProgressBarProps) {
  return (
    <div className={cn("w-full space-y-2", className)}>
      <Progress value={value} />
      <p className="text-right text-xs text-muted-foreground">
        {Math.round(value)}%
      </p>
    </div>
  );
}
