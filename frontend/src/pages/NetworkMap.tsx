import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiEndpoints } from '../lib/api'
import { useLiveStore } from '../store/liveStore'
import Navbar from '../components/navbar/Navbar'
import NetworkMapCanvas from '../components/map/NetworkMapCanvas'
import NetworkMapLeaflet from '../components/map/NetworkMapLeaflet'
import { LiveTicker, Skeleton } from '../components/ui'
import { cn } from '../utils/helpers'

type ColorMode = 'delay' | 'congestion' | 'vulnerability'

const MODES: { key: ColorMode; label: string }[] = [
  { key: 'delay', label: 'Delay' },
  { key: 'congestion', label: 'Congestion' },
  { key: 'vulnerability', label: 'Vulnerability' },
]

const LEGENDS: Record<ColorMode, Array<{ color: string; label: string }>> = {
  delay: [
    { color: 'bg-rail-green',  label: '< 10m' },
    { color: 'bg-rail-amber',  label: '10–30m' },
    { color: 'bg-rail-red',    label: '> 30m' },
  ],
  congestion: [
    { color: 'bg-rail-green',  label: 'LOW' },
    { color: 'bg-rail-cyan',   label: 'MEDIUM' },
    { color: 'bg-rail-amber',  label: 'HIGH' },
    { color: 'bg-rail-red',    label: 'CRITICAL' },
  ],
  vulnerability: [
    { color: 'bg-rail-cyan',   label: 'NORMAL' },
    { color: 'bg-rail-red',    label: 'HIGH' },
    { color: 'bg-rail-purple', label: 'CRITICAL' },
  ],
}

export default function NetworkMap() {
  const [mode, setMode] = useState<ColorMode>('delay')
  const { tick, stationDelays, stationCongestion, trains } = useLiveStore()

  const { data, isLoading } = useQuery({
    queryKey: ['network'],
    queryFn: () => apiEndpoints.network().then((r) => r.data),
    staleTime: 120_000,
  })

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Network Map" />
      <div className="flex-1 overflow-hidden p-6 flex flex-col gap-4">

        {/* Controls */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex gap-2">
            {MODES.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setMode(key)}
                className={cn(
                  'px-3.5 py-1.5 rounded-xl text-xs font-mono font-medium transition-all',
                  mode === key
                    ? 'bg-rail-cyan/15 text-rail-cyan border border-rail-cyan/40'
                    : 'bg-bg-elevated text-text-muted border border-bg-border hover:text-text-secondary'
                )}
              >
                {label.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4">
            {LEGENDS[mode].map(({ color, label }) => (
              <span key={label} className="flex items-center gap-1.5 text-[10px] font-mono text-text-muted">
                <span className={cn('w-2 h-2 rounded-full', color)} />
                {label}
              </span>
            ))}
            <span className="text-[10px] font-mono text-text-muted ml-2">· Node size = footfall</span>
          </div>

          <LiveTicker tick={tick} />
        </div>

        {/* Map with India basemap + topology overlay */}
        <div className="card flex-1 relative overflow-hidden">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center text-text-muted text-sm font-body">
              Loading network topology...
            </div>
          ) : (
            <NetworkMapLeaflet
              nodes={data?.nodes ?? []}
              edges={data?.edges ?? []}
              mode={mode}
              stationDelays={stationDelays}
              stationCongestion={stationCongestion}
              trains={trains}
              tick={tick}
            />
          )}
        </div>

      </div>
    </div>
  )
}
