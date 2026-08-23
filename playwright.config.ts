import { defineConfig } from '@playwright/test'

/**
 * Browser acceptance tests for the leaderboard feature.
 *
 * The suite runs against an already-running API and dev server, both seeded
 * with the deterministic TV5 fixture (see the feature quickstart).
 */
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: { timeout: 7_500 },
  fullyParallel: false,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
})
