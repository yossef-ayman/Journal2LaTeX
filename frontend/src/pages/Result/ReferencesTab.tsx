import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";
import { Bookmark } from "lucide-react";
import type { DocumentStructure } from "@/types";

interface ReferencesTabProps {
  doc: DocumentStructure;
}

export function ReferencesTab({ doc }: ReferencesTabProps) {
  if (!doc.references || doc.references.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>References</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={<Bookmark size={48} strokeWidth={1} />}
            title="No references found"
            description="No references were detected in the document."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>References ({doc.references.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="list-inside list-decimal space-y-2">
          {doc.references.map((ref, i) => (
            <li key={i} className="text-sm leading-relaxed text-muted-foreground">
              {ref}
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
