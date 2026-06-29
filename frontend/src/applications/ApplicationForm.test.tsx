import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test/renderWithProviders";
import { NewApplicationPage } from "./ApplicationForm";

// The form's create call is never reached in this test (validation fails first),
// but the module is mocked so nothing touches the network.
vi.mock("@/api/applications", () => ({
  createApplication: vi.fn(),
  updateApplication: vi.fn(),
  getApplication: vi.fn(),
  listApplications: vi.fn(),
  submitApplication: vi.fn(),
}));

describe("ApplicationForm (new)", () => {
  it("shows a validation error when the title is empty", async () => {
    renderWithProviders(<NewApplicationPage />);

    await userEvent.click(
      screen.getByRole("button", { name: "Create draft" }),
    );

    expect(await screen.findByText("Title is required")).toBeInTheDocument();
  });
});
