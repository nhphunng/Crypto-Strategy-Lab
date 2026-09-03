import {
  NEWS_SENTIMENT_LABELS,
  type NewsItem,
  type NewsPage,
  type NewsSentiment,
  type SentimentSummary,
} from './types'

export class ContractError extends Error {
  constructor(readonly path: string, message: string) {
    super(`${path}: ${message}`)
    this.name = 'ContractError'
  }
}

function record(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ContractError(path, 'expected an object')
  }
  return value as Record<string, unknown>
}

function str(value: unknown, path: string): string {
  if (typeof value !== 'string') throw new ContractError(path, 'expected a string')
  return value
}

function int(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isInteger(value)) {
    throw new ContractError(path, 'expected an integer')
  }
  return value
}

function instant(value: unknown, path: string): string {
  const raw = str(value, path)
  if (Number.isNaN(Date.parse(raw))) throw new ContractError(path, 'expected a UTC instant')
  return raw
}

const DECIMAL = /^-?[0-9]+(?:\.[0-9]+)?$/

function decimal(value: unknown, path: string): string {
  const raw = str(value, path)
  if (!DECIMAL.test(raw)) throw new ContractError(path, 'expected a decimal string')
  return raw
}

function member<const T extends readonly string[]>(
  value: unknown,
  allowed: T,
  path: string,
): T[number] {
  const raw = str(value, path)
  if (!allowed.includes(raw)) throw new ContractError(path, `unsupported value ${raw}`)
  return raw as T[number]
}

function list(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) throw new ContractError(path, 'expected an array')
  return value
}

function parseSentiment(value: unknown, path: string): NewsSentiment | null {
  if (value === null) return null
  const raw = record(value, path)
  return {
    label: member(raw.label, NEWS_SENTIMENT_LABELS, `${path}.label`),
    score: decimal(raw.score, `${path}.score`),
    modelId: str(raw.modelId, `${path}.modelId`),
    modelVersion: str(raw.modelVersion, `${path}.modelVersion`),
    analyzedAt: instant(raw.analyzedAt, `${path}.analyzedAt`),
  }
}

function parseNewsItem(value: unknown, path: string): NewsItem {
  const raw = record(value, path)
  return {
    newsId: str(raw.newsId, `${path}.newsId`),
    title: str(raw.title, `${path}.title`),
    content: str(raw.content, `${path}.content`),
    source: str(raw.source, `${path}.source`),
    publishedAt: instant(raw.publishedAt, `${path}.publishedAt`),
    crawledAt: instant(raw.crawledAt, `${path}.crawledAt`),
    relatedCoins: list(raw.relatedCoins, `${path}.relatedCoins`).map((coin, index) =>
      str(coin, `${path}.relatedCoins[${index}]`),
    ),
    url: str(raw.url, `${path}.url`),
    sentiment: parseSentiment(raw.sentiment, `${path}.sentiment`),
  }
}

function parseSummary(value: unknown): SentimentSummary | null {
  if (value == null) return null
  const raw = record(value, 'news.sentimentSummary')
  const count = (key: string) => {
    const value = int(raw[key], `news.sentimentSummary.${key}`)
    if (value < 0) throw new ContractError(`news.sentimentSummary.${key}`, 'expected a nonnegative count')
    return value
  }
  return { positive: count('positive'), neutral: count('neutral'), negative: count('negative'), pending: count('pending') }
}

export function parseNewsPage(value: unknown): NewsPage {
  const path = 'news'
  const raw = record(value, path)
  return {
    items: list(raw.items, `${path}.items`).map((item, index) =>
      parseNewsItem(item, `${path}.items[${index}]`),
    ),
    page: int(raw.page, `${path}.page`),
    pageSize: int(raw.pageSize, `${path}.pageSize`),
    total: int(raw.total, `${path}.total`),
    sentimentSummary: parseSummary(raw.sentimentSummary),
  }
}
