import { cn } from "@/utils/cn";
import { ArrowUpDown } from "lucide-react";

interface SortOption {
  value: string;
  label: string;
}

interface SortSelectProps {
  options: SortOption[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function SortSelect({
  options,
  value,
  onChange,
  className,
}: SortSelectProps) {
  return (
    <div className={cn("relative", className)}>
      <ArrowUpDown
        size={14}
        className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
      />
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full appearance-none rounded-md border bg-background pl-9 pr-8 text-sm text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <div className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground">
        <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
          <path
            d="M1 1L5 5L9 1"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </div>
  );
}
