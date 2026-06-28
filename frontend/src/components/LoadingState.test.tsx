import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoadingState } from "./LoadingState";

describe("LoadingState", () => {
  it("exposes a polite status region while loading", () => {
    render(<LoadingState />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-busy", "true");
  });

  it("renders the requested number of skeleton rows", () => {
    render(<LoadingState rows={5} />);
    const rows = screen
      .getByTestId("loading-state")
      .querySelectorAll(".animate-pulse");
    expect(rows).toHaveLength(5);
  });
});
