import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import { StoreProvider } from '../../lib/store'
import { ServiceProvider } from '../../services/registry'
import { appQueryClient } from './queryClient'

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={appQueryClient}>
      <BrowserRouter>
        <ServiceProvider>
          <StoreProvider>{children}</StoreProvider>
        </ServiceProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
