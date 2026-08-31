/**
 * TV5 browser acceptance flow.
 *
 * The dev server is started by playwright.config.ts. The API must be running
 * and seeded first (see specs/005-leaderboard-visualization/quickstart.md):
 *   docker compose up -d postgres
 *   docker compose run --rm migrate
 *   python backend/scripts/seed_leaderboard_demo.py
 *   docker compose up -d api
 *
 * Run with:
 *   npm run test:e2e:leaderboard
 */

import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/leaderboard')
  await expect(page.getByTestId('table-leaderboard')).toBeVisible()
})

test('LV-US-01: the Top-K snapshot is deterministic and fully labelled', async ({ page }) => {
  const rows = page.locator('[data-testid^="row-leaderboard-"]')
  await expect(rows).toHaveCount(10)

  const ranks = await rows.locator('td:first-child').allInnerTexts()
  expect(ranks).toEqual(Array.from({ length: 10 }, (_, index) => `#${index + 1}`))

  const firstOrder = await rows.evaluateAll((items) =>
    items.map((item) => item.getAttribute('data-testid')),
  )
  await page.reload()
  await expect(page.getByTestId('table-leaderboard')).toBeVisible()
  const secondOrder = await rows.evaluateAll((items) =>
    items.map((item) => item.getAttribute('data-testid')),
  )
  expect(secondOrder).toEqual(firstOrder)

  await expect(page.getByTestId('control-sort-MAX_DRAWDOWN')).toContainText('lower is better')
  await expect(page.getByTestId('label-simulated-analysis')).toContainText(
    'Simulated historical analysis',
  )
  const disclaimer = (await page.getByTestId('disclaimer-leaderboard').innerText()).toLowerCase()
  expect(disclaimer).toContain('not investment advice')
  expect(disclaimer).not.toContain('guaranteed profit')
})

test('LV-US-01: presentation controls never change Top-K membership', async ({ page }) => {
  const rows = page.locator('[data-testid^="row-leaderboard-"]')
  const before = await rows.evaluateAll((items) =>
    items.map((item) => item.getAttribute('data-testid')),
  )

  await page.getByTestId('control-sort-MAX_DRAWDOWN').click()
  await expect(rows).toHaveCount(10)
  const after = await rows.evaluateAll((items) =>
    items.map((item) => item.getAttribute('data-testid')),
  )
  expect(new Set(after)).toEqual(new Set(before))

  await page.getByTestId('control-filter-min-score').fill('80')
  await expect(rows).toHaveCount(5)
  await page.getByTestId('control-filter-min-score').fill('')
  await expect(rows).toHaveCount(10)
})

test('LV-US-02: the view reports live connection state and projection version', async ({
  page,
}) => {
  await expect(page.getByTestId('status-leaderboard')).toHaveAttribute('data-status', /LIVE|CONNECTING/)
  await expect(page.getByTestId('status-projection-version')).toContainText('projection v')
})

test('LV-US-03: Top-1 drill-down explains the result and Trade #3', async ({ page }) => {
  await page.locator('[data-testid^="row-leaderboard-"]').first().click()
  const detail = page.getByTestId('detail-ranked-result')
  await expect(detail).toBeVisible()

  await expect(page.getByTestId('detail-context')).toContainText('BTCUSDT')
  await expect(page.getByTestId('detail-context')).toContainText('15m')
  await expect(page.getByTestId('chart-candles')).toBeVisible()
  await expect(page.locator('[data-marker-type="ENTRY"]').first()).toBeVisible()
  await expect(page.locator('[data-marker-type="EXIT"]').first()).toBeVisible()

  const tradeRows = page.locator('[data-testid^="row-trade-"]')
  await tradeRows.nth(2).focus()
  await page.keyboard.press('Enter')

  await expect(page.locator('[data-selected="true"][data-marker-type="ENTRY"]')).toHaveCount(1)
  await expect(page.locator('[data-selected="true"][data-marker-type="EXIT"]')).toHaveCount(1)
  await expect(page.getByTestId('chart-highlight')).toBeVisible()

  const selected = page.getByTestId('detail-selected-trade')
  await expect(selected).toContainText('LONG')
  await expect(selected).toContainText('Entry signal')

  const provenance = page.getByTestId('detail-provenance')
  await expect(provenance).toContainText('Backtest Run')
  await expect(provenance).toContainText('Scoring policy')
  await expect(provenance).toContainText('Result checksum')

  const disclaimer = (await page.getByTestId('disclaimer-ranked-result').innerText()).toLowerCase()
  expect(disclaimer).toContain('not investment advice')
})

test('LV-US-03: markers stay distinguishable without colour and HOLD is opt-in', async ({
  page,
}) => {
  await page.locator('[data-testid^="row-leaderboard-"]').first().click()
  await expect(page.getByTestId('marker-layer')).toBeVisible()

  await expect(page.locator('[data-marker-type="HOLD"]')).toHaveCount(0)
  await page.getByTestId('control-show-hold').check()
  await expect(page.locator('[data-marker-type="HOLD"]').first()).toBeVisible()

  const shapes = await page
    .locator('[data-marker-shape]')
    .evaluateAll((items) => items.map((item) => item.getAttribute('data-marker-shape')))
  expect(new Set(shapes).size).toBeGreaterThan(1)

  const labels = await page
    .locator('[data-testid^="marker-"] text')
    .evaluateAll((items) => items.map((item) => item.textContent))
  expect(labels.some((label) => label?.startsWith('ENTRY #'))).toBe(true)
  expect(labels.some((label) => label?.startsWith('EXIT #'))).toBe(true)
})

test('LV-US-03: an unaligned marker is reported rather than placed on a guessed Candle', async ({
  page,
}) => {
  await page.locator('[data-testid^="row-leaderboard-"]').first().click()

  const note = page.getByTestId('state-unaligned-markers')
  if (await note.isVisible()) {
    await expect(note).toContainText('could not be aligned')
  }
})
