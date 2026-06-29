import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useParams } from "react-router-dom";

import type { ApplicationDetail, WorkflowAction } from "@/api/applications";
import { ApiError } from "@/api/client";
import { AuditTrail } from "@/components/AuditTrail";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { StatusBadge } from "@/components/StatusBadge";
import { TextareaField } from "@/components/TextareaField";
import { CATEGORY_LABELS, reviewDecisionSchema } from "@/lib/schemas";
import type { ReviewDecisionValues } from "@/lib/schemas";

import {
  useApprove,
  useReject,
  useReturn,
  useReviewerApplication,
  useStartReview,
} from "./hooks";

function actionErrorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "The action could not be completed.";
}

// How the latest audit entry's to_status reads in the resolved summary. The
// audit trail is the record of what happened; this only labels it.
const RESOLUTION_VERBS: Record<string, string> = {
  APPROVED: "Approved",
  REJECTED: "Rejected",
  RETURNED: "Returned for changes",
  SUBMITTED: "Submitted",
  UNDER_REVIEW: "Moved under review",
  DRAFT: "Drafted",
};

// Shown in place of the Decision panel when the server reports no available
// actions (a decision already made, or otherwise nothing for this reviewer to
// do). Derived from the most recent audit entry — never from a client-side
// status rule.
function ResolvedSummary({ data }: { data: ApplicationDetail }) {
  const latest = data.audit_logs.at(-1);
  return (
    <div
      data-testid="resolved-summary"
      className="rounded border bg-gray-50 p-4 text-sm"
    >
      {latest ? (
        <p>
          <span className="font-medium">
            {RESOLUTION_VERBS[latest.to_status] ?? latest.to_status}
          </span>{" "}
          by {latest.actor_name || latest.actor_email} ·{" "}
          {new Date(latest.created_at).toLocaleString()}
        </p>
      ) : (
        <p className="text-gray-500">No actions available.</p>
      )}
    </div>
  );
}

// A reviewer's view of one application: its fields, the actions the backend says
// are currently legal, and the audit trail. The button set comes straight from
// `available_actions` — the UI never decides legality from status. An illegal
// transition (403 / invalid_transition / comment_required) still comes back as a
// normal inline error; the backend remains the sole authority.
export function ReviewerApplicationDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const { data, isPending, isError, error, refetch } =
    useReviewerApplication(id);

  const startReview = useStartReview(id);
  const approve = useApprove(id);
  const reject = useReject(id);
  const returnForChanges = useReturn(id);

  const [rejectOpen, setRejectOpen] = useState(false);

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<ReviewDecisionValues>({
    resolver: zodResolver(reviewDecisionSchema),
    defaultValues: { comment: "" },
  });

  if (isPending) return <LoadingState />;
  if (isError) {
    return (
      <ErrorState
        message={error instanceof Error ? error.message : "Failed to load."}
        onRetry={() => void refetch()}
      />
    );
  }

  const mutations = [startReview, approve, reject, returnForChanges];
  const busy = mutations.some((mutation) => mutation.isPending);
  const failed = mutations.find((mutation) => mutation.isError);

  // Server truth: the only source for which controls to render. `can` reads the
  // list the backend returned — it does not look at status.
  const actions = data.available_actions;
  const can = (action: WorkflowAction) => actions.includes(action);
  const showComment = can("reject") || can("return");

  return (
    <section className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold">{data.title}</h1>
          <p className="text-sm text-gray-500">
            {CATEGORY_LABELS[data.category]} · {data.owner_email}
          </p>
        </div>
        <StatusBadge status={data.status} />
      </div>

      <dl className="grid grid-cols-[7rem_1fr] gap-2 text-sm">
        <dt className="text-gray-500">Amount</dt>
        <dd>{data.amount ?? "—"}</dd>
        <dt className="text-gray-500">Description</dt>
        <dd className="whitespace-pre-wrap">{data.description || "—"}</dd>
        <dt className="text-gray-500">Submitted</dt>
        <dd>
          {data.submitted_at
            ? new Date(data.submitted_at).toLocaleString()
            : "—"}
        </dd>
        <dt className="text-gray-500">Reviewed</dt>
        <dd>
          {data.reviewed_at
            ? new Date(data.reviewed_at).toLocaleString()
            : "—"}
        </dd>
      </dl>

      {actions.length === 0 ? (
        <ResolvedSummary data={data} />
      ) : (
        <div className="space-y-4 rounded border p-4">
          <h2 className="text-sm font-semibold">Decision</h2>

          {can("start_review") || can("approve") ? (
            <div className="flex flex-wrap gap-2">
              {can("start_review") ? (
                <button
                  type="button"
                  onClick={() => startReview.mutate()}
                  disabled={busy}
                  className="rounded border px-3 py-1.5 text-sm disabled:opacity-50"
                >
                  Start review
                </button>
              ) : null}
              {can("approve") ? (
                <button
                  type="button"
                  onClick={() => approve.mutate()}
                  disabled={busy}
                  className="rounded bg-green-700 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
                >
                  Approve
                </button>
              ) : null}
            </div>
          ) : null}

          {showComment ? (
            // Reject and return share one comment; the backend requires it for
            // both. The empty-comment check below is input validation only — the
            // backend still enforces the transition's legality.
            <form className="space-y-3">
              <TextareaField
                label="Comment"
                rows={3}
                error={errors.comment?.message}
                {...register("comment")}
              />
              <p className="text-xs text-gray-500">
                Required to reject or return.
              </p>
              <div className="flex flex-wrap gap-2">
                {can("reject") ? (
                  <button
                    type="button"
                    // Validate the comment first; only open the confirm dialog
                    // once it's present. Rejecting is irreversible.
                    onClick={handleSubmit(() => setRejectOpen(true))}
                    disabled={busy}
                    className="rounded bg-red-700 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
                  >
                    Reject
                  </button>
                ) : null}
                {can("return") ? (
                  <button
                    type="button"
                    onClick={handleSubmit((values) =>
                      returnForChanges.mutate(values.comment),
                    )}
                    disabled={busy}
                    className="rounded border px-3 py-1.5 text-sm disabled:opacity-50"
                  >
                    Return for changes
                  </button>
                ) : null}
              </div>
            </form>
          ) : null}

          {failed ? (
            <ErrorState message={actionErrorMessage(failed.error)} />
          ) : null}
        </div>
      )}

      <ConfirmDialog
        open={rejectOpen}
        onOpenChange={setRejectOpen}
        title="Reject this application?"
        description="This is final and can't be undone."
        confirmLabel="Reject"
        onConfirm={() => reject.mutate(getValues("comment"))}
      />

      <div className="space-y-2">
        <h2 className="text-sm font-semibold">History</h2>
        <AuditTrail entries={data.audit_logs} />
      </div>
    </section>
  );
}
