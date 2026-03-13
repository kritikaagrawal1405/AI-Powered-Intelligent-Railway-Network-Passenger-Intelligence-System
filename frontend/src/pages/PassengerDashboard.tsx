import { useQuery } from '@tanstack/react-query'
import { apiEndpoints } from '../lib/api'
import { useLiveStore } from '../store/liveStore'
import { KpiCard, StatusDot, DelayBar, IncidentBadge, Skeleton, LiveTicker, SectionHeader } from '../components/ui'
import Navbar from '../components/navbar/Navbar'
import { StyledBarChart } from '../components/charts'
import { cn, delayColor, statusColor } from '../utils/helpers'
import { PassengerAgentCard } from '../components/agent/PassengerAgentCard'
import {
  Train, Clock, Users, ShieldCheck,
  AlertTriangle, CheckCircle, Info, TrendingUp
} from 'lucide-react'

export default function PassengerDashboard() {
  const { tick, systemDelay, incidents, trains, topDelays } = useLiveStore()

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-passenger', Math.floor(tick / 15)],
    queryFn: () => apiEndpoints.passengerDashboard().then((r) => r.data),
    staleTime: 20_000,
    refetchInterval: 30_000,
  })

  const kpis       = data?.kpis
  const forecast   = data?.forecast_7d ?? []
  const bestStns   = data?.best_stations ?? []
  const worstStns  = data?.worst_stations ?? []
  const advisories = data?.travel_advisory ?? []

  const onTimeCount = trains.filter((t) => t.status === 'ON_TIME').length
  const lateCount   = trains.filter((t) => ['LATE', 'VERY_LATE'].includes(t.status)).length

  const ADVISORY_CFG: Record<string, { bg: string; border: string; icon: React.ElementType; color: string }> = {
    CRITICAL: { bg: 'bg-rail-red/10',   border: 'border-rail-red/30',   icon: AlertTriangle,  color: 'text-rail-red'   },
    WARNING:  { bg: 'bg-rail-amber/10', border: 'border-rail-amber/30', icon: AlertTriangle,  color: 'text-rail-amber' },
    INFO:     { bg: 'bg-rail-cyan/10',  border: 'border-rail-cyan/30',  icon: Info,           color: 'text-rail-cyan'  },
  }

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Passenger Dashboard" />
      <div className="flex-1 overflow-y-auto p-6 space-y-5 grid-bg">

        {/* Persona tag */}
        <div className="flex items-center gap-2">
          <span className="pill pill-cyan">PASSENGER VIEW</span>
          <span className="text-[10px] font-mono text-text-muted">
            Travel information & journey planning
          </span>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          <KpiCard
            label="Trains Running" live
            value={trains.length || kpis?.active_trains || '—'}
            sub={`${onTimeCount} on time · ${lateCount} delayed`}
            color="cyan" icon={<Train size={13} />}
          />
          <KpiCard
            label="On-Time Rate" live
            value={`${kpis?.on_time_pct ?? '—'}%`}
            sub="Live across all trains"
            color={!kpis || kpis.on_time_pct > 75 ? 'green' : kpis.on_time_pct > 50 ? 'amber' : 'red'}
            icon={<Clock size={13} />}
          />
          <KpiCard
            label="Avg Delay" live
            value={`${systemDelay.toFixed(1)}`}
            sub="minutes · system average"
            color={systemDelay > 20 ? 'red' : systemDelay > 10 ? 'amber' : 'green'}
            icon={<TrendingUp size={13} />}
          />
          <KpiCard
            label="Network Reliability"
            value={`${kpis?.network_reliability ?? '—'}%`}
            sub={incidents.length ? `${incidents.length} disruption(s) active` : 'All clear'}
            color={!kpis || kpis.network_reliability > 70 ? 'green' : 'amber'}
            icon={<ShieldCheck size={13} />}
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* Travel Advisory Banner */}
          <div className="col-span-2 space-y-2">
            {advisories.length > 0 && advisories.map((adv: any, i: number) => {
              const cfg = ADVISORY_CFG[adv.level] ?? ADVISORY_CFG.INFO
              const Icon = cfg.icon
              return (
                <div key={i} className={cn(
                  'flex items-start gap-3 rounded-xl border px-4 py-3 animate-[fadeIn_0.3s_ease-out]',
                  cfg.bg, cfg.border
                )}>
                  <Icon size={13} className={cn('shrink-0 mt-0.5', cfg.color)} />
                  <p className={cn('text-xs font-body', cfg.color)}>{adv.message}</p>
                </div>
              )
            })}
            {advisories.length === 0 && <Skeleton className="h-16" />}
          </div>

          {/* Passenger agent */}
          <PassengerAgentCard
            systemDelay={systemDelay}
            onTimePct={kpis?.on_time_pct}
            reliabilityPct={kpis?.network_reliability}
            bestStations={bestStns}
            worstStations={worstStns}
            forecast={forecast}
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* Active Incidents for Passengers */}
          <div className="card-p">
            <div className="flex items-center justify-between mb-4">
              <SectionHeader title="Service Disruptions" />
              <LiveTicker tick={tick} />
            </div>
            {incidents.length === 0 ? (
              <div className="flex flex-col items-center py-10 gap-2 text-text-muted">
                <CheckCircle size={24} className="text-rail-green opacity-60" />
                <p className="text-xs font-body">All services running normally</p>
              </div>
            ) : incidents.map((inc: any) => (
              <div key={inc.id} className="mb-3 bg-bg-elevated border border-rail-red/20 rounded-xl p-3 animate-[fadeIn_0.3s_ease-out]">
                <div className="flex items-start justify-between mb-1.5">
                  <p className="text-xs font-semibold text-text-primary">{inc.station_name}</p>
                  <IncidentBadge severity={inc.severity} />
                </div>
                <p className="text-[11px] text-text-muted">{inc.type}</p>
                <p className="text-[11px] font-mono text-rail-red mt-1">+{inc.delay_added}min added delay</p>
              </div>
            ))}
          </div>

          {/* 7-Day Travel Forecast */}
          <div className="card-p col-span-2">
            <SectionHeader title="7-Day Delay Outlook" sub="Plan your journey — lower is better" />
            {isLoading ? (
              <Skeleton className="h-44" />
            ) : (
              <>
                <StyledBarChart
                  data={forecast}
                  dataKey="avg_delay"
                  xKey="day"
                  height={150}
                  cellColors={forecast.map((d: any) => d.risk === 'HIGH' ? '#ff4757' : '#00d4ff')}
                  tooltipFormatter={(v) => `${v.toFixed(1)}min avg delay`}
                />
                <div className="flex gap-4 mt-2 text-[10px] font-mono text-text-muted">
                  <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-rail-cyan inline-block"/>&lt; 10min — Good travel day</span>
                  <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-rail-red inline-block"/>10min+ — Expect delays</span>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* Best Stations to Travel From */}
          <div className="card-p">
            <SectionHeader title="Best Departures Now" sub="Lowest live delays" />
            {isLoading ? <Skeleton className="h-36" /> : (
              <div className="space-y-3">
                {bestStns.map((s: any, i: number) => (
                  <div key={s.code} className="flex items-center gap-2.5 animate-[fadeIn_0.3s_ease-out]">
                    <span className="text-[10px] font-mono text-text-muted w-4">#{i + 1}</span>
                    <div className="flex-1">
                      <p className="text-xs text-text-secondary">{s.name}</p>
                    </div>
                    <DelayBar value={s.delay} />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Worst Stations */}
          <div className="card-p">
            <SectionHeader title="Avoid If Possible" sub="Highest live delays" />
            {isLoading ? <Skeleton className="h-36" /> : (
              <div className="space-y-3">
                {worstStns.map((s: any, i: number) => (
                  <div key={s.code} className="flex items-center gap-2.5 animate-[fadeIn_0.3s_ease-out]">
                    <span className="text-[10px] font-mono text-text-muted w-4">#{i + 1}</span>
                    <div className="flex-1">
                      <p className="text-xs text-text-secondary">{s.name}</p>
                    </div>
                    <DelayBar value={s.delay} />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Live Train Feed */}
          <div className="card-p">
            <div className="flex items-center justify-between mb-4">
              <SectionHeader title="Live Trains" />
              <LiveTicker tick={tick} />
            </div>
            <div className="space-y-0 divide-y divide-bg-border max-h-60 overflow-y-auto">
              {trains.slice(0, 12).map((t) => (
                <div key={t.number} className="flex items-center gap-3 py-2">
                  <StatusDot status={t.status} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-text-secondary truncate">{t.name}</p>
                    <p className="text-[10px] font-mono text-text-muted">{t.from_name} → {t.to_name}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className={cn('text-xs font-mono font-semibold', delayColor(t.delay))}>
                      {t.delay < 5 ? 'ON TIME' : `+${t.delay.toFixed(0)}m`}
                    </p>
                  </div>
                </div>
              ))}
              {trains.length === 0 && <Skeleton className="h-40" />}
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
