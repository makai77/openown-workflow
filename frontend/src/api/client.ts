// Single fetch wrapper for the whole app: base URL, auth header, JSON encoding,
// and parsing of the backend's structured error contract:
//   { "error": { "code": "...", "message": "...", "details": {} } }
// Non-2xx responses throw an ApiError; the UI renders that as a normal error
// state. The frontend never decides workflow legality — a 403 or
// invalid_transition from the API is just an error to surface.

const BASE_URL = import.meta.env.VITE_API_BASE_URL;
const TOKEN_KEY = "auth_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.details = body.details;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Record<string, string | undefined>;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, query } = options;

  // Second arg lets BASE_URL be a relative path (e.g. "/api" in production, served
  // same-origin behind Apache): "/api" + "/auth-token/" resolves against the page
  // origin. An absolute BASE_URL (e.g. the dev "http://localhost:8000/api") ignores
  // the base, so this stays correct in both modes.
  const url = new URL(`${BASE_URL}${path}`, window.location.origin);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, value);
    }
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Token ${token}`;

  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const data: unknown = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const body = parseErrorBody(data, response.statusText);
    throw new ApiError(response.status, body);
  }

  return data as T;
}

function parseErrorBody(data: unknown, statusText: string): ApiErrorBody {
  if (
    data &&
    typeof data === "object" &&
    "error" in data &&
    (data as { error: unknown }).error &&
    typeof (data as { error: unknown }).error === "object"
  ) {
    const error = (data as { error: Partial<ApiErrorBody> }).error;
    return {
      code: error.code ?? "unknown_error",
      message: error.message ?? statusText ?? "Request failed",
      details: error.details ?? {},
    };
  }
  return {
    code: "unknown_error",
    message: statusText || "Request failed",
    details: {},
  };
}
