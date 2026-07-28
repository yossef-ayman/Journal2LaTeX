import { cn } from "@/utils/cn";
import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  size?: number;
  className?: string;
  text?: string;
}

export function LoadingSpinner({
  size = 24,
  className,
  text,
}: LoadingSpinnerProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 py-16",
        className,
      )}
    >
      <div className="relative">
        <div className="h-10 w-10 rounded-full border-2 border-emerald-100" />
        <Loader2
          className="absolute inset-0 animate-spin text-emerald-500"
          size={size}
        />
      </div>
      {text && (
        <p className="text-sm font-medium text-gray-500">{text}</p>
      )}
    </div>
  );
}
