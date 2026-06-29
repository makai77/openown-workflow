import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TextareaField } from "./TextareaField";

describe("TextareaField", () => {
  it("associates the label with the textarea", () => {
    render(<TextareaField label="Description" />);
    expect(screen.getByLabelText("Description")).toBeInstanceOf(
      HTMLTextAreaElement,
    );
  });

  it("wires the error to the textarea for assistive tech", () => {
    render(<TextareaField label="Description" error="Too long" />);
    expect(screen.getByLabelText("Description")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Too long");
  });
});
