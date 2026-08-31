import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MarketRoute } from "../../src/app/routes/market";

describe("Market route third-party attribution", () => {
  it("exposes the required user-visible TradingView attribution link", () => {
    render(
      <MarketRoute
        initialTimeframes={["5m"]}
        createSlotId={() => "slot-attribution"}
      />,
    );

    const attribution = screen.getByRole("link", {
      name: /TradingView Lightweight Charts™.*Copyright \(с\) 2025 TradingView, Inc\./i,
    });

    expect(attribution).toBeVisible();
    expect(attribution).toHaveAttribute("href", "https://www.tradingview.com/");
  });
});
