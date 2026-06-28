---
description: Run the workflow service tests and report results. Use when working on applications/services/workflow.py, after adding a transition function, or when the user asks to verify transition logic.
---

Run only the workflow service tests with verbose output. Pass an optional test name via `$ARGUMENTS` to target a single test.

## Command

```bash
docker compose run --rm django pytest openown/applications/tests/test_workflow.py -v $ARGUMENTS
```

## Current phase context

!`cat context/current-feature.md`

## Report

After running, report:

- **Pass/fail per test** — list every test name and its result
- **For any failure:** the exact assertion that failed, actual vs expected values, and which transition rule from the Playbook §8.2 matrix it covers
- **Audit log discipline** — confirm that legal-path tests assert `audit_logs.count() == 1` and illegal-path tests assert `audit_logs.count() == 0`
- **Missing coverage** — flag any transition from Playbook §8.2 that has no test yet

If `openown/applications/tests/test_workflow.py` does not exist yet, say so clearly — it should be created before Phase 2 is marked done.
