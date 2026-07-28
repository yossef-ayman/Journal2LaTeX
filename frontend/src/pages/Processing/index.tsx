import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { PageContainer } from "@/components/PageContainer";
import { SectionTitle } from "@/components/SectionTitle";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { PipelineDiagram } from "@/components/PipelineDiagram";
import { SkeletonCard } from "@/components/Skeleton";
import { Progress } from "@/components/ui/progress";
import { useJobStatus, useCompileMutation } from "@/hooks";
import { AlertCircle, XCircle, Layers, CheckCircle2, Timer } from "lucide-react";

function useElapsed(startedAt: string | null) {
  const [elapsed, setElapsed] = useState("0s");

  useEffect(() => {
    if (!startedAt) return;
    const start = new Date(startedAt).getTime();

    const update = () => {
      const diff = Date.now() - start;
      const s = Math.floor(diff / 1000);
      if (s < 60) setElapsed(`${s}s`);
      else if (s < 3600) setElapsed(`${Math.floor(s / 60)}m ${s % 60}s`);
      else setElapsed(`${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`);
    };

    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  return elapsed;
}

const stageTimes: Record<string, number> = {
  CREATED: 2,
  VALIDATING: 5,
  ANALYZING_DOCUMENT: 8,
  EXTRACTING_ASSETS: 10,
  LOADING_TEMPLATE: 3,
  RENDERING_LATEX: 12,
  COMPILING: 8,
  COMPLETED: 2,
};

function estimateRemaining(status: string, progress: number): string {
  if (status === "COMPLETED" || status === "FAILED") return "—";
  const total = Object.values(stageTimes).reduce((a, b) => a + b, 0);
  const elapsed = Math.round((progress / 100) * total);
  const remaining = Math.max(0, total - elapsed);
  if (remaining < 60) return `~${remaining}s remaining`;
  return `~${Math.round(remaining / 60)}m remaining`;
}

function MetaRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
      <span className="text-sm text-gray-500">{label}</span>
      <div className="text-sm font-medium text-gray-900">{children}</div>
    </div>
  );
}

export default function ProcessingPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { data: job, isLoading, isError, error } = useJobStatus(jobId ?? null);
  const compile = useCompileMutation();
  const elapsed = useElapsed(job?.created_at ?? null);
  const [showRedirect, setShowRedirect] = useState(false);

  const compileTriggered = useRef(false);

  useEffect(() => {
    if (!job) return;
    if (job.status === "EXTRACTING_ASSETS" && !compileTriggered.current) {
      compileTriggered.current = true;
      compile.mutate({
        job_id: job.job_id,
        template_name: job.template_name || "default",
      });
    }
  }, [job, compile]);

  const completedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (job?.status === "COMPLETED" && !showRedirect) {
      setShowRedirect(true);
      completedTimer.current = setTimeout(
        () => navigate(`/result/${job.job_id}`, { replace: true }),
        1200,
      );
    }
    return () => {
      if (completedTimer.current) clearTimeout(completedTimer.current);
    };
  }, [job?.status, job?.job_id, navigate, showRedirect]);

  if (isLoading) {
    return (
      <PageContainer>
        <SectionTitle title="Processing" description="Starting conversion pipeline..." />
        <SkeletonCard lines={6} />
      </PageContainer>
    );
  }

  if (isError || !job) {
    return (
      <PageContainer>
        <SectionTitle title="Processing Error" />
        <Card>
          <CardContent className="flex flex-col items-center gap-5 py-20">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50 text-red-500">
              <XCircle size={32} />
            </div>
            <div className="text-center space-y-1">
              <p className="text-base font-semibold text-gray-900">Failed to load job</p>
              <p className="text-sm text-gray-500">
                {error?.message ?? "Failed to load job status"}
              </p>
            </div>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="text-sm font-medium text-emerald-600 hover:text-emerald-700 transition-colors"
            >
              Try again →
            </button>
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  const isFailed = job.status === "FAILED";
  const isCompleted = job.status === "COMPLETED";

  return (
    <PageContainer>
      <SectionTitle
        title={isCompleted ? "Conversion Complete" : "Processing Pipeline"}
        description={
          isCompleted
            ? "Redirecting to your results dashboard..."
            : job.current_step || "Processing manuscript through LaTeX pipeline..."
        }
      />

      {/* Progress bar at the top */}
      {!isCompleted && !isFailed && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span className="font-medium">{job.current_step || "Processing..."}</span>
            <span className="font-mono font-semibold text-gray-700">{job.progress}%</span>
          </div>
          <Progress value={job.progress} variant="default" />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardContent className="pt-6 pb-6">
              <PipelineDiagram status={job.status} progress={job.progress} />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          {/* Timing Card */}
          <Card>
            <CardContent className="pt-5 pb-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                  <Timer size={14} />
                </div>
                <span className="text-sm font-semibold text-gray-900">Pipeline Timing</span>
              </div>
              <div className="space-y-0">
                <MetaRow label="Time Elapsed">
                  <span className="font-mono text-sm">{elapsed}</span>
                </MetaRow>
                <MetaRow label="Est. Remaining">
                  <span className="font-mono text-sm">{estimateRemaining(job.status, job.progress)}</span>
                </MetaRow>
                <MetaRow label="Progress">
                  <span className="font-mono text-sm">{job.progress}%</span>
                </MetaRow>
              </div>
            </CardContent>
          </Card>

          {/* Job Metadata Card */}
          <Card>
            <CardContent className="pt-5 pb-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-50 text-violet-600">
                  <Layers size={14} />
                </div>
                <span className="text-sm font-semibold text-gray-900">Job Metadata</span>
              </div>
              <div className="space-y-0">
                <MetaRow label="Status">
                  <StatusBadge status={job.status} />
                </MetaRow>
                <MetaRow label="Paper Name">
                  <span className="truncate max-w-[130px] text-right text-sm">{job.paper_name || "Untitled"}</span>
                </MetaRow>
                <MetaRow label="LaTeX Template">
                  <span className="font-mono text-xs bg-gray-100 rounded px-1.5 py-0.5">{job.template_name}</span>
                </MetaRow>
              </div>
            </CardContent>
          </Card>

          {/* Failure Card */}
          {isFailed && (
            <Card className="border-red-100 bg-red-50/50">
              <CardContent className="pt-5 pb-5">
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-red-100 text-red-600">
                    <AlertCircle size={15} />
                  </div>
                  <div className="space-y-1 min-w-0">
                    <p className="text-sm font-semibold text-red-900">Conversion failed</p>
                    {job.errors.map((err, i) => (
                      <p key={i} className="text-xs text-red-700 leading-relaxed break-words">{err}</p>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Success Card */}
          {isCompleted && (
            <Card className="border-emerald-200 bg-gradient-to-br from-emerald-50 to-white">
              <CardContent className="pt-5 pb-5">
                <div className="flex items-center gap-4">
                  <div className="h-12 w-12 animate-scale-in rounded-2xl bg-emerald-100 flex items-center justify-center shrink-0 shadow-sm">
                    <CheckCircle2 size={22} className="text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-emerald-900">Ready!</p>
                    <p className="text-xs text-emerald-700 mt-0.5">
                      Redirecting to results...
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </PageContainer>
  );
}
