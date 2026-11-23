import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { isActive, type Page, type ScrapeJob } from "@/lib/api/types";

export const jobKeys = {
  all: ["scrape-jobs"] as const,
  list: () => [...jobKeys.all, "list"] as const,
  detail: (id: string) => [...jobKeys.all, "detail", id] as const,
};

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { url: string; force?: boolean }) =>
      api<ScrapeJob>("/scrape-jobs", { method: "POST", body: input }),
    onSuccess: (job) => {
      queryClient.setQueryData(jobKeys.detail(job.id), job);
      void queryClient.invalidateQueries({ queryKey: jobKeys.list() });
    },
  });
}

/** One job, polled while it is queued or running. */
export function useJob(id: string | null) {
  return useQuery({
    queryKey: jobKeys.detail(id ?? "none"),
    queryFn: ({ signal }) => api<ScrapeJob>(`/scrape-jobs/${id}`, { signal }),
    enabled: id !== null,
    refetchInterval: (query) => (query.state.data && !isActive(query.state.data) ? false : 1500),
  });
}

/** Recent jobs, polled only while any of them is still in flight. */
export function useRecentJobs(limit = 8) {
  return useQuery({
    queryKey: jobKeys.list(),
    queryFn: ({ signal }) => api<Page<ScrapeJob>>("/scrape-jobs", { query: { limit }, signal }),
    refetchInterval: (query) => (query.state.data?.items.some(isActive) ? 2000 : false),
  });
}
