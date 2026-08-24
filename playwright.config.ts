import path from "node:path";

import { defineConfig, devices } from "@playwright/test";

const quote = (value: string) => `"${value.replaceAll('"', '\\"')}"`;
const viteCli = path.resolve("frontend/node_modules/vite/bin/vite.js");

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  use: {
    baseURL: "http://127.0.0.1:43681",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `${quote(process.execPath)} ${quote(viteCli)} frontend --config frontend/vite.config.ts --host 127.0.0.1 --port 43681 --strictPort`,
    url: "http://127.0.0.1:43681",
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], channel: "chrome" },
    },
  ],
});
