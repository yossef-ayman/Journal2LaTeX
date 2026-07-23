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
  CheckCircle2,
  Sliders,
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
    title: "1. Upload Document",
    description: "Upload your .docx academic manuscript with embedded figures and tables.",
  },
  {
    icon: FileText,
    title: "2. Analysis & Extraction",
    description: "Automatic parsing of structure, equation conversion, and asset extraction.",
  },
  {
    icon: Sliders,
    title: "3. Template Styling",
    description: "Apply target journal LaTeX templates and formatting rules automatically.",
  },
  {
    icon: CheckCircle2,
    title: "4. Compilation & Verification",
    description: "Compile to high-resolution PDF with automated fidelity scoring.",
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
    <div className="page-enter mx-auto flex max-w-4xl flex-col items-center px-4 py-12 md:py-16">
      <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl border border-zinc-200 bg-white text-zinc-900 shadow-xs">
        <Sparkles size={24} className="text-zinc-800" />
      </div>

      <h1 className="mb-3 text-3xl font-bold tracking-tight text-zinc-900 md:text-4xl text-center">
        Academic DOCX to LaTeX Converter
      </h1>

      <p className="mb-8 max-w-lg text-center text-sm leading-relaxed text-zinc-600 md:text-base">
        Convert academic manuscripts into publication-ready LaTeX documents and PDFs with automated template matching and layout verification.
      </p>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <Button size="lg" onClick={() => navigate("/upload")} className="gap-2">
          <Upload size={16} />
          Start New Conversion
        </Button>
        <Button
          size="lg"
          variant="outline"
          onClick={() => navigate("/history")}
          className="gap-2"
        >
          <Clock size={16} />
          View History
        </Button>
      </div>

      {healthy !== null && (
        <div
          className={`mt-6 flex items-center gap-2 rounded-full border px-3 py-1 text-xs animate-fade-in ${
            healthy
              ? "border-emerald-200 bg-emerald-50/60 text-emerald-700"
              : "border-red-200 bg-red-50/60 text-red-700"
          }`}
        >
          <Server size={12} className={healthy ? "text-emerald-600" : "text-red-600"} />
          <span className="text-[11px] font-medium">
            Backend API {healthy ? "Connected" : "Unreachable"}
          </span>
        </div>
      )}

      <div className="mt-14 w-full">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-500">
            Pipeline Overview
          </h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((step) => (
            <div
              key={step.title}
              className="card-hover flex flex-col gap-2.5 rounded-xl border border-zinc-200 bg-white p-4"
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-100 text-zinc-800">
                <step.icon size={18} />
              </div>
              <div className="space-y-1">
                <h3 className="text-xs font-semibold text-zinc-900">
                  {step.title}
                </h3>
                <p className="text-xs leading-normal text-zinc-500">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {recentJobs && recentJobs.length > 0 && (
        <div className="mt-12 w-full animate-fade-in">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              Recent Jobs
            </h2>
            <button
              onClick={() => navigate("/history")}
              className="text-xs font-medium text-zinc-600 hover:text-zinc-900 flex items-center gap-1 cursor-pointer"
            >
              View all <ArrowRight size={12} />
            </button>
          </div>
          <Card className="border-zinc-200 bg-white">
            <CardContent className="p-0 divide-y divide-zinc-100">
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
                  className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-zinc-50/80 cursor-pointer"
                >
                  <div className="min-w-0 flex-1 pr-4">
                    <p className="truncate text-xs font-semibold text-zinc-900">
                      {j.paper_name || "Untitled Paper"}
                    </p>
                    <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                      ID: {j.job_id.slice(0, 8)} • {new Date(j.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={j.status} />
                    <ArrowRight size={14} className="text-zinc-400" />
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

