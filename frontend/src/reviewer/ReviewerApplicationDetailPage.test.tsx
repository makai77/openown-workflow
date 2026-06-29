import { describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";

import { ApiError } from "@/api/client";
import type { ApplicationDetail, AuditLogEntry } from "@/api/applications";
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
  it("blocks reject until a comment is entered (input validation only)", async () => {
    mockGet.mockResolvedValueOnce(makeDetail());
    renderDetail();

    await screen.findByRole("heading", { name: "Grant request" });

    // Empty comment: the action is blocked client-side as input validation and
    // never reaches the API.
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(await screen.findByText("A comment is required")).toBeInTheDocument();
    expect(mockReject).not.toHaveBeenCalled();

    // With a comment, the transition fires with (id, comment).
    await userEvent.type(
      screen.getByLabelText(/Comment/),
      "Insufficient detail",
    );
    mockReject.mockResolvedValueOnce(
      makeDetail({
        status: "REJECTED",
        audit_logs: [makeAudit({ to_status: "REJECTED" })],
      }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(mockReject).toHaveBeenCalledWith(7, "Insufficient detail");
  });

  it("surfaces a backend rejection as a normal inline error", async () => {
    mockGet.mockResolvedValueOnce(makeDetail({ status: "APPROVED" }));
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
