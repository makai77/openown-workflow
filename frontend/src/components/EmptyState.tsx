import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

interface EmptyStateProps {
  message: string;
  cta?: ReactNode;
}

// Icon + invitation + optional call-to-action for empty result sets.
export function EmptyState({ message, cta }: EmptyStateProps) {
  return (
    <div
      data-testid="empty-state"
      className="flex flex-col items-center gap-2 p-8 text-center text-gray-500"
    >
      <Inbox className="size-8" aria-hidden="true" />
      <p>{message}</p>
      {cta}
    </div>
  );
}
