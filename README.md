# Submission & Approval Workflow

A two-sided web app (Assignment B) built around one thing done correctly: a status
workflow with a tamper-evident audit trail. An **Applicant** drafts and submits
applications; a **Reviewer** works a queue and approves, rejects, or returns them with a
comment. Every legal transition writes exactly one audit row; every illegal one is
rejected and writes nothing.

---

## Contents

- [Live demo](#live-demo)
- [What it implements](#what-it-implements)
- [Tech stack](#tech-stack)
- [Architecture overview](#architecture-overview)
- [Data model & key design decisions](#data-model--key-design-decisions)
- [API](#api)
- [Local development](#local-development)
  - [Get the code](#get-the-code)
  - [Backend + database](#backend--database)
  - [Create a local admin (optional)](#create-a-local-admin-optional)
  - [Frontend](#frontend)
  - [End-to-end tests](#end-to-end-tests)
- [Testing](#testing)
- [Security](#security)
- [Deployment](#deployment)
- [Trade-offs & what I'd do with more time](#trade-offs--what-id-do-with-more-time)
- [AI usage disclosure](#ai-usage-disclosure)

---

## Live demo

| | |
|---|---|
| **Live URL** | https://remuma.org |
| **API docs** | https://remuma.org/api/docs/ (Swagger UI, served by drf-spectacular) |

**Test credentials** (created by the `seed_users` command):

| Role | Email | Password |
|---|---|---|
| Applicant | `applicant@example.com` | `applicantpass123` |
| Reviewer | `reviewer@example.com` | `reviewerpass123` |

**Reading the API docs.** `/api/docs/` (and the raw schema at `/api/schema/`) is
**admin-only** — `SERVE_PERMISSIONS = [IsAdminUser]`, so it requires `is_staff`. To make
the docs reachable for review, the **Reviewer account is granted `is_staff`** — with **no
Django-admin model permissions** assigned. Business access is governed by `role`, not by
`is_staff`, so this is purely "can open the docs," not admin power. So: **log in as the
reviewer to view the API docs.**

Only role-scoped demo accounts are published. The production **Django-admin URL and
superuser credentials are intentionally anonymized/redacted** here and are **available on
request**.

---

## What it implements

The core is the state machine the backend enforces. Illegal transitions are rejected with
a structured error; they never change state and never write an audit row.

```
DRAFT ──submit──▶ SUBMITTED ──start-review──▶ UNDER_REVIEW ──approve──▶ APPROVED
  ▲                   │                            │
  │                   ├──────── reject ────────────┼──▶ REJECTED
  │                   │                            │
  └─── re-submit ─── RETURNED ◀──── return ────────┘
```

- **Applicant** — creates, edits, and submits their own drafts; sees only their own
  applications. Can edit only while the application is `DRAFT` or `RETURNED`; once it
  leaves those states the applicant cannot touch it.
- **Reviewer** — sees the queue of non-draft applications (filterable by `?status=`),
  opens one, and moves it forward. `reject` and `return` require a non-blank comment;
  `start-review` and `approve` do not. `APPROVED` and `REJECTED` are terminal.
- **Audit trail** — every transition records who acted, the old → new status, the comment,
  and a timestamp, written inside the same transaction as the status change and shown on
  the detail page.

Authorization is enforced server-side on every mutation: an applicant cannot approve,
reject, or return anything — even by calling the reviewer endpoint directly. That path
returns `403` and is covered by an explicit test.

---

## Tech stack

**Backend** — Django 6.0 + Django REST Framework 3.17, PostgreSQL, Gunicorn, Docker.
API documentation via drf-spectacular (OpenAPI 3 + Swagger UI). Python 3.14.

**Frontend** — React 19 + TypeScript (Vite 8), Tailwind CSS 4, TanStack Query for
server-state, React Hook Form + Zod for forms and validation, React Router.

**Testing** — pytest + pytest-django (backend), Vitest + Testing Library (frontend unit),
Playwright (end-to-end). Ruff for lint/format; pyrefly as an additional type-checking gate.

Exact pinned versions live in `pyproject.toml` and `frontend/package.json`.

---

## Architecture overview

The request path is a straight line: **React → DRF view → workflow service → PostgreSQL**.
Views stay thin — they fetch the object, call a service function, catch `WorkflowError`,
and respond. They contain no business legality of their own.

Two principles govern the whole design:

1. **All transition rules live in one service.** `applications/services/workflow.py` is the
   only code that assigns `application.status`. It runs each transition inside
   `transaction.atomic()` with `select_for_update()`, writes the audit row in the same
   block, and returns the updated object or raises a typed `WorkflowError`. An illegal
   transition is rejected before any write — so the database can never hold a status the
   workflow doesn't permit, and never an audit row for a transition that didn't happen.
   This rule is enforced in development by a hook that blocks any `application.status = …`
   assignment outside that module.

2. **The frontend renders server truth and never decides legality.** The detail endpoint
   returns an `available_actions` list — the exact reviewer actions the current user may
   take on that object right now, computed by the same service that enforces the
   transitions. The UI renders buttons from that list and encodes zero rules of its own.
   If the UI and the backend ever disagreed, the backend would still reject the call; the
   `available_actions` design removes the chance for them to disagree in the first place.

---

## Data model & key design decisions

Two models, in `openown/applications/models.py`:

**`Application`** — `owner` (FK to user), `title`, `category`
(`GENERAL`/`COMPLIANCE`/`FINANCE`/`OPERATIONS`), `description`, `amount` (nullable
decimal), `status` (the six states), plus backend-managed `submitted_at`, `reviewed_at`,
`created_at`, `updated_at`. `status`, `owner`, and the timestamps are assigned by the
backend and never trusted from the client.

**`ApplicationAuditLog`** — `application`, `actor`, `from_status`, `to_status`, `comment`,
`created_at`.

Decisions worth calling out:

- **`PROTECT` on the audit actor.** The audit FK to the user who acted uses
  `on_delete=PROTECT`. An audit trail you can erase by deleting a user is not an audit
  trail; deleting an actor who has history is refused.
- **No `DELETE` on applications.** The applicant viewset deliberately omits destroy —
  removing an application would erase its trail, the opposite of an auditable workflow.
- **Workflow logic lives in a service module, not in models, signals, or views.** Keeping
  every transition in one place is what makes the rules testable in isolation and
  impossible to bypass. The audit row is written inline in the transition, never via a
  signal — signals make "did this write happen?" non-local and hard to reason about.
- **Fixed query budget, no N+1.** List responses use `ApplicationListSerializer` with
  `.with_owner()` (one JOIN) and never carry the audit trail. Detail responses and every
  transition response use `.with_owner().with_audit_trail()`, so a detail read is a
  constant ~handful of queries regardless of how long the trail is. `available_actions`
  is computed purely from the already-loaded object — it adds no query.
- **Indexes** on `Application(owner, status)` and `(status, created_at)` back the two real
  access patterns (an applicant's own list, the reviewer queue ordered by recency); the
  audit log is indexed by `(application, created_at)` and `(actor, created_at)`.

---

## API

Interactive documentation: **`/api/docs/`** (Swagger UI; **admin-only** — log in as the
reviewer, which is `is_staff`; see [Live demo](#live-demo)). The raw schema is at
`/api/schema/`. Authentication is token-based via `/api/auth-token/`.

| Method | Path | Role | Purpose |
|---|---|---|---|
| `GET` | `/api/applications/` | Applicant | List own applications |
| `POST` | `/api/applications/` | Applicant | Create a draft |
| `GET` | `/api/applications/{id}/` | Applicant | Retrieve own application + trail |
| `PATCH` | `/api/applications/{id}/` | Applicant | Edit a `DRAFT`/`RETURNED` application |
| `POST` | `/api/applications/{id}/submit/` | Applicant | `DRAFT`/`RETURNED` → `SUBMITTED` |
| `GET` | `/api/reviewer/applications/` | Reviewer | Queue (filter with `?status=`) |
| `GET` | `/api/reviewer/applications/{id}/` | Reviewer | Retrieve + trail |
| `POST` | `/api/reviewer/applications/{id}/start-review/` | Reviewer | `SUBMITTED` → `UNDER_REVIEW` |
| `POST` | `/api/reviewer/applications/{id}/approve/` | Reviewer | → `APPROVED` |
| `POST` | `/api/reviewer/applications/{id}/reject/` | Reviewer | → `REJECTED` (comment required) |
| `POST` | `/api/reviewer/applications/{id}/return/` | Reviewer | → `RETURNED` (comment required) |

Every error — validation, illegal transition, not-found, unauthorized — returns a single
structured envelope; the API never replies `200` with an error body and never leaks a
stack trace.

```json
{ "error": { "code": "invalid_transition", "message": "…", "details": {} } }
```

| Status | Used for | `code` |
|---|---|---|
| `400` | Validation failure / illegal transition / missing comment | `validation_error`, `invalid_transition`, `comment_required` |
| `401` | Unauthenticated request to a protected endpoint | `not_authenticated` |
| `403` | Authenticated but wrong role / not the owner | `permission_denied` |
| `404` | Object not found (or not visible to this user) | `not_found` |

---

## Local development

Everything runs in Docker — you do **not** need Python, Postgres, or `uv` on the host,
only Docker (with Compose) and, for the frontend, Node 20. Commands below use the `just`
shortcuts (a `justfile` is included with `COMPOSE_FILE=docker-compose.local.yml`
exported); the explicit `docker compose -f docker-compose.local.yml …` form works too.

### Get the code

```bash
git clone https://github.com/makai77/openown-workflow.git
cd openown-workflow
```

Local env files for development ship in `.envs/.local/` (committed for convenience), so no
secrets setup is required to run locally.

### Backend + database

```bash
just build                       # build the Django image
just up                          # start postgres + django (and mailpit) in Docker
just manage migrate              # apply migrations
just manage seed_users           # create the applicant + reviewer demo users
```

The API is then at `http://localhost:8000/` (docs at `http://localhost:8000/api/docs/`).
Run the test suite with `just pytest`.

### Create a local admin (optional)

`seed_users` creates only the applicant and reviewer demo accounts — no superuser. To get
into the local Django admin (e.g. to inspect rows), create one yourself:

```bash
just manage createsuperuser      # prompts for email (the USERNAME_FIELD) + password
```

There is no `username` field — log in with the email you entered. The admin is at
`http://localhost:8000/admin/` locally. (The seeded reviewer is `is_staff`, so it too can
reach the admin and the admin-only `/api/docs/`, but it has no model permissions there.)

### Frontend

```bash
cd frontend
npm install
npm run dev                      # Vite dev server at http://localhost:5173
```

The dev server proxies API calls to the backend on `:8000`; CORS in local settings allows
`http://localhost:5173`.

### End-to-end tests

Playwright drives the real app, so it needs **both servers up** — backend on `:8000`
(migrated and seeded) and the frontend on `:5173`:

```bash
cd frontend
npx playwright install           # first run only, fetches browsers
npm run e2e
```

Note: the E2E flows create real rows in the dev database and do **not** auto-reset it. Re-runs
accumulate applications; recreate the dev DB if you want a clean slate.

---

## Testing

The strategy follows the rubric: prove the workflow rules and the authorization boundary,
not just the happy path. Counts below are from running the suites.

**Backend — `135 passed` (pytest).** The workflow and API layers carry, among others:

- **Workflow transition matrix** (`test_workflow.py`, 14 tests) — for each transition: the
  legal path succeeds and writes one audit row; the illegal path raises the typed error;
  and the illegal path writes **zero** audit rows.
- **Reviewer API** (`test_api_reviewer.py`, 18) and **applicant API**
  (`test_api_applicant.py`, 12) — endpoint behavior, status codes, and the error envelope.
- **Authorization** (`test_api_permissions.py`, 3) — including the mandatory case: an
  applicant calling the reviewer `approve` endpoint directly gets **`403`** and the
  application is unchanged.
- **`available_actions`** (`test_available_actions.py`, 4) — the server-driven action list
  matches what the transition functions actually permit, per role and per status.
- **Auth** (`test_login.py`, 2) — a browser carrying a Django session cookie can still
  obtain a token (no spurious CSRF 403), and `TokenAuthentication` takes precedence over
  `SessionAuthentication` so token-authenticated writes are never blocked by CSRF.
- Plus model and user/seed tests.

**Frontend — `39 passed` across 13 files (Vitest + Testing Library).** Component and
page-level tests covering the four UI states (loading / error / empty / loaded), form
validation, the status badge, and the audit trail rendering.

**End-to-end — `4` Playwright flows.** Applicant create-edit-submit; reviewer
start-review-and-approve; reviewer must-comment-to-reject with the rejection showing in the
trail; and the forbidden applicant-→-reviewer-endpoint `403` path.

---

## Security

The production settings are locked down, not left at framework defaults:

- **`DEBUG=False`** in production; no stack traces in responses.
- **Secrets from the environment** — `SECRET_KEY`, database credentials, and allowed hosts
  are read from env files that are never committed.
- **HTTPS enforced** — `SECURE_SSL_REDIRECT`, HSTS, `SECURE_PROXY_SSL_HEADER`, and
  `__Secure-` session/CSRF cookie names with `Secure` flags.
- **`ALLOWED_HOSTS`, CSRF, and CORS** are restricted to the real origin; production never
  opens CORS the way local development does.

This was **validated with `python manage.py check --deploy`** (run clean) and **reviewed
against the DJ Checkup checklist** (djcheckup.com, the current successor to the retired
Pony Checkup) as an external reference for Django deployment hardening.

---

## Deployment

Production runs as a Dockerized stack (`docker-compose.production.yml`) behind the
host's Apache:

- **Django behind Gunicorn**, published on `127.0.0.1:8000` (localhost only — never
  exposed publicly by Docker),
- **PostgreSQL** (with backup tooling) and **Redis**, both internal to the Docker network,
- **Apache** as the public reverse proxy: it serves the built React SPA, proxies `/api`,
  `/admin`, and `/static` to Gunicorn, injects `X-Forwarded-Proto`, and terminates TLS
  with a **Let's Encrypt** certificate (certbot).

The **Namecheap VPS** already hosts an unrelated site on Apache (ports 80/443), so the
cookiecutter default Traefik front end — which wants those ports — was dropped in favour
of an Apache vhost scoped to `remuma.org`, leaving the existing site untouched. The full
step-by-step runbook (server paths, vhost, admin URL, TLS) contains
deployment-environment specifics and is kept out of the public repo; it is **available on
request**.

---

## Trade-offs & what I'd do with more time

The brief rewards a small, solid surface over feature breadth, so several things were left
out **deliberately** to keep the core clean and well-tested:

- **No notifications** (email / in-app on status change) — a stretch goal; out of scope.
- **No file attachments** — explicitly optional in the brief; the model carries `amount`
  instead, and skipping uploads avoided storage/scanning concerns that add no workflow value.
- **`available_actions` covers reviewer actions only.** Applicant-side actions (edit,
  submit) are still derived in the UI from status. Folding them into the same server-driven
  list would make the frontend fully rule-free; it's a natural next step.
- **No E2E database reset.** The Playwright flows append to the dev DB. A fixture that
  resets state per run would make them idempotent.
- **Pagination/search on the reviewer queue** beyond the status filter — a listed stretch
  goal; not built so the queue stays simple.

With more time I'd close the `available_actions` gap, add the E2E reset fixture, and add
queue pagination + search.

---

## AI usage disclosure

This project was built with **Claude** (the model) via **Claude Code** (the CLI agent). As
the brief requires, here's how — and, more importantly, what I verified myself.

**How AI was used:**

- Planning and breaking the work into reviewable slices.
- Scaffolding boilerplate (models, serializers, viewsets) from a stated spec.
- Generating the test matrix — legal/illegal transitions, the zero-audit-on-illegal
  assertions, and the authorization tests.
- Drafting documentation, including this README.
- Reviewing my own diffs for the architecture rules (thin views, service-only transitions,
  the query budget).
- Setting up the repo's agent configuration and pre-commit hooks (e.g. the hook that blocks
  any `application.status` assignment outside the workflow service).

**What I verified myself** — I understand and can explain every line submitted:

- Ran the full backend gate locally: `ruff format`/`check`, `manage.py check`,
  `makemigrations --check`, and the **135** pytest cases.
- Ran the frontend gate: typecheck, lint, the **39** Vitest cases, and the production build.
- Ran the **4** Playwright E2E flows against both servers, and smoke-tested both happy paths
  and the forbidden-call `403` in a real browser.
- Ran `manage.py check --deploy` against production settings and reviewed the deployment
  against the DJ Checkup checklist.
- Performed the deploy and confirmed the live app and API docs are reachable.

AI accelerated the work; the design decisions, the verification, and the final
correctness are mine.
