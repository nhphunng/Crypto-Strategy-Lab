#!/usr/bin/env node
/**
 * Orchestrates the full-stack regression check: bring up the real Docker
 * Compose stack (PostgreSQL, migrate, API, frontend), seed the deterministic
 * leaderboard demo data, wait for both services to answer, then run the
 * Playwright specs in `tests/e2e/` against the real reverse proxy.
 *
 * This automates the manual sequence documented in the README's "Chạy demo"
 * section so it can run unattended in CI or with a single command locally:
 *
 *   node scripts/integration/run-compose-e2e.mjs
 *
 * The stack is always torn down afterwards (`docker compose down`), even if
 * a step fails, unless KEEP_STACK=1 is set for local debugging.
 *
 * `realtime-multi-chart-compose.spec.ts` is deliberately excluded from this
 * automated run: it drives the API's real Binance WebSocket/REST connection
 * end to end, and several hosted CI networks (GitHub-hosted runners
 * included) cannot reliably reach Binance's public endpoints, which makes it
 * flaky as a hard regression gate. It stays runnable manually — with a
 * network known to reach Binance — via:
 *
 *   COMPOSE_E2E=1 npx playwright test --config=playwright.compose.config.ts \
 *     tests/e2e/realtime-multi-chart-compose.spec.ts
 */

import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import process from "node:process";

const ROOT = new URL("../..", import.meta.url).pathname.replace(/^\/([A-Za-z]):/, "$1:");
const DEFAULT_PYTHON = join(
  ROOT,
  "backend",
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const PYTHON = process.env.PYTHON ?? (existsSync(DEFAULT_PYTHON) ? DEFAULT_PYTHON : "python");
const PLAYWRIGHT_CLI = join(ROOT, "node_modules", "@playwright", "test", "cli.js");
const PLAYWRIGHT = existsSync(PLAYWRIGHT_CLI)
  ? process.execPath
  : process.platform === "win32"
    ? "npx.cmd"
    : "npx";
const KEEP_STACK = process.env.KEEP_STACK === "1";
const DETERMINISTIC_SPECS = [
  "tests/e2e/leaderboard-visualization.spec.ts",
  "tests/e2e/realtime-multi-chart.spec.ts",
  "tests/e2e/market-pair-context.spec.ts",
];

function run(command, args, options = {}) {
  console.log(`\n> ${command} ${args.join(" ")}`);
  const result = spawnSync(command, args, { cwd: ROOT, stdio: "inherit", shell: false, ...options });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} exited with code ${result.status}`);
  }
}

function runAsync(command, args, options = {}) {
  console.log(`\n> ${command} ${args.join(" ")}`);
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd: ROOT, stdio: "inherit", shell: false, ...options });
    child.on("error", reject);
    child.on("exit", (code) => resolve(code ?? 1));
  });
}

async function waitFor(label, check, { retries = 60, delayMs = 2000 } = {}) {
  for (let attempt = 1; attempt <= retries; attempt += 1) {
    if (await check()) {
      console.log(`${label}: ready (attempt ${attempt}/${retries})`);
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }
  throw new Error(`${label}: not ready after ${retries} attempts`);
}

async function httpOk(url) {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(3000) });
    return response.ok;
  } catch {
    return false;
  }
}

function postgresReady() {
  const result = spawnSync(
    "docker",
    ["compose", "exec", "-T", "postgres", "pg_isready", "-U", "crypto_lab", "-d", "crypto_lab"],
    { cwd: ROOT },
  );
  return result.status === 0;
}

async function main() {
  run("docker", ["compose", "up", "-d", "postgres"]);
  await waitFor("postgres", async () => postgresReady());

  run("docker", ["compose", "run", "--rm", "migrate"]);

  run(PYTHON, ["backend/scripts/seed_leaderboard_demo.py"]);

  run("docker", ["compose", "up", "-d", "--build", "api", "frontend"]);
  await waitFor("api", () => httpOk("http://127.0.0.1:8000/health/ready"));
  await waitFor("frontend", () => httpOk("http://127.0.0.1:5173/"));

  const exitCode = await runAsync(
    PLAYWRIGHT,
    [
      ...(existsSync(PLAYWRIGHT_CLI) ? [PLAYWRIGHT_CLI] : ["playwright"]),
      "test",
      "--config=playwright.compose.config.ts",
      ...DETERMINISTIC_SPECS,
    ],
    { env: { ...process.env, COMPOSE_E2E: "1" } },
  );
  if (exitCode !== 0) {
    throw new Error(`playwright test exited with code ${exitCode}`);
  }
}

main()
  .then(() => {
    console.log("\nIntegration regression check passed.");
  })
  .catch((error) => {
    console.error(`\nIntegration regression check failed: ${error.message}`);
    process.exitCode = 1;
  })
  .finally(() => {
    if (KEEP_STACK) {
      console.log("KEEP_STACK=1 set — leaving the Compose stack running.");
      return;
    }
    console.log("\n> docker compose down");
    spawnSync("docker", ["compose", "down"], { cwd: ROOT, stdio: "inherit" });
  });
