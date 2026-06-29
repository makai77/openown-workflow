// Typed calls, one per endpoint (Playbook §6.3). Types mirror the DRF
// serializers (§6.1); `status`, `owner`, and timestamps are backend-assigned
// and read-only here.
import { apiRequest } from "./client";

export type ApplicationStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "RETURNED";

export type Category = "GENERAL" | "COMPLIANCE" | "FINANCE" | "OPERATIONS";

export interface ApplicationListItem {
  id: number;
  owner_email: string;
  title: string;
  category: Category;
  amount: string | null;
  status: ApplicationStatus;
  submitted_at: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditLogEntry {
  id: number;
  actor_name: string;
  actor_email: string;
  from_status: ApplicationStatus;
  to_status: ApplicationStatus;
  comment: string;
  created_at: string;
}

export interface ApplicationDetail extends ApplicationListItem {
  owner: number;
  description: string;
  audit_logs: AuditLogEntry[];
}

export interface CreateApplicationPayload {
  title: string;
  category: Category;
  description?: string;
  amount?: string | null;
}

// Response of POST /applications/. ApplicationCreateSerializer (§6.1) returns
// only these fields — not the full detail shape: no `owner`, no timestamps, no
// `audit_logs`. Screens read `id` here, then navigate to the detail route which
// refetches the full ApplicationDetail. Keeping this distinct from
// ApplicationDetail makes the smaller contract explicit rather than implied.
export interface ApplicationCreateResponse {
  id: number;
  title: string;
  category: Category;
  description: string;
  amount: string | null;
  status: ApplicationStatus;
}

export type UpdateApplicationPayload = Partial<CreateApplicationPayload>;

// DRF PageNumberPagination wraps list responses; the screens only need the rows,
// so the list calls below unwrap `results`.
interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ── Applicant ──────────────────────────────────────────────────────────────

export async function listApplications(): Promise<ApplicationListItem[]> {
  const page =
    await apiRequest<Paginated<ApplicationListItem>>("/applications/");
  return page.results;
}

export function createApplication(
  payload: CreateApplicationPayload,
): Promise<ApplicationCreateResponse> {
  return apiRequest<ApplicationCreateResponse>("/applications/", {
    method: "POST",
    body: payload,
  });
}

export function getApplication(id: number): Promise<ApplicationDetail> {
  return apiRequest<ApplicationDetail>(`/applications/${id}/`);
}

export function updateApplication(
  id: number,
  payload: UpdateApplicationPayload,
): Promise<ApplicationDetail> {
  return apiRequest<ApplicationDetail>(`/applications/${id}/`, {
    method: "PATCH",
    body: payload,
  });
}

export function submitApplication(id: number): Promise<ApplicationDetail> {
  return apiRequest<ApplicationDetail>(`/applications/${id}/submit/`, {
    method: "POST",
  });
}

// ── Reviewer ───────────────────────────────────────────────────────────────

export async function listReviewerQueue(
  status?: ApplicationStatus,
): Promise<ApplicationListItem[]> {
  const page = await apiRequest<Paginated<ApplicationListItem>>(
    "/reviewer/applications/",
    { query: { status } },
  );
  return page.results;
}

export function getReviewerApplication(id: number): Promise<ApplicationDetail> {
  return apiRequest<ApplicationDetail>(`/reviewer/applications/${id}/`);
}

export function startReview(id: number): Promise<ApplicationDetail> {
  return apiRequest<ApplicationDetail>(
    `/reviewer/applications/${id}/start-review/`,
    { method: "POST" },
  );
}

export function approveApplication(id: number): Promise<ApplicationDetail> {
  return apiRequest<ApplicationDetail>(
    `/reviewer/applications/${id}/approve/`,
    { method: "POST" },
  );
}

export function rejectApplication(
  id: number,
  comment: string,
): Promise<ApplicationDetail> {
  return apiRequest<ApplicationDetail>(`/reviewer/applications/${id}/reject/`, {
    method: "POST",
    body: { comment },
  });
}

export function returnApplication(
  id: number,
  comment: string,
): Promise<ApplicationDetail> {
  return apiRequest<ApplicationDetail>(`/reviewer/applications/${id}/return/`, {
    method: "POST",
    body: { comment },
  });
}
