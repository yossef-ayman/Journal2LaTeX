import { cn } from "@/utils/cn";

interface JsonViewerProps {
  data: unknown;
  className?: string;
  maxHeight?: string;
}

export function JsonViewer({ data, className, maxHeight }: JsonViewerProps) {
  const formatted = JSON.stringify(data, null, 2);
  return (
    <pre
      className={cn(
        "overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-relaxed text-slate-50",
        className,
      )}
      style={maxHeight ? { maxHeight } : undefined}
    >
      <code>{formatted}</code>
    </pre>
  );
}
