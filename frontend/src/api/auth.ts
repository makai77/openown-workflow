// Authentication calls. Login uses DRF's obtain_auth_token; the returned token
// is persisted by client.ts and sent as `Authorization: Token <token>`. We then
// read /users/me/ to learn the current user's role, which drives role-guarded
// routing. The frontend never decides authorization — it just needs the role to
// pick which screens to show; the backend enforces every action regardless.
import { apiRequest, clearToken, setToken } from "./client";

export type Role = "APPLICANT" | "REVIEWER";

export interface CurrentUser {
  id: number;
  email: string;
  name: string;
  role: Role;
}

interface TokenResponse {
  token: string;
}

export function fetchMe(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/users/me/");
}

// obtain_auth_token expects a `username` field; our USERNAME_FIELD is `email`,
// so the email is sent as the username. On success we persist the token and
// resolve the current user; if the follow-up /me fails we roll back the token.
export async function login(
  email: string,
  password: string,
): Promise<CurrentUser> {
  const { token } = await apiRequest<TokenResponse>("/auth-token/", {
    method: "POST",
    body: { username: email, password },
  });
  setToken(token);
  try {
    return await fetchMe();
  } catch (error) {
    clearToken();
    throw error;
  }
}

export function logout(): void {
  clearToken();
}
