import { createContext, useContext, useMemo, type ReactNode } from 'react'
import { createMockServices } from './mock/createMockServices'
import type { AppServices } from './ports'

const ServiceContext = createContext<AppServices | null>(null)

export function ServiceProvider({
  children,
  services,
}: {
  children: ReactNode
  services?: AppServices
}) {
  const value = useMemo(() => services ?? createMockServices(), [services])
  return <ServiceContext.Provider value={value}>{children}</ServiceContext.Provider>
}

export function useServices() {
  const services = useContext(ServiceContext)
  if (!services) throw new Error('useServices must be used within ServiceProvider')
  return services
}
