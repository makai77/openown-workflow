import { expect, test } from "@playwright/test";

import { createSubmittedApplication, loginViaUi } from "./helpers";

// Reject flow (Playbook §8.4 #3): a blank comment is blocked as input validation;
// rejecting with a comment moves the application to REJECTED and the comment is
// visible in the audit trail. The comment requirement is the backend's rule — the
// UI mirrors it only as field validation.
test("reviewer must comment to reject, and the rejection shows in the trail", async ({
  page,
  request,
}) => {
  const id = await createSubmittedApplication(request, `E2E Reject ${Date.now()}`);

  await loginViaUi(page, "reviewer");
  await page.goto(`/reviewer/applications/${id}`);

  // Blank comment: blocked before any request goes out.
  await page.getByRole("button", { name: "Reject", exact: true }).click();
  await expect(page.getByText("A comment is required")).toBeVisible();
  await expect(page.getByTestId("status-badge").first()).toContainText(
    "Submitted",
  );

  // With a comment: the transition goes through.
  const reason = "E2E rejection — missing detail.";
  await page.getByLabel(/Comment/).fill(reason);
  await page.getByRole("button", { name: "Reject", exact: true }).click();

  await expect(page.getByTestId("status-badge").first()).toContainText(
    "Rejected",
  );
  await expect(page.getByTestId("audit-trail")).toContainText(reason);
});
