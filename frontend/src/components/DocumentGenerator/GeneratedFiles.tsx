/**
 * The result of a generation run: one row per paper, with every produced file.
 *
 * Downloads are plain anchors to the backend rather than fetch-and-blob, so a
 * twenty-paper ZIP streams straight to disk instead of through the browser's
 * memory.
 */

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  Download,
  FileText,
  Package,
  ShieldCheck,
  X,
} from "lucide-react";
import {
  absoluteUrl,
  type BatchSummary,
  type DocumentValidation,
  type GeneratedArtifact,
} from "@/services/documentGenerator";

function formatSize(bytes: number): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ArtifactLink({ artifact }: { artifact: GeneratedArtifact }) {
  const isPdf = artifact.format === "pdf";
  return (
    <a
      href={absoluteUrl(artifact.download_url)}
      className={
        "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors " +
        (isPdf
          ? "border-red-200 bg-red-50 text-red-700 hover:bg-red-100"
          : "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100")
      }
      title={`${artifact.filename} · ${formatSize(artifact.size_bytes)}`}
    >
      <FileText size={12} />
      {artifact.filename}
    </a>
  );
}

/**
 * The per-document validation report.
 *
 * Collapsed by default and opened by a click: on a clean batch this is a single
 * reassuring line, and the operator only needs the fifteen individual checks
 * when one of them failed. A failing report opens itself, because a document
 * that did not match its template is the one thing here that cannot wait to be
 * noticed.
 */
function ValidationReport({ validations }: { validations: DocumentValidation[] }) {
  const failed = validations.filter((v) => !v.valid);
  const [open, setOpen] = useState(failed.length > 0);
  if (validations.length === 0) return null;

  return (
    <div className="pt-1">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className={
          "inline-flex items-center gap-1.5 text-xs font-medium " +
          (failed.length > 0
            ? "text-red-700 hover:text-red-800"
            : "text-emerald-700 hover:text-emerald-800")
        }
      >
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <ShieldCheck size={12} />
        {failed.length > 0
          ? `${failed.length} document${failed.length === 1 ? "" : "s"} did not match the template`
          : "Verified against the template"}
      </button>

      {open && (
        <div className="mt-2 space-y-3 rounded-lg bg-gray-50 px-3 py-2.5">
          {validations.map((validation) => (
            <div key={validation.document} className="space-y-1">
              <p className="text-xs font-medium text-gray-700">
                {validation.document}
              </p>
              <ul className="grid gap-x-4 gap-y-0.5 sm:grid-cols-2">
                {Object.entries(validation.checks).map(([check, passed]) => (
                  <li
                    key={check}
                    className={
                      "flex items-center gap-1.5 text-[11px] " +
                      (passed ? "text-gray-500" : "text-red-700")
                    }
                  >
                    {passed ? (
                      <Check size={11} className="shrink-0 text-emerald-600" />
                    ) : (
                      <X size={11} className="shrink-0" />
                    )}
                    {check}
                  </li>
                ))}
              </ul>
              {validation.errors.map((error) => (
                <p key={error} className="text-[11px] text-red-700">
                  {error}
                </p>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function GeneratedFiles({ summary }: { summary: BatchSummary }) {
  return (
    <Card>
      <CardContent className="p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900 leading-none">
                {summary.document_count} document
                {summary.document_count === 1 ? "" : "s"} generated
              </h3>
              <Badge variant="success">
                {summary.paper_count} paper{summary.paper_count === 1 ? "" : "s"}
              </Badge>
            </div>
            <p className="text-xs text-gray-500">
              Batch <span className="font-mono">{summary.batch_id}</span>
              {summary.pdf_backend ? ` · PDFs via ${summary.pdf_backend}` : ""}
            </p>
          </div>
          {summary.zip_available && summary.zip_download_url && (
            <Button asChild size="lg">
              <a href={absoluteUrl(summary.zip_download_url)}>
                <Package size={15} /> Download ZIP
              </a>
            </Button>
          )}
        </div>

        {summary.warnings.length > 0 && (
          <div className="rounded-lg bg-amber-50 px-3 py-2 space-y-1">
            {summary.warnings.map((warning) => (
              <p
                key={warning}
                className="flex items-start gap-1.5 text-xs text-amber-800"
              >
                <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                {warning}
              </p>
            ))}
          </div>
        )}

        <div className="divide-y divide-gray-100 rounded-xl border border-gray-100">
          {summary.documents.map((set) => (
            <div key={set.folder} className="space-y-2 p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div className="min-w-0 space-y-0.5">
                  <p className="flex items-center gap-2 text-sm font-medium text-gray-900">
                    <span className="text-gray-400">{set.folder}</span>
                    <span className="font-mono text-xs text-emerald-700">
                      {set.paper.reference_number}
                    </span>
                  </p>
                  <p className="truncate text-sm text-gray-700" title={set.paper.title}>
                    {set.paper.title}
                  </p>
                  <p className="truncate text-xs text-gray-400">
                    {set.paper.authors.length > 0
                      ? set.paper.authors.join(", ")
                      : "No authors detected"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {set.artifacts.map((artifact) => (
                    <ArtifactLink key={artifact.relative_path} artifact={artifact} />
                  ))}
                </div>
              </div>

              <ValidationReport validations={set.validations} />

              {(set.errors.length > 0 || set.paper.warnings.length > 0) && (
                <div className="space-y-1 pt-1">
                  {set.errors.map((error) => (
                    <p key={error} className="text-xs text-red-700">
                      {error}
                    </p>
                  ))}
                  {set.paper.warnings.map((warning) => (
                    <p key={warning} className="text-xs text-amber-700">
                      {warning}
                    </p>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        <p className="flex items-center gap-1.5 text-[11px] text-gray-400">
          <Download size={12} />
          Every file is also inside the ZIP, arranged as Output / {summary.documents[0]?.folder ?? "Paper 1"} / …
        </p>
      </CardContent>
    </Card>
  );
}
