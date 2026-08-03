/**
 * Module settings: the reference-number suffix, the default editor and journal
 * names, and whether PDFs are produced.
 *
 * Separate from the application's own Settings page so the converter's settings
 * screen is untouched and this module's configuration travels with the module.
 */

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Save } from "lucide-react";
import type {
  GeneratorSettings,
  GeneratorSettingsUpdate,
} from "@/services/documentGenerator";

interface GeneratorSettingsPanelProps {
  settings: GeneratorSettings;
  saving?: boolean;
  onSave: (update: GeneratorSettingsUpdate) => void;
}

export function GeneratorSettingsPanel({
  settings,
  saving = false,
  onSave,
}: GeneratorSettingsPanelProps) {
  const [journalCode, setJournalCode] = useState(settings.journal_code);
  const [suffix, setSuffix] = useState(settings.reference_suffix);
  const [editor, setEditor] = useState(settings.editor_name);
  const [journal, setJournal] = useState(settings.journal_name);
  const [generatePdf, setGeneratePdf] = useState(settings.generate_pdf);

  // Re-sync when the server's copy changes (another tab, or a save round-trip).
  useEffect(() => {
    setJournalCode(settings.journal_code);
    setSuffix(settings.reference_suffix);
    setEditor(settings.editor_name);
    setJournal(settings.journal_name);
    setGeneratePdf(settings.generate_pdf);
  }, [settings]);

  const dirty =
    journalCode !== settings.journal_code ||
    suffix !== settings.reference_suffix ||
    editor !== settings.editor_name ||
    journal !== settings.journal_name ||
    generatePdf !== settings.generate_pdf;

  return (
    <Card>
      <CardContent className="p-5 space-y-5">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-1.5">
            <Label htmlFor="dg-journal-code">Journal Code</Label>
            <Input
              id="dg-journal-code"
              placeholder="JSAP"
              value={journalCode}
              maxLength={12}
              onChange={(e) => setJournalCode(e.target.value.toUpperCase())}
            />
            <p className="text-[11px] text-gray-400">
              Opens every reference number:{" "}
              <span className="font-mono">JSAP</span>MMDDYYIIX. Leave blank if
              this installation serves a single unnumbered journal.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="dg-suffix">Reference Suffix</Label>
            <Input
              id="dg-suffix"
              value={suffix}
              maxLength={8}
              onChange={(e) => setSuffix(e.target.value)}
            />
            <p className="text-[11px] text-gray-400">
              The final character of{" "}
              <span className="font-mono">JSAP</span>MMDDYYII<strong>X</strong>.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="dg-editor">Editor Name</Label>
            <Input
              id="dg-editor"
              placeholder="Prof. A. Rahman"
              value={editor}
              onChange={(e) => setEditor(e.target.value)}
            />
            <p className="text-[11px] text-gray-400">
              Fills <span className="font-mono">{"{{EDITOR}}"}</span>.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="dg-journal">Journal Name</Label>
            <Input
              id="dg-journal"
              placeholder="Journal name as it appears on the letterhead"
              value={journal}
              onChange={(e) => setJournal(e.target.value)}
            />
            <p className="text-[11px] text-gray-400">
              Fills <span className="font-mono">{"{{JOURNAL}}"}</span>.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 pt-4">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
              checked={generatePdf}
              disabled={!settings.pdf_backend_available}
              onChange={(e) => setGeneratePdf(e.target.checked)}
            />
            Export a PDF alongside every DOCX
            <span className="text-xs text-gray-400">
              {settings.pdf_backend_available
                ? `(via ${settings.pdf_backend})`
                : "(no PDF converter installed on this server)"}
            </span>
          </label>
          <Button
            size="sm"
            disabled={!dirty || saving}
            onClick={() =>
              onSave({
                journal_code: journalCode,
                reference_suffix: suffix,
                editor_name: editor,
                journal_name: journal,
                generate_pdf: generatePdf,
              })
            }
          >
            <Save size={14} /> {saving ? "Saving…" : "Save settings"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
