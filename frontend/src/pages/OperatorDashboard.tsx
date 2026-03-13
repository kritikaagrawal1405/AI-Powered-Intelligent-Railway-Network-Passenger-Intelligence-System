import { useQuery } from '@tanstack/react-query'
import { apiEndpoints } from '../lib/api'
import { useLiveStore } from '../store/liveStore'
import { KpiCard, LiveTicker, Skeleton, SectionHeader, DelayBar } from '../components/ui'
import Navbar from '../components/navbar/Navbar'
import { HorizontalBarChart } from '../components/charts'
import { cn } from '../utils/helpers'
import { OperatorAgentCard } from '../components/agent/OperatorAgentCard'
import {
  Activity, AlertOctagon, AlertTriangle, ShieldAlert,
  Train, Network, Zap, CheckCircle, Users
} from 'lucide-react'

const PRIORITY_CFG: Record<string, { bg: string; border: string; text: string; icon: React.ElementType }> = {
  CRITICAL: { bg: 'bg-rail-red/10',   border: 'border-rail-red/40',   text: 'text-rail-red',   icon: AlertOctagon  },
  HIGH:     { bg: 'bg-rail-amber/10', border: 'border-rail-amber/30', text: 'text-rail-amber', icon: AlertTriangle },
  MEDIUM:   { bg: 'bg-rail-cyan/10',  border: 'border-rail-cyan/20',  text: 'text-rail-cyan',  icon: ShieldAlert   },
  LOW:      { bg: 'bg-bg-elevated',   border: 'border-bg-border',     text: 'text-text-muted', icon: Zap           },
}

const ZONE_STATUS_COLOR: Record<string, string> = {
  CRITICAL: 'text-rail-red',
  WARNING:  'text-rail-amber',
  NOMINAL:  'text-rail-green',
}

