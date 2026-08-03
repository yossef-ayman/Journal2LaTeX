import apiClient from "@/api/client";
import { API_BASE_URL } from "@/config";
import type {
  JobMetadata,
  JobSummary,
  TemplateMetadata,
  FidelityReport,
  AssetReport,
  DocumentStructure,
} from "@/types";

export async function uploadDocument(file: File): Promise<JobMetadata> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<JobMetadata>("/upload", form);
  return data;
}

export async function startConversion(
  jobId: string,
  templateId?: string,
  templateName = "default",
): Promise<JobMetadata> {
  const { data } = await apiClient.post<JobMetadata>(
    "/convert",
    {
      job_id: jobId,
      template_id: templateId,
      template_name: templateName,
    },
    { timeout: 0 }, // long-running: never abort a successful conversion
  );
  return data;
}

export async function startCompilation(
  jobId: string,
  templateId?: string,
  templateName = "default",
): Promise<JobMetadata> {
  const { data } = await apiClient.post<JobMetadata>(
    "/compile",
    {
      job_id: jobId,
      template_id: templateId,
      template_name: templateName,
    },
    { timeout: 0 }, // long-running: never abort a successful compilation
  );
  return data;
}

export async function uploadTemplate(file: File): Promise<TemplateMetadata> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<TemplateMetadata>("/templates/upload", form);
  return data;
}

export async function deleteTemplate(templateId: string): Promise<void> {
  await apiClient.delete(`/templates/${templateId}`);
}

export async function updateTemplate(
  templateId: string,
  updates: { display_name: string; journal_name: string; version: string; description: string }
): Promise<TemplateMetadata> {
  const { data } = await apiClient.put<TemplateMetadata>(`/templates/${templateId}`, updates);
  return data;
}

export async function getJobStatus(jobId: string): Promise<JobMetadata> {
  const { data } = await apiClient.get<JobMetadata>(`/job/${jobId}`);
  return data;
}

export async function deleteJob(jobId: string): Promise<void> {
  await apiClient.delete(`/job/${jobId}`);
}

export async function listJobs(): Promise<JobSummary[]> {
  const { data } = await apiClient.get<JobSummary[]>("/jobs");
  return data;
}

export async function listTemplates(): Promise<TemplateMetadata[]> {
  const { data } = await apiClient.get<TemplateMetadata[]>("/templates");
  return data;
}

/**
 * PDF download URL.
 * Backend schema: GET /download/{job_id}
 * (not /job/{job_id}/download — that path does not exist on the server)
 */
export function getDownloadUrl(jobId: string): string {
  return `${API_BASE_URL}/download/${jobId}`;
}

/**
 * LaTeX source download URL.
 * Backend schema: GET /job/{job_id}/latex (Content-Type: text/plain)
 */
export function getLatexUrl(jobId: string): string {
  return `${API_BASE_URL}/job/${jobId}/latex`;
}

// NOTE: /job/{job_id}/log does NOT exist in the backend OpenAPI schema.
// The getLogUrl helper has been removed. Log access is not available.

// NOTE: /job/{job_id}/assets/{path} does NOT exist in the backend OpenAPI schema.
// Individual asset serving is not available. The asset list endpoint
// (/job/{job_id}/assets) returns metadata only — no binary proxy.

export async function getFidelityReport(
  jobId: string,
): Promise<FidelityReport> {
  const { data } = await apiClient.get<FidelityReport>(
    `/job/${jobId}/fidelity`,
  );
  return data;
}

export async function getAssetReport(jobId: string): Promise<AssetReport> {
  const { data } = await apiClient.get<AssetReport>(`/job/${jobId}/assets`);
  return data;
}

export async function getDocumentStructure(
  jobId: string,
): Promise<DocumentStructure> {
  const { data } = await apiClient.get<DocumentStructure>(
    `/job/${jobId}/document`,
  );
  return data;
}

export async function getLatexSource(jobId: string): Promise<string> {
  const { data } = await apiClient.get<string>(`/job/${jobId}/latex`, {
    responseType: "text",
  });
  return data;
}
