import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
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
  Zap,
  Activity,
} from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/config";

function useHealthCheck() {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((r) => setHealthy(r.ok))
      .catch(() => setHealthy(false));
  }, []);

  return healthy;
}

const steps = [
  {
    icon: Upload,
    step: "01",
    title: "Upload Document",
    description: "Upload your .docx academic manuscript with embedded figures, tables, and equations.",
    color: "from-emerald-500 to-teal-500",
    bg: "bg-emerald-50",
  },
  {
    icon: FileText,
    step: "02",
    title: "Analysis & Extraction",
    description: "Automatic parsing of structure, equation conversion, and asset extraction.",
    color: "from-blue-500 to-cyan-500",
    bg: "bg-blue-50",
  },
  {
    icon: Sliders,
    step: "03",
    title: "Template Styling",
    description: "Apply target journal LaTeX templates and formatting rules automatically.",
    color: "from-violet-500 to-purple-500",
    bg: "bg-violet-50",
  },
  {
    icon: CheckCircle2,
    step: "04",
    title: "Compile & Verify",
    description: "Compile to high-resolution PDF with automated fidelity scoring.",
    color: "from-amber-500 to-orange-500",
    bg: "bg-amber-50",
  },
];

const stats = [
  { label: "Avg. Processing Time", value: "< 60s", icon: Zap },
  { label: "Templates Available", value: "10+", icon: FileText },
  { label: "Success Rate", value: "98%", icon: Activity },
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
    <div className="page-enter">
      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-gray-100 bg-white">
        {/* Decorative background */}
        <div className="absolute inset-0 hero-gradient pointer-events-none" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-bl from-emerald-50 to-transparent rounded-full blur-3xl opacity-50 pointer-events-none" />

        <div className="relative mx-auto max-w-5xl px-6 py-16 md:py-24 md:px-8">
          <div className="flex flex-col items-center text-center max-w-3xl mx-auto">
            {/* Badge */}
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-1.5">
              <Sparkles size={13} className="text-emerald-600" />
              <span className="text-xs font-semibold text-emerald-700 tracking-wide">Academic Publishing Tool</span>
            </div>

            <h1 className="mb-4 text-4xl md:text-5xl font-extrabold tracking-tight text-gray-900 leading-tight">
              Convert Academic DOCX{" "}
              <span className="gradient-text">to LaTeX</span>
            </h1>

            <p className="mb-8 max-w-xl text-base md:text-lg leading-relaxed text-gray-500">
              Transform manuscripts into publication-ready LaTeX documents and PDFs with automated template matching and layout verification.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-3">
              <Button size="xl" onClick={() => navigate("/upload")} className="gap-2 shadow-lg shadow-emerald-200">
                <Upload size={17} />
                Start New Conversion
              </Button>
              <Button
                size="xl"
                variant="outline"
                onClick={() => navigate("/history")}
                className="gap-2"
              >
                <Clock size={17} />
                View History
              </Button>
            </div>

            {/* System Status */}
            {healthy !== null && (
              <div
                className={`mt-6 inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs animate-fade-in ${
                  healthy
                    ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                    : "border-red-200 bg-red-50 text-red-700"
                }`}
              >
                <Server size={12} className={healthy ? "text-emerald-600" : "text-red-600"} />
                <span className="font-medium">
                  Backend API {healthy ? "Connected" : "Unreachable"}
                </span>
              </div>
            )}
          </div>

          {/* Stats row */}
          <div className="mt-12 grid grid-cols-3 gap-4 max-w-lg mx-auto">
            {stats.map((s) => (
              <div key={s.label} className="flex flex-col items-center gap-1 p-4 rounded-2xl bg-white border border-gray-100 shadow-sm">
                <span className="text-2xl font-bold text-gray-900">{s.value}</span>
                <span className="text-[11px] text-gray-400 text-center leading-tight">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-5xl px-6 py-10 md:px-8 space-y-12">
        {/* Pipeline Steps */}
        <section>
          <div className="flex items-center gap-3 mb-6">
            <h2 className="text-lg font-bold text-gray-900">How It Works</h2>
            <div className="flex-1 h-px bg-gray-100" />
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map((step) => (
              <div
                key={step.step}
                className="card-hover group relative flex flex-col gap-4 rounded-2xl border border-gray-100 bg-white p-5 cursor-default shadow-sm"
              >
                {/* Step number */}
                <div className="flex items-center justify-between">
                  <div className={`flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${step.color} shadow-sm`}>
                    <step.icon size={18} className="text-white" />
                  </div>
                  <span className="text-2xl font-black text-gray-100 font-mono">{step.step}</span>
                </div>
                <div className="space-y-1.5">
                  <h3 className="text-sm font-semibold text-gray-900">{step.title}</h3>
                  <p className="text-xs leading-relaxed text-gray-500">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Recent Jobs */}
        {recentJobs && recentJobs.length > 0 && (
          <section className="animate-fade-in">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-bold text-gray-900">Recent Conversions</h2>
                <div className="flex-1 h-px bg-gray-100" />
              </div>
              <button
                onClick={() => navigate("/history")}
                className="flex items-center gap-1 text-sm font-medium text-emerald-600 hover:text-emerald-700 transition-colors"
              >
                View all <ArrowRight size={14} />
              </button>
            </div>

            <div className="rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden divide-y divide-gray-50">
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
                  className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-gray-50/80 cursor-pointer group"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-100">
                      <FileText size={15} />
                    </div>
                    <div className="min-w-0 space-y-0.5">
                      <p className="truncate text-sm font-semibold text-gray-900">
                        {j.paper_name || "Untitled Paper"}
                      </p>
                      <p className="text-xs text-gray-400 font-mono">
                        {j.job_id.slice(0, 8)}… · {new Date(j.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0 ml-4">
                    <StatusBadge status={j.status} />
                    <ArrowRight size={14} className="text-gray-300 group-hover:text-emerald-500 transition-colors" />
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}

        {jobsLoading && (
          <section>
            <div className="h-6 w-40 rounded-lg bg-gray-100 animate-pulse mb-4" />
            <SkeletonCard lines={4} />
          </section>
        )}
      </div>
    </div>
  );
}
