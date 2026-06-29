// TanStack Query wrappers around the typed api/applications calls. Every screen
// reads and mutates server state through these — never hand-rolled fetch +
// useState/useEffect — so caching, loading/error state, and invalidation are
// consistent and the four UI states fall out of the query result.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createApplication,
  getApplication,
  listApplications,
  submitApplication,
  updateApplication,
} from "@/api/applications";
import type {
  ApplicationDetail,
  ApplicationListItem,
  CreateApplicationPayload,
  UpdateApplicationPayload,
} from "@/api/applications";

export const applicationKeys = {
  all: ["applications"] as const,
  list: () => [...applicationKeys.all, "list"] as const,
  detail: (id: number) => [...applicationKeys.all, "detail", id] as const,
};

export function useMyApplications() {
  return useQuery<ApplicationListItem[]>({
    queryKey: applicationKeys.list(),
    queryFn: listApplications,
  });
}

export function useApplication(id: number) {
  return useQuery<ApplicationDetail>({
    queryKey: applicationKeys.detail(id),
    queryFn: () => getApplication(id),
  });
}

export function useCreateApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateApplicationPayload) =>
      createApplication(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: applicationKeys.list() });
    },
  });
}

export function useUpdateApplication(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdateApplicationPayload) =>
      updateApplication(id, payload),
    onSuccess: (data) => {
      queryClient.setQueryData(applicationKeys.detail(id), data);
      void queryClient.invalidateQueries({ queryKey: applicationKeys.list() });
    },
  });
}

export function useSubmitApplication(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => submitApplication(id),
    onSuccess: (data) => {
      queryClient.setQueryData(applicationKeys.detail(id), data);
      void queryClient.invalidateQueries({ queryKey: applicationKeys.list() });
    },
  });
}
