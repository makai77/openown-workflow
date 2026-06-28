import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Field } from "./Field";

describe("Field", () => {
  it("renders a label wired to the input", () => {
    render(<Field label="Title" />);
    expect(screen.getByLabelText("Title")).toBeInTheDocument();
  });

  it("shows the inline error and marks the input invalid", () => {
    render(<Field label="Title" error="Title is required" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Title is required");
    expect(screen.getByLabelText("Title")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("renders no error node when error is absent", () => {
    render(<Field label="Title" />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
