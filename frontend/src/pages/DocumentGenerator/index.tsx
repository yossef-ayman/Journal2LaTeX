/**
 * Document Generator page.
 *
 * A self-contained feature alongside the converter: master templates are stored
 * once, then a batch of papers is turned into an acceptance letter and an invoice
 * each, in DOCX and PDF, with no manual editing.
 *
 * Nothing here touches the converter's pages, hooks or services.
 */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageContainer } from "@/components/PageContainer";
import { SectionTitle } from "@/components/SectionTitle";
import { SkeletonCard } from "@/components/Skeleton";
import { EmptyState } from "@/components/EmptyState";
import { useToast } from "@/components/Toast";
import { TemplateCard } from "@/components/DocumentGenerator/TemplateCard";
import { BatchForm } from "@/components/DocumentGenerator/BatchForm";
import { GeneratedFiles } from "@/components/DocumentGenerator/GeneratedFiles";
import { GeneratorSettingsPanel } from "@/components/DocumentGenerator/GeneratorSettingsPanel";
import { MappingWizard } from "@/components/DocumentGenerator/MappingWizard";
import {
  generateBatch,
  getSettings,
  inspectTemplate,
  listDocumentTypes,
  listTemplates,
  saveTemplateMapping,
  updateSettings,
  uploadTemplate,
  type BatchFormValues,
  type BatchSummary,
  type GeneratorSettingsUpdate,
} from "@/services/documentGenerator";
import { FileSignature, ServerCrash } from "lucide-react";
import axios from "axios";

/** Backend error detail, or a readable fallback. */
function errorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

