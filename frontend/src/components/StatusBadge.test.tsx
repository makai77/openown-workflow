import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./StatusBadge";
import type { ApplicationStatus } from "@/api/applications";

const CASES: Array<[ApplicationStatus, string]> = [
  ["DRAFT", "Draft"],
  ["SUBMITTED", "Submitted"],
  ["UNDER_REVIEW", "Under review"],
  ["APPROVED", "Approved"],
  ["REJECTED", "Rejected"],
  ["RETURNED", "Returned for changes"],
];

describe("StatusBadge", () => {
  it.each(CASES)("renders label and icon for %s", (status, label) => {
    const { container } = render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
    // never colour-only: an icon accompanies the label
    expect(container.querySelector("svg")).toBeInTheDocument();
  });
});
