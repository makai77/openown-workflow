import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SelectField } from "./SelectField";

describe("SelectField", () => {
  it("associates the label with the select", () => {
    render(
      <SelectField label="Category">
        <option value="GENERAL">General</option>
      </SelectField>,
    );
    expect(screen.getByLabelText("Category")).toBeInstanceOf(HTMLSelectElement);
  });

  it("wires the error to the select for assistive tech", () => {
    render(
      <SelectField label="Category" error="Required">
        <option value="GENERAL">General</option>
      </SelectField>,
    );
    expect(screen.getByLabelText("Category")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Required");
  });
});
