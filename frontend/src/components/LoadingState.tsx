// Skeleton rows for any data screen's loading state.
export function LoadingState({ rows = 3 }: { rows?: number }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      data-testid="loading-state"
    >
      <span className="sr-only">Loading…</span>
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className="mb-2 h-4 animate-pulse rounded bg-gray-200"
        />
      ))}
    </div>
  );
}
