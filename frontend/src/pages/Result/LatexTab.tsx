import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LatexViewer } from "@/components/LatexViewer";
import { SkeletonCard } from "@/components/Skeleton";

interface LatexTabTabProps {
  data: string | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
}

export function LatexTab({ data, isLoading, isError, errorMessage }: LatexTabTabProps) {
  if (isLoading) return <SkeletonCard lines={8} />;

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Generated LaTeX</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">
            {errorMessage ?? "Failed to load LaTeX source"}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generated LaTeX</CardTitle>
      </CardHeader>
      <CardContent>
        <LatexViewer code={data ?? ""} filename="main.tex" />
      </CardContent>
    </Card>
  );
}
