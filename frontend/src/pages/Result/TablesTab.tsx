import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TablePreview } from "@/components/TablePreview";
import { EmptyState } from "@/components/EmptyState";
import { TableIcon } from "lucide-react";
import type { AssetReport } from "@/types";

interface TablesTabProps {
  assets: AssetReport;
}

export function TablesTab({ assets }: TablesTabProps) {
  const tables = assets.assets.filter((a) => a.type === "table");

  if (tables.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Tables</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={<TableIcon size={48} strokeWidth={1} />}
            title="No tables found"
            description="No tables were detected in the document."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-foreground">
        {tables.length} table(s) found
      </h3>
      <div className="grid gap-4">
        {tables.map((t, i) => (
          <TablePreview
            key={t.asset_index ?? i}
            caption={t.caption || t.nearby_captions?.[0] || ""}
            headers={[]}
            rows={[]}
            tableIndex={i}
          />
        ))}
      </div>
    </div>
  );
}
