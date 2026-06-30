# Coding Standards

`AGENTS.md` lists the architecture non-negotiables. This adds the detail behind them.
Full code: `engineering/OpenOwnership_Assignment_B_Engineering_Playbook.md`. Full rationale: `engineering/Engineering_Principles_and_Architecture.md`.

## Where logic lives

| Layer | Owns | Does not own |
|---|---|---|
| `services/workflow.py` | All transitions, audit-log creation | HTTP details |
| Models | Schema, choices, computed properties (`is_reviewable`, `is_editable_by_applicant`) | Transitions |
| ViewSets | get object → call service → catch `WorkflowError` → respond (~4 lines per action) | Business legality |
| Serializers | Input/output validation; never mutate `status` | Transitions, access decisions |
| Permissions | `IsApplicant`, `IsReviewer` — first gate | Full workflow logic |
| React | Display, form input | Business security — backend rejects regardless of what UI shows |

## Functions

- Transition functions are keyword-only: `def approve_application(*, application, actor)`.
- No mutable default args (`details: dict | None = None`, never `= {}`).
- Return the updated object or raise a `WorkflowError` subclass — never `True/False/None` on failure.
- `_require_reviewer`, `_require_owner`, `_require_status`, `_require_comment` are private.
- `applications/services/__init__.py` re-exports only the five public transition functions.

## Queries — fixed budget, no N+1

- **List:** `.with_owner()` only (one JOIN). Never nest the audit trail. Use `ApplicationListSerializer`.
- **Detail / any transition response:** always use `_detail_queryset()` = `.with_owner().with_audit_trail()`.
  Constant ~4 queries regardless of trail length.
- Adding a field that renders a new relation → extend the queryset helper, never let the serializer
  trigger a lazy query per row.

## Imports

Relative within an app (`from .models import Application`), absolute across app boundaries.
Apply consistently in `applications/` regardless of what the scaffold does.

## Tests are part of the work

Every new or changed transition needs three tests: legal path, illegal path, zero audit rows on
the illegal path. Use `ApplicantFactory`, `ReviewerFactory`, `ApplicationFactory` — not
`Model.objects.create()`. At least one test proves a forbidden action returns 403. Coverage is
a ratchet — it must hold or rise after every commit.

## Pyrefly — optional type-checking gate

Run after the workflow service and permissions are complete:

```bash
docker compose -f docker-compose.local.yml run --rm django pyrefly init
docker compose -f docker-compose.local.yml run --rm django pyrefly check
```

Best targets: `applications/services/workflow.py`, `applications/services/exceptions.py`,
`applications/permissions.py`, `tools/agent_contracts.py`. Pyrefly is additional verification —
tests remain the primary correctness proof and are what the rubric scores.

## Agent contracts (`tools/agent_contracts.py`)

Use `AgentTaskPlan` before editing anything non-trivial. Use `AgentChangeReport` after finishing
a slice. Use `FinalSubmissionReport` as the go/no-go before submission. These are Pydantic
models — not DRF serializers, not Django models.
