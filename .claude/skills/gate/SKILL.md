---
description: Run the full pre-commit quality gate — format, lint, system check, migration check, tests. Use before any commit, or when the user asks if code is ready to commit.
disable-model-invocation: true
---

Run the full pre-commit gate in this exact order. Stop at the first failure and report it — do not skip ahead.

## Steps

1. **Format check** (read-only, no writes)
   ```bash
   docker compose run --rm django ruff format --check .
   ```

2. **Lint**
   ```bash
   docker compose run --rm django ruff check .
   ```

3. **Django system check**
   ```bash
   docker compose run --rm django python manage.py check
   ```

4. **Migration check** — confirms no schema change is missing a migration
   ```bash
   docker compose run --rm django python manage.py makemigrations --check
   ```

5. **Tests**
   ```bash
   docker compose run --rm django pytest
   ```

## Report format

After running, output a table:

| Step | Result | Notes |
|---|---|---|
| ruff format | ✓ / ✗ | |
| ruff lint | ✓ / ✗ | |
| django check | ✓ / ✗ | |
| migration check | ✓ / ✗ | |
| pytest | ✓ / ✗ | X/Y tests passed |

For any failure: show the exact error output and the specific fix needed.
If all pass: confirm the slice is ready to commit, remind the user to write a descriptive commit message per Playbook §10.5.
