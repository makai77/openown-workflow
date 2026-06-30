# Current Feature

The one file to edit between phases, so Claude knows what "now" means. Keep it short.
Update it at the start of each phase — this is the single source of "what are we building."

## Now — Phase 2: Workflow service

Domain model is in place and committed. Now build the state machine.

Spec: `engineering/OpenOwnership_Assignment_B_Engineering_Playbook.md` §5 (workflow service) + §8.2 (test matrix).

Done when:
- `openown/applications/services/exceptions.py` — `WorkflowError`, `InvalidTransition`,
  `CommentRequired`, `WorkflowPermissionDenied` hierarchy (Playbook §5.1).
- `openown/applications/services/workflow.py` — five public transition functions
  (`submit_application`, `start_review_application`, `approve_application`,
  `reject_application`, `return_application`) plus private helpers (Playbook §5.2).
- `openown/applications/services/__init__.py` — re-exports only the five public functions.
- Every transition wrapped in `transaction.atomic()` + `select_for_update()`.
- Audit log written inside the same atomic block — never via a signal.
- Full test matrix (§8.2): legal path, illegal path, zero audit rows on illegal path,
  for all five transitions. Tests use `ApplicantFactory`, `ReviewerFactory`,
  `ApplicationFactory` — not `Model.objects.create()`.
- `makemigrations --check` still passes (no new models).
- Gate green: ruff clean, check passes, all tests pass.

Do NOT start serializers, permissions, or ViewSets yet — that is Phase 3.

## Next (don't start until Now is done and committed)

3. Serializers, permissions, both ViewSets, query-budget wiring (Playbook §6).
4. API authorization tests including the mandatory 403 test (Playbook §8.3).
5. React applicant + reviewer screens, all four UI states (Playbook §7).
6. README, deploy, final QA (Playbook §10).

## Decisions / notes

- `username = None` on User model — factory uses `email` as unique identifier, no username field.
- Seeded credentials: `applicant@example.com` / `applicantpass123`, `reviewer@example.com` / `reviewerpass123`.
- `frontend/` will be created at repo root (sibling of `openown/`) in Phase 5 via
  `npm create vite@latest frontend -- --template react-ts`. django-cors-headers already wired.
- `startapp` creates at repo root — must move to `openown/<app>/` and fix `apps.py name`.
  (Already done for applications; remembered for any future app.)
