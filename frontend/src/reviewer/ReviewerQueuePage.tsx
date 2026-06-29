import { useState } from "react";
import { Link } from "react-router-dom";

import type { ApplicationStatus } from "@/api/applications";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { SelectField } from "@/components/SelectField";
import { StatusBadge } from "@/components/StatusBadge";
import { CATEGORY_LABELS } from "@/lib/schemas";

import { useReviewerQueue } from "./hooks";

// "" is the "All" option (no ?status= filter); every other value is a real
// ApplicationStatus the backend understands. DRAFT is intentionally absent — the
// reviewer queue never includes drafts (for_reviewer_queue excludes them).
const FILTER_OPTIONS: { value: "" | ApplicationStatus; label: string }[] = [
  { value: "SUBMITTED", label: "Submitted" },
  { value: "UNDER_REVIEW", label: "Under review" },
  { value: "APPROVED", label: "Approved" },
  { value: "REJECTED", label: "Rejected" },
  { value: "RETURNED", label: "Returned" },
  { value: "", label: "All" },
];

// The reviewer's queue. Defaults to the actionable SUBMITTED view; the filter
// drives the ?status= param. The list uses the lightweight ApplicationListItem
// shape (no audit trail) to keep the query budget flat.
export function ReviewerQueuePage() {
  const [filter, setFilter] = useState<"" | ApplicationStatus>("SUBMITTED");
  const status = filter === "" ? undefined : filter;
  const { data, isPending, isError, error, refetch } = useReviewerQueue(status);

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold">Review queue</h1>
        <div className="w-48">
          <SelectField
            label="Status"
            value={filter}
            onChange={(event) =>
              setFilter(event.target.value as "" | ApplicationStatus)
            }
          >
            {FILTER_OPTIONS.map((option) => (
              <option key={option.value || "ALL"} value={option.value}>
                {option.label}
              </option>
            ))}
          </SelectField>
        </div>
      </div>

      {isPending ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState
          message={
            error instanceof Error ? error.message : "Failed to load the queue."
          }
          onRetry={() => void refetch()}
        />
      ) : data.length === 0 ? (
        <EmptyState message="No applications match this filter." />
      ) : (
        <ul className="divide-y rounded border">
          {data.map((application) => (
            <li key={application.id}>
              <Link
                to={`/reviewer/applications/${application.id}`}
                className="flex items-center justify-between gap-3 p-3 hover:bg-gray-50"
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">
                    {application.title}
                  </span>
                  <span className="text-xs text-gray-500">
                    {CATEGORY_LABELS[application.category]} ·{" "}
                    {application.owner_email}
                  </span>
                </span>
                <StatusBadge status={application.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
