import { useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { useToast } from "@/components/Toast";
import { getDownloadUrl } from "@/services";
import {
  FileDown,
  ExternalLink,
  Copy,
  Printer,
  CheckCheck,
  Award,
  FileText,
  Clock,
  AlertTriangle,
} from "lucide-react";
import type { JobMetadata, FidelityReport } from "@/types";

interface OverviewTabProps {
  job: JobMetadata;
  fidelity?: FidelityReport;
  onNavigateToLatex: () => void;
}

function StatBox({ label, value, icon }: { label: string; value: string | number; icon: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card p-3 card-hover">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-semibold text-foreground truncate">{value}</p>
      </div>
    </div>
  );
}

export function OverviewTab({ job, fidelity, onNavigateToLatex }: OverviewTabProps) {
  const { toast } = useToast();
  const downloadUrl = getDownloadUrl(job.job_id);

  const copyToClipboard = useCallback(
    async (text: string, label: string) => {
      try {
        await navigator.clipboard.writeText(text);
        toast({ type: "success", title: "Copied!", message: `${label} copied to clipboard.` });
      } catch {
        toast({ type: "error", title: "Copy failed", message: "Could not copy to clipboard." });
      }
    },
    [toast],
  );

  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Job Summary</CardTitle>
          <StatusBadge status={job.status} />
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatBox
              label="Paper"
              value={job.paper_name || "Untitled"}
              icon={<FileText size={18} className="text-primary" />}
            />
            <StatBox
              label="Template"
              value={job.template_name}
              icon={<Award size={18} className="text-amber-500" />}
            />
            <StatBox
              label="Created"
              value={new Date(job.created_at).toLocaleDateString()}
              icon={<Clock size={18} className="text-muted-foreground" />}
            />
            <StatBox
              label={fidelity ? "Fidelity Score" : "Compile"}
              value={
                fidelity
                  ? `${Math.round(fidelity.overall_fidelity_score)}%`
                  : job.compile_success
                    ? "Passed"
                    : "Failed"
              }
              icon={
                fidelity ? (
                  <Award size={18} className={fidelity.overall_fidelity_score >= 80 ? "text-emerald-500" : "text-amber-500"} />
                ) : (
                  <CheckCheck size={18} className={job.compile_success ? "text-emerald-500" : "text-destructive"} />
                )
              }
            />
          </div>

          {job.warnings.length > 0 && (
            <div className="flex items-start gap-3 rounded-md border border-amber-200 bg-amber-50 px-4 py-3">
              <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-600" />
              <div className="space-y-1">
                <p className="text-xs font-medium text-amber-800">Warnings</p>
                {job.warnings.map((w, i) => (
                  <p key={i} className="text-xs text-amber-700">{w}</p>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-3 pt-2">
            <a href={downloadUrl} download target="_blank" rel="noreferrer">
              <Button>
                <FileDown size={16} />
                Download PDF
              </Button>
            </a>
            <Button variant="outline" onClick={onNavigateToLatex}>
              <ExternalLink size={16} />
              View LaTeX
            </Button>
            <Button
              variant="outline"
              onClick={() => copyToClipboard(job.job_id, "Job ID")}
              aria-label="Copy job ID"
            >
              <Copy size={16} />
              Copy Job ID
            </Button>
            <Button
              variant="outline"
              onClick={() => copyToClipboard(`${downloadUrl}`, "Download URL")}
              aria-label="Copy download URL"
            >
              <Copy size={16} />
              Copy PDF URL
            </Button>
            <Button variant="outline" onClick={handlePrint} aria-label="Print page">
              <Printer size={16} />
              Print
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
