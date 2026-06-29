import type { APIRequestContext, Page } from "@playwright/test";

// The API base for direct calls (token auth, seeding). The frontend talks to the
// same URL via VITE_API_BASE_URL.
export const API_BASE_URL =
  process.env.E2E_API_BASE_URL ?? "http://localhost:8000/api";

// Seeded credentials (see context/current-feature.md). E2E never creates users.
export const CREDENTIALS = {
  applicant: { email: "applicant@example.com", password: "applicantpass123" },
  reviewer: { email: "reviewer@example.com", password: "reviewerpass123" },
} as const;

type Role = keyof typeof CREDENTIALS;

// obtain_auth_token authenticates by email-as-username (USERNAME_FIELD = email).
export async function getToken(
  request: APIRequestContext,
  role: Role,
): Promise<string> {
  const { email, password } = CREDENTIALS[role];
  const response = await request.post(`${API_BASE_URL}/auth-token/`, {
    data: { username: email, password },
  });
  if (!response.ok()) {
    throw new Error(`auth-token failed for ${role}: ${response.status()}`);
  }
  return (await response.json()).token as string;
}

// Seeds a SUBMITTED application owned by the applicant, so reviewer specs have a
// deterministic subject without depending on pre-existing data.
export async function createSubmittedApplication(
  request: APIRequestContext,
  title: string,
): Promise<number> {
  const token = await getToken(request, "applicant");
  const headers = { Authorization: `Token ${token}` };
  const created = await request.post(`${API_BASE_URL}/applications/`, {
    headers,
    data: {
      title,
      category: "GENERAL",
      description: "Seeded by an E2E spec.",
      amount: "1000.00",
    },
  });
  if (!created.ok()) {
    throw new Error(`create failed: ${created.status()}`);
  }
  const id = (await created.json()).id as number;
  const submitted = await request.post(
    `${API_BASE_URL}/applications/${id}/submit/`,
    { headers },
  );
  if (!submitted.ok()) {
    throw new Error(`submit failed: ${submitted.status()}`);
  }
  return id;
}

// Logs in through the real UI so the token lands in localStorage exactly as a
// user session would.
export async function loginViaUi(page: Page, role: Role): Promise<void> {
  const { email, password } = CREDENTIALS[role];
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  // Wait for the role-based redirect so the token is set before the caller
  // navigates anywhere itself (otherwise the auth guard bounces back to /login).
  await page.waitForURL((url) => !url.pathname.startsWith("/login"));
}
