import { useState, useCallback, useRef, memo } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { PageContainer } from "@/components/PageContainer";
import { SectionTitle } from "@/components/SectionTitle";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { useToast } from "@/components/Toast";
import { SkeletonCard } from "@/components/Skeleton";
import { Upload, AlertCircle, Loader2, FileWarning, Clock, X, Trash2, Sparkles, CheckCircle2, Info } from "lucide-react";
import { cn } from "@/utils/cn";
import { useTemplates, useUploadMutation, useConvertMutation, useUploadTemplateMutation } from "@/hooks";

const MAX_FILE_SIZE = 50 * 1024 * 1024;
const ALLOWED_EXT = ".docx,.doc";

interface ValidationError {
  type: "extension" | "size";
  message: string;
}

function validateFile(file: File): ValidationError | null {
  const lower = file.name.toLowerCase();
  if (!lower.endsWith(".docx") && !lower.endsWith(".doc")) {
    return { type: "extension", message: "Only .docx and .doc files are supported." };
  }
  if (file.size > MAX_FILE_SIZE) {
    return { type: "size", message: `File size exceeds ${MAX_FILE_SIZE / 1024 / 1024}MB limit.` };
  }
  return null;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const PROCESSING_ESTIMATES: Record<string, string> = {
  small: "~15 seconds",
  medium: "~30 seconds",
  large: "~60 seconds",
};

function estimateProcessingSize(bytes: number): string {
  if (bytes < 500 * 1024) return PROCESSING_ESTIMATES.small;
  if (bytes < 5 * 1024 * 1024) return PROCESSING_ESTIMATES.medium;
  return PROCESSING_ESTIMATES.large;
}

const FileCard = memo(function FileCard({
  file,
  onRemove,
  onReplace,
}: {
  file: File;
  onRemove: () => void;
  onReplace: () => void;
}) {
  return (
    <div className="animate-scale-in rounded-2xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-white p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4 min-w-0">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 text-white font-bold text-xs shadow-sm shadow-emerald-200">
            DOCX
          </div>
          <div className="min-w-0 space-y-1.5">
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold text-gray-900 truncate max-w-[260px] sm:max-w-[400px]">
                {file.name}
              </p>
              <CheckCircle2 size={15} className="shrink-0 text-emerald-500" />
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-gray-400">
              <span className="font-mono bg-gray-100 rounded px-1.5 py-0.5">{formatFileSize(file.size)}</span>
              <span className="flex items-center gap-1">
                <Clock size={11} />
                {estimateProcessingSize(file.size)}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={onReplace}
            aria-label="Replace file"
            className="text-xs h-8"
          >
            Replace
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onRemove}
            aria-label="Remove file"
            className="text-gray-400 hover:text-red-600 hover:bg-red-50"
          >
            <X size={14} />
          </Button>
        </div>
      </div>
    </div>
  );
});

