import apiClient from "@/api/client";

/** One entry in a template's file tree. */
export interface TemplateFileEntry {
  path: string;
  type: "file" | "dir";
  size: number | null;
  is_text?: boolean;
}

/** Content of a single template file (text, or base64 for binaries). */
export interface TemplateFileContent {
  path: string;
  encoding: "text" | "base64";
  size: number;
  content: string;
}

/** One validation check result. */
export interface TemplateValidationCheck {
  name: string;
  ok: boolean;
  detail: string;
}

/** Full pre-conversion validation report for a template. */
export interface TemplateValidationReport {
  valid: boolean;
  errors: string[];
  warnings: string[];
  checks: TemplateValidationCheck[];
}

export async function listTemplateFiles(
  templateId: string,
): Promise<TemplateFileEntry[]> {
  const { data } = await apiClient.get<TemplateFileEntry[]>(
    `/templates/${templateId}/files`,
    noStore(),
  );
  return data;
}

export async function readTemplateFile(
  templateId: string,
  filePath: string,
): Promise<TemplateFileContent> {
  const { data } = await apiClient.get<TemplateFileContent>(
    `/templates/${templateId}/files/${encodePath(filePath)}`,
    noStore(),
  );
  return data;
}

export async function writeTemplateFile(
  templateId: string,
  filePath: string,
  content: string,
  encoding: "text" | "base64" = "text",
): Promise<{ path: string; size: number }> {
  const { data } = await apiClient.put<{ path: string; size: number }>(
    `/templates/${templateId}/files/${encodePath(filePath)}`,
    { content, encoding },
  );
  return data;
}

export async function deleteTemplateFile(
  templateId: string,
  filePath: string,
): Promise<void> {
  await apiClient.delete(`/templates/${templateId}/files/${encodePath(filePath)}`);
}

export function getTemplateDownloadUrl(templateId: string): string {
  return `${apiClient.defaults.baseURL}/templates/${templateId}/download`;
}

export async function validateTemplate(
  templateId: string,
): Promise<TemplateValidationReport> {
  const { data } = await apiClient.get<TemplateValidationReport>(
    `/templates/${templateId}/validate`,
  );
  return data;
}

/**
 * Request config that defeats every layer of HTTP caching for template reads.
 * A file's URL does not change when its contents change, so without this a
 * replaced binary (or an externally modified .tex) can be served from the
 * browser cache after a write.
 */
function noStore() {
  return {
    headers: { "Cache-Control": "no-cache", Pragma: "no-cache" },
    params: { _ts: Date.now() },
  };
}

/** Encode a relative file path segment-by-segment (keep the slashes). */
function encodePath(filePath: string): string {
  return filePath
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}
