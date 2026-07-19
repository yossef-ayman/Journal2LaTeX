import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { SkeletonCard } from "@/components/Skeleton";
import { listJobs } from "@/services";
import {
  Upload,
  FileText,
  CheckCircle,
  Settings as SettingsIcon,
  Server,
  ArrowRight,
  Clock,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";

function useHealthCheck() {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
    fetch(`${baseUrl}/health`)
      .then((r) => setHealthy(r.ok))
      .catch(() => setHealthy(false));
  }, []);

  return healthy;
}

const steps = [
  {
    icon: Upload,
    title: "Upload Document",
    description: "Upload a .docx academic paper for conversion",
    color: "text-primary",
    bg: "bg-primary/10",
  },
  {
    icon: FileText,
    title: "Conversion & Analysis",
    description: "Automatic parsing, asset extraction, and LaTeX rendering",
    color: "text-violet-500",
    bg: "bg-violet-50",
  },
  {
    icon: CheckCircle,
    title: "Compile & Verify",
    description: "PDF generation with automated fidelity checking",
    color: "text-emerald-500",
    bg: "bg-emerald-50",
  },
  {
    icon: SettingsIcon,
    title: "Customize Template",
    description: "Apply journal-specific templates and styles",
    color: "text-amber-500",
    bg: "bg-amber-50",
  },
];

export default function HomePage() {
  const navigate = useNavigate();
  const healthy = useHealthCheck();

  const { data: recentJobs, isLoading: jobsLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: listJobs,
    refetchInterval: 30_000,
  });

  return (
    <div className="page-enter mx-auto flex max-w-4xl flex-col items-center px-6 py-16">
      <div className="relative mb-6">
        <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-blue-600 shadow-lg shadow-primary/20">
          <FileText size={36} className="text-white" />
        </div>
        <div className="absolute -top-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500 shadow-sm">
          <Sparkles size={14} className="text-white" />
        </div>
      </div>

      <h1 className="mb-3 text-4xl font-bold tracking-tight text-foreground">
        Journal2LaTeX
      </h1>

      <p className="mb-8 max-w-lg text-center text-lg text-muted-foreground">
        Convert academic DOCX papers to publication-ready LaTeX and PDF with
        automated template matching and fidelity checking.
      </p>

      <div className="flex flex-wrap items-center justify-center gap-4">
        <Button size="lg" onClick={() => navigate("/upload")} className="gap-2">
          <Upload size={18} />
          Start Conversion
        </Button>
        <Button
          size="lg"
          variant="outline"
          onClick={() => navigate("/history")}
          className="gap-2"
        >
          <Clock size={18} />
          View History
        </Button>
      </div>

      {healthy !== null && (
        <div
          className={`mt-4 flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs animate-fade-in ${
            healthy
              ? "border-emerald-200 bg-emerald-50"
              : "border-destructive/20 bg-destructive/5"
          }`}
        >
          <Server
            size={12}
            className={healthy ? "text-emerald-500" : "text-destructive"}
          />
          <span
            className={
              healthy ? "text-emerald-600" : "text-destructive"
            }
          >
            Backend {healthy ? "connected" : "unreachable"}
          </span>
        </div>
      )}

      <div className="mt-16 w-full">
        <h2 className="mb-6 text-lg font-semibold text-foreground">
          How it works
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((step) => (
            <div
              key={step.title}
              className="card-hover flex flex-col gap-3 rounded-lg border bg-card p-5"
            >
              <div
                className={`flex h-11 w-11 items-center justify-center rounded-xl ${step.bg}`}
              >
                <step.icon size={22} className={step.color} />
              </div>
              <div className="space-y-1.5">
                <h3 className="text-sm font-semibold text-foreground">
                  {step.title}
                </h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {recentJobs && recentJobs.length > 0 && (
        <div className="mt-16 w-full animate-fade-in">
          <h2 className="mb-4 text-lg font-semibold text-foreground">
            Recent Jobs
          </h2>
          <Card>
            <CardContent className="p-0">
              {recentJobs.slice(0, 5).map((j) => (
                <button
                  key={j.job_id}
                  type="button"
                  onClick={() =>
                    navigate(
                      j.status === "COMPLETED" || j.status === "FAILED"
                        ? `/result/${j.job_id}`
                        : `/processing/${j.job_id}`,
                    )
                  }
                  className="card-hover flex w-full items-center justify-between border-b px-5 py-3.5 text-left last:border-0"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {j.paper_name || "Untitled"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(j.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={j.status} />
                    <ArrowRight size={14} className="text-muted-foreground" />
                  </div>
                </button>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {jobsLoading && (
        <div className="mt-8 w-full">
          <SkeletonCard lines={4} />
        </div>
      )}
    </div>
  );
}
