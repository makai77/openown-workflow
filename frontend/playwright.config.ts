import { defineConfig, devices } from "@playwright/test";

// E2E runs against the live stack (Playbook §8.4): the Vite dev server on :5173
// and the Dockerised Django API on :8000. Both must be running locally; the
// webServer block reuses an already-running Vite rather than spawning a second.
const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  // The specs create and mutate real rows through the API, so they must not race
  // each other against the shared dev database.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
