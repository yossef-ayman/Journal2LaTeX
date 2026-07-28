import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { PageContainer } from "@/components/PageContainer";
import { SectionTitle } from "@/components/SectionTitle";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { SkeletonCard } from "@/components/Skeleton";
import { useToast } from "@/components/Toast";
import {
  listTemplateFiles,
  readTemplateFile,
  writeTemplateFile,
  deleteTemplateFile,
  validateTemplate,
  getTemplateDownloadUrl,
  type TemplateFileEntry,
  type TemplateFileContent,
  type TemplateValidationReport,
} from "@/services/templateEditor";
import {
  ArrowLeft,
  Download,
  FileText,
  FileCode,
  FileImage,
  File as FileIcon,
  Folder,
  Save,
  Trash2,
  Plus,
  UploadCloud,
  ShieldCheck,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Lock,
} from "lucide-react";

const IMAGE_EXTENSIONS = new Set(["png", "jpg", "jpeg", "gif", "svg", "bmp", "webp"]);
const CODE_EXTENSIONS = new Set(["tex", "cls", "sty", "bst", "bib", "def", "clo", "cfg"]);

function extension(path: string): string {
  const i = path.lastIndexOf(".");
  return i >= 0 ? path.slice(i + 1).toLowerCase() : "";
}

function fileIcon(entry: TemplateFileEntry) {
  if (entry.type === "dir") return <Folder size={14} className="text-amber-500" />;
  const ext = extension(entry.path);
  if (IMAGE_EXTENSIONS.has(ext)) return <FileImage size={14} className="text-violet-500" />;
  if (CODE_EXTENSIONS.has(ext)) return <FileCode size={14} className="text-emerald-600" />;
  if (entry.is_text) return <FileText size={14} className="text-sky-600" />;
  return <FileIcon size={14} className="text-gray-400" />;
}

