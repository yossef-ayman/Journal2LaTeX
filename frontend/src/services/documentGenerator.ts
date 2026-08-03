/**
 * API client for the Document Generator module.
 *
 * Kept in its own file, talking only to `/document-generator/*`, so the module
 * shares nothing with the converter's service layer beyond the axios instance.
 * Removing this file and the DocumentGenerator folders removes the feature.
 */

import apiClient from "@/api/client";
import { API_BASE_URL } from "@/config";

export interface DocumentTypeInfo {
  key: string;
  label: string;
  output_basename: string;
  description: string;
}

export interface TemplateInfo {
  key: string;
  label: string;
  uploaded: boolean;
  original_filename: string | null;
  uploaded_at: string | null;
  size_bytes: number | null;
  placeholders: string[];
  archived_versions: number;
  /** True once the template's dynamic fields have been mapped in the wizard. */
  mapped: boolean;
  mapped_fields: string[];
  /** Mapped fields whose saved text no longer occurs, e.g. after a replacement. */
  stale_fields: string[];
  /** Neither a mapping nor a placeholder: generation would copy it out unchanged. */
  needs_mapping: boolean;
}

/** A dynamic value the operator can point at while mapping a template. */
export interface TemplateFieldInfo {
  key: string;
  label: string;
  description: string;
  required: boolean;
}

/** One selectable line of the uploaded document. */
export interface DocumentSegment {
  id: string;
  part: string;
  location: string;
  index: number;
  text: string;
  in_table: boolean;
  occurrences: number;
}

export interface FieldMapping {
  field: string;
  text: string;
  occurrences: number;
}

export interface TemplateMapping {
  document_type: string;
  mappings: FieldMapping[];
  updated_at: string | null;
  stale_fields: string[];
}

export interface FieldSuggestion {
  field: string;
  text: string;
  segment_id: string;
  occurrences: number;
  reason: string;
}

export interface TemplateInspection {
  document_type: string;
  label: string;
  fields: TemplateFieldInfo[];
  segments: DocumentSegment[];
  suggestions: FieldSuggestion[];
  mapping: TemplateMapping | null;
}

export interface PaperMetadata {
  index: number;
  source_filename: string;
  title: string;
  authors: string[];
  reference_number: string;
  warnings: string[];
}

export interface GeneratedArtifact {
  document_type: string;
  format: "docx" | "pdf";
  filename: string;
  relative_path: string;
  size_bytes: number;
  download_url: string;
}

/** The result of checking one generated document against its template. */
export interface DocumentValidation {
  document_type: string;
  document: string;
  valid: boolean;
  /** Check name -> passed, in the order the checks ran. */
  checks: Record<string, boolean>;
  errors: string[];
  fields_replaced: string[];
  fields_missing: string[];
}

export interface GeneratedDocumentSet {
  paper: PaperMetadata;
  folder: string;
  artifacts: GeneratedArtifact[];
  errors: string[];
  validations: DocumentValidation[];
}

export interface BatchSummary {
  batch_id: string;
  created_at: string;
  paper_count: number;
  document_count: number;
  documents: GeneratedDocumentSet[];
  zip_available: boolean;
  zip_download_url: string | null;
  pdf_backend: string | null;
  warnings: string[];
  /** How many generated documents failed validation against their template. */
  validation_failures: number;
}

export interface GeneratorSettings {
  journal_code: string;
  reference_suffix: string;
  editor_name: string;
  journal_name: string;
  custom_placeholders: Record<string, string>;
  generate_pdf: boolean;
  pdf_backend_available: boolean;
  pdf_backend: string | null;
}

export interface GeneratorSettingsUpdate {
  journal_code?: string;
  reference_suffix?: string;
  editor_name?: string;
  journal_name?: string;
  custom_placeholders?: Record<string, string>;
  generate_pdf?: boolean;
}

export interface BatchFormValues {
  acceptanceDate: string;
  deadline: string;
  referencePrefix?: string;
  referenceSuffix?: string;
  journalCode?: string;
  editor?: string;
  journal?: string;
  generatePdf?: boolean;
}

