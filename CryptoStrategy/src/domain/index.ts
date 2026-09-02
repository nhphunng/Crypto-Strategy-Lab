import type {
  LeaderRow,
  MarketInfo,
  NewsItem,
  RunRow,
  Strategy,
  Timeframe,
  Trade,
} from '../lib/mock'

export type ResourceStatus = 'idle' | 'loading' | 'success' | 'empty' | 'error'
export type ResourceFreshness = 'live' | 'partial' | 'stale' | 'reconnecting' | 'degraded'

export type ResourceState<T> = {
  status: ResourceStatus
  freshness?: ResourceFreshness
  data?: T
  error?: string
  updatedAt?: string
}

export type ConnectionState = 'live' | 'reconnecting' | 'stale'

export type SearchRun = {
  id: string
  generator: string
  tested: number
  candidateLimit: number
  workers: number
  queue: number
  failed: number
  retried: number
  seed: number
  throughput: number
  top1: number
}

export type OperationalDependency = {
  id: string
  name: string
  status: 'healthy' | 'degraded' | 'offline'
  latencyMs?: number
  optional?: boolean
}

export type OperationsSnapshot = {
  pipeline: readonly string[]
  dependencies: readonly {
    name: string
    status: 'HEALTHY' | 'CONNECTED' | 'DEGRADED'
    required: boolean
    lag: string
    last: string
  }[]
  workers: readonly {
    id: string
    status: 'RUNNING' | 'IDLE'
    job: string | null
    util: number
  }[]
  events: readonly {
    t: string
    kind: string
    ref: string
    detail: string
    cat: string
  }[]
  eventCategories: readonly string[]
}

export type {
  LeaderRow,
  MarketInfo,
  NewsItem,
  RunRow,
  Strategy,
  Timeframe,
  Trade,
}
