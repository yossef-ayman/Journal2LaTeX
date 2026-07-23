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
  CheckCircle2,
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
    <div className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-white p-3.5 card-hover">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-zinc-700">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-medium text-zinc-500 uppercase tracking-wider">{label}</p>
        <p className="text-xs font-semibold text-zinc-900 truncate">{value}</p>
      </div>
    </div>
  );
}

interface OutputFileCardProps {
  title: string;
  extension: string;
  sizeEstimate: string;
  downloadUrl: string;
  onOpen: () => void;
  onCopyPath: () => void;
}

function OutputFileCard({
  title,
  extension,
  sizeEstimate,
  downloadUrl,
  onOpen,
  onCopyPath,
}: OutputFileCardProps) {
  return (
    <div className="flex flex-col justify-between rounded-xl border border-zinc-200 bg-white p-4 card-hover space-y-4">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-white shadow-2xs font-mono text-xs font-bold">
          {extension}
        </div>
        <div className="min-w-0 flex-1">
          <h4 className="text-xs font-semibold text-zinc-900 truncate">{title}</h4>
          <p className="text-[11px] font-mono text-zinc-400 mt-0.5">{sizeEstimate}</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-zinc-100">
        <a href={downloadUrl} download target="_blank" rel="noreferrer" className="flex-1">
          <Button size="sm" className="w-full text-xs h-8 gap-1.5">
            <FileDown size={13} />
            Download
          </Button>
        </a>
        <Button variant="outline" size="sm" onClick={onOpen} className="text-xs h-8 gap-1.5">
          <ExternalLink size={13} />
          Open
        </Button>
        <Button variant="outline" size="sm" onClick={onCopyPath} className="text-xs h-8 gap-1.5">
          <Copy size={13} />
          Copy Path
        </Button>
      </div>
    </div>
  );
}

export function OverviewTab({ job, fidelity, onNavigateToLatex }: OverviewTabProps) {
  const { toast } = useToast();
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const pdfDownloadUrl = getDownloadUrl(job.job_id);

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

  const openPdfInNewTab = () => {
    window.open(pdfDownloadUrl, "_blank");
  };

  const openLogFile = () => {
    window.open(`${baseUrl}/api/jobs/${job.job_id}/log`, "_blank");
  };

  return (
    <div className="space-y-6">
      {/* Conversion Summary & Metadata Grid */}
      <Card className="border-zinc-200 bg-white">
        <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-zinc-100">
          <div>
            <CardTitle className="text-sm font-semibold text-zinc-900">Conversion Dashboard</CardTitle>
            <p className="text-xs text-zinc-500 mt-0.5 font-mono">Job ID: {job.job_id}</p>
          </div>
          <StatusBadge status={job.status} />
        </CardHeader>
        <CardContent className="space-y-6 pt-5">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatBox
              label="Paper Name"
              value={job.paper_name || "Untitled"}
              icon={<FileText size={16} />}
            />
            <StatBox
              label="LaTeX Template"
              value={job.template_name}
              icon={<Award size={16} />}
            />
            <StatBox
              label="Date Created"
              value={new Date(job.created_at).toLocaleDateString()}
              icon={<Clock size={16} />}
            />
            <StatBox
              label={fidelity ? "Fidelity Score" : "Compilation"}
              value={
                fidelity
                  ? `${Math.round(fidelity.overall_fidelity_score)}%`
                  : job.compile_success
                    ? "Passed"
                    : "Failed"
              }
              icon={
                fidelity ? (
                  <Award size={16} className={fidelity.overall_fidelity_score >= 80 ? "text-emerald-600" : "text-amber-600"} />
                ) : (
                  <CheckCircle2 size={16} className={job.compile_success ? "text-emerald-600" : "text-red-600"} />
                )
              }
            />
          </div>

          {job.warnings.length > 0 && (
            <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50/70 p-4">
              <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-600" />
              <div className="space-y-1">
                <p className="text-xs font-semibold text-amber-900">Pipeline Warnings ({job.warnings.length})</p>
                {job.warnings.map((w, i) => (
                  <p key={i} className="text-xs text-amber-800 leading-relaxed">{w}</p>
                ))}
              </div>
            </div>
          )}

          {/* Quick Header Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-zinc-100">
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(job.job_id, "Job ID")}
                className="text-xs h-8"
              >
                <Copy size={13} />
                Copy Job ID
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(pdfDownloadUrl, "PDF URL")}
                className="text-xs h-8"
              >
                <Copy size={13} />
                Copy Download Link
              </Button>
            </div>
            <Button variant="ghost" size="sm" onClick={handlePrint} className="text-xs h-8 text-zinc-500">
              <Printer size={13} />
              Print Summary
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Output Files Cards Grid */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500">
          Generated Output Artifacts
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <OutputFileCard
            title="Compiled PDF Document"
            extension="PDF"
            sizeEstimate="Target PDF Output"
            downloadUrl={pdfDownloadUrl}
            onOpen={openPdfInNewTab}
            onCopyPath={() => copyToClipboard(pdfDownloadUrl, "PDF Path")}
          />

          <OutputFileCard
            title="LaTeX Source Code"
            extension="TEX"
            sizeEstimate="main.tex file"
            downloadUrl={pdfDownloadUrl}
            onOpen={onNavigateToLatex}
            onCopyPath={() => copyToClipboard(`${baseUrl}/api/jobs/${job.job_id}/latex`, "LaTeX Source Path")}
          />

          <OutputFileCard
            title="Compilation Build Log"
            extension="LOG"
            sizeEstimate="pdflatex execution log"
            downloadUrl={`${baseUrl}/api/jobs/${job.job_id}/log`}
            onOpen={openLogFile}
            onCopyPath={() => copyToClipboard(`${baseUrl}/api/jobs/${job.job_id}/log`, "Log File Path")}
          />
        </div>
      </div>
    </div>
  );
}
