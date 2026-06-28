import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuditTrail } from "./AuditTrail";
import type { AuditLogEntry } from "@/api/applications";

const entry = (overrides: Partial<AuditLogEntry> = {}): AuditLogEntry => ({
  id: 1,
  actor_name: "Bob Reviewer",
  actor_email: "reviewer@example.com",
  from_status: "SUBMITTED",
  to_status: "APPROVED",
  comment: "",
  created_at: "2026-06-29T10:00:00Z",
  ...overrides,
});

describe("AuditTrail", () => {
  it("renders one row per entry", () => {
    render(
      <AuditTrail
        entries={[entry({ id: 1 }), entry({ id: 2, to_status: "REJECTED" })]}
      />,
    );
    expect(screen.getByTestId("audit-trail").querySelectorAll("li")).toHaveLength(
      2,
    );
  });

  it("shows the comment when present", () => {
    render(<AuditTrail entries={[entry({ comment: "Looks good" })]} />);
    expect(screen.getByText("Looks good")).toBeInTheDocument();
  });

  it("renders a placeholder when there is no history", () => {
    render(<AuditTrail entries={[]} />);
    expect(screen.getByText("No history yet.")).toBeInTheDocument();
  });
});
