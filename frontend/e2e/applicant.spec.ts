import { expect, test } from "@playwright/test";

import { loginViaUi } from "./helpers";

// Applicant happy path (Playbook §8.4 #1): login → create draft → edit → submit
// → status SUBMITTED with the DRAFT → SUBMITTED audit row visible.
test("applicant can create, edit, and submit a draft", async ({ page }) => {
  await loginViaUi(page, "applicant");
  await expect(page).toHaveURL(/\/applications$/);

  const title = `E2E Draft ${Date.now()}`;
  await page.getByRole("link", { name: "New application" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByLabel("Amount").fill("1500.00");
  await page.getByRole("button", { name: "Create draft" }).click();

  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  await expect(page.getByTestId("status-badge").first()).toContainText("Draft");

  // Edit while still a draft.
  await page.getByRole("link", { name: "Edit" }).click();
  await page.getByLabel("Title").fill(`${title} edited`);
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(
    page.getByRole("heading", { name: `${title} edited` }),
  ).toBeVisible();

  // Submit for review.
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(page.getByTestId("status-badge").first()).toContainText(
    "Submitted",
  );
  const trail = page.getByTestId("audit-trail");
  await expect(trail).toContainText("Draft");
  await expect(trail).toContainText("Submitted");
});
