import { BrowserRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { StoreProvider } from '../../lib/store'
import { ServiceProvider } from '../../services/registry'

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter>
      <ServiceProvider>
        <StoreProvider>{children}</StoreProvider>
      </ServiceProvider>
    </BrowserRouter>
  )
}
