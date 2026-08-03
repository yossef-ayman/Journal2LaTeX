import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FigureCard } from "@/components/FigureCard";
import { EmptyState } from "@/components/EmptyState";
import { ImageIcon } from "lucide-react";
import type { AssetReport } from "@/types";

// NOTE: Individual asset serving (/job/{id}/assets/{path}) does not exist in
// the backend OpenAPI schema. Figure images cannot be served; filenames are shown instead.

interface FiguresTabProps {
  assets: AssetReport;
}

export function FiguresTab({ assets }: FiguresTabProps) {
  const figures = assets.assets.filter((a) => a.type === "figure");

  if (figures.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Figures</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={<ImageIcon size={48} strokeWidth={1} />}
            title="No figures found"
            description="No figures were detected in the document."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-foreground">
        {figures.length} figure(s) found
      </h3>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {figures.map((f, i) => (
          <FigureCard
            key={f.asset_index ?? i}
            caption={f.caption || f.nearby_captions?.[0] || ""}
            filename={f.path?.split("/").pop() || `figure-${i}`}
            sourceLocation={f.original_relationship_id || null}
            assetPath={undefined}
          />
        ))}
      </div>
    </div>
  );
}
