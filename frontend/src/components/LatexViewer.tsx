import { useMemo, useState, useRef, useCallback } from "react";
import { cn } from "@/utils/cn";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Copy, Search, Check, FileDown } from "lucide-react";

interface LatexViewerProps {
  code: string;
  className?: string;
  filename?: string;
}

function highlightLatex(source: string): string {
  const escaped = source
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return escaped
    .replace(/(%.*)$/gm, '<span class="text-emerald-400">$1</span>')
    .replace(
      /(\\(?:[a-zA-Z]+|.))/g,
      '<span class="text-blue-300">$1</span>',
    )
    .replace(
      /(\$[^$]*\$)/g,
      '<span class="text-amber-300">$1</span>',
    )
    .replace(
      /(\\\[[^]*?\\\])/g,
      '<span class="text-amber-300">$1</span>',
    )
    .replace(
      /(\\begin\{[a-zA-Z]*\}[^]*?\\end\{[a-zA-Z]*\})/g,
      (m) =>
        m.replace(
          /(\\begin\{[a-zA-Z]*\}|\\end\{[a-zA-Z]*\})/g,
          '<span class="text-purple-300">$1</span>',
        ),
    );
}

export function LatexViewer({ code, className, filename }: LatexViewerProps) {
  const [copied, setCopied] = useState(false);
  const [search, setSearch] = useState("");
  const [searchMatch, setSearchMatch] = useState<number | null>(null);
  const preRef = useRef<HTMLPreElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const lines = useMemo(() => code.split("\n"), [code]);

  const highlightedLines = useMemo(
    () => lines.map((l) => highlightLatex(l)),
    [lines],
  );

  const onCopy = useCallback(async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [code]);

  const onDownload = useCallback(() => {
    const blob = new Blob([code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename ?? "main.tex";
    a.click();
    URL.revokeObjectURL(url);
  }, [code, filename]);

  const onSearch = useCallback(
    (term: string) => {
      setSearch(term);
      if (!term) {
        setSearchMatch(null);
        return;
      }
      const idx = lines.findIndex((l) =>
        l.toLowerCase().includes(term.toLowerCase()),
      );
      setSearchMatch(idx >= 0 ? idx : null);
      if (idx >= 0 && preRef.current) {
        const lineEl = preRef.current.querySelector(
          `[data-line="${idx}"]`,
        );
        lineEl?.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    },
    [lines],
  );

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            ref={searchInputRef}
            placeholder="Search in LaTeX..."
            value={search}
            onChange={(e) => onSearch(e.target.value)}
            className="h-9 pl-9 text-sm"
          />
        </div>
        <Button variant="outline" size="sm" onClick={onCopy}>
          {copied ? (
            <Check size={14} className="text-emerald-500" />
          ) : (
            <Copy size={14} />
          )}
          {copied ? "Copied" : "Copy"}
        </Button>
        <Button variant="outline" size="sm" onClick={onDownload}>
          <FileDown size={14} />
          Download
        </Button>
      </div>

      <div className="overflow-auto rounded-lg border bg-slate-950" style={{ maxHeight: "600px" }}>
        <pre ref={preRef} className="relative p-4 text-xs leading-relaxed">
          <code>
            {highlightedLines.map((hl, i) => (
              <div
                key={i}
                data-line={i}
                className={cn(
                  "flex",
                  searchMatch === i && search
                    ? "bg-yellow-500/10"
                    : "",
                )}
              >
                <span className="mr-4 inline-block w-8 select-none text-right text-slate-600">
                  {i + 1}
                </span>
                <span
                  className="flex-1"
                  dangerouslySetInnerHTML={{ __html: hl || " " }}
                />
              </div>
            ))}
          </code>
        </pre>
      </div>
    </div>
  );
}
