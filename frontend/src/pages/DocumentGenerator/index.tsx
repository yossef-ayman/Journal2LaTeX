/**
 * Document Generator page.
 *
 * A self-contained feature alongside the converter: master templates are stored
 * once, then a batch of papers is turned into an acceptance letter and an invoice
 * each, in DOCX and PDF, with no manual editing.
 */

import { useEffect, useState } from "react";
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
  listJournals,
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
  const [selectedJournal, setSelectedJournal] = useState<string>("AMISL");

  const journals = useQuery({
    queryKey: ["document-generator", "journals"],
    queryFn: listJournals,
  });

  useEffect(() => {
    if (journals.data && journals.data.length > 0 && !selectedJournal) {
      setSelectedJournal(journals.data[0].code);
    }
  }, [journals.data, selectedJournal]);

  const templates = useQuery({
    queryKey: ["document-generator", "templates", selectedJournal],
    queryFn: () => listTemplates(selectedJournal),
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
    queryKey: ["document-generator", "inspect", mappingType, selectedJournal],
    queryFn: () => inspectTemplate(mappingType as string, selectedJournal),
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
    }) => saveTemplateMapping(documentType, mappings, selectedJournal),
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
          {/* Batch generation */}
          <section className="space-y-3">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight text-gray-900">
                Batch Generation & Journal Selection
              </h2>
              <p className="text-sm text-gray-500">
                Choose one of your 20 journal profiles. Titles, authors, and reference numbers are derived automatically per paper.
              </p>
            </div>

            <BatchForm
              disabled={generateMutation.isPending}
              running={generateMutation.isPending}
              journals={journals.data ?? []}
              selectedJournal={selectedJournal}
              onSelectJournal={(code) => setSelectedJournal(code)}
              defaultSuffix={settings.data?.reference_suffix ?? "A"}
              pdfAvailable={settings.data?.pdf_backend_available ?? true}
              onGenerate={(files, values) =>
                generateMutation.mutate({ files, values })
              }
            />
          </section>

          {/* Active Journal Templates */}
          <section className="space-y-3">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight text-gray-900">
                Templates for Journal: <span className="font-mono text-emerald-700">{selectedJournal}</span>
              </h2>
              <p className="text-sm text-gray-500">
                Master templates active for the selected journal.
              </p>
            </div>

            {templates.isLoading ? (
              <div className="grid gap-4 md:grid-cols-2">
                <SkeletonCard />
                <SkeletonCard />
              </div>
            ) : noTemplates ? (
              <EmptyState
                icon={<FileSignature size={28} strokeWidth={1.5} />}
                title="No templates found for this journal"
                description={`Store an acceptance letter and invoice template in backend/document_generator_data/templates/${selectedJournal}/.`}
              />
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
