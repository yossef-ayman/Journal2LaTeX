import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { listTemplates } from "@/services";
import type { TemplateMetadata } from "@/types";

export function useTemplates(): UseQueryResult<TemplateMetadata[]> {
  return useQuery<TemplateMetadata[]>({
    queryKey: ["templates"],
    queryFn: listTemplates,
    staleTime: 300_000,
  });
}
