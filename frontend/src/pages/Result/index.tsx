import { useState, memo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PageContainer } from "@/components/PageContainer";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/StatusBadge";
import { SkeletonCard } from "@/components/Skeleton";
import { useJobStatus } from "@/hooks";
import {
  getFidelityReport,
  getAssetReport,
  getDocumentStructure,
  getLatexSource,
  getDownloadUrl,
} from "@/services";
import { OverviewTab } from "./OverviewTab";
import { DocumentTab } from "./DocumentTab";
import { FiguresTab } from "./FiguresTab";
import { TablesTab } from "./TablesTab";
import { ReferencesTab } from "./ReferencesTab";
import { BiographiesTab } from "./BiographiesTab";
import { LatexTab } from "./LatexTab";
import { FidelityTab } from "./FidelityTab";
import { RawDataTab } from "./RawDataTab";
import {
  FileText,
  BarChart3,
  Image,
  Table,
  Bookmark,
  User,
  FileJson,
  Code,
  XCircle,
  ArrowLeft,
  FileDown,
} from "lucide-react";

const TABS = [
  { value: "overview", label: "Overview", icon: FileText },
  { value: "document", label: "Document", icon: FileText },
  { value: "figures", label: "Figures", icon: Image },
  { value: "tables", label: "Tables", icon: Table },
  { value: "references", label: "References", icon: Bookmark },
  { value: "biographies", label: "Biographies", icon: User },
  { value: "latex", label: "LaTeX", icon: Code },
  { value: "fidelity", label: "Fidelity", icon: BarChart3 },
  { value: "raw", label: "Raw Data", icon: FileJson },
] as const;

const SkeletonTabs = memo(function SkeletonTabs() {
  return (
    <div className="space-y-6">
      <div className="flex gap-1 border-b border-gray-100 pb-0">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-10 w-24 animate-pulse rounded-t-lg bg-gray-100" />
        ))}
      </div>
      <SkeletonCard lines={6} />
    </div>
  );
});

export default function ResultPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [tab, setTab] = useState("overview");

  const job = useJobStatus(jobId ?? null);

  const fidelity = useQuery({
    queryKey: ["job", "fidelity", jobId],
    queryFn: () => getFidelityReport(jobId!),
    enabled: !!jobId && job.data?.status === "COMPLETED",
  });

  const assets = useQuery({
    queryKey: ["job", "assets", jobId],
    queryFn: () => getAssetReport(jobId!),
    enabled: !!jobId && job.data?.status === "COMPLETED",
  });

  const documentStructure = useQuery({
    queryKey: ["job", "document", jobId],
    queryFn: () => getDocumentStructure(jobId!),
    enabled: !!jobId && job.data?.status === "COMPLETED",
  });

  const latex = useQuery({
    queryKey: ["job", "latex", jobId],
    queryFn: () => getLatexSource(jobId!),
    enabled: !!jobId && job.data?.status === "COMPLETED",
  });

  if (job.isLoading) {
    return (
      <PageContainer>
        <div className="h-8 w-64 rounded-lg bg-gray-100 animate-pulse mb-2" />
        <div className="h-4 w-40 rounded bg-gray-100 animate-pulse mb-8" />
        <SkeletonTabs />
      </PageContainer>
    );
  }

  if (job.isError || !job.data) {
    return (
      <PageContainer>
        <Card>
          <CardContent className="flex flex-col items-center gap-5 py-20">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50 text-red-500">
              <XCircle size={32} />
            </div>
            <div className="text-center space-y-1">
              <p className="text-base font-semibold text-gray-900">Job not found</p>
              <p className="text-sm text-gray-500">
                {job.error?.message ?? "This job may have been deleted or does not exist."}
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={() => navigate("/history")} className="gap-2">
              <ArrowLeft size={14} />
              Back to History
            </Button>
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  const j = job.data;
  const isCompleted = j.status === "COMPLETED";
  const pdfUrl = getDownloadUrl(j.job_id);

  return (
    <PageContainer>
      {/* Page Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <button
              onClick={() => navigate("/history")}
              className="text-sm text-gray-400 hover:text-gray-600 transition-colors flex items-center gap-1"
            >
              <ArrowLeft size={13} />
              History
            </button>
            <span className="text-gray-300">/</span>
            <span className="text-sm text-gray-500 truncate max-w-[200px]">
              {j.paper_name || "Untitled"}
            </span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-gray-900 leading-tight truncate">
            {j.paper_name || "Conversion Result"}
          </h2>
          <p className="text-sm text-gray-400 font-mono mt-1">
            {j.job_id.slice(0, 8)}… · {new Date(j.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <StatusBadge status={j.status} />
          {j.compile_success && (
            <a href={pdfUrl} download target="_blank" rel="noreferrer">
              <Button size="sm" className="gap-2 h-9">
                <FileDown size={14} />
                Download PDF
              </Button>
            </a>
          )}
        </div>
      </div>

      {/* Error banner for failed jobs */}
      {j.status === "FAILED" && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5">
          <div className="flex items-start gap-3">
            <XCircle size={18} className="text-red-500 shrink-0 mt-0.5" />
            <div className="space-y-1 min-w-0">
              <p className="text-sm font-semibold text-red-900">Conversion Failed</p>
              {j.errors.map((err, i) => (
                <p key={i} className="text-xs text-red-700 leading-relaxed break-words">{err}</p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      {isCompleted && (
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="overflow-x-auto">
            {TABS.map((t) => (
              <TabsTrigger key={t.value} value={t.value} className="gap-1.5 shrink-0">
                <t.icon size={13} />
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="overview">
            <OverviewTab
              job={j}
              fidelity={fidelity.data}
              onNavigateToLatex={() => setTab("latex")}
            />
          </TabsContent>

          <TabsContent value="document">
            {documentStructure.data ? (
              <DocumentTab doc={documentStructure.data} />
            ) : (
              <SkeletonCard lines={5} />
            )}
          </TabsContent>

          <TabsContent value="figures">
            {assets.data ? (
              <FiguresTab assets={assets.data} />
            ) : (
              <SkeletonCard lines={3} />
            )}
          </TabsContent>

          <TabsContent value="tables">
            {assets.data ? (
              <TablesTab assets={assets.data} />
            ) : (
              <SkeletonCard lines={3} />
            )}
          </TabsContent>

          <TabsContent value="references">
            {documentStructure.data ? (
              <ReferencesTab doc={documentStructure.data} />
            ) : (
              <SkeletonCard lines={4} />
            )}
          </TabsContent>

          <TabsContent value="biographies">
            {documentStructure.data ? (
              <BiographiesTab doc={documentStructure.data} jobId={j.job_id} />
            ) : (
              <SkeletonCard lines={3} />
            )}
          </TabsContent>

          <TabsContent value="latex">
            <LatexTab
              data={latex.data}
              isLoading={latex.isLoading}
              isError={latex.isError}
              errorMessage={latex.error?.message}
            />
          </TabsContent>

          <TabsContent value="fidelity">
            <FidelityTab
              report={fidelity.data}
              isLoading={fidelity.isLoading}
              isError={fidelity.isError}
              compileSuccess={j.compile_success}
              errorMessage={fidelity.error?.message}
            />
          </TabsContent>

          <TabsContent value="raw">
            <RawDataTab
              data={{
                job: j,
                fidelity: fidelity.data,
                assets: assets.data,
                document: documentStructure.data,
              }}
            />
          </TabsContent>
        </Tabs>
      )}
    </PageContainer>
  );
}
