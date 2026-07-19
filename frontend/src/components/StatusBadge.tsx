import { Badge } from "@/components/ui/badge";
import type { JobStatus } from "@/types";

const variantMap: Record<string, "success" | "warning" | "destructive" | "secondary" | "default"> =
  {
    CREATED: "secondary",
    VALIDATING: "warning",
    ANALYZING_DOCUMENT: "warning",
    EXTRACTING_ASSETS: "warning",
    LOADING_TEMPLATE: "warning",
    RENDERING_LATEX: "warning",
    COMPILING: "warning",
    COMPLETED: "success",
    FAILED: "destructive",
  };

interface StatusBadgeProps {
  status: JobStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <Badge variant={variantMap[status] ?? "secondary"}>{status}</Badge>
  );
}
