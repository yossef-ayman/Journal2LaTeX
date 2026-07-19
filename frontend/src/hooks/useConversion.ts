import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  uploadDocument,
  startConversion,
  startCompilation,
  uploadTemplate,
} from "@/services";
import type { ConversionRequest, CompileRequest } from "@/types";

export function useUploadMutation() {
  return useMutation({ mutationFn: (file: File) => uploadDocument(file) });
}

export function useConvertMutation() {
  return useMutation({
    mutationFn: (req: ConversionRequest) =>
      startConversion(req.job_id, req.template_id, req.template_name),
  });
}

export function useCompileMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: CompileRequest) =>
      startCompilation(req.job_id, req.template_id, req.template_name),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["job", "status", variables.job_id] });
    },
  });
}

export function useUploadTemplateMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadTemplate(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["templates"] });
    },
  });
}
