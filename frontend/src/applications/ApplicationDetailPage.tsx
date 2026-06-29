import { Link, useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import { AuditTrail } from "@/components/AuditTrail";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { StatusBadge } from "@/components/StatusBadge";
import { CATEGORY_LABELS } from "@/lib/schemas";

import { useApplication, useSubmitApplication } from "./hooks";

// One application: its fields, the submit action (when the workflow allows it),
// and the audit trail. The Submit button is a convenience; if the backend
// rejects the transition (403 / invalid_transition) we render that as a normal
// error — the UI never decides legality itself.
export function ApplicationDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const { data, isPending, isError, error, refetch } = useApplication(id);
  const submit = useSubmitApplication(id);

  if (isPending) return <LoadingState />;
  if (isError) {
    return (
      <ErrorState
        message={error instanceof Error ? error.message : "Failed to load."}
        onRetry={() => void refetch()}
      />
    );
  }

  const editable = data.status === "DRAFT" || data.status === "RETURNED";

  return (
    <section className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold">{data.title}</h1>
          <p className="text-sm text-gray-500">
            {CATEGORY_LABELS[data.category]}
          </p>
        </div>
        <StatusBadge status={data.status} />
      </div>

      <dl className="grid grid-cols-[7rem_1fr] gap-2 text-sm">
        <dt className="text-gray-500">Amount</dt>
        <dd>{data.amount ?? "—"}</dd>
        <dt className="text-gray-500">Description</dt>
        <dd className="whitespace-pre-wrap">{data.description || "—"}</dd>
        <dt className="text-gray-500">Created</dt>
        <dd>{new Date(data.created_at).toLocaleString()}</dd>
        <dt className="text-gray-500">Submitted</dt>
        <dd>
          {data.submitted_at
            ? new Date(data.submitted_at).toLocaleString()
            : "—"}
        </dd>
      </dl>

      {editable ? (
        <div className="flex gap-2">
          <Link
            to={`/applications/${id}/edit`}
            className="rounded border px-3 py-1.5 text-sm"
          >
            Edit
          </Link>
          <button
            type="button"
            onClick={() => submit.mutate()}
            disabled={submit.isPending}
            className="rounded bg-gray-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {submit.isPending ? "Submitting…" : "Submit for review"}
          </button>
        </div>
      ) : null}
      {submit.isError ? (
        <ErrorState
          message={
            submit.error instanceof ApiError
              ? submit.error.message
              : "Could not submit."
          }
        />
      ) : null}

      <div className="space-y-2">
        <h2 className="text-sm font-semibold">History</h2>
        <AuditTrail entries={data.audit_logs} />
      </div>
    </section>
  );
}
