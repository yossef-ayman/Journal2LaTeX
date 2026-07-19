import { cn } from "@/utils/cn";
import { Progress } from "@/components/ui/progress";
import type { FidelityReport } from "@/types";
import {
  BarChart3,
  Image,
  Layout,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Trophy,
} from "lucide-react";

interface MetricCardProps {
  label: string;
  value: number;
  icon: React.ReactNode;
  className?: string;
}

function MetricCard({ label, value, icon, className }: MetricCardProps) {
  const color =
    value >= 90
      ? "text-emerald-500"
      : value >= 70
        ? "text-amber-500"
        : "text-destructive";

  return (
    <div className={cn("rounded-lg border bg-card p-4", className)}>
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className={cn("text-2xl font-bold", color)}>
            {Math.round(value)}%
          </p>
        </div>
        <div className="text-muted-foreground">{icon}</div>
      </div>
      <Progress value={value} className="mt-3" />
    </div>
  );
}

interface FidelityDashboardProps {
  report: FidelityReport;
  compileSuccess: boolean;
}

export function FidelityDashboard({
  report,
  compileSuccess,
}: FidelityDashboardProps) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Overall Score"
          value={report.overall_fidelity_score}
          icon={<Trophy size={24} />}
        />
        <MetricCard
          label="Content Match"
          value={report.content_match_score}
          icon={<BarChart3 size={24} />}
        />
        <MetricCard
          label="Layout Match"
          value={report.layout_match_score}
          icon={<Layout size={24} />}
        />
        <MetricCard
          label="Asset Match"
          value={report.asset_match_score}
          icon={<Image size={24} />}
        />
      </div>

      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-3 text-sm font-medium text-foreground">
          Compilation Status
        </h3>
        <div className="flex items-center gap-2">
          {compileSuccess ? (
            <>
              <CheckCircle size={18} className="text-emerald-500" />
              <span className="text-sm text-emerald-600">
                PDF compiled successfully
              </span>
            </>
          ) : (
            <>
              <XCircle size={18} className="text-destructive" />
              <span className="text-sm text-destructive">
                PDF compilation failed
              </span>
            </>
          )}
        </div>
      </div>

      {(report.layout_warnings.length > 0 ||
        report.pdf_validations.text_overflow_warnings > 0 ||
        report.pdf_validations.empty_pages_detected) && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div className="mb-2 flex items-center gap-2">
            <AlertTriangle size={16} className="text-amber-600" />
            <h3 className="text-sm font-medium text-amber-800">
              Layout Warnings
            </h3>
          </div>
          <ul className="space-y-1">
            {report.pdf_validations.text_overflow_warnings > 0 && (
              <li className="text-xs text-amber-700">
                {report.pdf_validations.text_overflow_warnings} text overflow
                warning(s) detected
              </li>
            )}
            {report.pdf_validations.empty_pages_detected && (
              <li className="text-xs text-amber-700">
                Empty pages detected in output
              </li>
            )}
            {report.layout_warnings.slice(0, 10).map((w, i) => (
              <li key={i} className="text-xs text-amber-700">
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {report.critical_missing_content > 0 && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4">
          <div className="mb-2 flex items-center gap-2">
            <XCircle size={16} className="text-destructive" />
            <h3 className="text-sm font-medium text-destructive">
              Missing Content
            </h3>
          </div>
          <p className="text-xs text-destructive/80">
            {report.critical_missing_content} section(s) with missing content
            detected
          </p>
        </div>
      )}
    </div>
  );
}
