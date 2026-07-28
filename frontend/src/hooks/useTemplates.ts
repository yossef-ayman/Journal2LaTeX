import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { listTemplates } from "@/services";
import type { TemplateMetadata } from "@/types";

export function useTemplates(): UseQueryResult<TemplateMetadata[]> {
  return useQuery<TemplateMetadata[]>({
    queryKey: ["templates"],
    queryFn: listTemplates,
    // Template metadata changes whenever a template is uploaded, edited or
    // deleted, so never serve it from a stale cache.
    staleTime: 0,
    refetchOnMount: "always",
  });
}
