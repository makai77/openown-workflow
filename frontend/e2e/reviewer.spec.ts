import { expect, test } from "@playwright/test";

import { createSubmittedApplication, loginViaUi } from "./helpers";

// Reviewer happy path (Playbook §8.4 #2): login → open a submitted application →
// start review → approve → status APPROVED with the trail showing each step.
test("reviewer can start review and approve a submitted application", async ({
  page,
  request,
}) => {
  const id = await createSubmittedApplication(request, `E2E Review ${Date.now()}`);

  await loginViaUi(page, "reviewer");
  await expect(page).toHaveURL(/\/reviewer\/applications$/);

  await page.goto(`/reviewer/applications/${id}`);
  await page.getByRole("button", { name: "Start review" }).click();
  await expect(page.getByTestId("status-badge").first()).toContainText(
    "Under review",
  );

  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByTestId("status-badge").first()).toContainText(
    "Approved",
  );

  const trail = page.getByTestId("audit-trail");
  await expect(trail).toContainText("Under review");
  await expect(trail).toContainText("Approved");
});
