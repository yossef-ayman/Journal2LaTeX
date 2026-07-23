import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { PageContainer } from "@/components/PageContainer";
import { SectionTitle } from "@/components/SectionTitle";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { PipelineDiagram } from "@/components/PipelineDiagram";
import { SkeletonCard } from "@/components/Skeleton";
import { useJobStatus, useCompileMutation } from "@/hooks";
import { AlertCircle, XCircle, Clock, FileText, Layers } from "lucide-react";

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
        <SectionTitle title="Processing" description="Starting conversion..." />
        <SkeletonCard lines={6} />
      </PageContainer>
    );
  }

  if (isError || !job) {
    return (
      <PageContainer>
        <SectionTitle title="Processing Error" />
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-16">
            <XCircle size={48} className="text-destructive" />
            <p className="text-sm text-muted-foreground">
              {error?.message ?? "Failed to load job status"}
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="text-sm text-primary underline underline-offset-2 hover:text-primary/80"
            >
              Retry
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
        title={isCompleted ? "Conversion Complete" : "Conversion Pipeline"}
        description={
          isCompleted
            ? "Redirecting to your result dashboard..."
            : job.current_step || "Processing manuscript through LaTeX pipeline..."
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card className="border-zinc-200 bg-white">
            <CardContent className="pt-5 pb-6">
              <PipelineDiagram status={job.status} progress={job.progress} />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="border-zinc-200 bg-white">
            <CardContent className="pt-5 pb-5">
              <div className="flex items-center gap-2 mb-3.5 pb-2 border-b border-zinc-100">
                <Clock size={15} className="text-zinc-500" />
                <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">Pipeline Timing</span>
              </div>
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-zinc-500">Time Elapsed</span>
                  <span className="font-mono font-semibold text-zinc-900">{elapsed}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-500">Est. Remaining</span>
                  <span className="font-mono font-semibold text-zinc-900">
                    {estimateRemaining(job.status, job.progress)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-500">Current Progress</span>
                  <span className="font-mono font-semibold text-zinc-900">{job.progress}%</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-zinc-200 bg-white">
            <CardContent className="pt-5 pb-5">
              <div className="flex items-center gap-2 mb-3.5 pb-2 border-b border-zinc-100">
                <Layers size={15} className="text-zinc-500" />
                <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">Job Metadata</span>
              </div>
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-zinc-500">Current Status</span>
                  <StatusBadge status={job.status} />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-500">Paper Name</span>
                  <span className="truncate max-w-[140px] text-right font-medium text-zinc-900">
                    {job.paper_name || "Untitled"}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-zinc-500">LaTeX Template</span>
                  <span className="font-mono text-[11px] font-semibold text-zinc-900">{job.template_name}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {isFailed && (
            <Card className="border-red-200 bg-red-50/50">
              <CardContent className="pt-5 pb-5">
                <div className="flex items-start gap-2.5">
                  <AlertCircle size={17} className="mt-0.5 shrink-0 text-red-600" />
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-red-900">Conversion failed</p>
                    {job.errors.map((err, i) => (
                      <p key={i} className="text-[11px] text-red-700 leading-normal">{err}</p>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {isCompleted && (
            <Card className="border-emerald-200 bg-emerald-50/50">
              <CardContent className="pt-5 pb-5">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 animate-scale-in rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                    <FileText size={16} className="text-emerald-700" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-emerald-900">Ready!</p>
                    <p className="text-[11px] text-emerald-700">
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
