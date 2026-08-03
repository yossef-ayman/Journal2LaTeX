import apiClient from "@/api/client";
import type {
  AnalyzeResult,
  EngineStatus,
  PluginDescription,
  PreviewResult,
  Suggestion,
  SuggestResult,
} from "@/types/documentEngine";

async function readErrorDetail(error: unknown): Promise<string | null> {
  if (!(error instanceof Error)) return null;
  const anyError = error as Error & { response?: { data?: unknown } };
  const data = anyError.response?.data;
  if (data instanceof Blob) {
    try {
      const text = await data.text();
      const parsed = JSON.parse(text) as { detail?: string };
      return parsed.detail ?? text;
    } catch {
      return null;
    }
  }
  const detail = data as { detail?: string } | undefined;
  return detail?.detail ?? null;
}

/** Which parts of the Document Engine are live on the server. */
export async function getEngineStatus(): Promise<EngineStatus> {
  const { data } = await apiClient.get<EngineStatus>("/document-engine/status");
  return data;
}

/** Every suggestion plugin this deployment has, with its default state. */
export async function listEnginePlugins(): Promise<PluginDescription[]> {
  const { data } = await apiClient.get<{ plugins: PluginDescription[] }>(
    "/document-engine/plugins",
  );
  return data.plugins;
}

/** Upload a .docx and get back the semantic model the engine understood. */
export async function analyzeDocument(file: File): Promise<AnalyzeResult> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<AnalyzeResult>(
    "/document-engine/analyze",
    form,
    { timeout: 0 },
  );
  return data;
}

/** Run the selected plugins (defaults when empty) over a manuscript. Proposes only. */
export async function suggestDocument(
  file: File,
  plugins: string[] = [],
): Promise<SuggestResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("plugins", plugins.join(","));
  const { data } = await apiClient.post<SuggestResult>(
    "/document-engine/suggest",
    form,
    { timeout: 0 },
  );
  return data;
}

function decisionsPayload(decisions: Suggestion[]): string {
  return JSON.stringify(
    decisions.map((s) => ({
      id: s.id,
      node_id: s.node_id,
      kind: s.kind,
      reason: s.reason,
      source: s.source,
      confidence: s.confidence,
      status: s.status,
      original: s.original,
      suggested: s.suggested,
      user_text: s.user_text,
    })),
  );
}

/** What accepting these decisions would do. Writes nothing. */
export async function previewDocument(
  file: File,
  decisions: Suggestion[],
): Promise<PreviewResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("suggestions", decisionsPayload(decisions));
  const { data } = await apiClient.post<PreviewResult>(
    "/document-engine/preview",
    form,
    { timeout: 0 },
  );
  return data;
}

export interface ApplyOutcome {
  blob: Blob;
  fileName: string;
  applied: number;
  refused: { suggestion_id: string; node_id: string; reason: string }[];
}

/** The document with the accepted suggestions written into it. */
export async function applyDocument(
  file: File,
  decisions: Suggestion[],
): Promise<ApplyOutcome> {
  const form = new FormData();
  form.append("file", file);
  form.append("suggestions", decisionsPayload(decisions));
  const response = await apiClient.post<Blob>("/document-engine/apply", form, {
    responseType: "blob",
    timeout: 0,
  });

  const disposition = response.headers["content-disposition"] ?? "";
  const dispositionMatch = disposition.match(/filename="?([^"]+)"?/);
  const fileName = dispositionMatch?.[1] ?? `edited-${file.name}`;

  let applied = 0;
  const appliedHeader = response.headers["x-edits-applied"];
  if (appliedHeader !== undefined && appliedHeader !== null && appliedHeader !== "") {
    applied = Number(appliedHeader) || 0;
  }

  let refused: ApplyOutcome["refused"] = [];
  const refusedHeader = response.headers["x-edits-refused"];
  if (refusedHeader && refusedHeader !== "0") {
    try {
      const parsed = JSON.parse(refusedHeader);
      if (Array.isArray(parsed)) refused = parsed;
    } catch {
      refused = [];
    }
  }

  return { blob: response.data, fileName, applied, refused };
}

export { readErrorDetail };
