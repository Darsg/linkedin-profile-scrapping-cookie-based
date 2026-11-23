import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { Page, ProfileDetail, ProfileSummary, ScrapeJob } from "@/lib/api/types";

export const profileKeys = {
  all: ["profiles"] as const,
  list: (q: string, offset: number) => [...profileKeys.all, "list", q, offset] as const,
  detail: (id: string) => [...profileKeys.all, "detail", id] as const,
};

export const PAGE_SIZE = 20;

export function useProfiles(q: string, offset: number) {
  return useQuery({
    queryKey: profileKeys.list(q, offset),
    queryFn: ({ signal }) =>
      api<Page<ProfileSummary>>("/profiles", { query: { q, limit: PAGE_SIZE, offset }, signal }),
    placeholderData: keepPreviousData,
  });
}

export function useProfile(id: string) {
  return useQuery({
    queryKey: profileKeys.detail(id),
    queryFn: ({ signal }) => api<ProfileDetail>(`/profiles/${id}`, { signal }),
  });
}

export function useRefreshProfile(id: string) {
  return useMutation({
    mutationFn: () => api<ScrapeJob>(`/profiles/${id}/refresh`, { method: "POST" }),
  });
}

export function useDeleteProfile(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>(`/profiles/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: profileKeys.detail(id) });
      void queryClient.invalidateQueries({ queryKey: profileKeys.all });
    },
  });
}
