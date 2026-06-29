import { QueryClient } from "@tanstack/react-query";

// One QueryClient for the whole app. Server state is read-mostly here, so we
// disable refetch-on-focus and keep a short staleTime; a single retry covers a
// transient network blip without masking real 4xx errors (those surface to the
// UI as ErrorState).
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30_000,
    },
  },
});
