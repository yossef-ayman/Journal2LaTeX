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
    <div className="animate-fade-in rounded-lg border-2 border-primary/20 bg-primary/5 p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3 min-w-0">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
            <FileText size={20} className="text-primary" />
          </div>
          <div className="min-w-0 space-y-1">
            <p className="text-sm font-medium text-foreground truncate max-w-[300px]">
              {file.name}
            </p>
            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              <span>{formatFileSize(file.size)}</span>
              <span className="flex items-center gap-1">
                <Clock size={12} />
                {estimateProcessingSize(file.size)}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={onReplace}
            aria-label="Replace file"
            className="text-xs"
          >
            Replace
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onRemove}
            aria-label="Remove file"
          >
            <X size={16} className="text-destructive" />
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
        description="Upload a .docx academic paper to begin the conversion process"
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Select File</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
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
                    "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-16 text-center transition-all duration-200",
                    dragOver
                      ? "border-primary bg-primary/5 scale-[1.01]"
                      : validationError
                        ? "border-destructive/50 bg-destructive/5"
                        : "border-border hover:border-primary/50 hover:bg-accent/30",
                  )}
                >
                  <div
                    className={cn(
                      "mb-5 flex h-16 w-16 items-center justify-center rounded-full transition-colors",
                      validationError ? "bg-destructive/10" : "bg-primary/10",
                    )}
                  >
                    {validationError ? (
                      <FileWarning size={28} className="text-destructive" />
                    ) : (
                      <Upload size={28} className="text-primary" />
                    )}
                  </div>
                  <h3 className="mb-1 text-lg font-medium text-foreground">
                    {dragOver ? "Drop your file here" : "Drop your DOCX file here"}
                  </h3>
                  <p className="mb-6 text-sm text-muted-foreground">
                    or click to browse from your computer
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={(e) => { e.stopPropagation(); onBrowse(); }}
                    aria-label="Browse files"
                  >
                    Browse Files
                  </Button>
                  <div className="mt-6 flex items-center gap-4 text-xs text-muted-foreground">
                    <span>Format: .docx</span>
                    <span className="h-3 w-px bg-border" />
                    <span>Max: {MAX_FILE_SIZE / 1024 / 1024}MB</span>
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
                <div className="animate-fade-in flex items-center gap-2 rounded-md border border-destructive/50 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                  <AlertCircle size={16} />
                  {validationError.message}
                </div>
              )}

              <div className="space-y-2">
                <div className="flex gap-3 items-end">
                  <div className="flex-1 space-y-2">
                    <Label htmlFor="template">Template</Label>
                    <div className="relative">
                      <Select value={template} onValueChange={setTemplate}>
                        <SelectTrigger id="template">
                          <SelectValue>
                            {templates.data?.find((t) => t.template_id === template)
                              ?.display_name ?? templates.data?.find((t) => t.template_id === template)
                              ?.journal_title ?? template}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {templates.data?.map((t) => (
                            <SelectItem key={t.template_id} value={t.template_id}>
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
                    onClick={handleTemplateUploadClick}
                    disabled={templateUpload.isPending}
                    aria-label="Upload custom template ZIP"
                  >
                    {templateUpload.isPending ? "Uploading..." : "Upload ZIP Template"}
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
                <div className="animate-fade-in flex items-center gap-2 rounded-md border border-destructive/50 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                  <AlertCircle size={16} />
                  {apiError.message}
                </div>
              )}

              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={handleClear}
                  disabled={(!file && !validationError) || isProcessing}
                >
                  <Trash2 size={14} />
                  Clear
                </Button>
                <Button onClick={onSubmit} disabled={!file || isProcessing} size="lg">
                  {isProcessing ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Upload size={16} />
                  )}
                  {isProcessing ? "Processing..." : "Start Conversion"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Supported Formats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex items-center gap-3 rounded-md bg-muted/50 px-3 py-2">
                <FileText size={16} className="text-primary" />
                <span className="font-medium text-foreground">.docx</span>
                <span className="ml-auto text-xs text-muted-foreground">Word Document</span>
              </div>
              <div className="flex items-center gap-3 rounded-md bg-muted/30 px-3 py-2 text-muted-foreground/50">
                <FileText size={16} />
                <span>.pdf</span>
                <span className="ml-auto text-xs">Coming soon</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>File Requirements</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Max size</span>
                <span className="font-medium text-foreground">50 MB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Format</span>
                <span className="font-medium text-foreground">DOCX only</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Processing</span>
                <span className="font-medium text-foreground">15–60s</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}
