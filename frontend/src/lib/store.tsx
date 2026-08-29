import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { PAGE_PATHS, PATH_PAGES, WORKSPACE_DEFAULTS } from '../config'
import type { MarketInfo, Timeframe } from '../domain'
import { useServices } from '../services/registry'

export type Page =
  | 'landing'
  | 'market'
  | 'strategies'
  | 'strategyNew'
  | 'backtests'
  | 'leaderboard'
  | 'news'
  | 'operations'

export type ConnState = 'live' | 'reconnecting' | 'stale'

export type Toast = { id: number; text: string; tone: 'info' | 'positive' | 'warning' }

type NavPayload = {
  backtestTab?: 'single' | 'search' | 'runs'
  strategyName?: string
  strategyConfigurationId?: string
  overlayContext?: string
}

type Store = {
  page: Page
  navigate: (p: Page, payload?: NavPayload) => void
  navCollapsed: boolean
  toggleNav: () => void

  conn: ConnState
  setConn: (c: ConnState) => void
  reconnect: () => void

  // beginner-friendly explanations (progressive disclosure)
  showExplain: boolean
  toggleExplain: (v: boolean) => void

  // cross-screen context
  market: MarketInfo
  setMarket: (pair: string) => void
  watchlist: string[]
  toggleWatch: (pair: string) => void
  timeframe: Timeframe
  setTimeframe: (t: Timeframe) => void
  activeStrategy: string
  setActiveStrategy: (s: string) => void
  overlayContext: string | null
  requestedBacktestTab: 'single' | 'search' | 'runs' | null
  consumeBacktestTab: () => void

  // search run (Backtests › Strategy Search)
  searchStatus: 'ready' | 'running' | 'stopped' | 'completed'
  searchTested: number
  startSearch: () => void
  stopSearch: () => void

  // continuous loop (Operations)
  loopStatus: 'running' | 'stopped'
  loopTested: number
  loopElapsed: number
  toggleLoop: (v: boolean) => void

  toasts: Toast[]
  toast: (text: string, tone?: Toast['tone']) => void
  dismissToast: (id: number) => void
}

const Ctx = createContext<Store | null>(null)

function readStoredList(key: string, fallback: string[]) {
  const storage = browserStorage()
  if (!storage) return fallback
  try {
    const value = JSON.parse(storage.getItem(key) ?? 'null')
    return Array.isArray(value) && value.every((item) => typeof item === 'string') ? value : fallback
  } catch {
    return fallback
  }
}

function browserStorage(): Storage | null {
  if (typeof window === 'undefined') return null
  try {
    const storage = window.localStorage
    return typeof storage?.getItem === 'function' && typeof storage.setItem === 'function'
      ? storage
      : null
  } catch {
    return null
  }
}

