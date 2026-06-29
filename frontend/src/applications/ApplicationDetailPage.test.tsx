import { describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";

import type { ApplicationDetail, AuditLogEntry } from "@/api/applications";
import { renderWithProviders } from "@/test/renderWithProviders";
import { ApplicationDetailPage } from "./ApplicationDetailPage";

vi.mock("@/api/applications", () => ({
  listApplications: vi.fn(),
  getApplication: vi.fn(),
  createApplication: vi.fn(),
  updateApplication: vi.fn(),
  submitApplication: vi.fn(),
}));

const { getApplication, submitApplication } = await import(
  "@/api/applications"
);
const mockGet = vi.mocked(getApplication);
const mockSubmit = vi.mocked(submitApplication);

function makeDetail(overrides: Partial<ApplicationDetail> = {}): ApplicationDetail {
  return {
    id: 7,
    owner: 1,
    owner_email: "applicant@example.com",
    title: "Verify Walkthrough",
    category: "GENERAL",
    description: "Initial draft description.",
    amount: "2500.00",
    status: "DRAFT",
    submitted_at: null,
    reviewed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    audit_logs: [],
    // Applicant-side detail: the reviewer-action list is always empty here.
    available_actions: [],
    ...overrides,
  };
}

function makeAudit(overrides: Partial<AuditLogEntry> = {}): AuditLogEntry {
  return {
    id: 1,
    actor_name: "Alice Applicant",
    actor_email: "applicant@example.com",
    from_status: "DRAFT",
    to_status: "SUBMITTED",
    comment: "",
    created_at: "2026-01-02T00:00:00Z",
    ...overrides,
  };
}

// The page reads the id from the route param, so render it under a matching
// Route — this also keeps the query cache key aligned with the submit mutation's
// setQueryData, which is what makes the submit→re-render assertion meaningful.
function renderDetail() {
  return renderWithProviders(
    <Routes>
      <Route path="/applications/:id" element={<ApplicationDetailPage />} />
    </Routes>,
    { route: "/applications/7" },
  );
}

describe("ApplicationDetailPage", () => {
  it("renders an ErrorState when the query fails", async () => {
    mockGet.mockRejectedValueOnce(new Error("Network down"));
    renderDetail();
    expect(await screen.findByTestId("error-state")).toBeInTheDocument();
  });

  it("renders the status and the audit trail for a submitted application", async () => {
    mockGet.mockResolvedValueOnce(
      makeDetail({
        status: "SUBMITTED",
        submitted_at: "2026-01-02T00:00:00Z",
        audit_logs: [makeAudit()],
      }),
    );
    renderDetail();

    expect(
      await screen.findByRole("heading", { name: "Verify Walkthrough" }),
    ).toBeInTheDocument();

    const trail = screen.getByTestId("audit-trail");
    const badges = within(trail).getAllByTestId("status-badge");
    expect(badges).toHaveLength(2);
    expect(badges[0]).toHaveTextContent("Draft");
    expect(badges[1]).toHaveTextContent("Submitted");

    // A submitted application is not editable: no Edit/Submit affordances.
    expect(
      screen.queryByRole("button", { name: "Submit for review" }),
    ).not.toBeInTheDocument();
  });

  it("submits a draft and renders the resulting Draft→Submitted audit row", async () => {
    mockGet.mockResolvedValueOnce(makeDetail({ status: "DRAFT" }));
    mockSubmit.mockResolvedValueOnce(
      makeDetail({
        status: "SUBMITTED",
        submitted_at: "2026-01-02T00:00:00Z",
        audit_logs: [makeAudit()],
      }),
    );
    renderDetail();

    // Draft state: empty history, submit affordance present.
    expect(await screen.findByText("No history yet.")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Submit for review" }),
    );

    // After the transition resolves the page re-renders from the returned
    // detail: the single new audit row appears.
    const trail = await screen.findByTestId("audit-trail");
    const badges = within(trail).getAllByTestId("status-badge");
    expect(badges).toHaveLength(2);
    expect(badges[0]).toHaveTextContent("Draft");
    expect(badges[1]).toHaveTextContent("Submitted");
    expect(mockSubmit).toHaveBeenCalledWith(7);
  });
});