export default function UploadPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [template, setTemplate] = useState("default");
  const [validationError, setValidationError] = useState<ValidationError | null>(null);
  const { toast } = useToast();

  const templates = useTemplates();
  const upload = useUploadMutation();
  const convert = useConvertMutation();
  const templateUpload = useUploadTemplateMutation();
  const templateInputRef = useRef<HTMLInputElement>(null);

  const handleTemplateUploadClick = () => {
    templateInputRef.current?.click();
  };

  const handleTemplateFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    try {
      toast({ type: "info", title: "Uploading template...", message: f.name });
      const uploadedTemplate = await templateUpload.mutateAsync(f);
      toast({ type: "success", title: "Template uploaded", message: uploadedTemplate.display_name || "Custom Template ready" });
      setTemplate(uploadedTemplate.template_id);
    } catch (err: any) {
      toast({
        type: "error",
        title: "Template upload failed",
        message: err.response?.data?.detail || "Make sure the file is a valid LaTeX ZIP package.",
      });
    }
  };

  const isProcessing = upload.isPending || convert.isPending;
  const apiError = upload.error || convert.error;

  const handleFile = useCallback((f: File) => {
    const err = validateFile(f);
    if (err) {
      setFile(null);
      setValidationError(err);
    } else {
      setFile(f);
      setValidationError(null);
    }
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const onDragLeave = useCallback(() => setDragOver(false), []);

  const onBrowse = () => inputRef.current?.click();

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  };

  const onSubmit = async () => {
    if (!file) return;
    try {
      toast({ type: "info", title: "Uploading...", message: file.name });
      const uploaded = await upload.mutateAsync(file);
      toast({ type: "success", title: "Upload completed", message: "Starting conversion..." });
      await convert.mutateAsync({
        job_id: uploaded.job_id,
        template_id: template,
      } as const);
      navigate(`/processing/${uploaded.job_id}`);
    } catch {
      toast({ type: "error", title: "Conversion failed", message: "Check your file and try again." });
    }
  };

  const handleClear = () => {
    setFile(null);
    setValidationError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleReplace = () => {
    onBrowse();
  };

  if (templates.isLoading) {
    return (
      <PageContainer>
        <SectionTitle title="Upload Document" description="Upload an academic manuscript to convert to LaTeX" />
        <SkeletonCard lines={5} />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <SectionTitle
        title="Upload Document"
        description="Upload your academic .docx manuscript to start the LaTeX conversion pipeline"
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main upload card */}
        <div className="lg:col-span-2 space-y-5">
          <Card>
            <CardHeader className="pb-4 border-b border-gray-50">
              <CardTitle className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-100">
                  <Upload size={13} className="text-emerald-700" />
                </div>
                Document Upload
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 pt-5">
              {/* Drop Zone */}
              {!file ? (
                <div
                  onDrop={onDrop}
                  onDragOver={onDragOver}
                  onDragLeave={onDragLeave}
                  onClick={onBrowse}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onBrowse(); }}
                  role="button"
                  tabIndex={0}
                  aria-label="Upload DOCX file"
                  className={cn(
                    "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-8 py-14 text-center transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500",
                    dragOver
                      ? "border-emerald-400 bg-emerald-50 scale-[0.99]"
                      : validationError
                        ? "border-red-300 bg-red-50/40"
                        : "border-gray-200 hover:border-emerald-300 hover:bg-emerald-50/30",
                  )}
                >
                  <div
                    className={cn(
                      "mb-5 flex h-14 w-14 items-center justify-center rounded-2xl transition-colors shadow-sm",
                      dragOver
                        ? "bg-emerald-100 text-emerald-600"
                        : validationError
                          ? "bg-red-100 text-red-500"
                          : "bg-gradient-to-br from-gray-100 to-gray-50 text-gray-500",
                    )}
                  >
                    {validationError ? (
                      <FileWarning size={24} />
                    ) : dragOver ? (
                      <Sparkles size={24} />
                    ) : (
                      <Upload size={24} />
                    )}
                  </div>
                  <h3 className="mb-1.5 text-base font-semibold text-gray-900">
                    {dragOver ? "Drop your manuscript here" : "Drag & drop your manuscript"}
                  </h3>
                  <p className="mb-5 text-sm text-gray-400">
                    or click to browse files from your computer
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={(e) => { e.stopPropagation(); onBrowse(); }}
                    aria-label="Browse files"
                    className="h-9"
                  >
                    Browse Files
                  </Button>
                  <div className="mt-6 flex items-center gap-4 text-[11px] text-gray-400 font-mono">
                    <span className="flex items-center gap-1.5">
                      <span className="h-1 w-1 rounded-full bg-gray-300" />
                      Format: .docx
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-1 w-1 rounded-full bg-gray-300" />
                      Max: {MAX_FILE_SIZE / 1024 / 1024}MB
                    </span>
                  </div>
                </div>
              ) : (
                <FileCard file={file} onRemove={handleClear} onReplace={handleReplace} />
              )}

              <input
                ref={inputRef}
                type="file"
                accept={ALLOWED_EXT}
                className="hidden"
                onChange={onFileChange}
                aria-hidden="true"
              />

              {validationError && (
                <div className="animate-fade-in flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  <AlertCircle size={16} className="shrink-0" />
                  <span>{validationError.message}</span>
                </div>
              )}

              {/* Template Selection */}
              <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 space-y-3">
                <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
                  <div className="flex-1 space-y-1.5">
                    <Label htmlFor="template" className="text-xs font-semibold text-gray-700">
                      Target LaTeX Template
                    </Label>
                    <Select value={template} onValueChange={setTemplate}>
                      <SelectTrigger id="template" className="h-9 text-sm bg-white">
                        <SelectValue>
                          {templates.data?.find((t) => t.template_id === template)
                            ?.display_name ?? templates.data?.find((t) => t.template_id === template)
                            ?.journal_title ?? template}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {templates.data?.map((t) => (
                          <SelectItem key={t.template_id} value={t.template_id} className="text-sm">
                            {t.display_name || t.journal_title || t.template_id}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleTemplateUploadClick}
                    disabled={templateUpload.isPending}
                    aria-label="Upload custom template ZIP"
                    className="h-9 shrink-0"
                  >
                    {templateUpload.isPending ? "Uploading..." : "Upload Custom ZIP"}
                  </Button>
                </div>
                <input
                  ref={templateInputRef}
                  type="file"
                  accept=".zip"
                  className="hidden"
                  onChange={handleTemplateFileChange}
                  aria-hidden="true"
                />
              </div>

              {apiError && (
                <div className="animate-fade-in flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  <AlertCircle size={16} className="shrink-0" />
                  <span>{apiError.message}</span>
                </div>
              )}

              <div className="flex justify-end gap-2.5 pt-2 border-t border-gray-100">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClear}
                  disabled={(!file && !validationError) || isProcessing}
                  className="h-9"
                >
                  <Trash2 size={14} />
                  Clear
                </Button>
                <Button
                  onClick={onSubmit}
                  disabled={!file || isProcessing}
                  size="sm"
                  className="h-9 px-6 gap-2"
                >
                  {isProcessing ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Upload size={14} />
                  )}
                  {isProcessing ? "Processing..." : "Start Conversion"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar info cards */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3 border-b border-gray-50">
              <CardTitle className="text-xs font-bold uppercase tracking-widest text-gray-400">
                Supported Format
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3 rounded-xl border border-emerald-100 bg-emerald-50 px-3.5 py-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600 text-white font-bold text-[10px]">
                  W
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">.docx</p>
                  <p className="text-[11px] text-gray-500">Microsoft Word Document</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3 border-b border-gray-50">
              <CardTitle className="text-xs font-bold uppercase tracking-widest text-gray-400">
                Requirements
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-3">
              {[
                { label: "Maximum File Size", value: "50 MB" },
                { label: "Supported Inputs", value: "DOCX Manuscripts" },
                { label: "Estimated Duration", value: "15 – 60 seconds" },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">{label}</span>
                  <span className="font-mono text-xs font-semibold text-gray-900 bg-gray-100 rounded px-2 py-0.5">{value}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-emerald-100 bg-gradient-to-br from-emerald-50 to-white">
            <CardContent className="pt-5 pb-4">
              <div className="flex items-start gap-3">
                <Info size={15} className="text-emerald-600 shrink-0 mt-0.5" />
                <p className="text-xs text-emerald-700 leading-relaxed">
                  For best results, ensure your document has proper heading styles and embedded media.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}
