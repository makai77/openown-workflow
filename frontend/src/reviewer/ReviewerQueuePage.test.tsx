import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { ApplicationListItem } from "@/api/applications";
import { renderWithProviders } from "@/test/renderWithProviders";
import { ReviewerQueuePage } from "./ReviewerQueuePage";

vi.mock("@/api/applications", () => ({
  listReviewerQueue: vi.fn(),
  getReviewerApplication: vi.fn(),
  startReview: vi.fn(),
  approveApplication: vi.fn(),
  rejectApplication: vi.fn(),
  returnApplication: vi.fn(),
}));

const { listReviewerQueue } = await import("@/api/applications");
const mockQueue = vi.mocked(listReviewerQueue);

function makeRow(overrides: Partial<ApplicationListItem> = {}): ApplicationListItem {
  return {
    id: 1,
    owner_email: "applicant@example.com",
    title: "Quarterly filing",
    category: "GENERAL",
    amount: null,
    status: "SUBMITTED",
    submitted_at: "2026-01-01T00:00:00Z",
    reviewed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("ReviewerQueuePage", () => {
  it("renders an ErrorState when the query fails", async () => {
    mockQueue.mockRejectedValueOnce(new Error("Network down"));
    renderWithProviders(<ReviewerQueuePage />);
    expect(await screen.findByTestId("error-state")).toBeInTheDocument();
  });

  it("renders the queue rows on success", async () => {
    mockQueue.mockResolvedValueOnce([makeRow({ title: "Grant request" })]);
    renderWithProviders(<ReviewerQueuePage />);
    expect(await screen.findByText("Grant request")).toBeInTheDocument();
  });

  it("renders an EmptyState when nothing matches", async () => {
    mockQueue.mockResolvedValueOnce([]);
    renderWithProviders(<ReviewerQueuePage />);
    expect(await screen.findByTestId("empty-state")).toBeInTheDocument();
  });

  it("defaults to the SUBMITTED filter and re-queries when it changes", async () => {
    mockQueue.mockResolvedValue([makeRow()]);
    renderWithProviders(<ReviewerQueuePage />);

    // Default filter drives ?status=SUBMITTED.
    await waitFor(() =>
      expect(mockQueue).toHaveBeenCalledWith("SUBMITTED"),
    );

    await userEvent.selectOptions(
      screen.getByLabelText("Status"),
      "APPROVED",
    );
    await waitFor(() => expect(mockQueue).toHaveBeenCalledWith("APPROVED"));

    // "All" clears the param (undefined → no ?status=).
    await userEvent.selectOptions(screen.getByLabelText("Status"), "");
    await waitFor(() => expect(mockQueue).toHaveBeenCalledWith(undefined));
  });
});
