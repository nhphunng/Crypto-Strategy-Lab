import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const frontendRoot = resolve(import.meta.dirname, "../..");
const canonicalMarketFiles = [
  resolve(frontendRoot, "src/app/routes/market.tsx"),
  ...[
    "api/marketDataApi.ts",
    "components/ChartGrid.tsx",
    "components/ChartSlot.tsx",
    "components/CandlestickChart.tsx",
    "components/ConnectionStatus.tsx",
    "components/MarketGuide.tsx",
    "hooks/useChartSlot.ts",
    "hooks/useMarketDataConnection.ts",
    "realtime/marketDataSocket.ts",
    "schemas.ts",
    "types.ts",
  ].map((relativePath) => resolve(frontendRoot, "src/features/market-chart", relativePath)),
];

const strategyRuntimeDenylist = [
  /IsolatedGeneratedStrategy/,
  /DockerGeneratedStrategyRuntime/,
  /(^|[^\w.])exec\s*\(/,
  /\beval\s*\(/,
  /calculateRsi/,
  /supportResistance/,
  /signalMarkers/,
];

describe("canonical market strategy boundary", () => {
  it("keeps generated execution and indicator decisions out of the market feature", () => {
    const source = canonicalMarketFiles
      .map((filePath) => readFileSync(filePath, "utf8"))
      .join("\n");

    for (const forbidden of strategyRuntimeDenylist) {
      expect(source).not.toMatch(forbidden);
    }
  });

  it("exposes backend-owned market transport and rendering seams", () => {
    const routeSource = readFileSync(canonicalMarketFiles[0]!, "utf8");
    const featureSource = canonicalMarketFiles
      .slice(1)
      .map((filePath) => readFileSync(filePath, "utf8"))
      .join("\n");

    expect(routeSource).toContain("createMarketDimensionsQueryOptions");
    expect(routeSource).toContain("setMarket");
    expect(featureSource).toContain("getCandles");
    expect(featureSource).toContain("subscribe");
    expect(featureSource).toContain("Candle");
  });
});
