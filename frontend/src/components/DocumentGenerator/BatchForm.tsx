/**
 * The batch-generation form: papers plus editable values (Title, Authors, Reference Number, Fee, Discount, Dates)
 */

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/utils/cn";
import {
  BookOpen,
  Calendar,
  DollarSign,
  Edit3,
  FilePlus2,
  FileText,
  Hash,
  Loader2,
  Percent,
  Play,
  User,
  Upload,
  X,
} from "lucide-react";
import {
  inspectPapers,
  type BatchFormValues,
  type JournalProfile,
  type PaperOverride,
} from "@/services/documentGenerator";

interface BatchFormProps {
  disabled?: boolean;
  running?: boolean;
  journals?: JournalProfile[];
  selectedJournal?: string;
  onSelectJournal?: (code: string) => void;
  defaultSuffix?: string;
  pdfAvailable?: boolean;
  onGenerate: (files: File[], values: BatchFormValues) => void;
}

interface LocalOverride {
  title: string;
  authors: string;
  reference_number: string;
  fee: string;
  hasDiscount: boolean;
  discount: string;
  acceptanceDate: string;
  deadline: string;
}

export function BatchForm({
  disabled = false,
  running = false,
  journals = [],
  selectedJournal = "",
  onSelectJournal,
  defaultSuffix = "A",
  pdfAvailable = true,
  onGenerate,
}: BatchFormProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [acceptanceDate, setAcceptanceDate] = useState(
    new Date().toISOString().split("T")[0],
  );
  const [deadline, setDeadline] = useState(
    new Date(Date.now() + 14 * 86400000).toISOString().split("T")[0],
  );

  const [inspecting, setInspecting] = useState(false);

  // Per-paper manual overrides indexed by paper 1-based index
  const [paperOverrides, setPaperOverrides] = useState<Record<number, LocalOverride>>({});

  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const accepted = Array.from(incoming).filter((f) => {
      const lower = f.name.toLowerCase();
      return lower.endsWith(".docx") || lower.endsWith(".doc") || lower.endsWith(".pdf");
    });
    setFiles((current) => [...current, ...accepted]);
    if (inputRef.current) inputRef.current.value = "";
  };

  const removeFile = (index: number) => {
    setFiles((current) => current.filter((_, i) => i !== index));
    setPaperOverrides((current) => {
      const next = { ...current };
      delete next[index + 1];
      return next;
    });
  };

  // Run paper inspection whenever files, selectedJournal, or acceptanceDate changes
  useEffect(() => {
    if (files.length === 0) {
      setPaperOverrides({});
      return;
    }
    let active = true;
    setInspecting(true);
    inspectPapers(files, selectedJournal, acceptanceDate, "", defaultSuffix)
      .then((res) => {
        if (!active) return;
        setPaperOverrides((prev) => {
          const next = { ...prev };
          res.forEach((item, idx) => {
            const paperIndex = idx + 1;
            if (!next[paperIndex]) {
              next[paperIndex] = {
                title: item.title || "",
                authors: item.formatted_authors || (item.authors ? item.authors.join(", ") : ""),
                reference_number: item.reference_number || "",
                fee: "2100$",
                hasDiscount: false,
                discount: "0$",
                acceptanceDate: acceptanceDate,
                deadline: deadline,
              };
            }
          });
          return next;
        });
      })
      .catch((err) => {
        console.error("Paper inspection error:", err);
      })
      .finally(() => {
        if (active) setInspecting(false);
      });
    return () => {
      active = false;
    };
  }, [files, selectedJournal, acceptanceDate, defaultSuffix]);

  const updateOverride = <K extends keyof LocalOverride>(
    paperIndex: number,
    field: K,
    value: LocalOverride[K],
  ) => {
    setPaperOverrides((prev) => ({
      ...prev,
      [paperIndex]: {
        title: prev[paperIndex]?.title ?? "",
        authors: prev[paperIndex]?.authors ?? "",
        reference_number: prev[paperIndex]?.reference_number ?? "",
        fee: prev[paperIndex]?.fee ?? "2100$",
        hasDiscount: prev[paperIndex]?.hasDiscount ?? false,
        discount: prev[paperIndex]?.discount ?? "0$",
        acceptanceDate: prev[paperIndex]?.acceptanceDate ?? acceptanceDate,
        deadline: prev[paperIndex]?.deadline ?? deadline,
        [field]: value,
      },
    }));
  };

  const canGenerate =
    !disabled && !running && files.length > 0 && acceptanceDate.trim().length > 0;

  // Format YYYY-MM-DD into human readable date string like "11 August 2026"
  const formatDateDisplay = (dateStr: string) => {
    if (!dateStr) return "";
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return dateStr;
      return date.toLocaleDateString("en-US", {
        day: "numeric",
        month: "long",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  const parseNumber = (val: string, defaultNum = 0): number => {
    const cleaned = (val || "").replace(/[^0-9.]/g, "");
    const parsed = parseFloat(cleaned);
    return isNaN(parsed) ? defaultNum : parsed;
  };

  const handleGenerateClick = () => {
    const formattedOverrides: PaperOverride[] = files.map((_, i) => {
      const idx = i + 1;
      const ov = paperOverrides[idx];

      const numFee = parseNumber(ov?.fee, 2100);
      const numDiscount = ov?.hasDiscount ? parseNumber(ov?.discount, 0) : 0;
      const numTotal = Math.max(0, numFee - numDiscount);

      return {
        index: idx,
        title: ov?.title,
        authors: ov?.authors ? ov.authors.split(",").map((a) => a.trim()).filter(Boolean) : undefined,
        reference_number: ov?.reference_number,
        fee: `${numFee}$`,
        discount: `${numDiscount}$`,
        total_charge: `${numTotal}$`,
        acceptance_date: ov?.acceptanceDate ? formatDateDisplay(ov.acceptanceDate) : undefined,
        deadline: ov?.deadline ? formatDateDisplay(ov.deadline) : undefined,
      };
    });

    onGenerate(files, {
      acceptanceDate: formatDateDisplay(acceptanceDate),
      deadline: formatDateDisplay(deadline),
      journalCode: selectedJournal,
      paperOverrides: formattedOverrides,
    });
  };

  return (
    <Card className="border border-emerald-100/60 shadow-sm">
      <CardContent className="p-6 space-y-6">
        {/* Journal Selector & Settings Bar */}
        <div className="rounded-xl border border-emerald-100 bg-emerald-50/30 p-4 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <Label className="flex items-center gap-2 text-sm font-semibold text-emerald-900">
                <BookOpen size={16} className="text-emerald-600" /> Choose Journal / اختر المجلة
              </Label>
              <p className="text-xs text-gray-500">
                Select from the 20 journal template profiles
              </p>
            </div>
            <select
              value={selectedJournal}
              disabled={disabled || running}
              onChange={(e) => onSelectJournal?.(e.target.value)}
              className="h-10 min-w-[260px] rounded-lg border border-emerald-200 bg-white px-3 text-sm font-medium text-gray-800 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              {journals.map((j) => (
                <option key={j.code} value={j.code}>
                  {j.code} — {j.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Papers Upload Zone */}
        <div className="space-y-3">
          <Label className="text-sm font-semibold text-gray-900">Upload Papers / رفع المقالات</Label>
          <div
            className={cn(
              "rounded-xl border-2 border-dashed px-6 py-8 text-center transition-all cursor-pointer",
              dragging
                ? "border-emerald-500 bg-emerald-50/60"
                : "border-gray-200 bg-gray-50/50 hover:border-emerald-300 hover:bg-emerald-50/20",
              disabled && "opacity-60 cursor-not-allowed",
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
            onClick={() => inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".docx,.doc,.pdf"
              multiple
              className="hidden"
              onChange={(e) => addFiles(e.target.files)}
            />
            <div className="flex flex-col items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-emerald-600 shadow-sm border border-emerald-100">
                <Upload size={22} />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-gray-700">
                  Drop Word (.docx, .doc) or PDF (.pdf) paper files here, or click to browse
                </p>
                <p className="text-xs text-gray-400">
                  Select as many papers as you want in this batch
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                type="button"
                disabled={disabled}
                onClick={(e) => {
                  e.stopPropagation();
                  inputRef.current?.click();
                }}
              >
                <FilePlus2 size={14} /> Choose Papers
              </Button>
            </div>
          </div>

          {/* Editable Paper Cards (Title, Authors, Reference Number, Fee & Discount) */}
          {files.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500 flex items-center gap-1.5">
                  Selected Papers & Details ({files.length})
                </span>
                {inspecting && (
                  <span className="flex items-center gap-1.5 text-xs text-emerald-600">
                    <Loader2 size={12} className="animate-spin" /> Extracting details…
                  </span>
                )}
              </div>

              <div className="space-y-3">
                {files.map((file, index) => {
                  const paperIndex = index + 1;
                  const currentOv = paperOverrides[paperIndex] || {
                    title: "",
                    authors: "",
                    reference_number: "",
                    fee: "2100$",
                    hasDiscount: false,
                    discount: "0$",
                  };

                  const numFee = parseNumber(currentOv.fee, 2100);
                  const numDiscount = currentOv.hasDiscount ? parseNumber(currentOv.discount, 0) : 0;
                  const numTotal = Math.max(0, numFee - numDiscount);

                  return (
                    <div
                      key={`${file.name}-${index}`}
                      className="p-4 rounded-xl border border-gray-200 bg-white shadow-xs space-y-4 hover:border-emerald-300 transition-colors"
                    >
                      {/* Header with Filename & Delete Button */}
                      <div className="flex items-center justify-between gap-2 border-b border-gray-100 pb-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-emerald-100 text-emerald-800 font-mono text-xs font-bold">
                            {String(paperIndex).padStart(2, "0")}
                          </span>
                          <FileText size={15} className="shrink-0 text-emerald-600" />
                          <span className="font-semibold text-sm text-gray-900 truncate">
                            {file.name}
                          </span>
                        </div>
                        <Button
                          variant="ghost-destructive"
                          size="icon-sm"
                          aria-label={`Remove ${file.name}`}
                          disabled={running}
                          onClick={() => removeFile(index)}
                        >
                          <X size={15} />
                        </Button>
                      </div>

                      {/* Line 1: Title, Authors, Reference Number */}
                      <div className="grid gap-3 sm:grid-cols-12">
                        {/* Title */}
                        <div className="sm:col-span-6 space-y-1">
                          <label className="text-[11px] font-semibold text-gray-600 flex items-center gap-1">
                            <Edit3 size={11} className="text-emerald-600" /> Article Title / عنوان المقالة
                          </label>
                          <Input
                            type="text"
                            value={currentOv.title}
                            placeholder="Enter or edit article title..."
                            className="h-8 text-xs font-medium bg-gray-50/50 focus:bg-white"
                            onChange={(e) => updateOverride(paperIndex, "title", e.target.value)}
                          />
                        </div>

                        {/* Authors */}
                        <div className="sm:col-span-3 space-y-1">
                          <label className="text-[11px] font-semibold text-gray-600 flex items-center gap-1">
                            <User size={11} className="text-emerald-600" /> Authors / المؤلفون
                          </label>
                          <Input
                            type="text"
                            value={currentOv.authors}
                            placeholder="Author 1, Author 2..."
                            className="h-8 text-xs font-medium bg-gray-50/50 focus:bg-white"
                            onChange={(e) => updateOverride(paperIndex, "authors", e.target.value)}
                          />
                        </div>

                        {/* Reference Number */}
                        <div className="sm:col-span-3 space-y-1">
                          <label className="text-[11px] font-semibold text-gray-600 flex items-center gap-1">
                            <Hash size={11} className="text-emerald-600" /> Ref No. / الرقم المرجعي
                          </label>
                          <Input
                            type="text"
                            value={currentOv.reference_number}
                            placeholder="e.g. JSAPL08112601A"
                            className="h-8 text-xs font-mono font-medium text-emerald-900 bg-emerald-50/30 focus:bg-white border-emerald-200"
                            onChange={(e) => updateOverride(paperIndex, "reference_number", e.target.value)}
                          />
                        </div>
                      </div>

                      {/* Line 2: Payment Fee, Discount Toggle & Amount, Net Total */}
                      <div className="rounded-lg bg-emerald-50/40 border border-emerald-100 p-3 grid gap-3 sm:grid-cols-12 items-center">
                        {/* Fee Input */}
                        <div className="sm:col-span-3 space-y-1">
                          <label className="text-[11px] font-semibold text-emerald-900 flex items-center gap-1">
                            <DollarSign size={12} className="text-emerald-600" /> Fee Amount / المبلغ الأصلي
                          </label>
                          <Input
                            type="text"
                            value={currentOv.fee}
                            placeholder="2100$"
                            className="h-8 text-xs font-bold text-emerald-900 bg-white"
                            onChange={(e) => updateOverride(paperIndex, "fee", e.target.value)}
                          />
                        </div>

                        {/* Has Discount Checkbox */}
                        <div className="sm:col-span-3 flex items-center gap-2 pt-4 sm:pt-3">
                          <input
                            type="checkbox"
                            id={`discount-check-${paperIndex}`}
                            checked={currentOv.hasDiscount}
                            onChange={(e) => updateOverride(paperIndex, "hasDiscount", e.target.checked)}
                            className="h-4 w-4 rounded border-emerald-300 text-emerald-600 focus:ring-emerald-500"
                          />
                          <label htmlFor={`discount-check-${paperIndex}`} className="text-xs font-semibold text-gray-700 cursor-pointer select-none flex items-center gap-1">
                            <Percent size={12} className="text-emerald-600" /> Apply Discount? / يوجد خصم؟
                          </label>
                        </div>

                        {/* Discount Input (Shown when checked) */}
                        <div className="sm:col-span-3 space-y-1">
                          {currentOv.hasDiscount ? (
                            <>
                              <label className="text-[11px] font-semibold text-emerald-900 flex items-center gap-1">
                                Discount Amount / قيمة الخصم
                              </label>
                              <Input
                                type="text"
                                value={currentOv.discount}
                                placeholder="500$"
                                className="h-8 text-xs font-semibold text-emerald-700 bg-white"
                                onChange={(e) => updateOverride(paperIndex, "discount", e.target.value)}
                              />
                            </>
                          ) : (
                            <span className="text-xs text-gray-400 italic">No discount applied ($0)</span>
                          )}
                        </div>

                        {/* Calculated Net Total */}
                        <div className="sm:col-span-3 text-right space-y-0.5 border-t sm:border-t-0 sm:border-l border-emerald-100 pt-2 sm:pt-0 sm:pl-3">
                          <span className="text-[10px] font-medium uppercase tracking-wider text-gray-500 block">
                            Net Invoice Total / الصافي
                          </span>
                          <span className="text-base font-extrabold font-mono text-emerald-700 block">
                            ${numTotal}
                          </span>
                        </div>
                      </div>

                      {/* Line 3: Per-Paper Acceptance Date & Deadline */}
                      <div className="grid gap-3 sm:grid-cols-2 pt-2 border-t border-gray-100">
                        <div className="space-y-1">
                          <label className="text-[11px] font-semibold text-gray-600 flex items-center gap-1">
                            <Calendar size={11} className="text-emerald-600" /> Acceptance Date / تاريخ القبول لهذا المقال
                          </label>
                          <Input
                            type="date"
                            value={currentOv.acceptanceDate || acceptanceDate}
                            className="h-8 text-xs font-medium bg-white"
                            onChange={(e) => updateOverride(paperIndex, "acceptanceDate", e.target.value)}
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[11px] font-semibold text-gray-600 flex items-center gap-1">
                            <Calendar size={11} className="text-emerald-600" /> Payment Deadline / الديدلاين لهذا المقال
                          </label>
                          <Input
                            type="date"
                            value={currentOv.deadline || deadline}
                            className="h-8 text-xs font-medium bg-white"
                            onChange={(e) => updateOverride(paperIndex, "deadline", e.target.value)}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Date Pickers Section */}
        <div className="grid gap-4 sm:grid-cols-2 pt-2">
          {/* Acceptance Date */}
          <div className="space-y-1.5 rounded-xl border border-gray-200 bg-gray-50/40 p-4">
            <Label htmlFor="dg-accept-date" className="flex items-center gap-2 text-sm font-semibold text-gray-800">
              <Calendar size={16} className="text-emerald-600" /> Acceptance Date / تاريخ القبول
            </Label>
            <Input
              id="dg-accept-date"
              type="date"
              value={acceptanceDate}
              disabled={disabled || running}
              className="bg-white font-medium text-sm"
              onChange={(e) => setAcceptanceDate(e.target.value)}
            />
            <p className="text-[11px] text-gray-500">
              Printed in document as: <span className="font-semibold text-gray-700">{formatDateDisplay(acceptanceDate)}</span>
            </p>
          </div>

          {/* Deadline */}
          <div className="space-y-1.5 rounded-xl border border-gray-200 bg-gray-50/40 p-4">
            <Label htmlFor="dg-deadline" className="flex items-center gap-2 text-sm font-semibold text-gray-800">
              <Calendar size={16} className="text-emerald-600" /> Payment Deadline / الموعد النهائي (الديدلاين)
            </Label>
            <Input
              id="dg-deadline"
              type="date"
              value={deadline}
              disabled={disabled || running}
              className="bg-white font-medium text-sm"
              onChange={(e) => setDeadline(e.target.value)}
            />
            <p className="text-[11px] text-gray-500">
              Printed in invoice as: <span className="font-semibold text-gray-700">{formatDateDisplay(deadline)}</span>
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
              : `${files.length} paper${files.length === 1 ? "" : "s"} ready for journal ${selectedJournal}.`}
          </p>
          <Button
            size="lg"
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
            disabled={!canGenerate}
            onClick={handleGenerateClick}
          >
            {running ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Generating Documents…
              </>
            ) : (
              <>
                <Play size={15} /> Generate Documents ({files.length})
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