/** Absolute URL for a download link the backend produced. */
export function absoluteUrl(path: string): string {
  const base = API_BASE_URL.replace(/\/$/, "");
  return `${base}${path}`;
}

export async function listDocumentTypes(): Promise<DocumentTypeInfo[]> {
  const { data } = await apiClient.get<DocumentTypeInfo[]>(
    "/document-generator/document-types",
  );
  return data;
}

export async function listTemplates(): Promise<TemplateInfo[]> {
  const { data } = await apiClient.get<TemplateInfo[]>(
    "/document-generator/templates",
    // Templates change out of band (an upload from another tab), so this
    // listing must never be served from a stale cache.
    { headers: { "Cache-Control": "no-store" } },
  );
  return data;
}

/**
 * Store or replace a master template.
 *
 * `replace` selects the endpoint; both archive whatever was in the slot, so the
 * distinction is about intent, not behaviour.
 */
export async function uploadTemplate(
  documentType: string,
  file: File,
  replace = false,
): Promise<TemplateInfo> {
  const form = new FormData();
  form.append("file", file);
  const endpoint = replace
    ? "/document-generator/templates/replace"
    : "/document-generator/templates/upload";
  const { data } = await apiClient.post<TemplateInfo>(endpoint, form, {
    params: { document_type: documentType },
  });
  return data;
}

/**
 * The stored template broken into selectable text, plus a first guess at each
 * field. This is what lets an ordinary Word file become a template without the
 * operator ever typing a `{{PLACEHOLDER}}`.
 */
export async function inspectTemplate(
  documentType: string,
): Promise<TemplateInspection> {
  const { data } = await apiClient.get<TemplateInspection>(
    `/document-generator/templates/${documentType}/inspect`,
    { headers: { "Cache-Control": "no-store" } },
  );
  return data;
}

export async function getTemplateMapping(
  documentType: string,
): Promise<TemplateMapping> {
  const { data } = await apiClient.get<TemplateMapping>(
    `/document-generator/templates/${documentType}/mapping`,
    { headers: { "Cache-Control": "no-store" } },
  );
  return data;
}

/** Confirm the wizard's mapping. Saved permanently and reused for every batch. */
export async function saveTemplateMapping(
  documentType: string,
  mappings: Array<{ field: string; text: string }>,
): Promise<TemplateMapping> {
  const { data } = await apiClient.put<TemplateMapping>(
    `/document-generator/templates/${documentType}/mapping`,
    { mappings },
  );
  return data;
}

function batchForm(files: File[], values: BatchFormValues): FormData {
  const form = new FormData();
  // Appended in the operator's chosen order: that order is what the reference
  // number's sequence component encodes.
  files.forEach((file) => form.append("files", file));
  form.append("acceptance_date", values.acceptanceDate ?? "");
  form.append("deadline", values.deadline ?? "");
  if (values.referencePrefix) form.append("reference_prefix", values.referencePrefix);
  if (values.referenceSuffix) form.append("reference_suffix", values.referenceSuffix);
  if (values.journalCode) form.append("journal_code", values.journalCode);
  if (values.editor) form.append("editor", values.editor);
  if (values.journal) form.append("journal", values.journal);
  if (values.generatePdf !== undefined) {
    form.append("generate_pdf", String(values.generatePdf));
  }
  return form;
}

export async function generateBatch(
  files: File[],
  values: BatchFormValues,
): Promise<BatchSummary> {
  const { data } = await apiClient.post<BatchSummary>(
    "/document-generator/generate-batch",
    batchForm(files, values),
  );
  return data;
}

export async function getBatch(batchId: string): Promise<BatchSummary> {
  const { data } = await apiClient.get<BatchSummary>(
    `/document-generator/batches/${batchId}`,
  );
  return data;
}

export async function getSettings(): Promise<GeneratorSettings> {
  const { data } = await apiClient.get<GeneratorSettings>(
    "/document-generator/settings",
    { headers: { "Cache-Control": "no-store" } },
  );
  return data;
}

export async function updateSettings(
  update: GeneratorSettingsUpdate,
): Promise<GeneratorSettings> {
  const { data } = await apiClient.put<GeneratorSettings>(
    "/document-generator/settings",
    update,
  );
  return data;
}
