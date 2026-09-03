export const NEWS_SENTIMENT_LABELS = ['POSITIVE', 'NEUTRAL', 'NEGATIVE'] as const

export type NewsSentimentLabel = (typeof NEWS_SENTIMENT_LABELS)[number]

export type NewsSentiment = {
  label: NewsSentimentLabel
  score: string
  modelId: string
  modelVersion: string
  analyzedAt: string
}

export type NewsItem = {
  newsId: string
  title: string
  content: string
  source: string
  publishedAt: string
  crawledAt: string
  relatedCoins: string[]
  url: string
  sentiment: NewsSentiment | null
}

export type NewsPage = {
  items: NewsItem[]
  page: number
  pageSize: number
  total: number
}

export type NewsQuery = {
  coin?: string
  sentiment?: NewsSentimentLabel
  publishedAfter?: string
  publishedBefore?: string
  page?: number
  pageSize?: number
}

export type NewsApiError = {
  code: string
  message: string
  details?: Record<string, unknown>
}
