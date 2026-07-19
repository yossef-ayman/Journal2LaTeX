import { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { PageContainer } from "@/components/PageContainer";
import { SectionTitle } from "@/components/SectionTitle";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import { SearchInput } from "@/components/SearchInput";
import { SortSelect } from "@/components/SortSelect";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { SkeletonTable } from "@/components/Skeleton";
import { useToast } from "@/components/Toast";
import { useJobsList, useDeleteJob } from "@/hooks";
import { getDownloadUrl } from "@/services";
import {
  ExternalLink,
  Trash2,
  CheckCircle,
  XCircle,
  FileDown,
  History,
} from "lucide-react";
import type { JobSummary, JobStatus } from "@/types";

const PAGE_SIZE = 10;

const SORT_OPTIONS = [
  { value: "created_at-desc", label: "Newest first" },
  { value: "created_at-asc", label: "Oldest first" },
  { value: "paper_name-asc", label: "Name A-Z" },
  { value: "paper_name-desc", label: "Name Z-A" },
];

const STATUS_OPTIONS: { value: JobStatus | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "COMPLETED", label: "Completed" },
  { value: "FAILED", label: "Failed" },
  { value: "COMPILING", label: "Compiling" },
  { value: "RENDERING_LATEX", label: "Rendering" },
];

