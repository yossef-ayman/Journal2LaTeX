import { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { PageContainer } from "@/components/PageContainer";
import { SectionTitle } from "@/components/SectionTitle";
import { Card, CardContent } from "@/components/ui/card";
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
  ArrowRight,
  FileText,
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
  { value: "all", label: "All statuses" },
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
      <table className="w-full" role="table">
        <thead>
          <tr className="border-b border-gray-100">
            <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide" scope="col">Paper</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide" scope="col">Template</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide" scope="col">Status</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide" scope="col">Compile</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide hidden md:table-cell" scope="col">Progress</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide hidden sm:table-cell" scope="col">Created</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide" scope="col">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {jobs.map((j) => (
            <tr
              key={j.job_id}
              className="group transition-colors hover:bg-emerald-50/40"
            >
              <td className="px-5 py-4">
                <button
                  type="button"
                  onClick={() => onOpen(j.job_id)}
                  className="flex items-center gap-3 text-left group/btn"
                  aria-label={`Open ${j.paper_name || "Untitled"}`}
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 border border-emerald-100">
                    <FileText size={13} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900 group-hover/btn:text-emerald-700 transition-colors max-w-[160px] truncate">
                      {j.paper_name || "Untitled"}
                    </p>
                    <p className="text-[11px] text-gray-400 font-mono mt-0.5">
                      {j.job_id.slice(0, 8)}…
                    </p>
                  </div>
                </button>
              </td>
              <td className="px-4 py-4">
                <span className="text-xs text-gray-500 bg-gray-100 rounded px-2 py-1 font-mono">
                  {j.template_name || "—"}
                </span>
              </td>
              <td className="px-4 py-4">
                <StatusBadge status={j.status} />
              </td>
              <td className="px-4 py-4">
                {j.compile_success === true ? (
                  <div className="flex items-center gap-1.5">
                    <CheckCircle size={14} className="text-emerald-500" />
                    <span className="text-xs text-emerald-600 font-medium hidden lg:block">Pass</span>
                  </div>
                ) : j.compile_success === false ? (
                  <div className="flex items-center gap-1.5">
                    <XCircle size={14} className="text-red-500" />
                    <span className="text-xs text-red-600 font-medium hidden lg:block">Fail</span>
                  </div>
                ) : (
                  <span className="text-gray-300">—</span>
                )}
              </td>
              <td className="px-4 py-4 hidden md:table-cell">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 rounded-full bg-gray-100 max-w-[60px] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-emerald-400 transition-all"
                      style={{ width: `${j.progress}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 font-mono w-8">{j.progress}%</span>
                </div>
              </td>
              <td className="px-4 py-4 hidden sm:table-cell">
                <span className="text-xs text-gray-400">
                  {new Date(j.created_at).toLocaleDateString()}
                </span>
              </td>
              <td className="px-4 py-4">
                <div className="flex items-center justify-end gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => onOpen(j.job_id)}
                    aria-label={`View result for ${j.paper_name || "Untitled"}`}
                    className="h-7 w-7 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50"
                  >
                    <ExternalLink size={13} />
                  </Button>
                  {j.compile_success && (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => onDownload(j.job_id)}
                      aria-label={`Download PDF for ${j.paper_name || "Untitled"}`}
                      className="h-7 w-7 text-gray-400 hover:text-blue-600 hover:bg-blue-50"
                    >
                      <FileDown size={13} />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => onDelete(j)}
                    disabled={deletePending}
                    aria-label={`Delete ${j.paper_name || "Untitled"}`}
                    className="h-7 w-7 text-gray-400 hover:text-red-600 hover:bg-red-50"
                  >
                    <Trash2 size={13} />
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
        <SectionTitle title="Conversion History" description="View and manage your converted documents" />
        <SkeletonTable rows={5} />
      </PageContainer>
    );
  }

  if (isError) {
    return (
      <PageContainer>
        <SectionTitle title="Conversion History" />
        <Card>
          <CardContent className="flex flex-col items-center gap-5 py-20">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50 text-red-500">
              <XCircle size={32} />
            </div>
            <div className="text-center space-y-1">
              <p className="text-base font-semibold text-gray-900">Failed to load history</p>
              <p className="text-sm text-gray-500">Is the backend running?</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
              Try again
            </Button>
          </CardContent>
        </Card>
      </PageContainer>
    );
  }

  const completedCount = jobs?.filter(j => j.status === "COMPLETED").length ?? 0;
  const failedCount = jobs?.filter(j => j.status === "FAILED").length ?? 0;

  return (
    <PageContainer>
      <SectionTitle
        title="Conversion History"
        description="View and manage your previously converted documents"
        action={
          <Button size="sm" onClick={() => navigate("/upload")} className="gap-2">
            <ArrowRight size={14} />
            New Conversion
          </Button>
        }
      />

      {/* Summary Stats */}
      {jobs && jobs.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Total Jobs", value: jobs.length, color: "text-gray-900" },
            { label: "Completed", value: completedCount, color: "text-emerald-700" },
            { label: "Failed", value: failedCount, color: "text-red-600" },
          ].map(({ label, value, color }) => (
            <div key={label} className="rounded-2xl border border-gray-100 bg-white shadow-sm p-4 text-center">
              <p className={`text-2xl font-bold ${color}`}>{value}</p>
              <p className="text-xs text-gray-400 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
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
          className="h-9 appearance-none rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 cursor-pointer"
          aria-label="Filter by status"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <SortSelect options={SORT_OPTIONS} value={sort} onChange={(v) => { setSort(v); setPage(0); }} className="w-40" />
      </div>

      {filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-5 py-20">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-50 to-emerald-100 text-emerald-400">
              <History size={28} strokeWidth={1.5} />
            </div>
            <div className="text-center space-y-1.5">
              <h3 className="text-base font-semibold text-gray-900">
                {search || statusFilter !== "all" ? "No matching jobs" : "No conversions yet"}
              </h3>
              <p className="text-sm text-gray-500 max-w-xs leading-relaxed">
                {search || statusFilter !== "all"
                  ? "Try a different search term or filter."
                  : "Upload your first manuscript to get started."}
              </p>
            </div>
            {!search && statusFilter === "all" && (
              <Button size="sm" onClick={() => navigate("/upload")} className="gap-2">
                <ArrowRight size={14} />
                Start First Conversion
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-50">
            <span className="text-xs font-semibold text-gray-500">
              {filtered.length} job{filtered.length !== 1 ? "s" : ""} found
            </span>
          </div>
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

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2" role="navigation" aria-label="Pagination">
          <Button
            variant="outline"
            size="sm"
            disabled={safePage === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            aria-label="Previous page"
          >
            ← Previous
          </Button>
          <div className="flex items-center gap-1">
            {Array.from({ length: totalPages }, (_, i) => (
              <button
                key={i}
                onClick={() => setPage(i)}
                aria-label={`Page ${i + 1}`}
                aria-current={i === safePage ? "page" : undefined}
                className={`h-8 w-8 rounded-lg text-sm font-medium transition-all ${
                  i === safePage
                    ? "bg-emerald-600 text-white shadow-sm"
                    : "text-gray-500 hover:bg-gray-100"
                }`}
              >
                {i + 1}
              </button>
            ))}
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled={safePage >= totalPages - 1}
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            aria-label="Next page"
          >
            Next →
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
