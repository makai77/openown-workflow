import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";

import type { ApplicationListItem } from "@/api/applications";
import { renderWithProviders } from "@/test/renderWithProviders";
import { MyApplicationsPage } from "./MyApplicationsPage";

vi.mock("@/api/applications", () => ({
  listApplications: vi.fn(),
  getApplication: vi.fn(),
  createApplication: vi.fn(),
  updateApplication: vi.fn(),
  submitApplication: vi.fn(),
}));

const { listApplications } = await import("@/api/applications");
const mockList = vi.mocked(listApplications);

function makeRow(overrides: Partial<ApplicationListItem> = {}): ApplicationListItem {
  return {
    id: 1,
    owner_email: "applicant@example.com",
    title: "My application",
    category: "GENERAL",
    amount: null,
    status: "DRAFT",
    submitted_at: null,
    reviewed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("MyApplicationsPage", () => {
  it("renders an ErrorState when the query fails", async () => {
    mockList.mockRejectedValueOnce(new Error("Network down"));
    renderWithProviders(<MyApplicationsPage />);
    expect(await screen.findByTestId("error-state")).toBeInTheDocument();
  });

  it("renders the applications on success", async () => {
    mockList.mockResolvedValueOnce([makeRow({ title: "Quarterly filing" })]);
    renderWithProviders(<MyApplicationsPage />);
    expect(await screen.findByText("Quarterly filing")).toBeInTheDocument();
  });
});
