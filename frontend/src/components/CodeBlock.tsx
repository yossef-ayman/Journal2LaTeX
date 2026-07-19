import { cn } from "@/utils/cn";

interface CodeBlockProps {
  code: string;
  className?: string;
  maxHeight?: string;
}

export function CodeBlock({ code, className, maxHeight }: CodeBlockProps) {
  return (
    <pre
      className={cn(
        "overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-relaxed text-slate-50",
        className,
      )}
      style={maxHeight ? { maxHeight } : undefined}
    >
      <code>{code}</code>
    </pre>
  );
}
