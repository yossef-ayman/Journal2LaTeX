/**
 * The batch-generation form: papers plus the values that apply to all of them.
 *
 * The dates are free text on purpose -- they are printed into the letter exactly
 * as typed, so an operator writing "22 July 2026" gets "22 July 2026" and not a
 * locale-reformatted version of it.
 */

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/utils/cn";
import { FilePlus2, FileText, Play, Upload, X } from "lucide-react";
import type { BatchFormValues } from "@/services/documentGenerator";

interface BatchFormProps {
  disabled?: boolean;
  running?: boolean;
  defaultSuffix?: string;
  defaultJournalCode?: string;
  pdfAvailable?: boolean;
  onGenerate: (files: File[], values: BatchFormValues) => void;
}

export function BatchForm({
  disabled = false,
  running = false,
  defaultSuffix = "A",
  defaultJournalCode = "",
  pdfAvailable = true,
  onGenerate,
}: BatchFormProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [acceptanceDate, setAcceptanceDate] = useState("");
  const [deadline, setDeadline] = useState("");
  const [referencePrefix, setReferencePrefix] = useState("");
  // Blank means "use the configured journal code"; typing here overrides it for
  // this batch only, which is what an operator handling a second journal needs.
  const [journalCode, setJournalCode] = useState("");

  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const accepted = Array.from(incoming).filter((f) =>
      f.name.toLowerCase().endsWith(".docx"),
    );
    // Appended rather than replaced so an operator can build a batch from
    // several folders, and the order they add them is the order used for the
    // reference numbers.
    setFiles((current) => [...current, ...accepted]);
    if (inputRef.current) inputRef.current.value = "";
  };

  const removeFile = (index: number) =>
    setFiles((current) => current.filter((_, i) => i !== index));

  const canGenerate =
    !disabled && !running && files.length > 0 && acceptanceDate.trim().length > 0;

  return (
    <Card>
      <CardContent className="p-5 space-y-5">
        {/* Papers */}
        <div className="space-y-2">
          <Label>Upload Papers</Label>
          <div
            className={cn(
              "rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors",
              dragging
                ? "border-emerald-400 bg-emerald-50/50"
                : "border-gray-200 bg-gray-50/50",
              disabled && "opacity-60",
            )}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              if (!disabled) addFiles(e.dataTransfer.files);
            }}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".docx"
              multiple
              className="hidden"
              onChange={(e) => addFiles(e.target.files)}
            />
            <div className="flex flex-col items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-emerald-500 shadow-sm">
                <Upload size={20} />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-gray-700">
                  Drop the paper files here, or choose them
                </p>
                <p className="text-xs text-gray-400">
                  Word .docx files · upload as many as the batch contains
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled={disabled}
                onClick={() => inputRef.current?.click()}
              >
                <FilePlus2 size={14} /> Choose papers
              </Button>
            </div>
          </div>

          {files.length > 0 && (
            <ul className="divide-y divide-gray-100 rounded-xl border border-gray-100">
              {files.map((file, index) => (
                <li
                  key={`${file.name}-${index}`}
                  className="flex items-center gap-3 px-3 py-2"
                >
                  <span className="w-8 shrink-0 text-center font-mono text-[11px] text-gray-400">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <FileText size={14} className="shrink-0 text-gray-400" />
                  <span className="min-w-0 flex-1 truncate text-sm text-gray-700">
                    {file.name}
                  </span>
                  <Button
                    variant="ghost-destructive"
                    size="icon-sm"
                    aria-label={`Remove ${file.name}`}
                    disabled={running}
                    onClick={() => removeFile(index)}
                  >
                    <X size={14} />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Batch values */}
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-1.5">
            <Label htmlFor="dg-accept-date">Acceptance Date</Label>
            <Input
              id="dg-accept-date"
              placeholder="22 July 2026"
              value={acceptanceDate}
              disabled={disabled}
              onChange={(e) => setAcceptanceDate(e.target.value)}
            />
            <p className="text-[11px] text-gray-400">
              Printed as typed, and used for the date part of every reference number.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="dg-deadline">Deadline</Label>
            <Input
              id="dg-deadline"
              placeholder="15 August 2026"
              value={deadline}
              disabled={disabled}
              onChange={(e) => setDeadline(e.target.value)}
            />
            <p className="text-[11px] text-gray-400">
              Applied to every document in the batch.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="dg-prefix">Reference Prefix (optional)</Label>
            <Input
              id="dg-prefix"
              placeholder="JSAP-"
              value={referencePrefix}
              disabled={disabled}
              onChange={(e) => setReferencePrefix(e.target.value)}
            />
            <p className="text-[11px] text-gray-400">
              Numbers follow {journalCode || defaultJournalCode}MMDDYYII
              {defaultSuffix} — e.g.{" "}
              <span className="font-mono">
                {referencePrefix}
                {journalCode || defaultJournalCode}
                0730{new Date().getFullYear() % 100}01{defaultSuffix}
              </span>
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="dg-batch-journal-code">Journal Code (optional)</Label>
            <Input
              id="dg-batch-journal-code"
              placeholder={defaultJournalCode || "JSAP"}
              maxLength={12}
              value={journalCode}
              disabled={disabled}
              onChange={(e) => setJournalCode(e.target.value.toUpperCase())}
            />
            <p className="text-[11px] text-gray-400">
              Overrides the configured code for this batch only.
            </p>
          </div>
        </div>

        {!pdfAvailable && (
          <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            PDF export is unavailable on this server, so this batch will produce
            DOCX files only.
          </p>
        )}

        <div className="flex items-center justify-between gap-3 border-t border-gray-100 pt-4">
          <p className="text-xs text-gray-500">
            {files.length === 0
              ? "No papers selected yet."
              : `${files.length} paper${files.length === 1 ? "" : "s"} ready — titles and authors are read automatically.`}
          </p>
          <Button
            size="lg"
            disabled={!canGenerate}
            onClick={() =>
              onGenerate(files, {
                acceptanceDate,
                deadline,
                referencePrefix: referencePrefix || undefined,
                journalCode: journalCode || undefined,
              })
            }
          >
            {running ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Generating…
              </>
            ) : (
              <>
                <Play size={15} /> Generate Documents
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
