import * as React from "react";
import { cn } from "@/utils/cn";

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  variant?: "default" | "success" | "warning" | "error";
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value = 0, variant = "default", ...props }, ref) => {
    const trackColors = {
      default: "bg-emerald-100",
      success: "bg-emerald-100",
      warning: "bg-amber-100",
      error: "bg-red-100",
    };
    const barColors = {
      default: "bg-gradient-to-r from-emerald-500 to-emerald-400",
      success: "bg-gradient-to-r from-emerald-600 to-emerald-400",
      warning: "bg-gradient-to-r from-amber-500 to-amber-400",
      error: "bg-gradient-to-r from-red-500 to-red-400",
    };
    const safeValue = Math.min(100, Math.max(0, value));
    return (
      <div
        ref={ref}
        role="progressbar"
        aria-valuenow={safeValue}
        aria-valuemin={0}
        aria-valuemax={100}
        className={cn(
          "relative h-2 w-full overflow-hidden rounded-full",
          trackColors[variant],
          className,
        )}
        {...props}
      >
        <div
          className={cn("h-full transition-all duration-700 ease-out rounded-full", barColors[variant])}
          style={{ width: `${safeValue}%` }}
        />
      </div>
    );
  },
);
Progress.displayName = "Progress";

export { Progress };
