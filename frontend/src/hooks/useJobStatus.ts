import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { getJobStatus } from "@/services";
import type { JobMetadata } from "@/types";

export function useJobStatus(
  jobId: string | null,
): UseQueryResult<JobMetadata> {
  return useQuery<JobMetadata>({
    queryKey: ["job", "status", jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "COMPLETED" || status === "FAILED") {
        return false;
      }
      return 2000;
    },
    retry: false,
  });
}
