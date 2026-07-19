import { useState, memo } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PageContainer } from "@/components/PageContainer";
import { SectionTitle } from "@/components/SectionTitle";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/StatusBadge";
import { SkeletonCard } from "@/components/Skeleton";
import { useJobStatus } from "@/hooks";
import {
  getFidelityReport,
  getAssetReport,
  getDocumentStructure,
  getLatexSource,
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
    <div className="space-y-4">
      <div className="flex gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-9 w-24 animate-pulse rounded-md bg-muted" />
        ))}
      </div>
      <SkeletonCard lines={6} />
    </div>
  );
});

export default function ResultPage() {
  const { jobId } = useParams<{ jobId: string }>();
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
        <SectionTitle title="Result" description="Loading job data..." />
        <SkeletonTabs />
      </PageContainer>
    );
  }

  if (job.isError || !job.data) {
    return (
      <PageContainer>
        <SectionTitle title="Result" />
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-16">
            <XCircle size={48} className="text-destructive" />
            <p className="text-sm text-muted-foreground">
              {job.error?.message ?? "Job not found"}
            </p>
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  const j = job.data;
  const isCompleted = j.status === "COMPLETED";

  return (
    <PageContainer>
      <div className="flex items-center justify-between">
        <SectionTitle
          title={j.paper_name || "Conversion Result"}
          description={`Job ${j.job_id.slice(0, 8)}...`}
        />
        <StatusBadge status={j.status} />
      </div>

      {j.status === "FAILED" && (
        <Card className="border-destructive/50">
          <CardContent className="space-y-2 pt-6">
            <p className="text-sm font-medium text-destructive">Conversion failed</p>
            {j.errors.map((err, i) => (
              <p key={i} className="text-xs text-destructive/80">{err}</p>
            ))}
          </CardContent>
        </Card>
      )}

      {isCompleted && (
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="flex-wrap">
            {TABS.map((t) => (
              <TabsTrigger key={t.value} value={t.value}>
                <t.icon size={14} className="mr-1" />
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
              <FiguresTab assets={assets.data} jobId={j.job_id} />
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
