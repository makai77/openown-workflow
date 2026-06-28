import { AlertTriangle } from "lucide-react";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

// Icon + message + optional retry. A 403 / invalid_transition from the API is
// surfaced here like any other error — the UI never guards transitions itself.
export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div
      role="alert"
      data-testid="error-state"
      className="flex flex-col items-center gap-2 p-8 text-center text-red-600"
    >
      <AlertTriangle className="size-8" aria-hidden="true" />
      <p>{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded border px-3 py-1 text-sm"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
