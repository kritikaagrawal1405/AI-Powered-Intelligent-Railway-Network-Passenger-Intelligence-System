import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiEndpoints } from '../lib/api'
import { useLiveStore } from '../store/liveStore'
import Navbar from '../components/navbar/Navbar'
import { SectionHeader, Skeleton, LiveTicker } from '../components/ui'
import { StyledAreaChart, Sparkline } from '../components/charts'
import { cn, delayColor } from '../utils/helpers'

const STATIONS = [
  ['NDLS','New Delhi'],['CSTM','Mumbai CST'],['HWH','Howrah'],['MAS','Chennai Central'],
  ['SBC','Bangalore City'],['PUNE','Pune'],['ADI','Ahmedabad'],['BPL','Bhopal'],
  ['LKO','Lucknow'],['VSKP','Visakhapatnam'],['BBS','Bhubaneswar'],['JAT','Jammu Tawi'],
  ['PNBE','Patna'],['NGP','Nagpur'],['HYB','Hyderabad'],['TVC','Trivandrum'],
  ['GHY','Guwahati'],['CNB','Kanpur'],['AGC','Agra Cantt'],['NZM','Hazrat Nizamuddin'],
] as const

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-rail-red/10 border-rail-red/30 text-rail-red',
  HIGH:     'bg-rail-amber/10 border-rail-amber/30 text-rail-amber',
  MEDIUM:   'bg-rail-cyan/10 border-rail-cyan/30 text-rail-cyan',
  LOW:      'bg-bg-elevated border-bg-border text-text-muted',
}

export default function DelayRadar() {
  const [selected, setSelected] = useState('NDLS')
  const { tick, stationDelays } = useLiveStore()

  const { data, isLoading } = useQuery({
    queryKey: ['delay', selected, Math.floor(tick / 10)],
    queryFn: () => apiEndpoints.delayForecast(selected).then((r) => r.data),
    staleTime: 15_000,
    refetchInterval: 20_000,
  })

  const liveDelay = stationDelays[selected] ?? data?.live_delay ?? 0
  const risk = data?.risk ?? 'LOW'
  const cascade = data?.cascade ?? []
  const hourly = data?.hourly_forecast ?? []
  const history = data?.history ?? []

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Delay Radar" />
      <div className="flex-1 overflow-y-auto p-6 space-y-5 grid-bg">

        {/* Station selector + live stats */}
        <div className="card-p">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <p className="label mb-2">Station</p>
              <select value={selected} onChange={(e) => setSelected(e.target.value)} className="select w-60">
                {STATIONS.map(([code, name]) => (
                  <option key={code} value={code}>{name} ({code})</option>
                ))}
              </select>
            </div>

            <div className="flex gap-8">
              <div>
                <p className="label mb-1">Live Delay</p>
                <p className={cn('text-2xl font-display font-bold tabular-nums', delayColor(liveDelay))}>
                  {liveDelay.toFixed(1)}<span className="text-sm text-text-muted ml-1">min</span>
                </p>
              </div>
              <div>
                <p className="label mb-1">Risk Level</p>
                <p className={cn('text-2xl font-display font-bold',
                  risk === 'HIGH' ? 'text-rail-red' : risk === 'MEDIUM' ? 'text-rail-amber' : 'text-rail-green'
                )}>{risk}</p>
              </div>
              <div>
                <p className="label mb-1">Cascade Impact</p>
                <p className="text-2xl font-display font-bold text-rail-purple">
                  {cascade.length}<span className="text-sm text-text-muted ml-1">stations</span>
                </p>
              </div>
            </div>

            <LiveTicker tick={tick} />
          </div>
        </div>

        <div className="grid grid-cols-5 gap-4">
          {/* 24h forecast */}
          <div className="card-p col-span-3">
            <SectionHeader title="24-Hour Forecast" sub="ML model + live state blend" />
            {isLoading ? <Skeleton className="h-48" /> : (
              <StyledAreaChart
                data={hourly} dataKey="delay" xKey="hour"
                color="#ffb347" gradientId="delayGrad"
                height={180}
                xFormatter={(h) => `${h}:00`}
                tooltipFormatter={(v) => `${v.toFixed(1)}min`}
                referenceLine={10}
              />
            )}
          </div>

          {/* History sparkline */}
          <div className="card-p col-span-2 flex flex-col">
            <SectionHeader title="Live History" sub="Last 60 simulation ticks" />
            {history.length > 5 ? (
              <div className="flex-1">
                <Sparkline data={history} color="#00d4ff" height={100} />
                <div className="flex justify-between text-[10px] font-mono text-text-muted mt-2">
                  <span>60 ticks ago</span>
                  <span>NOW</span>
                </div>
              </div>
            ) : <Skeleton className="h-24" />}
            <div className="mt-3 pt-3 border-t border-bg-border grid grid-cols-2 gap-2 text-[10px] font-mono text-text-muted">
              <div className="flex justify-between">
                <span>Min</span>
                <span className="text-rail-green">{history.length ? Math.min(...history).toFixed(1) : '—'}m</span>
              </div>
              <div className="flex justify-between">
                <span>Max</span>
                <span className="text-rail-red">{history.length ? Math.max(...history).toFixed(1) : '—'}m</span>
              </div>
            </div>
          </div>
        </div>

        {/* Cascade */}
        <div className="card-p">
          <SectionHeader
            title="Cascade Propagation"
            sub={`BFS propagation from ${selected} · current delay = ${liveDelay.toFixed(1)}min`}
          />
          {cascade.length === 0 ? (
            <div className="py-8 text-center text-text-muted text-sm font-body">
              No significant cascade at current delay level
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2">
              {cascade.map((c) => (
                <div key={c.station_code}
                  className={cn('rounded-xl border p-3 flex items-center justify-between', SEVERITY_COLORS[c.severity])}>
                  <div>
                    <p className="text-xs font-semibold text-text-primary">{c.station_name}</p>
                    <p className="text-[10px] font-mono mt-0.5">{c.severity}</p>
                  </div>
                  <p className="text-sm font-display font-bold tabular-nums">{c.delay}m</p>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
