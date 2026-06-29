# Frontend Setup Reference — `frontend/`

Drop this at `docs/engineering/FRONTEND_SETUP.md` (or wherever your engineering docs live).
It is the verified, current setup target for the React SPA. The frontend is a **separate
project** living at the repo root next to `openown/`, invisible to the Django Docker setup.
The two meet only over HTTP.

```
openown/                     ← repo root
├── openown/                 ← Django apps
├── config/                  ← Django config
├── docker-compose.local.yml ← Django + Postgres on :8000
└── frontend/                ← THIS — React SPA on :5173, talks to :8000/api
```

---

## 1. Stack (fixed — do not extend)

| Concern | Choice |
|---|---|
| Build / language | Vite + React + TypeScript (strict) |
| Styling | Tailwind v4 via the `@tailwindcss/vite` plugin |
| Components | shadcn/ui (new-york style) |
| Icons | lucide-react |
| Routing | react-router-dom |
| Server state | @tanstack/react-query |
| Forms + validation | react-hook-form + zod + @hookform/resolvers |
| Motion (optional) | framer-motion — micro-interactions only |
| Unit tests | vitest + @testing-library/react + jsdom |
| E2E tests | @playwright/test |
| Lint / format | ESLint (flat) + Prettier + eslint-plugin-jsx-a11y |

Not used: Zustand, Storybook, MSW, i18n. Out of scope for six screens.

---

## 2. Setup commands (verified current, June 2026)

```bash
# from repo root
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install

# Tailwind v4 (Vite plugin, NOT PostCSS)
npm install tailwindcss @tailwindcss/vite

# runtime deps
npm install @tanstack/react-query react-router-dom react-hook-form zod @hookform/resolvers lucide-react

# shadcn (initializes Tailwind v4 wiring, components.json, @ alias)
npx shadcn@latest init

# dev deps: testing + a11y lint
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @playwright/test eslint-plugin-jsx-a11y
npx playwright install chromium
```

---

## 3. Config files

### `vite.config.ts`
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
```

### `src/index.css` (Tailwind v4 — one import line, no `@tailwind` directives)
```css
@import "tailwindcss";
```
There is NO `tailwind.config.js` with `@tailwind base/components/utilities`. Any tutorial
showing that is pre-v4 and stale.

### `tsconfig.json` — strict + the `@` path alias
```jsonc
{
  "compilerOptions": {
    "strict": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "references": [{ "path": "./tsconfig.app.json" }, { "path": "./tsconfig.node.json" }]
}
```
(Vite generates split tsconfigs; add `baseUrl`/`paths` to `tsconfig.app.json` too so the
editor and build agree.)

### `src/test/setup.ts`
```ts
import "@testing-library/jest-dom";
```

### `frontend/.env.example`
```
VITE_API_BASE_URL=http://localhost:8000/api
```

### `package.json` scripts (the pre-commit gate, mirroring the backend)
```jsonc
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest",
    "e2e": "playwright test",
    "gate": "npm run typecheck && npm run lint && npm run test && npm run build"
  }
}
```

---

## 4. Structure

```
frontend/src/
├── api/
│   ├── client.ts            one fetch wrapper: base URL, auth header, JSON, error parsing
│   └── applications.ts      typed calls, one per endpoint
├── auth/
│   ├── AuthProvider.tsx     session + role (from /me), exposes useAuth()
│   └── LoginPage.tsx
├── components/
│   ├── StatusBadge.tsx      6-status enum -> icon + label + tint (never colour-only)
│   ├── AuditTrail.tsx       timeline; pure render of audit_logs
│   ├── Field.tsx            label + input + inline error beside the field
│   ├── LoadingState.tsx     skeleton rows
│   ├── EmptyState.tsx       icon + invitation + CTA
│   ├── ErrorState.tsx       icon + message + retry
│   └── ui/                  shadcn components land here
├── applications/            MyApplicationsPage, ApplicationForm, ApplicationDetailPage
├── reviewer/                ReviewerQueuePage, ReviewerApplicationDetailPage
├── routes/                  route tree, role-guarded
├── lib/                     schemas (zod), types, queryClient
└── test/setup.ts
e2e/                         Playwright specs (applicant submit, reviewer approve, …)
```

---

## 5. Non-negotiables (the rules that win rubric points)

- **Frontend renders server truth; never decides legality.** It shows
  approve/reject/return as a convenience, but a 403 or `invalid_transition` from the API is
  handled as a normal error state. No client-side transition guards that duplicate the backend.
- **Every data screen handles all four states** — loading, empty, error, success — via the
  shared state components. The TanStack Query return values drive them.
- **Every input goes through `Field`** (label + input + inline error beside the field, not a
  top banner). This is most of the "accessible forms" score.
- **One `StatusBadge`** for all six statuses; icon + label + tint, never colour alone.
- **All server data through TanStack Query** — never hand-rolled fetch + useState/useEffect.
- **One Zod schema per boundary**, reused for both form validation and API-response parsing,
  so TS types and runtime validation can't drift.
- **TS strict; the `gate` script passes before every commit.**

---

## 6. Tests (15% of the grade — required)

**Vitest + RTL (component/unit):**
- `StatusBadge` renders the correct icon+label for each of the six statuses.
- `ApplicationForm` shows a validation error when title is empty.
- Reviewer decision panel: reject/return action is blocked until a comment is entered.
- A query error renders `ErrorState` (not a blank screen).

**Playwright (3–4 specs, no more — point at the real Dockerized backend):**
- Applicant logs in, creates a draft, submits it; status shows SUBMITTED.
- Reviewer logs in, opens the submitted app, approves; status shows APPROVED, trail updated.
- Reject-without-comment shows the validation error; with a comment, status shows REJECTED.
- Applicant calling a reviewer action (direct) is rejected — the UI surfaces the 403 cleanly.

---

## 7. Running both together (local dev)

```bash
# terminal 1 — backend (Django + Postgres)
docker compose -f docker-compose.local.yml up

# terminal 2 — frontend
cd frontend && npm run dev      # http://localhost:5173
```
The SPA reads `VITE_API_BASE_URL` to reach `http://localhost:8000/api`. Add
`django-cors-headers` to the backend (allow `http://localhost:5173` in local settings) so
the browser can call across origins. Seeded users (from the backend seed command) are the
login credentials — document them in the README.
```
