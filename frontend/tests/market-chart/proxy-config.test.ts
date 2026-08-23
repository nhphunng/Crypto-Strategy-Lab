import { readFile } from "node:fs/promises";
import path from "node:path";

import { describe, expect, it } from "vitest";

const frontendRoot = path.resolve(import.meta.dirname, "../..");

describe("market dashboard backend proxy", () => {
  it("proxies REST and WebSocket paths in the Vite development server", async () => {
    const config = await readFile(path.join(frontendRoot, "vite.config.ts"), "utf8");

    expect(config).toMatch(/"\/api"\s*:\s*\{/);
    expect(config).toMatch(/target:\s*"http:\/\/127\.0\.0\.1:8000"/);
    expect(config).toMatch(/"\/ws"\s*:\s*\{/);
    expect(config).toMatch(/target:\s*"ws:\/\/127\.0\.0\.1:8000"/);
    expect(config).toMatch(/ws:\s*true/);
  });

  it("proxies REST and upgrades WebSockets in the Nginx runtime", async () => {
    const config = await readFile(path.join(frontendRoot, "nginx.conf"), "utf8");

    expect(config).toMatch(/location \/api\/\s*\{/);
    expect(config).toMatch(/location \/ws\/\s*\{/);
    expect(config.match(/proxy_pass http:\/\/api:8000;/g)).toHaveLength(2);
    expect(config).toMatch(/proxy_http_version 1\.1;/);
    expect(config).toMatch(/proxy_set_header Upgrade \$http_upgrade;/);
    expect(config).toMatch(/proxy_set_header Connection "upgrade";/);
  });
});
