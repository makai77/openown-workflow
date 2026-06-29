// TanStack Query wrappers around the typed reviewer api calls, mirroring
// applications/hooks.ts. Every reviewer screen reads and mutates server state
// through these so caching, the four UI states, and cache invalidation stay
// consistent. The frontend never decides workflow legality — these just call the
// endpoint and let the backend's response (success or WorkflowError) flow back.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  approveApplication,
  getReviewerApplication,
  listReviewerQueue,
  rejectApplication,
  returnApplication,
  startReview,
} from "@/api/applications";
import type {
  ApplicationDetail,
  ApplicationListItem,
  ApplicationStatus,
} from "@/api/applications";

export const reviewerKeys = {
  all: ["reviewer"] as const,
  // Prefix shared by every queue variant; invalidating it refreshes all status
  // filters at once without touching detail caches.
  queues: () => [...reviewerKeys.all, "queue"] as const,
  queue: (status?: ApplicationStatus) =>
    [...reviewerKeys.queues(), status ?? "ALL"] as const,
  detail: (id: number) => [...reviewerKeys.all, "detail", id] as const,
};

export function useReviewerQueue(status?: ApplicationStatus) {
  return useQuery<ApplicationListItem[]>({
    queryKey: reviewerKeys.queue(status),
    queryFn: () => listReviewerQueue(status),
  });
}

export function useReviewerApplication(id: number) {
  return useQuery<ApplicationDetail>({
    queryKey: reviewerKeys.detail(id),
    queryFn: () => getReviewerApplication(id),
  });
}

// After any transition the returned detail is the source of truth (the endpoint
// returns the full detail + trail): seed the detail cache with it directly, and
// invalidate only the queue so the row reflects the new status — or drops out of
// a filtered view. The detail we just set is authoritative, so we don't refetch
// it (mirrors useSubmitApplication in applications/hooks.ts).
function useReviewerTransition<TVars = void>(
  id: number,
  mutationFn: (variables: TVars) => Promise<ApplicationDetail>,
) {
  const queryClient = useQueryClient();
  return useMutation<ApplicationDetail, Error, TVars>({
    mutationFn,
    onSuccess: (data) => {
      queryClient.setQueryData(reviewerKeys.detail(id), data);
      void queryClient.invalidateQueries({ queryKey: reviewerKeys.queues() });
    },
  });
}

export function useStartReview(id: number) {
  return useReviewerTransition(id, () => startReview(id));
}

export function useApprove(id: number) {
  return useReviewerTransition(id, () => approveApplication(id));
}

export function useReject(id: number) {
  return useReviewerTransition<string>(id, (comment) =>
    rejectApplication(id, comment),
  );
}

export function useReturn(id: number) {
  return useReviewerTransition<string>(id, (comment) =>
    returnApplication(id, comment),
  );
}
