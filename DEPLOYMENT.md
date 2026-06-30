# Deployment

How `remuma.org` is deployed: a Dockerized Django/Postgres/Redis stack behind the
host's **Apache**, which serves the React SPA and reverse-proxies the API.

## Why Apache, not Traefik

The cookiecutter production stack puts **Traefik** on ports 80/443 and lets it obtain
Let's Encrypt certs. The target VPS, however, **already runs Apache on 80/443** for an
unrelated site (`southwayinstitute.com` + a Moodle portal). Two processes can't bind the
same ports, so we:

- removed the `traefik` and `nginx` services from `docker-compose.production.yml`,
- published Gunicorn on `127.0.0.1:8000` (localhost only),
- made the host **Apache** the public front door via a vhost scoped to `remuma.org`,
  serving the SPA and proxying the backend, with TLS from **certbot** (not Traefik).

The existing site's vhosts are never edited — `remuma.org` lives in its own file.

## Production stack (`docker-compose.production.yml`)

| Service | Exposure | Role |
|---|---|---|
| `django` | `127.0.0.1:8000 → :5000` | Gunicorn (`config.wsgi`), localhost only |
| `postgres` | internal | PostgreSQL + backup/restore tooling |
| `redis` | internal | cache |

## Host topology

```
            ┌─────────────────────── VPS (Apache :80/:443) ───────────────────────┐
  Internet  │  southwayinstitute.com / portal  → existing vhosts (untouched)       │
  ───────▶  │  remuma.org / www.remuma.org     → remuma.org.conf                   │
            │      ├─ /, /assets, client routes → /opt/openown/frontend/dist (SPA) │
            │      └─ /api /admin /static       → http://127.0.0.1:8000 (Gunicorn) │
            └─────────────────────────────────────────────────────────────────────┘
                         127.0.0.1:8000 → django container → postgres / redis (internal)
```

## Prerequisites (already true on the VPS)

- DNS: `remuma.org` and `www.remuma.org` → the VPS IP.
- Docker + Compose, Node 20, certbot, Apache with `proxy_http`, `headers`, `rewrite`,
  `ssl` modules enabled.

## Runbook

All commands run as `root` on the VPS.

**1. Back up Apache config (before any change):**
```bash
tar czf /root/apache2-backup-$(date +%F-%H%M%S).tar.gz /etc/apache2
```

**2. Clone the repo:**
```bash
git clone https://github.com/makai77/openown-workflow.git /opt/openown
cd /opt/openown
```

**3. Create production env files** (not committed; `chmod 600`):

`/opt/openown/.envs/.production/.django`
```
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<generated>
DJANGO_ADMIN_URL=<random>/
DJANGO_ALLOWED_HOSTS=remuma.org,www.remuma.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://remuma.org,https://www.remuma.org
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SERVER_EMAIL=noreply@remuma.org
DJANGO_DEFAULT_FROM_EMAIL=Open Ownership Workflow <noreply@remuma.org>
REDIS_URL=redis://redis:6379/0
```
> `DJANGO_SETTINGS_MODULE` must be set here — `manage.py` defaults to `local`, and
> `/start` runs `collectstatic` through `manage.py`.

`/opt/openown/.envs/.production/.postgres`
```
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=openown
POSTGRES_USER=<generated>
POSTGRES_PASSWORD=<generated>
```

**4. Build, migrate, seed, start:**
```bash
DC="docker compose -f docker-compose.production.yml"
$DC build
$DC up -d postgres redis
$DC run --rm django python manage.py migrate
$DC run --rm django python manage.py seed_users
$DC up -d
```

**5. Build the SPA** (API base baked at build time → must be the absolute https URL):
```bash
cd /opt/openown/frontend
npm ci
VITE_API_BASE_URL=https://remuma.org/api npm run build   # → frontend/dist
```

**6. Apache vhost + TLS:**
```bash
a2enmod proxy_http headers rewrite ssl
# Install a :80-only vhost first (DocumentRoot = frontend/dist) so the ACME
# webroot challenge is reachable, enable it, reload:
a2ensite remuma.org && apache2ctl configtest && systemctl reload apache2

certbot certonly --webroot -w /opt/openown/frontend/dist \
  -d remuma.org -d www.remuma.org \
  --non-interactive --agree-tos -m makaikahilu4@gmail.com --no-eff-email

# Swap in the full vhost (:80 → https redirect, :443 proxy + SPA + cert), reload:
apache2ctl configtest && systemctl reload apache2
```

The `:443` vhost (`/etc/apache2/sites-available/remuma.org.conf`) sets
`RequestHeader set X-Forwarded-Proto "https"` (so `SECURE_SSL_REDIRECT` doesn't loop),
`ProxyPass` for `/api` `/admin` `/static` → `http://127.0.0.1:8000`, and
`FallbackResource /index.html` on `DocumentRoot /opt/openown/frontend/dist` for SPA
client-side routing.

## Updating a deployed release

```bash
cd /opt/openown && git pull origin main
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml run --rm django python manage.py migrate
docker compose -f docker-compose.production.yml up -d
cd frontend && npm ci && VITE_API_BASE_URL=https://remuma.org/api npm run build
# static/SPA changes are picked up on the next request; no Apache reload needed
```

## Verification

```bash
curl -I https://remuma.org/                     # 200 (SPA)
curl -I https://remuma.org/api/docs/            # 401 (Swagger is admin-only)
curl -I http://remuma.org/                      # 301 → https
curl -I https://southwayinstitute.com/          # 200 (existing site unaffected)
```

`python manage.py check --deploy` is run against production settings as part of release QA.

## TLS renewal

certbot installed a renewal timer at issuance. Renewal uses the same webroot
(`/opt/openown/frontend/dist`); the `:80` vhost serves `/.well-known/acme-challenge/`
before redirecting everything else to https. Verify with `certbot renew --dry-run`.

## Notes / caveats

- Secrets live only in `.envs/.production/*` on the host (git-ignored), never in the repo.
- The seeded demo users and any rows created by smoke/E2E persist in the production DB —
  there is no automatic reset.
- Email is configured for SMTP/Anymail but not wired to a provider; 500-error admin mail
  is best-effort and not required for the workflow.
