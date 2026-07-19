import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FidelityDashboard } from "@/components/FidelityDashboard";
import { SkeletonCard } from "@/components/Skeleton";
import type { FidelityReport } from "@/types";

interface FidelityTabProps {
  report: FidelityReport | undefined;
  isLoading: boolean;
  isError: boolean;
  compileSuccess: boolean;
  errorMessage?: string;
}

export function FidelityTab({
  report,
  isLoading,
  isError,
  compileSuccess,
  errorMessage,
}: FidelityTabProps) {
  if (isLoading) return <SkeletonCard lines={8} />;

  if (isError || !report) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Fidelity Report</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">
            {errorMessage ?? "Failed to load fidelity report"}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Fidelity Report</CardTitle>
      </CardHeader>
      <CardContent>
        <FidelityDashboard report={report} compileSuccess={compileSuccess} />
      </CardContent>
    </Card>
  );
}
