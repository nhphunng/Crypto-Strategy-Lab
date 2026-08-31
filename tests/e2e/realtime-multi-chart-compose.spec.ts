import { expect, test } from "@playwright/test";

test.skip(
  process.env.COMPOSE_E2E !== "1",
  "Set COMPOSE_E2E=1 after starting Docker Compose to run the real-stack smoke test.",
);

test.use({ baseURL: "http://127.0.0.1:5173" });

test("loads historical and realtime candles through the frontend reverse proxy", async ({
  page,
}) => {
  const websocketOpened = page.waitForEvent("websocket");
  const historyLoaded = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/market-data/candles?") &&
      response.status() === 200,
  );

  await page.goto("/market");

  const [websocket, historyResponse] = await Promise.all([
    websocketOpened,
    historyLoaded,
  ]);
  expect(new URL(websocket.url()).pathname).toBe("/ws/v1/market-data");
  expect(historyResponse.headers()["content-type"]).toContain(
    "application/json",
  );

  const firstSlot = page.locator("#chart-btcusdt-5m-slot-1");
  await expect(firstSlot).toBeVisible();
  await expect(page.locator("#status-chart-slot-1")).toContainText("Live", {
    timeout: 30_000,
  });
  await expect(firstSlot.getByLabel("Latest Candle summary")).toContainText(
    "BTCUSDT 5m",
  );
  await expect(firstSlot.locator("[data-series-length]")).not.toHaveAttribute(
    "data-series-length",
    "0",
  );

  const secondPage = await page.context().newPage();
  await secondPage.goto("/market");
  await expect(secondPage.locator("#status-chart-slot-1")).toContainText(
    "Live",
    { timeout: 30_000 },
  );
  await page.close();
  await expect(secondPage.locator("#status-chart-slot-1")).toContainText(
    "Live",
  );
  await expect(
    secondPage.locator("#chart-btcusdt-5m-slot-1 [data-series-length]"),
  ).not.toHaveAttribute("data-series-length", "0");
});
