---
description: Run the test suite with coverage and report gaps. Use before marking a phase done, or when the user asks about test coverage.
disable-model-invocation: true
---

Run tests with coverage and show what's missing.

## Commands

```bash
docker compose run --rm django coverage run -m pytest
docker compose run --rm django coverage report --show-missing
```

## Report

After running:

1. **Overall coverage** — state the percentage
2. **Modules below 90%** — for each one:
   - File name
   - Missing line ranges
   - What behavior those lines implement (read the file if needed)
   - What test is needed to cover them
3. **Coverage verdict** — did it hold, rise, or drop since the last known baseline?
   - Coverage is a ratchet per `Engineering_Principles_and_Architecture.md` §4.4 — it must not drop
   - If it dropped, identify which new code lacks tests before this slice can be committed

Do not treat 100% as the goal. The goal is that every transition function, every permission check, every model property, and every error path has at least one test that exercises it.
