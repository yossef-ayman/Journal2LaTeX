import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { listJobs, deleteJob } from "@/services";
import type { JobSummary } from "@/types";

export function useJobsList(): UseQueryResult<JobSummary[]> {
  return useQuery<JobSummary[]>({
    queryKey: ["jobs"],
    queryFn: listJobs,
    refetchInterval: 10_000,
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteJob,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });
}