function formatSize(size: number | null): string {
  if (size === null) return "";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function mimeFor(path: string): string {
  const ext = extension(path);
  if (ext === "svg") return "image/svg+xml";
  if (ext === "jpg" || ext === "jpeg") return "image/jpeg";
  return `image/${ext}`;
}

function ValidationPanel({ report }: { report: TemplateValidationReport }) {
  return (
    <div
      className={
        "rounded-xl border p-4 text-sm space-y-2 " +
        (report.valid ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50")
      }
    >
      <div className="flex items-center gap-2 font-semibold">
        {report.valid ? (
          <>
            <CheckCircle size={15} className="text-emerald-600" />
            <span className="text-emerald-700">Template is valid and ready for conversion</span>
          </>
        ) : (
          <>
            <XCircle size={15} className="text-red-600" />
            <span className="text-red-700">Template has problems</span>
          </>
        )}
      </div>
      <ul className="space-y-1">
        {report.checks.map((c) => (
          <li key={c.name} className="flex items-start gap-1.5 text-xs">
            {c.ok ? (
              <CheckCircle size={12} className="mt-0.5 shrink-0 text-emerald-500" />
            ) : (
              <XCircle size={12} className="mt-0.5 shrink-0 text-red-500" />
            )}
            <span className={c.ok ? "text-gray-600" : "text-red-700"}>
              <span className="font-medium">{c.name}</span>: {c.detail}
            </span>
          </li>
        ))}
      </ul>
      {report.warnings.map((w) => (
        <p key={w} className="flex items-start gap-1.5 text-xs text-amber-700">
          <AlertTriangle size={12} className="mt-0.5 shrink-0" /> {w}
        </p>
      ))}
    </div>
  );
}

export default function TemplateEditorPage() {
  const { templateId = "" } = useParams();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const filesQuery = useQuery({
    queryKey: ["template-files", templateId],
    queryFn: () => listTemplateFiles(templateId),
    enabled: templateId !== "",
    staleTime: 0,
    refetchOnMount: "always",
  });

  const [selected, setSelected] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [readOnly, setReadOnly] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);
  const [newFileName, setNewFileName] = useState("");
  const [showNewFile, setShowNewFile] = useState(false);
  const [report, setReport] = useState<TemplateValidationReport | null>(null);
  const [validating, setValidating] = useState(false);
  const replaceInputRef = useRef<HTMLInputElement>(null);

  // File contents live in the query cache (not local state) so that a write,
  // replace or delete can invalidate them exactly like the tree.
  const fileQuery = useQuery<TemplateFileContent>({
    queryKey: ["template-file", templateId, selected],
    queryFn: () => readTemplateFile(templateId, selected as string),
    enabled: templateId !== "" && selected !== null,
    staleTime: 0,
    gcTime: 0,
  });
  const fileContent = fileQuery.data ?? null;
  const loadingFile = fileQuery.isFetching && !fileQuery.data;

  const dirty = fileContent?.encoding === "text" && draft !== fileContent.content;

  const files = useMemo(
    () => (filesQuery.data ?? []).filter((f) => f.type === "file"),
    [filesQuery.data],
  );

  // Surface read failures without swallowing them.
  useEffect(() => {
    if (fileQuery.isError) {
      toast({
        type: "error",
        title: "Could not open file",
        message:
          fileQuery.error instanceof Error ? fileQuery.error.message : selected ?? "",
      });
    }
  }, [fileQuery.isError, fileQuery.error, selected, toast]);

  // Keep the editable draft in sync with server truth for the selected file.
  useEffect(() => {
    if (fileContent) {
      setDraft(fileContent.encoding === "text" ? fileContent.content : "");
    }
  }, [fileContent]);

  /**
   * Refetch the tree and the affected file, and wait for both to land before
   * the caller continues. `refetchType: "active"` forces the mounted queries
   * to re-run rather than merely being marked stale.
   */
  const refresh = useCallback(
    (path?: string | null) =>
      Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["template-files", templateId],
          refetchType: "active",
        }),
        queryClient.invalidateQueries({
          queryKey: path
            ? ["template-file", templateId, path]
            : ["template-file", templateId],
          refetchType: "active",
        }),
      ]),
    [queryClient, templateId],
  );

  const openFile = useCallback((path: string) => {
    setSelected(path);
  }, []);

  // Select the template entry file on first load, and self-heal if the current
  // selection disappears (deleted elsewhere, or removed from the tree).
  useEffect(() => {
    if (!files.length) return;
    if (selected && files.some((f) => f.path === selected)) return;
    const entry =
      files.find((f) => f.path === "template.tex") ??
      files.find((f) => extension(f.path) === "tex") ??
      files[0];
    setSelected(entry.path);
  }, [files, selected]);

  const save = async () => {
    if (!fileContent || fileContent.encoding !== "text") return;
    setSaving(true);
    try {
      await writeTemplateFile(templateId, fileContent.path, draft);
      // Re-read server truth instead of optimistically patching local state:
      // the backend reports the real byte size and any normalization it did.
      await refresh(fileContent.path);
      toast({ type: "success", title: "Saved", message: fileContent.path });
      setReadOnly(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Save failed";
      if (message.toLowerCase().includes("read-only")) setReadOnly(true);
      toast({ type: "error", title: "Save failed", message });
    } finally {
      setSaving(false);
    }
  };

  const removeFile = async (path: string) => {
    try {
      await deleteTemplateFile(templateId, path);
      if (selected === path) setSelected(null);
      queryClient.removeQueries({ queryKey: ["template-file", templateId, path] });
      await refresh(path);
      toast({ type: "success", title: "Deleted", message: path });
    } catch (err: unknown) {
      toast({
        type: "error",
        title: "Delete failed",
        message: err instanceof Error ? err.message : path,
      });
    }
  };

  const addFile = async () => {
    const name = newFileName.trim().replace(/^\/+/, "");
    if (!name) return;
    try {
      await writeTemplateFile(templateId, name, "");
      setNewFileName("");
      setShowNewFile(false);
      await refresh(name);
      openFile(name);
      toast({ type: "success", title: "File created", message: name });
    } catch (err: unknown) {
      toast({
        type: "error",
        title: "Could not create file",
        message: err instanceof Error ? err.message : name,
      });
    }
  };

  const replaceBinary = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !fileContent) return;
    const buffer = await file.arrayBuffer();
    let binary = "";
    const bytes = new Uint8Array(buffer);
    for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
    const b64 = btoa(binary);
    try {
      await writeTemplateFile(templateId, fileContent.path, b64, "base64");
      await refresh(fileContent.path);
      toast({ type: "success", title: "File replaced", message: fileContent.path });
    } catch (err: unknown) {
      toast({
        type: "error",
        title: "Replace failed",
        message: err instanceof Error ? err.message : fileContent.path,
      });
    }
  };

  const runValidation = async () => {
    setValidating(true);
    try {
      setReport(await validateTemplate(templateId));
    } catch (err: unknown) {
      toast({
        type: "error",
        title: "Validation request failed",
        message: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setValidating(false);
    }
  };

  const isImage = fileContent && IMAGE_EXTENSIONS.has(extension(fileContent.path));

  return (
    <PageContainer>
      <SectionTitle
        title="Template Editor"
        description={templateId}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <Button asChild size="sm" variant="ghost">
              <Link to="/templates">
                <ArrowLeft size={14} />
                All templates
              </Link>
            </Button>
            <Button size="sm" variant="outline" onClick={runValidation} disabled={validating}>
              <ShieldCheck size={14} />
              {validating ? "Validating..." : "Validate"}
            </Button>
            <Button asChild size="sm" variant="outline">
              <a href={getTemplateDownloadUrl(templateId)} download>
                <Download size={14} />
                Download ZIP
              </a>
            </Button>
          </div>
        }
      />

      {readOnly && (
        <div className="mb-4 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
          <Lock size={14} />
          This is a built-in template and is read-only. Download it, then upload a copy to edit.
        </div>
      )}

      {report && (
        <div className="mb-4">
          <ValidationPanel report={report} />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        {/* File tree */}
        <Card className="self-start">
          <CardContent className="p-3">
            <div className="mb-2 flex items-center justify-between px-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                Files
              </p>
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-2"
                onClick={() => setShowNewFile((v) => !v)}
                title="Add file"
              >
                <Plus size={13} />
              </Button>
            </div>

            {showNewFile && (
              <div className="mb-2 flex items-center gap-1.5 px-1">
                <Input
                  value={newFileName}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewFileName(e.target.value)}
                  onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                    if (e.key === "Enter") addFile();
                    if (e.key === "Escape") setShowNewFile(false);
                  }}
                  placeholder="path/newfile.sty"
                  className="h-8 text-xs"
                  autoFocus
                />
                <Button size="sm" className="h-8 px-2.5" onClick={addFile}>
                  Add
                </Button>
              </div>
            )}

            {filesQuery.isLoading ? (
              <SkeletonCard lines={6} />
            ) : filesQuery.isError ? (
              <p className="px-1 text-sm text-red-600">Failed to load files.</p>
            ) : (
              <ul className="max-h-[520px] space-y-0.5 overflow-y-auto">
                {files.map((f) => (
                  <li key={f.path} className="group flex items-center">
                    <button
                      type="button"
                      onClick={() => openFile(f.path)}
                      className={
                        "flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs transition-colors " +
                        (selected === f.path
                          ? "bg-emerald-50 font-medium text-emerald-800"
                          : "text-gray-700 hover:bg-gray-50")
                      }
                    >
                      {fileIcon(f)}
                      <span className="truncate">{f.path}</span>
                      <span className="ml-auto shrink-0 text-[10px] text-gray-400">
                        {formatSize(f.size)}
                      </span>
                    </button>
                    <button
                      type="button"
                      className="ml-1 hidden rounded p-1 text-gray-300 hover:text-red-500 group-hover:block"
                      onClick={() => setPendingDelete(f.path)}
                      title={`Delete ${f.path}`}
                    >
                      <Trash2 size={12} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Content pane */}
        <Card>
          <CardContent className="p-4">
            {loadingFile ? (
              <SkeletonCard lines={8} />
            ) : !fileContent ? (
              <p className="py-16 text-center text-sm text-gray-400">
                Select a file to preview or edit it.
              </p>
            ) : (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <p className="truncate font-mono text-sm font-medium text-gray-900">
                      {fileContent.path}
                    </p>
                    <span className="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-500">
                      {formatSize(fileContent.size)}
                    </span>
                    {dirty && (
                      <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                        unsaved
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      ref={replaceInputRef}
                      type="file"
                      className="hidden"
                      onChange={replaceBinary}
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => replaceInputRef.current?.click()}
                      title="Replace this file with an uploaded one"
                    >
                      <UploadCloud size={13} />
                      Replace
                    </Button>
                    {fileContent.encoding === "text" && (
                      <Button size="sm" onClick={save} disabled={!dirty || saving}>
                        <Save size={13} />
                        {saving ? "Saving..." : "Save"}
                      </Button>
                    )}
                  </div>
                </div>

                {fileContent.encoding === "text" ? (
                  <textarea
                    value={draft}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDraft(e.target.value)}
                    spellCheck={false}
                    className="h-[480px] w-full resize-y rounded-xl border border-gray-200 bg-gray-50 p-3 font-mono text-xs leading-relaxed text-gray-800 focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-100"
                  />
                ) : isImage ? (
                  <div className="flex items-center justify-center rounded-xl border border-gray-200 bg-[repeating-conic-gradient(#f8fafc_0%_25%,#f1f5f9_0%_50%)] bg-[length:16px_16px] p-6">
                    <img
                      src={`data:${mimeFor(fileContent.path)};base64,${fileContent.content}`}
                      alt={fileContent.path}
                      className="max-h-[440px] max-w-full rounded-lg shadow-sm"
                    />
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 py-16 text-center text-sm text-gray-400">
                    Binary file — no inline preview. Use Replace to update it, or
                    download the template ZIP.
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete file?"
        message={`"${pendingDelete ?? ""}" will be removed from this template.`}
        onConfirm={() => {
          if (pendingDelete) removeFile(pendingDelete);
          setPendingDelete(null);
        }}
        onCancel={() => setPendingDelete(null)}
      />
    </PageContainer>
  );
}
