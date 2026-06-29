import { describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";

import { ApiError } from "@/api/client";
import type {
  ApplicationDetail,
  AuditLogEntry,
  WorkflowAction,
} from "@/api/applications";
import { renderWithProviders } from "@/test/renderWithProviders";
import { ReviewerApplicationDetailPage } from "./ReviewerApplicationDetailPage";

vi.mock("@/api/applications", () => ({
  listReviewerQueue: vi.fn(),
  getReviewerApplication: vi.fn(),
  startReview: vi.fn(),
  approveApplication: vi.fn(),
  rejectApplication: vi.fn(),
  returnApplication: vi.fn(),
}));

const { getReviewerApplication, approveApplication, rejectApplication } =
  await import("@/api/applications");
const mockGet = vi.mocked(getReviewerApplication);
const mockApprove = vi.mocked(approveApplication);
const mockReject = vi.mocked(rejectApplication);

// A SUBMITTED application: the backend reports all four actions as legal.
const SUBMITTED_ACTIONS: WorkflowAction[] = [
  "start_review",
  "approve",
  "reject",
  "return",
];

function makeDetail(overrides: Partial<ApplicationDetail> = {}): ApplicationDetail {
  return {
    id: 7,
    owner: 1,
    owner_email: "applicant@example.com",
    title: "Grant request",
    category: "FINANCE",
    description: "Please review.",
    amount: "2500.00",
    status: "SUBMITTED",
    submitted_at: "2026-01-01T00:00:00Z",
    reviewed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    audit_logs: [],
    available_actions: SUBMITTED_ACTIONS,
    ...overrides,
  };
}

function makeAudit(overrides: Partial<AuditLogEntry> = {}): AuditLogEntry {
  return {
    id: 1,
    actor_name: "Riya Reviewer",
    actor_email: "reviewer@example.com",
    from_status: "SUBMITTED",
    to_status: "APPROVED",
    comment: "",
    created_at: "2026-01-02T00:00:00Z",
    ...overrides,
  };
}

// The page reads the id from the route param, so render under a matching Route —
// this keeps the query cache key aligned with the mutations' setQueryData.
function renderDetail() {
  return renderWithProviders(
    <Routes>
      <Route
        path="/reviewer/applications/:id"
        element={<ReviewerApplicationDetailPage />}
      />
    </Routes>,
    { route: "/reviewer/applications/7" },
  );
}

describe("ReviewerApplicationDetailPage", () => {
  it("renders only the buttons in available_actions (UNDER_REVIEW: no start review)", async () => {
    mockGet.mockResolvedValueOnce(
      makeDetail({
        status: "UNDER_REVIEW",
        available_actions: ["approve", "reject", "return"],
      }),
    );
    renderDetail();

    await screen.findByRole("heading", { name: "Grant request" });

    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Return for changes" }),
    ).toBeInTheDocument();
    // start_review is absent from available_actions, so its button must not show.
    expect(
      screen.queryByRole("button", { name: "Start review" }),
    ).not.toBeInTheDocument();
  });

  it("renders a resolved summary and no action buttons when available_actions is empty", async () => {
    mockGet.mockResolvedValueOnce(
      makeDetail({
        status: "APPROVED",
        reviewed_at: "2026-01-02T00:00:00Z",
        available_actions: [],
        audit_logs: [makeAudit({ to_status: "APPROVED" })],
      }),
    );
    renderDetail();

    await screen.findByRole("heading", { name: "Grant request" });

    // Resolved summary derived from the latest audit entry — no Decision panel.
    expect(screen.getByTestId("resolved-summary")).toHaveTextContent(
      /Approved by Riya Reviewer/,
    );
    expect(screen.queryByRole("heading", { name: "Decision" })).not.toBeInTheDocument();
    for (const name of ["Start review", "Approve", "Reject", "Return for changes"]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
  });

  it("blocks reject until a comment is entered (input validation only)", async () => {
    mockGet.mockResolvedValueOnce(makeDetail());
    renderDetail();

    await screen.findByRole("heading", { name: "Grant request" });

    // Empty comment: blocked client-side as input validation. No dialog opens and
    // the API is never called.
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(await screen.findByText("A comment is required")).toBeInTheDocument();
    expect(
      screen.queryByRole("alertdialog"),
    ).not.toBeInTheDocument();
    expect(mockReject).not.toHaveBeenCalled();
  });

  it("confirms before rejecting, then fires the transition with the comment", async () => {
    mockGet.mockResolvedValueOnce(makeDetail());
    renderDetail();

    await screen.findByRole("heading", { name: "Grant request" });

    await userEvent.type(
      screen.getByLabelText(/Comment/),
      "Insufficient detail",
    );
    // With a comment, Reject opens the irreversible-action confirmation first.
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(
      within(dialog).getByText(/can't be undone/i),
    ).toBeInTheDocument();
    expect(mockReject).not.toHaveBeenCalled();

    // Confirming inside the dialog fires the transition with (id, comment).
    mockReject.mockResolvedValueOnce(
      makeDetail({
        status: "REJECTED",
        available_actions: [],
        audit_logs: [makeAudit({ to_status: "REJECTED" })],
      }),
    );
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Reject" }),
    );
    expect(mockReject).toHaveBeenCalledWith(7, "Insufficient detail");
  });

  it("surfaces a backend rejection as a normal inline error", async () => {
    mockGet.mockResolvedValueOnce(makeDetail({ status: "SUBMITTED" }));
    mockApprove.mockRejectedValueOnce(
      new ApiError(400, {
        code: "invalid_transition",
        message: "Only submitted or under-review applications can be approved.",
        details: {},
      }),
    );
    renderDetail();

    await screen.findByRole("heading", { name: "Grant request" });
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));

    expect(
      await screen.findByText(
        "Only submitted or under-review applications can be approved.",
      ),
    ).toBeInTheDocument();
  });

  it("renders the new status and audit row after a successful approve", async () => {
    mockGet.mockResolvedValueOnce(makeDetail({ status: "SUBMITTED" }));
    mockApprove.mockResolvedValueOnce(
      makeDetail({
        status: "APPROVED",
        reviewed_at: "2026-01-02T00:00:00Z",
        available_actions: [],
        audit_logs: [makeAudit()],
      }),
    );
    renderDetail();

    await screen.findByRole("heading", { name: "Grant request" });
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));

    const trail = await screen.findByTestId("audit-trail");
    const badges = within(trail).getAllByTestId("status-badge");
    expect(badges[0]).toHaveTextContent("Submitted");
    expect(badges[1]).toHaveTextContent("Approved");
  });
});
