/**
 * One master-template slot: its state, the placeholders it uses, and the
 * upload/replace control.
 *
 * The card deliberately shows the placeholders discovered inside the stored file
 * rather than a fixed list, so an operator who adds `{{APC_AMOUNT}}` to their own
 * Word file can see immediately that the system recognises it.
 */

import { useRef, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";
import {
  CheckCircle2,
  FileText,
  History,
  RefreshCw,
  Upload,
  AlertCircle,
  Wand2,
} from "lucide-react";
import type { TemplateInfo } from "@/services/documentGenerator";

function formatSize(bytes: number | null): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface TemplateCardProps {
  template: TemplateInfo;
  description?: string;
  busy?: boolean;
  onUpload: (file: File, replace: boolean) => void;
  onMapFields: () => void;
}

export function TemplateCard({
  template,
  description,
  busy = false,
  onUpload,
  onMapFields,
}: TemplateCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file) onUpload(file, template.uploaded);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <Card
      className={cn(
        "transition-colors",
        dragging && "border-emerald-400 bg-emerald-50/40",
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      <CardContent className="p-5 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <div
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
                template.uploaded
                  ? "bg-emerald-50 text-emerald-600"
                  : "bg-gray-100 text-gray-400",
              )}
            >
              <FileText size={18} />
            </div>
            <div className="min-w-0 space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-gray-900 leading-none truncate">
                  {template.label}
                </h3>
                {template.uploaded ? (
                  <Badge variant="success" className="shrink-0">
                    <CheckCircle2 size={11} className="mr-1" /> Stored
                  </Badge>
                ) : (
                  <Badge variant="warning" className="shrink-0">
                    Not uploaded
                  </Badge>
                )}
                {template.uploaded &&
                  (template.stale_fields.length > 0 ? (
                    <Badge variant="warning" className="shrink-0">
                      Re-map needed
                    </Badge>
                  ) : template.mapped ? (
                    <Badge variant="success" className="shrink-0">
                      {template.mapped_fields.length} field
                      {template.mapped_fields.length === 1 ? "" : "s"} mapped
                    </Badge>
                  ) : template.needs_mapping ? (
                    <Badge variant="warning" className="shrink-0">
                      Fields not mapped
                    </Badge>
                  ) : null)}
              </div>
              <p className="text-xs text-gray-500 leading-relaxed">
                {template.uploaded
                  ? `${template.original_filename ?? "template.docx"} · ${formatSize(
                      template.size_bytes,
                    )} · stored ${formatDate(template.uploaded_at)}`
                  : description ?? "Upload the Word file to use as the master template."}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {template.uploaded && (
              <Button
                variant={
                  template.mapped && template.stale_fields.length === 0
                    ? "ghost"
                    : "default"
                }
                size="sm"
                disabled={busy}
                onClick={onMapFields}
              >
                <Wand2 size={14} />
                {template.mapped ? "Edit mapping" : "Map fields"}
              </Button>
            )}
            <input
              ref={inputRef}
              type="file"
              accept=".docx"
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <Button
              variant={template.uploaded ? "outline" : "default"}
              size="sm"
              disabled={busy}
              onClick={() => inputRef.current?.click()}
            >
              {template.uploaded ? (
                <>
                  <RefreshCw size={14} /> Replace
                </>
              ) : (
                <>
                  <Upload size={14} /> Upload
                </>
              )}
            </Button>
          </div>
        </div>

        {template.uploaded && (
          <div className="space-y-2">
            {template.mapped && (
              <>
                <p className="text-[11px] font-medium uppercase tracking-wide text-gray-400">
                  Mapped fields
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {template.mapped_fields.map((name) => (
                    <span
                      key={name}
                      className={cn(
                        "rounded-md px-2 py-0.5 text-[11px]",
                        template.stale_fields.includes(name)
                          ? "bg-amber-50 text-amber-700"
                          : "bg-emerald-50 text-emerald-700",
                      )}
                    >
                      {name.replace(/_/g, " ").toLowerCase()}
                    </span>
                  ))}
                </div>
              </>
            )}
            {template.placeholders.length > 0 && (
              <>
                <p className="text-[11px] font-medium uppercase tracking-wide text-gray-400">
                  Placeholders in this template
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {template.placeholders.map((name) => (
                    <span
                      key={name}
                      className="rounded-md bg-gray-100 px-2 py-0.5 font-mono text-[11px] text-gray-600"
                    >
                      {`{{${name}}}`}
                    </span>
                  ))}
                </div>
              </>
            )}
            {template.stale_fields.length > 0 ? (
              <p className="flex items-start gap-1.5 text-xs text-amber-700">
                <AlertCircle size={13} className="mt-0.5 shrink-0" />
                The text saved for{" "}
                {template.stale_fields
                  .map((name) => name.replace(/_/g, " ").toLowerCase())
                  .join(", ")}{" "}
                is no longer in this file. Map those fields again.
              </p>
            ) : template.needs_mapping ? (
              <p className="flex items-start gap-1.5 text-xs text-amber-700">
                <AlertCircle size={13} className="mt-0.5 shrink-0" />
                This is still an ordinary Word file. Map its fields so each paper gets
                its own title, authors and reference number.
              </p>
            ) : null}
            {template.archived_versions > 0 && (
              <p className="flex items-center gap-1.5 text-[11px] text-gray-400">
                <History size={12} />
                {template.archived_versions} previous version
                {template.archived_versions === 1 ? "" : "s"} kept
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