export default function DocumentGeneratorPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [summary, setSummary] = useState<BatchSummary | null>(null);
  const [uploadingType, setUploadingType] = useState<string | null>(null);
  // Which template the mapping wizard is open for, if any.
  const [mappingType, setMappingType] = useState<string | null>(null);
  const [mappingError, setMappingError] = useState<string | null>(null);

  const templates = useQuery({
    queryKey: ["document-generator", "templates"],
    queryFn: listTemplates,
  });
  const documentTypes = useQuery({
    queryKey: ["document-generator", "document-types"],
    queryFn: listDocumentTypes,
  });
  const settings = useQuery({
    queryKey: ["document-generator", "settings"],
    queryFn: getSettings,
  });

  const uploadMutation = useMutation({
    mutationFn: ({
      documentType,
      file,
      replace,
    }: {
      documentType: string;
      file: File;
      replace: boolean;
    }) => uploadTemplate(documentType, file, replace),
    onMutate: ({ documentType }) => setUploadingType(documentType),
    onSuccess: (stored, { replace }) => {
      toast({
        title: replace ? "Template replaced" : "Template stored",
        message: `${stored.label} is saved and will be reused for every generation.`,
        type: "success",
      });
      queryClient.invalidateQueries({ queryKey: ["document-generator", "templates"] });
      queryClient.invalidateQueries({
        queryKey: ["document-generator", "inspect", stored.key],
      });
      // A first upload is an ordinary Word file with real values in it, so the
      // wizard opens straight away: mapping is the step that turns it into a
      // template, and doing it now means it is never asked for again.
      if (stored.needs_mapping || stored.stale_fields.length > 0) {
        setMappingError(null);
        setMappingType(stored.key);
      }
    },
    onError: (error) =>
      toast({
        title: "Upload failed",
        message: errorMessage(error, "The template could not be stored."),
        type: "error",
      }),
    onSettled: () => setUploadingType(null),
  });

  const generateMutation = useMutation({
    mutationFn: ({ files, values }: { files: File[]; values: BatchFormValues }) =>
      generateBatch(files, values),
    onSuccess: (result) => {
      setSummary(result);
      const failed = result.documents.filter((d) => d.errors.length > 0).length;
      toast({
        title: "Documents generated",
        message:
          `${result.document_count} file${result.document_count === 1 ? "" : "s"} for ` +
          `${result.paper_count} paper${result.paper_count === 1 ? "" : "s"}` +
          (failed > 0 ? ` · ${failed} paper(s) reported problems` : ""),
        type: failed > 0 ? "warning" : "success",
      });
    },
    onError: (error) =>
      toast({
        title: "Generation failed",
        message: errorMessage(error, "The documents could not be generated."),
        type: "error",
      }),
  });

  const inspection = useQuery({
    queryKey: ["document-generator", "inspect", mappingType],
    queryFn: () => inspectTemplate(mappingType as string),
    enabled: mappingType !== null,
    staleTime: 0,
  });

  const mappingMutation = useMutation({
    mutationFn: ({
      documentType,
      mappings,
    }: {
      documentType: string;
      mappings: Array<{ field: string; text: string }>;
    }) => saveTemplateMapping(documentType, mappings),
    onSuccess: (saved) => {
      setMappingError(null);
      setMappingType(null);
      toast({
        title: "Mapping saved",
        message: `${saved.mappings.length} field${
          saved.mappings.length === 1 ? "" : "s"
        } will be filled in automatically from now on.`,
        type: "success",
      });
      queryClient.invalidateQueries({ queryKey: ["document-generator", "templates"] });
    },
    // Shown inside the wizard rather than as a toast: the operator has to change
    // a selection to fix it, and the dialog is where the selections are.
    onError: (error) =>
      setMappingError(errorMessage(error, "The mapping could not be saved.")),
  });

  const settingsMutation = useMutation({
    mutationFn: (update: GeneratorSettingsUpdate) => updateSettings(update),
    onSuccess: () => {
      toast({ title: "Settings saved", type: "success" });
      queryClient.invalidateQueries({ queryKey: ["document-generator", "settings"] });
    },
    onError: (error) =>
      toast({
        title: "Could not save the settings",
        message: errorMessage(error, "The settings were not saved."),
        type: "error",
      }),
  });

  const descriptions = new Map(
    (documentTypes.data ?? []).map((t) => [t.key, t.description]),
  );
  const templateList = templates.data ?? [];
  const readyCount = templateList.filter((t) => t.uploaded).length;
  const noTemplates = templates.isSuccess && readyCount === 0;

  // The module is optional on the backend: if it is not mounted, say so plainly
  // rather than leaving a page of broken panels.
  const moduleMissing =
    axios.isAxiosError(templates.error) && templates.error.response?.status === 404;

  return (
    <PageContainer>
      <SectionTitle
        title="Document Generator"
        description="Generate acceptance letters and invoices for a batch of accepted papers from your own Word templates."
      />

      {moduleMissing ? (
        <EmptyState
          icon={<ServerCrash size={28} strokeWidth={1.5} />}
          title="The Document Generator is not available"
          description="The module is not enabled on the server. The Word to LaTeX converter is unaffected."
        />
      ) : (
        <div className="space-y-8">
          {/* Templates */}
          <section className="space-y-3">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight text-gray-900">
                Templates
              </h2>
              <p className="text-sm text-gray-500">
                Uploaded once and stored permanently. Replace a template only when
                you have a newer version — the previous file is kept.
              </p>
            </div>

            {templates.isLoading ? (
              <div className="grid gap-4 md:grid-cols-2">
                <SkeletonCard />
                <SkeletonCard />
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {templateList.map((template) => (
                  <TemplateCard
                    key={template.key}
                    template={template}
                    description={descriptions.get(template.key)}
                    busy={uploadingType === template.key}
                    onUpload={(file, replace) =>
                      uploadMutation.mutate({
                        documentType: template.key,
                        file,
                        replace,
                      })
                    }
                    onMapFields={() => {
                      setMappingError(null);
                      setMappingType(template.key);
                    }}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Batch generation */}
          <section className="space-y-3">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight text-gray-900">
                Batch Generation
              </h2>
              <p className="text-sm text-gray-500">
                Titles and authors are read from each paper automatically. Reference
                numbers follow the acceptance date and the upload order.
              </p>
            </div>

            {noTemplates ? (
              <EmptyState
                icon={<FileSignature size={28} strokeWidth={1.5} />}
                title="Upload your templates first"
                description="Store an acceptance letter and an invoice template above, then upload the papers to generate from."
              />
            ) : (
              <BatchForm
                disabled={generateMutation.isPending}
                running={generateMutation.isPending}
                defaultSuffix={settings.data?.reference_suffix ?? "A"}
                defaultJournalCode={settings.data?.journal_code ?? ""}
                pdfAvailable={settings.data?.pdf_backend_available ?? true}
                onGenerate={(files, values) =>
                  generateMutation.mutate({ files, values })
                }
              />
            )}
          </section>

          {/* Results */}
          {summary && (
            <section className="space-y-3">
              <div className="space-y-1">
                <h2 className="text-lg font-semibold tracking-tight text-gray-900">
                  Generated Files
                </h2>
                <p className="text-sm text-gray-500">
                  Download an individual file, or the whole batch as a ZIP archive.
                </p>
              </div>
              <GeneratedFiles summary={summary} />
            </section>
          )}

          {/* Settings */}
          {settings.data && (
            <section className="space-y-3">
              <div className="space-y-1">
                <h2 className="text-lg font-semibold tracking-tight text-gray-900">
                  Generator Settings
                </h2>
                <p className="text-sm text-gray-500">
                  Defaults applied to every batch. These are stored on the server.
                </p>
              </div>
              <GeneratorSettingsPanel
                settings={settings.data}
                saving={settingsMutation.isPending}
                onSave={(update) => settingsMutation.mutate(update)}
              />
            </section>
          )}
        </div>
      )}

      <MappingWizard
        open={mappingType !== null}
        label={
          templateList.find((t) => t.key === mappingType)?.label ?? "this template"
        }
        inspection={inspection.data ?? null}
        loading={inspection.isLoading}
        saving={mappingMutation.isPending}
        error={
          mappingError ??
          (inspection.isError
            ? errorMessage(inspection.error, "The template could not be read.")
            : null)
        }
        onSave={(mappings) =>
          mappingType && mappingMutation.mutate({ documentType: mappingType, mappings })
        }
        onClose={() => {
          setMappingType(null);
          setMappingError(null);
        }}
      />
    </PageContainer>
  );
}
