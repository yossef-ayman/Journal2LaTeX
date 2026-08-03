import { useQuery } from "@tanstack/react-query";
import { PageContainer } from "@/components/PageContainer";
import { SectionTitle } from "@/components/SectionTitle";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/StatusBadge";
import { SkeletonCard } from "@/components/Skeleton";
import { useTemplates } from "@/hooks";
import { listJobs } from "@/services";
import { CheckCircle, XCircle, Server, Database, Activity } from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/config";

function useHealthCheck() {
  const [status, setStatus] = useState<"loading" | "healthy" | "unhealthy">("loading");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/health`);
        if (cancelled) return;
        if (res.ok) {
          setStatus("healthy");
        } else {
          setStatus("unhealthy");
          setErrorMsg(`Status ${res.status}`);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        setStatus("unhealthy");
        setErrorMsg(err instanceof Error ? err.message : "Connection failed");
      }
    };

    check();
    return () => { cancelled = true; };
  }, []);

  return { status, errorMsg };
}

export default function SettingsPage() {
  const templates = useTemplates();
  const { status: health, errorMsg } = useHealthCheck();
  const { data: jobs } = useQuery({
    queryKey: ["jobs"],
    queryFn: listJobs,
  });

  const completedCount = jobs?.filter((j) => j.status === "COMPLETED").length ?? 0;
  const failedCount = jobs?.filter((j) => j.status === "FAILED").length ?? 0;

  return (
    <PageContainer>
      <SectionTitle
        title="Settings"
        description="Configure application preferences and view diagnostics"
      />

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Available Templates</CardTitle>
          </CardHeader>
          <CardContent>
            {templates.isLoading ? (
              <SkeletonCard lines={3} />
            ) : templates.isError ? (
              <p className="text-sm text-destructive">
                {templates.error?.message ?? "Failed to load templates"}
              </p>
            ) : !templates.data?.length ? (
              <p className="text-sm text-muted-foreground">No templates available.</p>
            ) : (
              <div className="space-y-3">
                {templates.data.map((t) => (
                  <div
                    key={t.name}
                    className="rounded-lg border bg-card p-4 card-hover"
                  >
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <p className="text-sm font-semibold text-foreground">
                          {t.journal_title || t.name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {t.publisher} &middot; v{t.version}
                        </p>
                      </div>
                      <StatusBadge status="COMPLETED" />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {t.supported_features.author_biographies && (
                        <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-medium text-primary">
                          Biographies
                        </span>
                      )}
                      {t.supported_features.double_column && (
                        <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-medium text-primary">
                          Double column
                        </span>
                      )}
                      {t.supported_features.custom_headers && (
                        <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-medium text-primary">
                          Custom headers
                        </span>
                      )}
                      <span className="rounded-full bg-muted px-2.5 py-0.5 text-[11px] text-muted-foreground">
                        {t.class_file}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Backend Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3 mb-4">
                <Server size={20} className="text-muted-foreground" />
                <div className="flex-1 space-y-0.5">
                  <p className="text-sm font-medium text-foreground">API Server</p>
                  <p className="text-xs text-muted-foreground">
                    {API_BASE_URL}
                  </p>
                </div>
                {health === "loading" ? (
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                ) : health === "healthy" ? (
                  <div className="flex items-center gap-1 text-sm font-medium text-emerald-600">
                    <CheckCircle size={14} />
                    Online
                  </div>
                ) : (
                  <div className="flex items-center gap-1 text-sm font-medium text-destructive" title={errorMsg}>
                    <XCircle size={14} />
                    Offline
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Usage Stats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database size={14} className="text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Total jobs</span>
                </div>
                <span className="text-sm font-medium text-foreground">{jobs?.length ?? "-"}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle size={14} className="text-emerald-500" />
                  <span className="text-sm text-muted-foreground">Completed</span>
                </div>
                <span className="text-sm font-medium text-foreground">{completedCount}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <XCircle size={14} className="text-destructive" />
                  <span className="text-sm text-muted-foreground">Failed</span>
                </div>
                <span className="text-sm font-medium text-foreground">{failedCount}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity size={14} className="text-primary" />
                  <span className="text-sm text-muted-foreground">Templates</span>
                </div>
                <span className="text-sm font-medium text-foreground">{templates.data?.length ?? "-"}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>General</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-sm font-medium text-foreground">Default Template</p>
                  <p className="text-xs text-muted-foreground">Used for new conversions</p>
                </div>
                <p className="text-sm text-muted-foreground">default</p>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-sm font-medium text-foreground">Version</p>
                  <p className="text-xs text-muted-foreground">Frontend build</p>
                </div>
                <p className="text-sm text-muted-foreground">1.0.0</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}
