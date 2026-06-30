# Agent Rules

Portable, tool-agnostic project rules. Claude Code loads this via `@AGENTS.md` in `CLAUDE.md`;
other agents read it directly. Keep it short and load-bearing.

## What this is

A two-sided submission-and-approval workflow app. The graded core is a correctly enforced
status workflow with an audit trail — not feature breadth. Stack: Django 6.0 + DRF + PostgreSQL
in Docker, React + TypeScript (Vite) frontend, pytest, Ruff.

## Non-negotiable architecture

- All status transitions go through `applications/services/workflow.py`. Nothing else
  mutates `application.status`.
- ViewSets stay thin: get object → call service → catch `WorkflowError` → respond.
- Serializers validate; they never decide transitions. React never decides legality.
- No `assert` for business/security rules. No `except Exception:` around a transition.
- Every transition is wrapped in `transaction.atomic()` and writes its audit row inside
  the same function — never via a signal.
- Every legal transition writes one audit row; every illegal one is rejected and writes none.
- `status`, `owner`, and timestamps are backend-assigned, never trusted from the client.

## Out of scope

Background queues, file attachments, notifications, generic workflow frameworks. Don't build
them. If a request looks out of scope, stop and ask.

## Commands (always inside the container)

```bash
# Preferred shortcuts (justfile — COMPOSE_FILE=docker-compose.local.yml is exported)
just build                          # rebuild image after dependency or Dockerfile changes
just up                             # docker compose up -d --remove-orphans
just down                           # stop containers
just manage <command>               # any manage.py command inside the container
just pytest [args]                  # run all tests; pass -k test_name for one test
just logs [service]                 # tail container logs

# Explicit form when just isn't available
docker compose -f docker-compose.local.yml build
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
docker compose -f docker-compose.local.yml run --rm django pytest
docker compose -f docker-compose.local.yml run --rm django pytest -k test_name

# Interactive debugger (ipdb) — requires service-ports
docker compose -f docker-compose.local.yml run --rm --service-ports django
```

`docker exec` does not work for management commands in this setup — always use
`docker compose run --rm django ...`. Add deps by editing `pyproject.toml` then
running `just build` — `uv add` inside a running container does not persist.

## Before every commit

```bash
docker compose -f docker-compose.local.yml run --rm django ruff format .
docker compose -f docker-compose.local.yml run --rm django ruff check .
docker compose -f docker-compose.local.yml run --rm django python manage.py makemigrations --check
docker compose -f docker-compose.local.yml run --rm django python manage.py check
just pytest
```

## Boundaries

- Never weaken authorization or delete a test to make something pass. If a test fails,
  the code is wrong — not the test.
- Never commit secrets or `.env*` files. `.envs/.local/` is acceptable for submission;
  `.envs/.production/` must never be committed.
- Reject direct applicant calls to reviewer endpoints with 403 — and test it explicitly.

## MCP tools (configured in `.mcp.json`)

- **context7** — resolve current library docs before implementing any unfamiliar API.
  Call it; don't rely on training-data memory for version-sensitive patterns.
- **playwright** — verify applicant + reviewer happy paths and the mandatory forbidden-call
  case (applicant → reviewer endpoint → 403) against localhost or the deployed URL.
  Restrict to those two targets only.

## Type-checking quality gate (pyrefly)

Run after the service layer and permissions are stable — additional verification, not a
substitute for tests:

```bash
docker compose -f docker-compose.local.yml run --rm django pyrefly init   # first time only
docker compose -f docker-compose.local.yml run --rm django pyrefly check
```

Best targets: `applications/services/`, `applications/permissions.py`, `tools/agent_contracts.py`.

## Deeper references (read on demand, not loaded by default)

- `engineering/OpenOwnership_Assignment_B_Engineering_Playbook.md` — full build spec, code, schema, tests, deploy.
- `engineering/Engineering_Principles_and_Architecture.md` — the reasoning behind every rule above.