export default function OperatorDashboard() {
  const { tick, incidents, trains } = useLiveStore()

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-operator', Math.floor(tick / 15)],
    queryFn: () => apiEndpoints.operatorDashboard().then((r) => r.data),
    staleTime: 20_000,
    refetchInterval: 30_000,
  })

  const kpis         = data?.kpis
  const zones        = data?.zone_performance ?? []
  const cascadeRisk  = data?.cascade_risk ?? []
  const trainsStatus = data?.trains_status
  const recommendations = data?.recommendations ?? []
  const cascadeEvents   = data?.cascade_events ?? []
  const capacity        = data?.capacity_by_zone ?? {}

  const fallbackRecs: string[] = []

  if (!isLoading && recommendations.length === 0) {
    const hotspotZones = zones
      .slice()
      .sort((a: any, b: any) => b.avg_delay - a.avg_delay)
      .slice(0, 3)
      .map((z: any) => z.zone)
    const incidentNames = incidents.slice(0, 3).map((i: any) => i.station_name)

    if (incidentNames.length) {
      fallbackRecs.push(
        `Stabilise operations around current incidents at ${incidentNames.join(
          ', ',
        )} with stronger platform control and clear passenger announcements.`,
      )
    }
    if (hotspotZones.length) {
      fallbackRecs.push(
        `Treat zones ${hotspotZones.join(
          ', ',
        )} as primary hotspots for the next hour — reduce non‑essential overtakes and prioritise through‑trains there.`,
      )
    }
    if (trainsStatus) {
      const late =
        (trainsStatus.late as number | undefined) ?? 0 +
        ((trainsStatus.very_late as number | undefined) ?? 0)
      if (late > 0) {
        fallbackRecs.push(
          `Create a short recovery window by holding back new maintenance slots and using spare rakes to absorb the ${late} late/very‑late trains.`,
        )
      }
    }
    if (cascadeRisk.length) {
      fallbackRecs.push(
        `At high cascade‑risk junctions, enforce tight dispatch discipline and avoid long dwell times on junction platforms to prevent delay propagation.`,
      )
    }
    if (!fallbackRecs.length) {
      fallbackRecs.push(
        'No critical AI alerts at the moment — monitor live KPIs and be ready to apply the congestion playbook when incidents spike.',
      )
    }
  }

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Operator Dashboard" />
      <div className="flex-1 overflow-y-auto p-6 space-y-5 grid-bg">

        {/* Persona tag */}
        <div className="flex items-center gap-2">
          <span className="pill pill-purple">OPERATOR VIEW</span>
          <span className="text-[10px] font-mono text-text-muted">
            Network operations control · Real-time management
          </span>
        </div>

        {/* Ops KPIs */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          <KpiCard
            label="Active Incidents" live
            value={incidents.length}
            sub={incidents.length === 0 ? 'Network nominal' : 'Immediate action required'}
            color={incidents.length > 0 ? 'red' : 'green'}
            icon={<AlertTriangle size={13} />}
          />
          <KpiCard
            label="Network Health" live
            value={`${kpis?.network_health_pct ?? '—'}%`}
            sub="Based on live congestion"
            color={!kpis || kpis.network_health_pct > 70 ? 'green' : 'amber'}
            icon={<Activity size={13} />}
          />
          <KpiCard
            label="Trains On Time" live
            value={`${kpis?.trains_on_time_pct ?? '—'}%`}
            sub={trainsStatus ? `${trainsStatus.late + trainsStatus.very_late} trains delayed` : ''}
            color={!kpis || kpis.trains_on_time_pct > 75 ? 'green' : 'amber'}
            icon={<Train size={13} />}
          />
          <KpiCard
            label="Cascade Risk Nodes"
            value={kpis?.cascade_risk_count ?? '—'}
            sub="Critical junctions · High betweenness"
            color="purple"
            icon={<Network size={13} />}
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* Operator Recommendations */}
          <div className="card-p col-span-2">
            <SectionHeader title="Action Required" sub="AI-derived operational recommendations" right={<LiveTicker tick={tick} />} />
            <div className="space-y-2">
              {isLoading && <Skeleton className="h-16" />}
              {recommendations.map((rec: any, i: number) => {
                const cfg = PRIORITY_CFG[rec.priority] ?? PRIORITY_CFG.LOW
                const Icon = cfg.icon
                return (
                  <div key={i} className={cn(
                    'flex items-start gap-3 rounded-xl border px-4 py-3 animate-[fadeIn_0.3s_ease-out]',
                    cfg.bg, cfg.border
                  )}>
                    <Icon size={13} className={cn('shrink-0 mt-0.5', cfg.text)} />
                    <div className="flex-1">
                      <p className={cn('text-xs font-body', cfg.text)}>{rec.message}</p>
                    </div>
                    <span className={cn('pill shrink-0 self-start', ({
                      CRITICAL: 'pill-red', HIGH: 'pill-amber', MEDIUM: 'pill-cyan', LOW: 'pill-purple'
                    } as Record<string, string>)[rec.priority as string] ?? 'pill-cyan')}>{rec.action}</span>
                  </div>
                )
              })}
              {!isLoading && recommendations.length === 0 && fallbackRecs.map((msg, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 rounded-xl border px-4 py-3 bg-bg-elevated border-bg-border/80 text-xs font-body text-text-secondary"
                >
                  <span className="mt-0.5 text-[9px] font-mono text-text-muted">#{i + 1}</span>
                  <p>{msg}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Operator agent */}
          <OperatorAgentCard
            networkHealthPct={kpis?.network_health_pct}
            trainsOnTimePct={kpis?.trains_on_time_pct}
            cascadeRiskCount={kpis?.cascade_risk_count}
            incidents={incidents as any}
            zones={zones as any}
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* Train Status Summary */}
          <div className="card-p">
            <SectionHeader title="Fleet Status" />
            {trainsStatus ? (
              <div className="space-y-3 mt-2">
                {[
                  { key: 'on_time',      label: 'On Time',       color: 'bg-rail-green', text: 'text-rail-green'  },
                  { key: 'slight_delay', label: 'Slight Delay',  color: 'bg-rail-amber', text: 'text-rail-amber'  },
                  { key: 'late',         label: 'Late (>15m)',    color: 'bg-rail-red',   text: 'text-rail-red'    },
                  { key: 'very_late',    label: 'Very Late (>45m)',color: 'bg-rail-red animate-pulse', text: 'text-rail-red' },
                ].map(({ key, label, color, text }) => {
                  const count = (trainsStatus as any)[key] as number
                  const pct   = trains.length ? Math.round((count / trains.length) * 100) : 0
                  return (
                    <div key={key}>
                      <div className="flex justify-between text-[11px] font-mono mb-1">
                        <span className="text-text-muted">{label}</span>
                        <span className={text}>{count} <span className="text-text-muted">({pct}%)</span></span>
                      </div>
                      <div className="h-1.5 bg-bg-elevated rounded-full overflow-hidden">
                        <div className={cn('h-full rounded-full transition-all duration-700', color)}
                          style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : <Skeleton className="h-36" />}

            {/* Live cascade events */}
            {cascadeEvents.length > 0 && (
              <div className="mt-4 pt-3 border-t border-bg-border">
                <p className="label mb-2">Active Cascade</p>
                {cascadeEvents.slice(0, 4).map((e: any, i: number) => (
                  <div key={i} className="flex justify-between text-[10px] font-mono py-1 border-b border-bg-border/50">
                    <span className="text-text-muted">{e.station}</span>
                    <span className="text-rail-amber">+{e.added}m propagated</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Zone Performance */}
          <div className="card-p col-span-2">
            <SectionHeader title="Zone Performance" sub="Live aggregated delay by zone" right={<LiveTicker tick={tick} />} />
            {isLoading ? <Skeleton className="h-52" /> : (
              <>
                <HorizontalBarChart
                  data={zones.slice(0, 10)}
                  dataKey="avg_delay"
                  labelKey="zone"
                  height={180}
                  colorFn={(e) => (e.avg_delay as number) > 20 ? '#ff4757' : (e.avg_delay as number) > 10 ? '#ffb347' : '#00ff87'}
                />
                <div className="grid grid-cols-4 gap-2 mt-3 text-[10px] font-mono">
                  {zones.slice(0, 4).map((z: any) => (
                    <div key={z.zone} className={cn(
                      'rounded-xl border px-2.5 py-2 text-center',
                      z.status === 'CRITICAL' ? 'bg-rail-red/10 border-rail-red/30' :
                      z.status === 'WARNING'  ? 'bg-rail-amber/10 border-rail-amber/30' :
                      'bg-bg-elevated border-bg-border'
                    )}>
                      <p className="font-bold text-text-primary">{z.zone}</p>
                      <p className={cn(ZONE_STATUS_COLOR[z.status] ?? 'text-text-muted')}>{z.status}</p>
                      <p className="text-text-muted mt-0.5">{z.avg_delay.toFixed(1)}m avg</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Cascade Risk Table + Capacity */}
        <div className="grid grid-cols-2 gap-4">
          <div className="card-p">
            <SectionHeader title="Critical Node Risk" sub="Stations where disruption cascades farthest" />
            {isLoading ? <Skeleton className="h-64" /> : (
              <div className="space-y-2">
                {cascadeRisk.map((s: any, i: number) => (
                  <div key={s.station_code}
                    className={cn('rounded-xl border p-3 flex items-center gap-3 animate-[fadeIn_0.3s_ease-out]',
                      s.risk_level === 'CRITICAL' ? 'bg-rail-red/5 border-rail-red/25' :
                      s.risk_level === 'HIGH'     ? 'bg-rail-amber/5 border-rail-amber/25' :
                      'bg-bg-elevated border-bg-border'
                    )}>
                    <span className="text-[10px] font-mono text-text-muted w-5">#{i+1}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-semibold text-text-primary">{s.station_name}</p>
                        <span className={cn('text-[9px] font-mono',
                          s.risk_level === 'CRITICAL' ? 'text-rail-red' : s.risk_level === 'HIGH' ? 'text-rail-amber' : 'text-rail-cyan'
                        )}>{s.risk_level}</span>
                      </div>
                      <div className="flex gap-3 text-[10px] font-mono text-text-muted mt-0.5">
                        <span>btw={s.betweenness.toFixed(3)}</span>
                        <span>↓{s.downstream_count} nodes</span>
                      </div>
                    </div>
                    <DelayBar value={s.live_delay} />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Zone Capacity Utilization */}
          <div className="card-p">
            <SectionHeader title="Capacity by Zone" sub="Live congestion-based utilization %" />
            {isLoading ? <Skeleton className="h-64" /> : (
              <div className="space-y-2.5">
                {Object.entries(capacity as Record<string, number>).map(([zone, pct]) => (
                  <div key={zone}>
                    <div className="flex justify-between text-[11px] font-mono mb-1">
                      <span className="text-text-secondary font-semibold">{zone}</span>
                      <span className={cn(pct > 80 ? 'text-rail-red' : pct > 60 ? 'text-rail-amber' : 'text-rail-green')}>
                        {pct}%
                      </span>
                    </div>
                    <div className="h-2 bg-bg-elevated rounded-full overflow-hidden">
                      <div
                        className={cn('h-full rounded-full transition-all duration-700',
                          pct > 80 ? 'bg-rail-red' : pct > 60 ? 'bg-rail-amber' : 'bg-rail-green'
                        )}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Incidents for ops */}
            {incidents.length > 0 && (
              <div className="mt-4 pt-4 border-t border-bg-border">
                <p className="label mb-2">Active Incidents</p>
                {incidents.map((inc: any) => (
                  <div key={inc.id} className="flex items-center gap-2 py-1.5 border-b border-bg-border/50">
                    <span className={cn('w-1.5 h-1.5 rounded-full shrink-0',
                      inc.severity === 'MAJOR' ? 'bg-rail-red animate-pulse' :
                      inc.severity === 'MODERATE' ? 'bg-rail-amber' : 'bg-rail-cyan'
                    )} />
                    <span className="text-[11px] text-text-secondary flex-1 truncate">{inc.station_name}</span>
                    <span className="text-[10px] font-mono text-rail-red shrink-0">+{inc.delay_added}m</span>
                    <span className="text-[9px] font-mono text-text-muted shrink-0">TTL:{inc.ttl}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
