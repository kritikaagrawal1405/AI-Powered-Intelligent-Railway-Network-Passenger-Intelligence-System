// Congestion.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiEndpoints } from '../lib/api'
import { useLiveStore } from '../store/liveStore'
import Navbar from '../components/navbar/Navbar'
import { CongestionBar, LiveTicker, Skeleton } from '../components/ui'
import { cn, congestionBarColor } from '../utils/helpers'

const LEVEL_BG: Record<string, string> = {
  CRITICAL: 'border-rail-red/30 bg-rail-red/5',
  HIGH:     'border-rail-amber/30 bg-rail-amber/5',
  MEDIUM:   'border-bg-border bg-bg-elevated',
  LOW:      'border-bg-border bg-bg-elevated opacity-60',
}
const LEVEL_DOT: Record<string, string> = {
  CRITICAL: 'bg-rail-red animate-pulse',
  HIGH:     'bg-rail-amber',
  MEDIUM:   'bg-rail-cyan',
  LOW:      'bg-rail-green',
}

export function Congestion() {
  const [hour, setHour] = useState<number | null>(null)
  const { tick, stationCongestion } = useLiveStore()

  const { data, isLoading } = useQuery({
    queryKey: ['congestion', hour, Math.floor(tick / 8)],
    queryFn: () => apiEndpoints.congestion(hour ?? undefined).then((r) => r.data),
    staleTime: 12_000,
    refetchInterval: 15_000,
  })

  const heatmap = data?.heatmap ?? []
  const critical = heatmap.filter((s) => s.level === 'CRITICAL').length
  const high     = heatmap.filter((s) => s.level === 'HIGH').length

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Congestion Heatmap" />
      <div className="flex-1 overflow-y-auto p-6 space-y-5 grid-bg">

        <div className="card-p flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setHour(null)}
              className={cn('px-3.5 py-1.5 rounded-xl text-xs font-mono transition-all',
                hour === null
                  ? 'bg-rail-cyan/15 text-rail-cyan border border-rail-cyan/40'
                  : 'btn-ghost'
              )}
            >LIVE</button>
            <input type="range" min={0} max={23}
              value={hour ?? new Date().getHours()}
              onChange={(e) => setHour(Number(e.target.value))}
              className="w-32 accent-rail-cyan" />
            <span className="text-xs font-mono text-text-secondary w-14">
              {hour !== null ? `${String(hour).padStart(2,'0')}:00 IST` : 'NOW'}
            </span>
          </div>
          <div className="flex gap-4 text-xs font-mono">
            <span className="text-rail-red">{critical} CRITICAL</span>
            <span className="text-rail-amber">{high} HIGH</span>
          </div>
          <LiveTicker tick={tick} />
        </div>

        {/* Summary */}
        <div className="grid grid-cols-4 gap-3">
          {(['CRITICAL','HIGH','MEDIUM','LOW'] as const).map((level) => {
            const count = heatmap.filter((s) => s.level === level).length
            const textColor = { CRITICAL:'text-rail-red', HIGH:'text-rail-amber', MEDIUM:'text-rail-cyan', LOW:'text-rail-green' }[level]
            const bg = { CRITICAL:'bg-rail-red/10 border-rail-red/20', HIGH:'bg-rail-amber/10 border-rail-amber/20', MEDIUM:'bg-bg-card border-bg-border', LOW:'bg-bg-card border-bg-border' }[level]
            return (
              <div key={level} className={cn('rounded-2xl border p-4 text-center', bg)}>
                <p className={cn('text-2xl font-display font-bold', textColor)}>{isLoading ? '—' : count}</p>
                <p className="text-[10px] font-mono text-text-muted mt-1">{level}</p>
              </div>
            )
          })}
        </div>

        {/* Grid */}
        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
            {Array.from({length:12}).map((_,i) => <Skeleton key={i} className="h-24" />)}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
            {heatmap.map((s) => {
              const liveCong = hour === null ? (stationCongestion[s.station_code] ?? s.congestion_score) : s.congestion_score
              return (
                <div key={s.station_code} className={cn('rounded-2xl border p-3.5 animate-[fadeIn_0.3s_ease-out] transition-all', LEVEL_BG[s.level])}>
                  <div className="flex items-start justify-between mb-2.5">
                    <div>
                      <p className="text-xs font-semibold text-text-primary leading-tight">{s.station_name}</p>
                      <p className="text-[9px] font-mono text-text-muted mt-0.5">{s.station_code} · {s.zone}</p>
                    </div>
                    <span className={cn('w-2 h-2 rounded-full shrink-0 mt-0.5', LEVEL_DOT[s.level])} />
                  </div>
                  <CongestionBar value={liveCong} />
                  <p className="mt-1.5 text-[10px] font-mono text-text-muted">
                    ~{(s.estimated_crowd / 1000).toFixed(1)}K pax/hr
                  </p>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
