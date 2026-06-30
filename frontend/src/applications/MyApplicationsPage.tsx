import { Link } from "react-router-dom";

import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { StatusBadge } from "@/components/StatusBadge";
import { CATEGORY_LABELS } from "@/lib/schemas";
import { useDocumentTitle } from "@/lib/useDocumentTitle";

import { useMyApplications } from "./hooks";

// The applicant's own applications. The query result drives all four states:
// loading, error (with retry), empty (with a CTA), and the populated list.
export function MyApplicationsPage() {
  const { data, isPending, isError, error, refetch } = useMyApplications();
  useDocumentTitle("My applications");

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">My applications</h1>
        <Link
          to="/applications/new"
          className="rounded bg-brand px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-hover"
        >
          New application
        </Link>
      </div>

      {isPending ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState
          message={
            error instanceof Error
              ? error.message
              : "Failed to load applications."
          }
          onRetry={() => void refetch()}
        />
      ) : data.length === 0 ? (
        <EmptyState
          message="You have no applications yet."
          cta={
            <Link
              to="/applications/new"
              className="rounded border px-3 py-1.5 text-sm"
            >
              Create your first one
            </Link>
          }
        />
      ) : (
        <ul className="divide-y rounded border">
          {data.map((application) => (
            <li key={application.id}>
              <Link
                to={`/applications/${application.id}`}
                className="flex items-center justify-between gap-3 p-3 hover:bg-gray-50"
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">
                    {application.title}
                  </span>
                  <span className="text-xs text-gray-500">
                    {CATEGORY_LABELS[application.category]}
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
