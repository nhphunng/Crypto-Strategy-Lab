import { useQuery } from '@tanstack/react-query'
import { discoverStrategies, STRATEGY_CATALOG_QUERY_KEY } from '../../../services/strategyCatalog'
import { recommendedStrategyValues } from '../../../config'

export function useStrategyCatalog() {
  const query = useQuery({
    queryKey: STRATEGY_CATALOG_QUERY_KEY,
    queryFn: discoverStrategies,
    staleTime: 30_000,
  })
  const methods = query.data ?? []
  const byId = (id: string) => {
    const strategy = methods.find((item) => item.id === id)
    if (!strategy) throw new Error(`Unknown strategy method: ${id}`)
    return strategy
  }
  const recommendedValues = (id: string) => recommendedStrategyValues(byId(id))
  return { ...query, methods, byId, recommendedValues }
}
