import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BiographyCard } from "@/components/BiographyCard";
import { EmptyState } from "@/components/EmptyState";
import { User } from "lucide-react";
import type { DocumentStructure } from "@/types";
import { getAssetUrl } from "@/services";

interface BiographiesTabProps {
  doc: DocumentStructure;
  jobId: string;
}

export function BiographiesTab({ doc, jobId }: BiographiesTabProps) {
  if (!doc.author_biographies || doc.author_biographies.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Author Biographies</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={<User size={48} strokeWidth={1} />}
            title="No biographies found"
            description="No author biographies were detected in the document."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-foreground">
        {doc.author_biographies.length} biography(ies)
      </h3>
      <div className="grid gap-4">
        {doc.author_biographies.map((b, i) => (
          <BiographyCard
            key={i}
            authorName={b.author_name}
            imagePath={b.image_path ? getAssetUrl(jobId, b.image_path) : null}
            biographyText={b.biography_text}
          />
        ))}
      </div>
    </div>
  );
}
