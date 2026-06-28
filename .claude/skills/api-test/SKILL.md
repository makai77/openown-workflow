---
description: Run the API authorization tests and report results. Use when working on views.py, permissions.py, or when the user asks to verify authorization behavior.
---

Run only the API-layer tests with verbose output. Pass an optional filter via `$ARGUMENTS`.

## Commands

```bash
docker compose run --rm django pytest openown/applications/tests/test_api_permissions.py \
  openown/applications/tests/test_api_applicant.py \
  openown/applications/tests/test_api_reviewer.py \
  -v $ARGUMENTS
```

## Report

After running, report:

- **Pass/fail per test**
- **Authorization matrix coverage** — verify that all of these are explicitly tested:
  - Anonymous user → 401 on any protected endpoint
  - Applicant accessing another applicant's application → 404 (hidden, not 403)
  - Applicant hitting a reviewer endpoint → **403** (the mandatory test from Playbook §8.3)
  - Reviewer hitting an applicant-only endpoint → 403
  - Applicant editing a non-DRAFT application → 400
  - Reject/return without comment → 400
- **The mandatory test** — confirm `test_applicant_cannot_approve_via_direct_api_call` exists and passes. This is explicitly required by the brief.
- **Any failure:** exact assertion, HTTP status received vs expected, which rule it covers

If the test files do not exist yet, list which ones are missing. All three files must exist before Phase 3 (API layer) is marked done.
