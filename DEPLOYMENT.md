# Deployment

> **Status: stub.** The full step-by-step production runbook is written in the next slice.
> This file records the shape of the production stack so the README can link to it; the
> exact commands, environment-variable reference, and TLS/DNS walkthrough land here next.

## Production stack

Defined in `docker-compose.production.yml`:

| Service | Role |
|---|---|
| `django` | Django app served by Gunicorn (`/start`) |
| `postgres` | PostgreSQL with backup/restore tooling under `compose/production/postgres/maintenance/` |
| `traefik` | Reverse proxy; terminates TLS with automatic Let's Encrypt certificates (ACME volume) |
| `redis` | Cache / supporting services |
| `nginx` | Serves user-uploaded media |

Host: a **Namecheap VPS**. Domain: **remuma.org**.

## Configuration

Production reads secrets from env files that are **never committed**:

- `./.envs/.production/.django`
- `./.envs/.production/.postgres`

These hold `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, the database credentials, and the
HTTPS toggles consumed by `config/settings/production.py`.

## To be documented here next

- Provisioning the VPS and DNS records for `remuma.org`.
- Populating `.envs/.production/*` (full variable reference).
- Build, migrate, `collectstatic`, and `seed_users` on the production stack.
- Traefik / Let's Encrypt certificate issuance and renewal.
- Database backup and restore procedure.
- The `manage.py check --deploy` verification step.
