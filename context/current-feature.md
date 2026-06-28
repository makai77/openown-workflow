# Current Feature

The one file to edit between phases, so Claude knows what "now" means. Keep it short.
Update it at the start of each phase — this is the single source of "what are we building."

## Now — Phase 1: Domain model

The Cookiecutter Django scaffold is in place (Docker + Postgres + DRF, `users` app running).
Now extend it with the domain model.

Spec: `OpenOwnership_Assignment_B_Engineering_Playbook.md` §4 (domain model) + §9.1 (setup notes).

Done when:
- `User` model has `role` field (APPLICANT / REVIEWER) with `is_applicant` and `is_reviewer`
  properties — see Playbook §4.1.
- `openown/applications/` app created, wired into `INSTALLED_APPS`.
- `Application` and `ApplicationAuditLog` models exist with the §4.2 indexes; `actor` uses
  `on_delete=PROTECT`; `owner` is server-side only.
- `ApplicationQuerySet` with `for_applicant`, `for_reviewer_queue`, `with_owner`,
  `with_audit_trail` methods.
- Migrations run cleanly; `makemigrations --check` passes.
- Admin registered (inspection only — Playbook §6.5).
- `ApplicantFactory`, `ReviewerFactory`, `ApplicationFactory` in place.
- Model tests pass (including properties, `__str__`, and `is_reviewable`).
- Committed as clean slices (Playbook §10.5 commit plan steps 2–5).

Do NOT start the workflow service yet — that is Phase 2.

## Next (don't start until Now is done and committed)

2. Workflow service + full test matrix (Playbook §5 + §8.2).
3. Serializers, permissions, both ViewSets, query-budget wiring (Playbook §6).
4. API authorization tests including the mandatory 403 test (Playbook §8.3).
5. React applicant + reviewer screens, all four UI states (Playbook §7).
6. README, deploy, final QA (Playbook §10).

## Decisions / notes for this phase

(Record anything decided mid-session — seeded credentials, chosen category list,
trade-offs taken — so it survives across sessions.)
