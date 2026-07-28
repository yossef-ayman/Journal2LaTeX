import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PageContainer } from "@/components/PageContainer";
import { SectionTitle } from "@/components/SectionTitle";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/EmptyState";
import { SkeletonCard } from "@/components/Skeleton";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useToast } from "@/components/Toast";
import { useTemplates } from "@/hooks";
import { uploadTemplate, deleteTemplate } from "@/services";
import {
  validateTemplate,
  getTemplateDownloadUrl,
  type TemplateValidationReport,
} from "@/services/templateEditor";
import type { TemplateMetadata } from "@/types";
import {
  FileArchive,
  Upload,
  Download,
  Pencil,
  Trash2,
  ShieldCheck,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Lock,
} from "lucide-react";

function templateKey(t: TemplateMetadata): string {
  return t.template_id || t.name || "";
}

function ValidationResult({ report }: { report: TemplateValidationReport }) {
  return (
    <div
      className={
        "mt-3 rounded-xl border p-3 text-sm space-y-2 " +
        (report.valid
          ? "border-emerald-200 bg-emerald-50"
          : "border-red-200 bg-red-50")
      }
    >
      <div className="flex items-center gap-2 font-medium">
        {report.valid ? (
          <>
            <CheckCircle size={15} className="text-emerald-600" />
            <span className="text-emerald-700">Template is valid</span>
          </>
        ) : (
          <>
            <XCircle size={15} className="text-red-600" />
            <span className="text-red-700">Validation failed</span>
          </>
        )}
      </div>
      {report.errors.map((e) => (
        <p key={e} className="flex items-start gap-1.5 text-red-700">
          <XCircle size={13} className="mt-0.5 shrink-0" /> {e}
        </p>
      ))}
      {report.warnings.map((w) => (
        <p key={w} className="flex items-start gap-1.5 text-amber-700">
          <AlertTriangle size={13} className="mt-0.5 shrink-0" /> {w}
        </p>
      ))}
    </div>
  );
}

export default function TemplatesPage() {
  const templates = useTemplates();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [pendingDelete, setPendingDelete] = useState<TemplateMetadata | null>(null);
  const [validation, setValidation] = useState<Record<string, TemplateValidationReport>>({});
  const [validating, setValidating] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: uploadTemplate,
    onSuccess: async (meta) => {
      await queryClient.invalidateQueries({
        queryKey: ["templates"],
        refetchType: "active",
      });
      toast({
        type: "success",
        title: "Template uploaded",
        message: meta.display_name || meta.template_id,
      });
    },
    onError: (err: unknown) => {
      toast({
        type: "error",
        title: "Upload failed",
        message: err instanceof Error ? err.message : "Invalid template package",
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTemplate,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["templates"],
        refetchType: "active",
      });
      toast({ type: "success", title: "Template deleted" });
    },
    onError: (err: unknown) => {
      toast({
        type: "error",
        title: "Delete failed",
        message: err instanceof Error ? err.message : "Unknown error",
      });
    },
  });

  const handleValidate = async (id: string) => {
    setValidating(id);
    try {
      const report = await validateTemplate(id);
      setValidation((v) => ({ ...v, [id]: report }));
    } catch (err: unknown) {
      toast({
        type: "error",
        title: "Validation request failed",
        message: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setValidating(null);
    }
  };

  const onFilePicked = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadMutation.mutate(file);
    e.target.value = "";
  };

  return (
    <PageContainer>
      <SectionTitle
        title="Journal Templates"
        description="Upload, inspect, edit and validate journal ZIP templates"
        action={
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={onFilePicked}
            />
            <Button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
            >
              <Upload size={15} />
              {uploadMutation.isPending ? "Uploading..." : "Upload ZIP"}
            </Button>
          </>
        }
      />

      {templates.isLoading ? (
        <SkeletonCard lines={4} />
      ) : templates.isError ? (
        <p className="text-sm text-red-600">
          {templates.error instanceof Error
            ? templates.error.message
            : "Failed to load templates"}
        </p>
      ) : !templates.data?.length ? (
        <EmptyState
          icon={<FileArchive size={28} strokeWidth={1.5} />}
          title="No templates yet"
          description="Upload a journal ZIP template to get started."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {templates.data.map((t) => {
            const id = templateKey(t);
            const isUploaded = t.template_type === "uploaded";
            const report = validation[id];
            return (
              <Card key={id}>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-sm font-semibold text-gray-900">
                          {t.display_name || t.journal_title || t.name || id}
                        </p>
                        {isUploaded ? (
                          <span className="rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                            uploaded
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 border border-gray-200 px-2 py-0.5 text-[10px] font-medium text-gray-600">
                            <Lock size={9} /> built-in
                          </span>
                        )}
                      </div>
                      <p className="truncate text-xs text-gray-500">
                        {t.journal_name || t.journal_title || "—"} · v{t.version}
                        {t.class_file ? ` · ${t.class_file}` : ""}
                      </p>
                      {t.description && (
                        <p className="line-clamp-2 text-xs text-gray-400">{t.description}</p>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap items-center gap-2">
                    <Button asChild size="sm" variant="outline">
                      <Link to={`/templates/${encodeURIComponent(id)}`}>
                        <Pencil size={13} />
                        {isUploaded ? "Edit files" : "Browse files"}
                      </Link>
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleValidate(id)}
                      disabled={validating === id}
                    >
                      <ShieldCheck size={13} />
                      {validating === id ? "Validating..." : "Validate"}
                    </Button>
                    <Button asChild size="sm" variant="outline">
                      <a href={getTemplateDownloadUrl(id)} download>
                        <Download size={13} />
                        Download
                      </a>
                    </Button>
                    {isUploaded && (
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => setPendingDelete(t)}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 size={13} />
                        Delete
                      </Button>
                    )}
                  </div>

                  {report && <ValidationResult report={report} />}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete template?"
        message={`"${pendingDelete ? pendingDelete.display_name || templateKey(pendingDelete) : ""}" and all of its files will be permanently removed.`}
        onConfirm={() => {
          if (pendingDelete) deleteMutation.mutate(templateKey(pendingDelete));
          setPendingDelete(null);
        }}
        onCancel={() => setPendingDelete(null)}
      />
    </PageContainer>
  );
}
