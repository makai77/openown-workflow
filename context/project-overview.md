# Project Overview

The detail behind the summary in `AGENTS.md`. Read that first for the rules; this adds the
workflow specifics.

## The workflow (the core of the exercise)

```
DRAFT → SUBMITTED → UNDER_REVIEW ─approve→ APPROVED
  ▲                      │
  └──── return ──────────┼─reject→ REJECTED
                         │
                      RETURNED  (owner can re-submit)
```

- Only the owner edits or submits a DRAFT. Only a reviewer moves it out of SUBMITTED/UNDER_REVIEW.
- An applicant cannot edit an application once it has left DRAFT.
- `reject` and `return` require a non-blank comment. `approve` and `start-review` do not.
- An applicant cannot approve/reject/return anything — even via a direct API call.
- Terminal states (APPROVED, REJECTED) cannot be mutated again.

## Roles & object

- **Applicant** — creates/edits/submits own drafts; sees only their own applications and statuses.
- **Reviewer** — sees the submitted queue (filterable by `?status=`), opens one, approves /
  rejects / returns with a comment.
- **Application fields:** `title` (required), `category` (GENERAL / COMPLIANCE / FINANCE /
  OPERATIONS), `description`, `amount`, plus backend-managed `status`, `owner`, `submitted_at`,
  `reviewed_at`, `created_at`, `updated_at`. No file attachments.
- **User model:** `email` is `USERNAME_FIELD` (no `username` field); `role` (APPLICANT /
  REVIEWER) governs business access; `is_staff` is kept separate for Django admin only.

## Endpoints

```
Applicant:
  GET    /api/applications/
  POST   /api/applications/
  GET    /api/applications/{id}/
  PATCH  /api/applications/{id}/
  POST   /api/applications/{id}/submit/

Reviewer:
  GET    /api/reviewer/applications/[?status=SUBMITTED]
  GET    /api/reviewer/applications/{id}/
  POST   /api/reviewer/applications/{id}/start-review/
  POST   /api/reviewer/applications/{id}/approve/
  POST   /api/reviewer/applications/{id}/reject/
  POST   /api/reviewer/applications/{id}/return/
```

## Error contract

```json
{ "error": { "code": "invalid_transition", "message": "...", "details": {} } }
```

Never 200 with an error body. Never expose a stack trace.

## What "done" means

Both roles log in with seeded credentials, the full workflow runs end to end, the audit trail
appears on the detail page, illegal transitions and unauthorized actions are rejected AND tested,
the app is deployed and reachable, and the README explains how and why.
