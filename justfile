export COMPOSE_FILE := "docker-compose.local.yml"

## Just does not yet manage signals for subprocesses reliably, which can lead to unexpected behavior.
## Exercise caution before expanding its usage in production environments.
## For more information, see https://github.com/casey/just/issues/2473 .


# Default command to list all available commands.
default:
    @just --list

# ── Docker ────────────────────────────────────────────────────────────────────

# build: Build the Django image (pass extra args to docker compose build).
build *args:
    @echo "Building python image..."
    @docker compose build {{args}}

# up: Start all containers in the background.
up:
    @echo "Starting up containers..."
    @docker compose up -d --remove-orphans

# down: Stop all containers.
down:
    @echo "Stopping containers..."
    @docker compose down

# prune: Remove containers and their volumes (destructive — data will be lost).
prune *args:
    @echo "Killing containers and removing volumes..."
    @docker compose down -v {{args}}

# logs: Tail container logs (pass a service name to filter, e.g. just logs django).
logs *args:
    @docker compose logs -f {{args}}

# ── Django management ─────────────────────────────────────────────────────────

# manage: Run any manage.py command inside the container.
manage +args:
    @docker compose run --rm django python ./manage.py {{args}}

# migrate: Run database migrations.
migrate *args:
    @docker compose run --rm django python ./manage.py migrate {{args}}

# makemigrations: Create new migrations (pass an app name to target one app).
makemigrations *args:
    @docker compose run --rm django python ./manage.py makemigrations {{args}}

# check: Run Django system checks.
check:
    @docker compose run --rm django python ./manage.py check

# createsuperuser: Create a Django superuser interactively.
createsuperuser:
    @docker compose run --rm --service-ports django python ./manage.py createsuperuser

# seed: Seed development database with Applicant and Reviewer accounts.
seed:
    @docker compose run --rm django python ./manage.py seed_users

# shell: Open the Django interactive shell.
shell:
    @docker compose run --rm --service-ports django python ./manage.py shell

# shell-plus: Open shell_plus with all models auto-imported (django-extensions).
shell-plus:
    @docker compose run --rm --service-ports django python ./manage.py shell_plus

# urls: Print all registered URL patterns (django-extensions).
urls:
    @docker compose run --rm django python ./manage.py show_urls

# ── Tests ─────────────────────────────────────────────────────────────────────

# pytest: Run the test suite (pass -k test_name to run a single test).
pytest *args:
    @docker compose run --rm django pytest {{args}}

# coverage: Run tests with coverage and show missing lines.
coverage:
    @docker compose run --rm django coverage run -m pytest
    @docker compose run --rm django coverage report --show-missing

# ── Code quality ──────────────────────────────────────────────────────────────

# lint: Run Ruff linter (pass --fix to auto-fix safe issues).
lint *args:
    @docker compose run --rm django ruff check {{args}} .

# format: Auto-format all Python files with Ruff.
format:
    @docker compose run --rm django ruff format .

# type-check: Run mypy static type checker.
type-check:
    @docker compose run --rm django mypy openown

# pyrefly: Run Pyrefly type checker (faster, Django-aware).
pyrefly:
    @docker compose run --rm django pyrefly check

# gate: Full pre-commit quality gate — stops at the first failure.
gate:
    @echo "==> [1/5] ruff format (check)"
    @docker compose run --rm django ruff format --check .
    @echo "==> [2/5] ruff lint"
    @docker compose run --rm django ruff check .
    @echo "==> [3/5] django system check"
    @docker compose run --rm django python ./manage.py check
    @echo "==> [4/5] migration check"
    @docker compose run --rm django python ./manage.py makemigrations --check
    @echo "==> [5/5] pytest"
    @docker compose run --rm django pytest
    @echo "Gate passed — ready to commit."

# ── Frontend ──────────────────────────────────────────────────────────────────

# frontend-install: Install npm dependencies.
frontend-install:
    @cd frontend && npm install

# frontend-dev: Start the Vite development server.
frontend-dev:
    @cd frontend && npm run dev

# frontend-build: Build the frontend for production.
frontend-build:
    @cd frontend && npm run build

# frontend-lint: Lint frontend TypeScript/React code.
frontend-lint:
    @cd frontend && npm run lint

# frontend-type-check: Run TypeScript type checker.
frontend-type-check:
    @cd frontend && npm run type-check
