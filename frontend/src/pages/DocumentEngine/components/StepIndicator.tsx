import { cn } from "@/utils/cn";
import { Check } from "lucide-react";

interface StepIndicatorProps {
  current: number;
  steps: Array<{ label: string }>;
}

export function StepIndicator({ current, steps }: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-2" aria-label="Workflow progress">
      {steps.map((step, i) => {
        const isComplete = i < current;
        const isActive = i === current;
        return (
          <div key={step.label} className="flex flex-1 items-center gap-2">
            <div className="flex items-center gap-2.5 min-w-0">
              <div
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-bold transition-all duration-200",
                  isComplete &&
                    "border-emerald-500 bg-emerald-500 text-white shadow-sm shadow-emerald-200",
                  isActive &&
                    "border-emerald-500 bg-white text-emerald-700 ring-2 ring-emerald-100",
                  !isComplete &&
                    !isActive &&
                    "border-gray-200 bg-white text-gray-400",
                )}
                aria-hidden="true"
              >
                {isComplete ? <Check size={14} strokeWidth={3} /> : i + 1}
              </div>
              <span
                className={cn(
                  "hidden text-xs font-semibold sm:block whitespace-nowrap transition-colors",
                  isComplete || isActive ? "text-gray-900" : "text-gray-400",
                )}
              >
                {step.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                className={cn(
                  "h-px flex-1 min-w-4 transition-colors duration-300",
                  i < current ? "bg-emerald-400" : "bg-gray-200",
                )}
                aria-hidden="true"
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
