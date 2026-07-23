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
import { Upload, FileText, AlertCircle, Loader2, FileWarning, Clock, X, Trash2 } from "lucide-react";
import { cn } from "@/utils/cn";
import { useTemplates, useUploadMutation, useConvertMutation, useUploadTemplateMutation } from "@/hooks";

const MAX_FILE_SIZE = 50 * 1024 * 1024;
const ALLOWED_EXT = ".docx";

interface ValidationError {
  type: "extension" | "size";
  message: string;
}

function validateFile(file: File): ValidationError | null {
  if (!file.name.toLowerCase().endsWith(ALLOWED_EXT)) {
    return { type: "extension", message: "Only .docx files are supported." };
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
    <div className="animate-fade-in rounded-xl border border-zinc-200 bg-zinc-50/80 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-white font-semibold text-xs shadow-2xs">
            DOCX
          </div>
          <div className="min-w-0 space-y-1">
            <p className="text-xs font-semibold text-zinc-900 truncate max-w-[280px] sm:max-w-[400px]">
              {file.name}
            </p>
            <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-500">
              <span className="font-mono text-[11px]">{formatFileSize(file.size)}</span>
              <span className="h-3 w-px bg-zinc-200" />
              <span className="flex items-center gap-1 text-[11px]">
                <Clock size={12} className="text-zinc-400" />
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
            size="icon"
            onClick={onRemove}
            aria-label="Remove file"
            className="h-8 w-8 text-zinc-400 hover:text-red-600 hover:bg-red-50"
          >
            <X size={15} />
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
        <SectionTitle title="Upload Document" />
        <SkeletonCard lines={5} />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <SectionTitle
        title="Upload Document"
        description="Upload an academic .docx manuscript to convert to LaTeX"
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card className="border-zinc-200 bg-white">
            <CardHeader className="pb-3 border-b border-zinc-100">
              <CardTitle className="text-sm font-semibold text-zinc-900">Document Upload</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6 pt-5">
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
                    "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition-all duration-200",
                    dragOver
                      ? "border-zinc-900 bg-zinc-50 scale-[0.99]"
                      : validationError
                        ? "border-red-300 bg-red-50/30"
                        : "border-zinc-200 hover:border-zinc-400 hover:bg-zinc-50/50",
                  )}
                >
                  <div
                    className={cn(
                      "mb-4 flex h-12 w-12 items-center justify-center rounded-full transition-colors",
                      validationError ? "bg-red-100 text-red-600" : "bg-zinc-100 text-zinc-800",
                    )}
                  >
                    {validationError ? (
                      <FileWarning size={22} />
                    ) : (
                      <Upload size={22} />
                    )}
                  </div>
                  <h3 className="mb-1 text-sm font-semibold text-zinc-900">
                    {dragOver ? "Drop your file here" : "Drag and drop your manuscript (.docx)"}
                  </h3>
                  <p className="mb-4 text-xs text-zinc-500">
                    or click to browse files from your computer
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={(e) => { e.stopPropagation(); onBrowse(); }}
                    aria-label="Browse files"
                    className="h-8 text-xs font-medium"
                  >
                    Browse Files
                  </Button>
                  <div className="mt-6 flex items-center gap-3 text-[11px] text-zinc-400 font-mono">
                    <span>Format: .docx</span>
                    <span className="h-3 w-px bg-zinc-200" />
                    <span>Max Size: {MAX_FILE_SIZE / 1024 / 1024}MB</span>
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
                <div className="animate-fade-in flex items-center gap-2 rounded-lg border border-red-200 bg-red-50/60 px-3.5 py-2.5 text-xs text-red-700">
                  <AlertCircle size={15} className="shrink-0" />
                  <span>{validationError.message}</span>
                </div>
              )}

              <div className="space-y-2 pt-2">
                <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
                  <div className="flex-1 space-y-1.5">
                    <Label htmlFor="template" className="text-xs font-semibold text-zinc-700">
                      Target LaTeX Template
                    </Label>
                    <div className="relative">
                      <Select value={template} onValueChange={setTemplate}>
                        <SelectTrigger id="template" className="h-9 text-xs border-zinc-200">
                          <SelectValue>
                            {templates.data?.find((t) => t.template_id === template)
                              ?.display_name ?? templates.data?.find((t) => t.template_id === template)
                              ?.journal_title ?? template}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {templates.data?.map((t) => (
                            <SelectItem key={t.template_id} value={t.template_id} className="text-xs">
                              {t.display_name || t.journal_title || t.template_id}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleTemplateUploadClick}
                    disabled={templateUpload.isPending}
                    aria-label="Upload custom template ZIP"
                    className="h-9 text-xs border-zinc-200 shrink-0"
                  >
                    {templateUpload.isPending ? "Uploading..." : "Upload Custom ZIP Template"}
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
                <div className="animate-fade-in flex items-center gap-2 rounded-lg border border-red-200 bg-red-50/60 px-3.5 py-2.5 text-xs text-red-700">
                  <AlertCircle size={15} className="shrink-0" />
                  <span>{apiError.message}</span>
                </div>
              )}

              <div className="flex justify-end gap-2.5 pt-2 border-t border-zinc-100">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClear}
                  disabled={(!file && !validationError) || isProcessing}
                  className="h-9 text-xs"
                >
                  <Trash2 size={13} />
                  Clear
                </Button>
                <Button
                  onClick={onSubmit}
                  disabled={!file || isProcessing}
                  size="sm"
                  className="h-9 text-xs px-5"
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

        <div className="space-y-4">
          <Card className="border-zinc-200 bg-white">
            <CardHeader className="pb-2 border-b border-zinc-100">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                Supported Format
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-2 text-xs">
              <div className="flex items-center gap-2.5 rounded-lg border border-zinc-200 bg-zinc-50/80 px-3 py-2">
                <FileText size={15} className="text-zinc-800" />
                <span className="font-semibold text-zinc-900">.docx</span>
                <span className="ml-auto text-[11px] text-zinc-400">Word Document</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-zinc-200 bg-white">
            <CardHeader className="pb-2 border-b border-zinc-100">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                Requirements
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-2.5 text-xs text-zinc-600">
              <div className="flex justify-between items-center">
                <span className="text-zinc-500">Maximum File Size</span>
                <span className="font-mono text-[11px] font-semibold text-zinc-900">50 MB</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-500">Supported Inputs</span>
                <span className="font-mono text-[11px] font-semibold text-zinc-900">DOCX Manuscripts</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-500">Est. Duration</span>
                <span className="font-mono text-[11px] font-semibold text-zinc-900">15 – 60s</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}
