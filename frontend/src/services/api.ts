import apiClient from "@/api/client";
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

export function getDownloadUrl(jobId: string): string {
  // Use the same job-based path pattern as other job endpoints to avoid 404s
  return `${apiClient.defaults.baseURL}/job/${jobId}/download`;
}

export function getLatexUrl(jobId: string): string {
  return `${apiClient.defaults.baseURL}/job/${jobId}/latex`;
}

export function getLogUrl(jobId: string): string {
  return `${apiClient.defaults.baseURL}/job/${jobId}/log`;
}

export function getAssetUrl(jobId: string, assetPath: string): string {
  // assetPath may already be a relative path; ensure no leading slash duplication
  const normalized = assetPath.startsWith("/") ? assetPath.slice(1) : assetPath;
  return `${apiClient.defaults.baseURL}/job/${jobId}/assets/${normalized}`;
}

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
