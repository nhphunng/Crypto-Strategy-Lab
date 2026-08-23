import { useStore } from './lib/store'
import { AppProviders } from './app/providers/AppProviders'
import { AppShell } from './components/Shell'
import { Toasts } from './components/ui'
import { Landing } from './screens/Landing'
import { ConnectedMarketRoute } from './app/routes/market'
import { Strategies } from './screens/Strategies'
import { Backtests } from './screens/Backtests'
import { Leaderboard } from './screens/Leaderboard'
import { News } from './screens/News'
import { Operations } from './screens/Operations'

function Router() {
  const { page } = useStore()

  if (page === 'landing') {
    return <Landing />
  }

  return (
    <AppShell>
      {page === 'market' && <ConnectedMarketRoute />}
      {page === 'strategies' && <Strategies />}
      {page === 'backtests' && <Backtests />}
      {page === 'leaderboard' && <Leaderboard />}
      {page === 'news' && <News />}
      {page === 'operations' && <Operations />}
    </AppShell>
  )
}

export default function App() {
  return (
    <AppProviders>
      <Router />
      <Toasts />
    </AppProviders>
  )
}
