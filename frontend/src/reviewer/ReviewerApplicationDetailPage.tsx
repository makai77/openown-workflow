import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import { AuditTrail } from "@/components/AuditTrail";
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

// A reviewer's view of one application: its fields, the four workflow actions,
// and the audit trail. The action buttons are a convenience — the backend is the
// sole authority on legality. An illegal transition (403 / invalid_transition /
// comment_required) comes back as a normal inline error; the UI never decides.
export function ReviewerApplicationDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const { data, isPending, isError, error, refetch } =
    useReviewerApplication(id);

  const startReview = useStartReview(id);
  const approve = useApprove(id);
  const reject = useReject(id);
  const returnForChanges = useReturn(id);

  const {
    register,
    handleSubmit,
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

      <div className="space-y-4 rounded border p-4">
        <h2 className="text-sm font-semibold">Decision</h2>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => startReview.mutate()}
            disabled={busy}
            className="rounded border px-3 py-1.5 text-sm disabled:opacity-50"
          >
            Start review
          </button>
          <button
            type="button"
            onClick={() => approve.mutate()}
            disabled={busy}
            className="rounded bg-green-700 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
          >
            Approve
          </button>
        </div>

        {/* Reject and return share one comment; the backend requires it for both.
            The empty-comment check below is input validation, not a legality
            decision — the backend still enforces the transition. */}
        <form className="space-y-3">
          <TextareaField
            label="Comment (required to reject or return)"
            rows={3}
            error={errors.comment?.message}
            {...register("comment")}
          />
          <p className="text-xs text-gray-500">
            Rejecting is final. Returning sends the application back to the
            applicant to revise and re-submit. Both notify the applicant via the
            audit trail.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleSubmit((values) => reject.mutate(values.comment))}
              disabled={busy}
              className="rounded bg-red-700 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            >
              Reject
            </button>
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
          </div>
        </form>

        {failed ? <ErrorState message={actionErrorMessage(failed.error)} /> : null}
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-semibold">History</h2>
        <AuditTrail entries={data.audit_logs} />
      </div>
    </section>
  );
}
