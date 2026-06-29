import { expect, test } from "@playwright/test";

import { API_BASE_URL, createSubmittedApplication, getToken } from "./helpers";

// The mandatory authorization test (Playbook §8.3 / §8.4 #4), end-to-end against
// the live API: an applicant calling a reviewer transition endpoint directly is
// rejected by the permission layer with 403, and the application's status is
// unchanged — the rule is enforced server-side, not by the UI hiding a button.
test("applicant is forbidden from the reviewer approve endpoint (403)", async ({
  request,
}) => {
  const id = await createSubmittedApplication(request, `Forbidden ${Date.now()}`);
  const token = await getToken(request, "applicant");
  const headers = { Authorization: `Token ${token}` };

  const response = await request.post(
    `${API_BASE_URL}/reviewer/applications/${id}/approve/`,
    { headers, data: {} },
  );
  expect(response.status()).toBe(403);

  // Status is untouched by the rejected call.
  const detail = await request.get(`${API_BASE_URL}/applications/${id}/`, {
    headers,
  });
  expect((await detail.json()).status).toBe("SUBMITTED");
});
