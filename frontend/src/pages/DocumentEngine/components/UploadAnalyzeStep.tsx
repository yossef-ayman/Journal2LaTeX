import { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Upload,
  Loader2,
  AlertCircle,
  FileWarning,
  Sparkles,
  X,
  CheckCircle2,
  FileText,
} from "lucide-react";
import { cn } from "@/utils/cn";

const MAX_FILE_SIZE = 64 * 1024 * 1024;
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
    return {
      type: "size",
      message: `File size exceeds ${MAX_FILE_SIZE / 1024 / 1024}MB limit.`,
    };
  }
  return null;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface UploadAnalyzeStepProps {
  file: File | null;
  setFile: (file: File | null) => void;
  analyzing: boolean;
  error: string | null;
  onAnalyze: () => void;
}

export function UploadAnalyzeStep({
  file,
  setFile,
  analyzing,
  error,
  onAnalyze,
}: UploadAnalyzeStepProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [validationError, setValidationError] = useState<ValidationError | null>(
    null,
  );

  const handleFile = useCallback(
    (f: File) => {
      const err = validateFile(f);
      if (err) {
        setFile(null);
        setValidationError(err);
      } else {
        setFile(f);
        setValidationError(null);
      }
    },
    [setFile],
  );

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

  const handleClear = () => {
    setFile(null);
    setValidationError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="space-y-5">
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
          {!file ? (
            <div
              onDrop={onDrop}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onClick={onBrowse}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onBrowse();
              }}
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
                {dragOver
                  ? "Drop your manuscript here"
                  : "Drag & drop your manuscript"}
              </h3>
              <p className="mb-5 text-sm text-gray-400">
                or click to browse files from your computer
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onBrowse();
                }}
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
            <div className="animate-scale-in rounded-2xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-white p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4 min-w-0">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 text-white font-bold text-xs shadow-sm shadow-emerald-200">
                    DOCX
                  </div>
                  <div className="min-w-0 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-semibold text-gray-900 max-w-[260px] sm:max-w-[400px]">
                        {file.name}
                      </p>
                      <CheckCircle2 size={15} className="shrink-0 text-emerald-500" />
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-gray-400">
                      <span className="font-mono bg-gray-100 rounded px-1.5 py-0.5">
                        {formatFileSize(file.size)}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onBrowse}
                    aria-label="Replace file"
                    className="text-xs h-8"
                  >
                    Replace
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={handleClear}
                    aria-label="Remove file"
                    className="text-gray-400 hover:text-red-600 hover:bg-red-50"
                  >
                    <X size={14} />
                  </Button>
                </div>
              </div>
            </div>
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

          {error && (
            <div className="animate-fade-in flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle size={16} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex justify-end gap-2.5 pt-2 border-t border-gray-100">
            <Button
              onClick={onAnalyze}
              disabled={!file || analyzing}
              size="sm"
              className="h-9 px-6 gap-2"
            >
              {analyzing ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <FileText size={14} />
              )}
              {analyzing ? "Analyzing..." : "Analyze Document"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <p className="text-xs text-gray-400 leading-relaxed">
        The document is parsed in memory and never stored on the server. Analysis
        reads the manuscript and reports what it understood; nothing is changed
        until you accept an edit and download the result.
      </p>
    </div>
  );
}