export function useStore() {
  const s = useContext(Ctx)
  if (!s) throw new Error('useStore must be used within StoreProvider')
  return s
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const location = useLocation()
  const routeNavigate = useNavigate()
  const services = useServices()
  const normalizedPath = location.pathname.replace(/\/$/, '') || '/'
  const page = PATH_PAGES[normalizedPath] ?? 'landing'
  const [navCollapsed, setNavCollapsed] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth < 1180 : false,
  )
  const [conn, setConn] = useState<ConnState>('live')
  const reconnect = useCallback(() => {
    setConn('reconnecting')
    window.setTimeout(() => setConn('live'), 900)
  }, [])

  const [showExplain, setShowExplain] = useState<boolean>(() => {
    return browserStorage()?.getItem('csl.showExplain') !== '0'
  })
  const toggleExplain = useCallback((v: boolean) => {
    setShowExplain(v)
    browserStorage()?.setItem('csl.showExplain', v ? '1' : '0')
  }, [])

  const [marketPair, setMarketPair] = useState<string>(() => {
    return browserStorage()?.getItem('csl.market') ?? WORKSPACE_DEFAULTS.marketPair
  })
  const market = useMemo(
    () => services.market.getMarket(marketPair) ?? services.market.listMarkets()[0],
    [marketPair, services],
  )
  const setMarket = useCallback((pair: string) => {
    const m = services.market.getMarket(pair)
    if (!m || !m.available) return
    setMarketPair(pair)
    browserStorage()?.setItem('csl.market', pair)
  }, [services])

  const [watchlist, setWatchlist] = useState<string[]>(() => {
    return readStoredList('csl.watchlist', WORKSPACE_DEFAULTS.watchlist)
  })
  const toggleWatch = useCallback((pair: string) => {
    setWatchlist((w) => {
      const next = w.includes(pair) ? w.filter((p) => p !== pair) : [...w, pair]
      browserStorage()?.setItem('csl.watchlist', JSON.stringify(next))
      return next
    })
  }, [])

  const [timeframe, setTimeframe] = useState(WORKSPACE_DEFAULTS.timeframe)
  const [activeStrategy, setActiveStrategy] = useState(WORKSPACE_DEFAULTS.activeStrategy)
  const [overlayContext, setOverlayContext] = useState<string | null>(null)
  const [requestedBacktestTab, setRequestedBacktestTab] = useState<
    'single' | 'search' | 'runs' | null
  >(null)

  const [searchStatus, setSearchStatus] = useState<Store['searchStatus']>('running')
  const [searchTested, setSearchTested] = useState(services.backtests.searchRun.tested)

  const [loopStatus, setLoopStatus] = useState<'running' | 'stopped'>('running')
  const [loopTested, setLoopTested] = useState(WORKSPACE_DEFAULTS.loopTested)
  const [loopElapsed, setLoopElapsed] = useState(WORKSPACE_DEFAULTS.loopElapsedSeconds)

  const [toasts, setToasts] = useState<Toast[]>([])
  const toastId = useRef(1)

  const toast = useCallback((text: string, tone: Toast['tone'] = 'info') => {
    const id = toastId.current++
    setToasts((t) => [...t, { id, text, tone }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200)
  }, [])
  const dismissToast = useCallback((id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id))
  }, [])

  const navigate = useCallback((p: Page, payload?: NavPayload) => {
    const query = new URLSearchParams()
    if (payload?.strategyConfigurationId) {
      query.set('configurationId', payload.strategyConfigurationId)
    }
    const suffix = query.size > 0 ? `?${query.toString()}` : ''
    routeNavigate(`${PAGE_PATHS[p]}${suffix}`)
    if (payload?.strategyName) setActiveStrategy(payload.strategyName)
    if (payload?.overlayContext !== undefined) setOverlayContext(payload.overlayContext)
    if (payload?.backtestTab) setRequestedBacktestTab(payload.backtestTab)
    window.scrollTo(0, 0)
  }, [routeNavigate])

  const consumeBacktestTab = useCallback(() => setRequestedBacktestTab(null), [])

  const startSearch = useCallback(() => {
    setSearchStatus('running')
    setSearchTested((v) =>
      v >= services.backtests.searchRun.candidateLimit ? services.backtests.searchRun.tested : v,
    )
  }, [services])
  const stopSearch = useCallback(() => setSearchStatus('stopped'), [])

  // deterministic search progress animation
  useEffect(() => {
    if (searchStatus !== 'running') return
    const iv = setInterval(() => {
      setSearchTested((v) => {
        if (v >= services.backtests.searchRun.candidateLimit) {
          setSearchStatus('completed')
          return v
        }
        return v + 1
      })
    }, 900)
    return () => clearInterval(iv)
  }, [searchStatus, services])

  // continuous loop metrics
  useEffect(() => {
    if (loopStatus !== 'running') return
    const iv = setInterval(() => {
      setLoopTested((v) => v + 1)
      setLoopElapsed((v) => v + 2)
    }, 2000)
    return () => clearInterval(iv)
  }, [loopStatus])

  const toggleLoop = useCallback((v: boolean) => setLoopStatus(v ? 'running' : 'stopped'), [])

  const value = useMemo<Store>(
    () => ({
      page,
      navigate,
      navCollapsed,
      toggleNav: () => setNavCollapsed((c) => !c),
      conn,
      setConn,
      reconnect,
      showExplain,
      toggleExplain,
      market,
      setMarket,
      watchlist,
      toggleWatch,
      timeframe,
      setTimeframe,
      activeStrategy,
      setActiveStrategy,
      overlayContext,
      requestedBacktestTab,
      consumeBacktestTab,
      searchStatus,
      searchTested,
      startSearch,
      stopSearch,
      loopStatus,
      loopTested,
      loopElapsed,
      toggleLoop,
      toasts,
      toast,
      dismissToast,
    }),
    [
      page,
      navigate,
      navCollapsed,
      conn,
      reconnect,
      showExplain,
      toggleExplain,
      market,
      setMarket,
      watchlist,
      toggleWatch,
      timeframe,
      activeStrategy,
      overlayContext,
      requestedBacktestTab,
      consumeBacktestTab,
      searchStatus,
      searchTested,
      startSearch,
      stopSearch,
      loopStatus,
      loopTested,
      loopElapsed,
      toggleLoop,
      toasts,
      toast,
      dismissToast,
    ],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
