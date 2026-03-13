import { useQuery } from '@tanstack/react-query'
import { apiEndpoints } from '../lib/api'
import { useLiveStore } from '../store/liveStore'
import Navbar from '../components/navbar/Navbar'
import { LiveTicker, Skeleton } from '../components/ui'
import OperatorNetworkTopology from '../components/map/OperatorNetworkTopology'

export default function OperatorTopology() {
  const { tick, stationCongestion, stationDelays } = useLiveStore()

  const { data, isLoading } = useQuery({
    queryKey: ['network-topology-operator'],
    queryFn: () => apiEndpoints.network().then((r) => r.data),
    staleTime: 120_000,
  })

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Network Topology" />
      <div className="flex-1 overflow-hidden p-6 flex flex-col gap-4">
        <div className="flex items-start justify-between mb-2 flex-wrap gap-3">
          <div>
            <span className="pill pill-purple">OPERATOR VIEW</span>
            <h1 className="text-lg font-display tracking-[0.2em] text-text-primary mt-2">
              LIVE LINE RUNNING STATUS
            </h1>
            <p className="text-[11px] font-mono text-text-muted mt-1">
              Animated network topology with congestion overlay and line activity
            </p>
          </div>

          <div className="flex items-center gap-4 glass rounded-lg px-4 py-2">
            {[
              ['#10b981', 'Normal'],
              ['#f97316', 'Moderate'],
              ['#fcd34d', 'High'],
              ['#ef4444', 'Critical'],
            ].map(([c, l]) => (
              <span key={l} className="flex items-center gap-1.5 text-[10px] font-mono text-text-muted">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ background: c, boxShadow: `0 0 5px ${c}` }}
                />
                {l}
              </span>
            ))}
            <LiveTicker tick={tick} />
          </div>
        </div>

        {isLoading || !data ? (
          <div className="card flex-1 flex items-center justify-center">
            <Skeleton className="w-40 h-10" />
          </div>
        ) : (
          <OperatorNetworkTopology
            nodes={data.nodes}
            edges={data.edges}
            stationCongestion={stationCongestion}
            stationDelays={stationDelays}
          />
        )}
      </div>
    </div>
  )
}

