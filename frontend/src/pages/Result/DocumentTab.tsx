import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TreeView } from "@/components/TreeView";
import { FileText, BookOpen, User, Hash } from "lucide-react";
import type { DocumentStructure } from "@/types";
import { useMemo } from "react";

interface DocumentTabProps {
  doc: DocumentStructure;
}

export function DocumentTab({ doc }: DocumentTabProps) {
  const treeNodes = useMemo(() => {
    return [
      {
        id: "abstract",
        label: "Abstract",
        icon: <BookOpen size={14} />,
      },
      ...(doc.keywords?.length
        ? [
            {
              id: "keywords",
              label: `Keywords: ${doc.keywords.join(", ")}`,
              icon: <Hash size={14} />,
            },
          ]
        : []),
      {
        id: "sections",
        label: `Sections (${doc.sections.length})`,
        icon: <FileText size={14} />,
        children: doc.sections.map((s, i) => ({
          id: `section-${i}`,
          label: s.title || `Section ${i + 1}`,
          icon: <FileText size={14} />,
          children: s.blocks.map((b, bi) => ({
            id: `block-${i}-${bi}`,
            label: `${b.type} block`,
            data: b.content,
          })),
        })),
      },
    ];
  }, [doc]);

  return (
    <div className="space-y-6">
      {doc.authors.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Authors ({doc.authors.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {doc.authors.map((a, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <User size={14} className="text-muted-foreground" />
                  <span className="font-medium text-foreground">{a.name}</span>
                  {a.affiliation && (
                    <span className="text-muted-foreground">- {a.affiliation}</span>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Document Structure</CardTitle>
        </CardHeader>
        <CardContent>
          <TreeView nodes={treeNodes} defaultExpanded />
        </CardContent>
      </Card>
    </div>
  );
}
