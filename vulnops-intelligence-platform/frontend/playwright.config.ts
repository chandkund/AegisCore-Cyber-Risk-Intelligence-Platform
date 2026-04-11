import { defineConfig, devices } from "@playwright/test";

/**
 * E2E: `npm run build` then `npm run start` (same as production-ish local run).
 * Next may log that `next start` is not recommended with `output: "standalone"`; it still serves
 * the app correctly for these smoke tests. Use `node .next/standalone/server.js` in Docker/K8s.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run start",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