function HistoryTable({
  jobs,
  onOpen,
  onDownload,
  onDelete,
  deletePending,
}: {
  jobs: (JobSummary & { template_name?: string; compile_success?: boolean })[];
  onOpen: (id: string) => void;
  onDownload: (id: string) => void;
  onDelete: (j: JobSummary) => void;
  deletePending: boolean;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" role="table">
        <thead>
          <tr className="border-b text-left text-xs text-muted-foreground">
            <th className="px-4 py-3 font-medium" scope="col">Paper</th>
            <th className="px-4 py-3 font-medium" scope="col">Template</th>
            <th className="px-4 py-3 font-medium" scope="col">Status</th>
            <th className="px-4 py-3 font-medium" scope="col">Compile</th>
            <th className="px-4 py-3 font-medium" scope="col">Progress</th>
            <th className="px-4 py-3 font-medium" scope="col">Created</th>
            <th className="px-4 py-3 font-medium" scope="col">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => (
            <tr
              key={j.job_id}
              className="group border-b last:border-0 transition-colors hover:bg-accent/50"
            >
              <td className="max-w-[180px] truncate px-4 py-3 font-medium text-foreground">
                <button
                  type="button"
                  onClick={() => onOpen(j.job_id)}
                  className="hover:text-primary transition-colors"
                  aria-label={`Open ${j.paper_name || "Untitled"}`}
                >
                  {j.paper_name || "Untitled"}
                </button>
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {j.template_name || "-"}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={j.status} />
              </td>
              <td className="px-4 py-3">
                {j.compile_success === true ? (
                  <CheckCircle size={14} className="text-emerald-500" />
                ) : j.compile_success === false ? (
                  <XCircle size={14} className="text-destructive" />
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {j.progress}%
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {new Date(j.created_at).toLocaleDateString()}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onOpen(j.job_id)}
                    aria-label={`View result for ${j.paper_name || "Untitled"}`}
                  >
                    <ExternalLink size={14} />
                  </Button>
                  {j.compile_success && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDownload(j.job_id)}
                      aria-label={`Download PDF for ${j.paper_name || "Untitled"}`}
                    >
                      <FileDown size={14} />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDelete(j)}
                    disabled={deletePending}
                    aria-label={`Delete ${j.paper_name || "Untitled"}`}
                  >
                    <Trash2 size={14} className="text-destructive" />
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const { data: jobs, isLoading, isError } = useJobsList();
  const deleteJob = useDeleteJob();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<JobStatus | "all">("all");
  const [sort, setSort] = useState("created_at-desc");
  const [page, setPage] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState<JobSummary | null>(null);

  const filtered = useMemo(() => {
    if (!jobs) return [];
    const q = search.toLowerCase();
    let result = jobs.filter((j) => {
      if (statusFilter !== "all" && j.status !== statusFilter) return false;
      return (
        j.paper_name?.toLowerCase().includes(q) ||
        j.status.toLowerCase().includes(q) ||
        j.job_id.toLowerCase().includes(q)
      );
    });
    const [sortKey, sortDir] = sort.split("-") as [string, "asc" | "desc"];
    result.sort((a, b) => {
      let cmp = 0;
      if (sortKey === "created_at") {
        cmp = a.created_at.localeCompare(b.created_at);
      } else if (sortKey === "paper_name") {
        cmp = (a.paper_name ?? "").localeCompare(b.paper_name ?? "");
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return result;
  }, [jobs, search, statusFilter, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const paged = filtered.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  const handleDelete = useCallback(() => {
    if (deleteTarget) {
      deleteJob.mutate(deleteTarget.job_id, {
        onSuccess: () => {
          toast({ type: "success", title: "Job deleted", message: deleteTarget.paper_name || "Untitled" });
        },
        onError: () => {
          toast({ type: "error", title: "Delete failed", message: "Could not delete the job." });
        },
      });
      setDeleteTarget(null);
    }
  }, [deleteTarget, deleteJob, toast]);

  const handleOpen = useCallback(
    (id: string) => navigate(`/result/${id}`),
    [navigate],
  );

  const handleDownload = useCallback((id: string) => {
    window.open(getDownloadUrl(id), "_blank", "noopener,noreferrer");
  }, []);

  if (isLoading) {
    return (
      <PageContainer>
        <SectionTitle title="Conversion History" />
        <SkeletonTable rows={5} />
      </PageContainer>
    );
  }

  if (isError) {
    return (
      <PageContainer>
        <SectionTitle title="Conversion History" />
        <Card>
          <CardContent className="py-16 text-center">
            <div className="mb-4 flex justify-center">
              <XCircle size={48} className="text-destructive" />
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              Failed to load jobs. Is the backend running?
            </p>
            <Button variant="outline" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <SectionTitle
        title="Conversion History"
        description="View previously converted documents"
      />

      <div className="flex flex-wrap items-center gap-3">
        <SearchInput
          value={search}
          onChange={(v) => { setSearch(v); setPage(0); }}
          placeholder="Search by name, status, or ID..."
          className="flex-1 min-w-[200px]"
        />
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as JobStatus | "all"); setPage(0); }}
          className="h-9 appearance-none rounded-md border bg-background px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
          aria-label="Filter by status"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <SortSelect options={SORT_OPTIONS} value={sort} onChange={(v) => { setSort(v); setPage(0); }} className="w-36" />
      </div>

      {filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-16">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted">
              <History size={40} className="text-muted-foreground" />
            </div>
            <h3 className="text-lg font-medium text-foreground">
              {search || statusFilter !== "all" ? "No matching jobs" : "No conversions yet"}
            </h3>
            <p className="max-w-sm text-center text-sm text-muted-foreground">
              {search || statusFilter !== "all"
                ? "Try a different search term or filter."
                : "Your first converted document will appear here."}
            </p>
            {!search && statusFilter === "all" && (
              <Button onClick={() => navigate("/upload")}>Start Conversion</Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {filtered.length} job{filtered.length !== 1 ? "s" : ""}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <HistoryTable
              jobs={paged}
              onOpen={handleOpen}
              onDownload={handleDownload}
              onDelete={setDeleteTarget}
              deletePending={deleteJob.isPending}
            />
          </CardContent>
        </Card>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2" role="navigation" aria-label="Pagination">
          <Button
            variant="outline"
            size="sm"
            disabled={safePage === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            aria-label="Previous page"
          >
            Previous
          </Button>
          {Array.from({ length: totalPages }, (_, i) => (
            <Button
              key={i}
              variant={i === safePage ? "default" : "outline"}
              size="sm"
              onClick={() => setPage(i)}
              aria-label={`Page ${i + 1}`}
              aria-current={i === safePage ? "page" : undefined}
            >
              {i + 1}
            </Button>
          ))}
          <Button
            variant="outline"
            size="sm"
            disabled={safePage >= totalPages - 1}
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            aria-label="Next page"
          >
            Next
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete Job"
        message={`Are you sure you want to delete the job for "${deleteTarget?.paper_name || "Untitled"}"? This will remove the workspace files.`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        confirmLabel="Delete"
      />
    </PageContainer>
  );
}
