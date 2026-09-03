/**
 * News pipeline browser acceptance flow.
 *
 * The Compose stack is seeded deterministically via seed_news_demo.py (no
 * public feed) so these specs are reproducible. Run with:
 *   node scripts/integration/run-compose-e2e.mjs
 */

import { expect, test, type Locator, type Page } from '@playwright/test'

const SEED_HEADLINE_BTC = '[Demo] BTC market update #1'
const SEED_HEADLINE_ETH = '[Demo] ETH market update #2'
const MOCK_HEADLINE = 'Bitcoin gains as institutional inflows accelerate'
const LEGACY_MODEL = 'FinSent-v2.3'

/** Find a row by its headline text (the headline is bracketed, so avoid RegExp). */
function rowByHeadline(page: Page, headline: string): Locator {
  return page.locator('tbody tr', { hasText: headline })
}

test('NC-US-01: News rows come from the API and never the legacy mock', async ({ page }) => {
  await page.goto('/news')

  const btcRow = rowByHeadline(page, SEED_HEADLINE_BTC)
  await expect(btcRow).toBeVisible()
  await expect(page.getByText(MOCK_HEADLINE)).toHaveCount(0)
  await expect(page.getByText(LEGACY_MODEL)).toHaveCount(0)

  // The deterministic runner disables analysis, so this seeded item stays pending.
  await expect(btcRow.getByText('Pending analysis')).toBeVisible()
})

test('NC-US-02: coin filter narrows rows to the selected coin', async ({ page }) => {
  await page.goto('/news')

  await page.getByRole('button', { name: 'BTC', exact: true }).click()
  await expect(rowByHeadline(page, SEED_HEADLINE_ETH)).toHaveCount(0)
  await expect(rowByHeadline(page, SEED_HEADLINE_BTC)).toBeVisible()

  await page.getByRole('button', { name: 'ETH', exact: true }).click()
  await expect(rowByHeadline(page, SEED_HEADLINE_BTC)).toHaveCount(0)
  await expect(rowByHeadline(page, SEED_HEADLINE_ETH)).toBeVisible()
})

test('NC-US-03: widening 24H to 7D reveals the older single-day item', async ({ page }) => {
  await page.goto('/news')

  // Start within the last 24h: only the BTC item qualifies.
  await page.getByRole('button', { name: '24H', exact: true }).click()
  await expect(rowByHeadline(page, SEED_HEADLINE_BTC)).toBeVisible()
  await expect(rowByHeadline(page, SEED_HEADLINE_ETH)).toHaveCount(0)

  // Widen to 7D: the older ETH item (published 3 days ago) appears.
  await page.getByRole('button', { name: '7D', exact: true }).click()
  await expect(rowByHeadline(page, SEED_HEADLINE_ETH)).toBeVisible()
  await expect(rowByHeadline(page, SEED_HEADLINE_BTC)).toBeVisible()
})

test('NC-US-04: drawer shows source, content, and related coins', async ({ page }) => {
  await page.goto('/news')

  // Click the source cell (td[1]) — the headline cell holds a target=_blank
  // link that stops propagation, so clicking the row centre would not open it.
  await rowByHeadline(page, SEED_HEADLINE_BTC).locator('td').nth(1).click()
  const drawer = page.getByRole('dialog')
  await expect(drawer).toBeVisible()
  await expect(drawer.getByText('Demo Feed').first()).toBeVisible()
  await expect(drawer.getByText(/Seeded BTC summary/)).toBeVisible()
  // This fixture has not been analyzed; the drawer must not invent model output.
  await expect(
    drawer.getByText('Available after sentiment analysis completes'),
  ).toBeVisible()
})
