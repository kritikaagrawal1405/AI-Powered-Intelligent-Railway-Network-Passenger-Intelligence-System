import { useQuery } from '@tanstack/react-query'
import { apiEndpoints } from '../lib/api'
import { useLiveStore } from '../store/liveStore'
import { KpiCard, StatusDot, DelayBar, IncidentBadge, Skeleton, LiveTicker, SectionHeader } from '../components/ui'
import Navbar from '../components/navbar/Navbar'
import { StyledBarChart } from '../components/charts'
import { Sparkline } from '../components/charts'
import { Train, Activity, Users, Clock } from 'lucide-react'
import { cn, delayColor, statusColor } from '../utils/helpers'

export default function Dashboard() {
  const { tick, systemDelay, congestedCount, incidents, trains, topDelays, stationDelays } = useLiveStore()

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard', Math.floor(tick / 15)],
    queryFn: () => apiEndpoints.passengerDashboard().then((r) => r.data),
    staleTime: 20_000,
    refetchInterval: 30_000,
  })

  const kpis = data?.kpis
  const forecast = data?.forecast_7d ?? []
  const onTimeCount = trains.filter((t) => t.status === 'ON_TIME').length
  const lateCount   = trains.filter((t) => ['LATE', 'VERY_LATE'].includes(t.status)).length

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Command Dashboard" />
      <div className="flex-1 overflow-y-auto p-6 space-y-5 grid-bg">

        {/* KPIs */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          <KpiCard
            label="Active Trains" live
            value={trains.length || kpis?.active_trains || '—'}
            sub={`${onTimeCount} on time · ${lateCount} late`}
            color="cyan" icon={<Train size={13} />}
          />
          <KpiCard
            label="Avg System Delay" live
            value={`${systemDelay.toFixed(1)}`}
            sub="minutes across network"
            color={systemDelay > 20 ? 'red' : systemDelay > 10 ? 'amber' : 'green'}
            icon={<Clock size={13} />}
          />
          <KpiCard
            label="Congested Stations" live
            value={congestedCount}
            sub={`of ${kpis?.total_stations ?? 40} total`}
            color={congestedCount > 10 ? 'red' : 'amber'}
            icon={<Users size={13} />}
          />
          <KpiCard
            label="Network Health"
            value={`${kpis?.network_health ?? '—'}%`}
            sub={incidents.length ? `${incidents.length} incident(s) active` : 'All systems nominal'}
            color={!kpis || kpis.network_health > 70 ? 'green' : 'amber'}
            icon={<Activity size={13} />}
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* Incidents */}
          <div className="card-p">
            <div className="flex items-center justify-between mb-4">
              <SectionHeader title="Active Incidents" />
              <LiveTicker tick={tick} />
            </div>
            {incidents.length === 0 ? (
              <div className="flex flex-col items-center py-10 gap-2 text-text-muted">
                <div className="w-8 h-8 rounded-full border border-rail-green/30 flex items-center justify-center">
                  <span className="text-rail-green text-xs">✓</span>
                </div>
                <p className="text-xs font-body">Network nominal</p>
              </div>
            ) : incidents.map((inc) => (
              <div key={inc.id} className="mb-3 bg-bg-elevated border border-rail-red/20 rounded-xl p-3 animate-[fadeIn_0.3s_ease-out]">
                <div className="flex items-start justify-between mb-1.5">
                  <p className="text-xs font-semibold text-text-primary">{inc.station_name}</p>
                  <IncidentBadge severity={inc.severity} />
                </div>
                <p className="text-[11px] text-text-muted">{inc.type}</p>
                <p className="text-[11px] font-mono text-rail-red mt-1">
                  +{inc.delay_added}min · {inc.ttl} ticks left
                </p>
              </div>
            ))}
          </div>

          {/* 7-Day Forecast */}
          <div className="card-p col-span-2">
            <SectionHeader title="7-Day Delay Forecast" sub="ML prediction blended with live state" />
            {isLoading ? (
              <Skeleton className="h-44" />
            ) : (
              <StyledBarChart
                data={forecast}
                dataKey="avg_delay"
                xKey="day"
                height={160}
                cellColors={forecast.map((d: any) => d.risk === 'HIGH' ? '#ff4757' : '#00d4ff')}
                tooltipFormatter={(v) => `${v.toFixed(1)}min avg delay`}
              />
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Top Delayed - LIVE */}
          <div className="card-p">
            <div className="flex items-center justify-between mb-4">
              <SectionHeader title="Top Delayed Stations" />
              <LiveTicker tick={tick} />
            </div>
            <div className="space-y-3">
              {topDelays.slice(0, 7).map((s) => (
                <div key={s.code} className="animate-[fadeIn_0.3s_ease-out]">
                  <div className="flex justify-between mb-1.5">
                    <span className="text-xs font-medium text-text-secondary">{s.name}</span>
                    <span className="text-[10px] font-mono text-text-muted">{s.code}</span>
                  </div>
                  <DelayBar value={s.delay} />
                </div>
              ))}
              {topDelays.length === 0 && <Skeleton className="h-36" />}
            </div>
          </div>

          {/* Live Train Feed */}
          <div className="card-p">
            <div className="flex items-center justify-between mb-4">
              <SectionHeader title="Live Train Feed" />
              <LiveTicker tick={tick} />
            </div>
            <div className="space-y-0 divide-y divide-bg-border max-h-72 overflow-y-auto">
              {trains.slice(0, 14).map((t) => (
                <div key={t.number} className="flex items-center gap-3 py-2">
                  <StatusDot status={t.status} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-text-secondary truncate">{t.name}</p>
                    <p className="text-[10px] font-mono text-text-muted truncate">{t.from_name} → {t.to_name}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className={cn('text-xs font-mono font-semibold', delayColor(t.delay))}>{t.delay.toFixed(0)}m</p>
                    <p className="text-[9px] text-text-muted">{Math.round(t.progress * 100)}%</p>
                  </div>
                </div>
              ))}
              {trains.length === 0 && <Skeleton className="h-52" />}
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
