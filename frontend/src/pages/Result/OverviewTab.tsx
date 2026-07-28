import { useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { useToast } from "@/components/Toast";
import { getDownloadUrl, getLatexUrl, getLogUrl } from "@/services";
import {
  FileDown,
  ExternalLink,
  Copy,
  CheckCircle2,
  Award,
  FileText,
  Clock,
  AlertTriangle,
  Printer,
} from "lucide-react";
import type { JobMetadata, FidelityReport } from "@/types";

interface OverviewTabProps {
  job: JobMetadata;
  fidelity?: FidelityReport;
  onNavigateToLatex: () => void;
}

function StatCard({
  label,
  value,
  icon,
  accent = false,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <div className={`flex items-center gap-3 rounded-2xl border p-4 ${accent ? "border-emerald-200 bg-emerald-50" : "border-gray-100 bg-white shadow-sm"}`}>
      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${accent ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">{label}</p>
        <p className="text-sm font-bold text-gray-900 truncate mt-0.5">{value}</p>
      </div>
    </div>
  );
}

function OutputFileCard({
  title,
  extension,
  sizeEstimate,
  downloadUrl,
  onOpen,
  onCopyPath,
  accentColor = "gray",
}: {
  title: string;
  extension: string;
  sizeEstimate: string;
  downloadUrl: string;
  onOpen: () => void;
  onCopyPath: () => void;
  accentColor?: "gray" | "emerald" | "blue" | "amber";
}) {
  const colorMap = {
    gray: "from-gray-700 to-gray-900",
    emerald: "from-emerald-500 to-emerald-700",
    blue: "from-blue-500 to-blue-700",
    amber: "from-amber-500 to-amber-700",
  };
  return (
    <div className="flex flex-col justify-between rounded-2xl border border-gray-100 bg-white p-5 shadow-sm hover:shadow-md hover:border-emerald-100 transition-all duration-200 space-y-4">
      <div className="flex items-start gap-3.5">
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${colorMap[accentColor]} text-white font-bold text-xs shadow-sm`}>
          {extension}
        </div>
        <div className="min-w-0 flex-1">
          <h4 className="text-sm font-semibold text-gray-900 truncate">{title}</h4>
          <p className="text-[11px] font-mono text-gray-400 mt-0.5">{sizeEstimate}</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-gray-50">
        <a href={downloadUrl} download target="_blank" rel="noreferrer" className="flex-1">
          <Button size="sm" className="w-full gap-1.5 h-8 text-xs">
            <FileDown size={13} />
            Download
          </Button>
        </a>
        <Button variant="outline" size="sm" onClick={onOpen} className="gap-1.5 h-8 text-xs">
          <ExternalLink size={13} />
          Open
        </Button>
        <Button variant="ghost" size="icon-sm" onClick={onCopyPath} className="h-8 w-8 text-gray-400">
          <Copy size={13} />
        </Button>
      </div>
    </div>
  );
}

export function OverviewTab({ job, fidelity, onNavigateToLatex }: OverviewTabProps) {
  const { toast } = useToast();
  const pdfDownloadUrl = getDownloadUrl(job.job_id);
  const latexUrl = getLatexUrl(job.job_id);
  const logUrl = getLogUrl(job.job_id);

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

  return (
    <div className="space-y-8">
      {/* Summary Header Card */}
      <Card>
        <CardHeader className="flex flex-row items-start justify-between pb-4 border-b border-gray-50">
          <div className="space-y-1">
            <CardTitle className="text-base font-bold text-gray-900">
              {job.paper_name || "Conversion Result"}
            </CardTitle>
            <p className="text-xs text-gray-400 font-mono">Job ID: {job.job_id}</p>
          </div>
          <StatusBadge status={job.status} />
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Paper Name"
              value={job.paper_name || "Untitled"}
              icon={<FileText size={16} />}
            />
            <StatCard
              label="LaTeX Template"
              value={job.template_name}
              icon={<Award size={16} />}
            />
            <StatCard
              label="Date Created"
              value={new Date(job.created_at).toLocaleDateString()}
              icon={<Clock size={16} />}
            />
            <StatCard
              label={fidelity ? "Fidelity Score" : "Compilation"}
              value={
                fidelity
                  ? `${Math.round(fidelity.overall_fidelity_score)}%`
                  : job.compile_success
                    ? "Passed ✓"
                    : "Failed ✗"
              }
              icon={
                fidelity ? (
                  <Award size={16} className={fidelity.overall_fidelity_score >= 80 ? "text-emerald-600" : "text-amber-600"} />
                ) : (
                  <CheckCircle2 size={16} className={job.compile_success ? "text-emerald-600" : "text-red-600"} />
                )
              }
              accent={!!job.compile_success}
            />
          </div>

          {job.warnings.length > 0 && (
            <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
              <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-600" />
              <div className="space-y-1 min-w-0">
                <p className="text-sm font-semibold text-amber-900">
                  Pipeline Warnings ({job.warnings.length})
                </p>
                {job.warnings.map((w, i) => (
                  <p key={i} className="text-xs text-amber-800 leading-relaxed break-words">{w}</p>
                ))}
              </div>
            </div>
          )}

          {/* Actions toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-gray-50">
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(job.job_id, "Job ID")}
                className="h-8 text-xs gap-1.5"
              >
                <Copy size={13} />
                Copy Job ID
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(pdfDownloadUrl, "PDF URL")}
                className="h-8 text-xs gap-1.5"
              >
                <Copy size={13} />
                Copy Download Link
              </Button>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => window.print()}
              className="h-8 text-xs text-gray-500 gap-1.5"
            >
              <Printer size={13} />
              Print Summary
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Output Files */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-gray-900">Generated Output Files</h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <OutputFileCard
            title="Compiled PDF Document"
            extension="PDF"
            sizeEstimate="Compiled PDF output"
            downloadUrl={pdfDownloadUrl}
            onOpen={() => window.open(pdfDownloadUrl, "_blank")}
            onCopyPath={() => copyToClipboard(pdfDownloadUrl, "PDF Path")}
            accentColor="emerald"
          />
          <OutputFileCard
            title="LaTeX Source Code"
            extension="TEX"
            sizeEstimate="main.tex source file"
            downloadUrl={latexUrl}
            onOpen={onNavigateToLatex}
            onCopyPath={() => copyToClipboard(latexUrl, "LaTeX Path")}
            accentColor="blue"
          />
          <OutputFileCard
            title="Compilation Build Log"
            extension="LOG"
            sizeEstimate="pdflatex execution log"
            downloadUrl={logUrl}
            onOpen={() => window.open(logUrl, "_blank")}
            onCopyPath={() => copyToClipboard(logUrl, "Log Path")}
            accentColor="amber"
          />
        </div>
      </div>
    </div>
  );
}
