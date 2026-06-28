import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders the message", () => {
    render(<EmptyState message="No applications yet" />);
    expect(screen.getByText("No applications yet")).toBeInTheDocument();
  });

  it("renders the optional call-to-action", () => {
    render(
      <EmptyState
        message="No applications yet"
        cta={<button type="button">New application</button>}
      />,
    );
    expect(
      screen.getByRole("button", { name: "New application" }),
    ).toBeInTheDocument();
  });
});
