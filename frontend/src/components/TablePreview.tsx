import { cn } from "@/utils/cn";

interface TablePreviewProps {
  caption: string;
  headers: string[];
  rows: string[][];
  tableIndex: number;
  className?: string;
}

export function TablePreview({
  caption,
  headers,
  rows,
  tableIndex,
  className,
}: TablePreviewProps) {
  return (
    <div className={cn("rounded-lg border bg-card", className)}>
      <div className="border-b bg-muted/30 px-4 py-2">
        <p className="text-xs font-medium text-foreground">
          Table {tableIndex + 1}
          {caption ? `: ${caption}` : ""}
        </p>
      </div>
      <div className="overflow-x-auto p-4">
        <table className="w-full text-left text-xs">
          {headers.length > 0 && (
            <thead>
              <tr className="border-b">
                {headers.map((h, i) => (
                  <th
                    key={i}
                    className="px-3 py-2 font-medium text-muted-foreground"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {rows.slice(0, 5).map((row, ri) => (
              <tr key={ri} className="border-b last:border-0">
                {row.map((cell, ci) => (
                  <td key={ci} className="px-3 py-2 text-muted-foreground">
                    <span className="line-clamp-1">{cell}</span>
                  </td>
                ))}
              </tr>
            ))}
            {rows.length > 5 && (
              <tr>
                <td
                  colSpan={headers.length || rows[0]?.length || 1}
                  className="px-3 py-2 text-center text-muted-foreground"
                >
                  ... {rows.length - 5} more row(s)
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
