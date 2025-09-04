import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/api'

type ServiceItem = {
  name: string
  status: 'ok' | 'degraded' | 'down' | 'unknown'
  detail?: string
  metrics?: Record<string, any>
}

const Dot: React.FC<{ status: string }> = ({ status }) => {
  const color = status === 'ok' ? 'bg-green-500' : status === 'degraded' ? 'bg-yellow-500' : status === 'down' ? 'bg-red-500' : 'bg-gray-500'
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />
}

const Row: React.FC<{ s: ServiceItem }> = ({ s }) => {
  // Derive UI status: treat Prices as green when pending == 0
  const displayStatus = React.useMemo(() => {
    if (s?.name === 'prices') {
      const pending = (s.metrics as any)?.pending
      if (pending === 0) return 'ok'
    }
    return s.status
  }, [s])
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-800/70 last:border-0">
      <div className="flex items-center gap-2">
        <Dot status={displayStatus} />
        <span className="text-sm text-gray-200 font-medium capitalize">{s.name}</span>
        <span className="text-xs text-gray-400">{s.detail}</span>
      </div>
      {s.metrics && (
        <div className="text-xs text-gray-400 flex items-center gap-3">
          {Object.entries(s.metrics).slice(0, 4).map(([k, v]) => (
            <span key={k} className="font-mono">
              {k}:{' '}
              {typeof v === 'object' ? '-' : String(v)}
            </span>
          ))}
        </div>
      )}
    </div>
  )}

const StatusPage: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['status'],
    queryFn: () => apiClient.getStatus(),
    refetchInterval: 15000,
    staleTime: 10000,
  })

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">System Status</div>
        <div className="card-body">
          {isLoading && <div className="text-sm text-gray-400">Loading status…</div>}
          {error && <div className="text-sm text-red-400">Failed to load status</div>}
          {data && (
            <>
              <div className="text-xs text-gray-500 mb-2">
                Updated at {new Date((data.generated_at || 0) * 1000).toLocaleTimeString()}
              </div>
              <div className="divide-y divide-gray-800/70">
                {data.services?.map((s: ServiceItem) => (
                  <Row key={s.name} s={s} />
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default StatusPage
