import { type ReactNode } from 'react'
import { cn, delayBarColor, congestionBarColor, congestionLabel, congestionColor } from '../../utils/helpers'

// ─── Skeleton ─────────────────────────────────────────────────────────────────
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton', className)} />
}

// ─── Section Header ───────────────────────────────────────────────────────────
interface SectionHeaderProps {
  title: string
  sub?: string
  right?: ReactNode
}
export function SectionHeader({ title, sub, right }: SectionHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-5">
      <div>
        <h2 className="text-sm font-display font-semibold text-text-primary">{title}</h2>
        {sub && <p className="text-xs text-text-muted mt-0.5 font-body">{sub}</p>}
      </div>
      {right && <div>{right}</div>}
    </div>
  )
}

// ─── Live Ticker ─────────────────────────────────────────────────────────────
export function LiveTicker({ tick }: { tick: number }) {
  return (
    <div className="flex items-center gap-1.5 text-[10px] font-mono text-text-muted">
      <span className="live-dot" />
      T{tick}
    </div>
  )
}

// ─── Status Dot ───────────────────────────────────────────────────────────────
export function StatusDot({ status }: { status: string }) {
  const cls = {
    ON_TIME:      'bg-rail-green',
    SLIGHTLY_LATE:'bg-rail-amber',
    LATE:         'bg-rail-red',
    VERY_LATE:    'bg-rail-red animate-pulse',
    LIVE:         'bg-rail-green animate-pulse',
    OFFLINE:      'bg-text-muted',
  }[status] ?? 'bg-text-muted'
  return <span className={cn('inline-block w-2 h-2 rounded-full shrink-0', cls)} />
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────
interface KpiCardProps {
  label: string
  value: ReactNode
  sub?: string
  color?: 'cyan' | 'green' | 'amber' | 'red' | 'purple'
  icon?: ReactNode
  live?: boolean
}
const KPI_COLORS = {
  cyan:   'text-rail-cyan',
  green:  'text-rail-green',
  amber:  'text-rail-amber',
  red:    'text-rail-red',
  purple: 'text-rail-purple',
}
export function KpiCard({ label, value, sub, color = 'cyan', icon, live }: KpiCardProps) {
  return (
    <div className="card-p flex flex-col gap-3 animate-[fadeIn_0.3s_ease-out] relative overflow-hidden group">
      {/* subtle grid bg */}
      <div className="absolute inset-0 grid-bg opacity-30 pointer-events-none" />
      <div className="flex items-center justify-between relative">
        <span className="label">{label}</span>
        <div className="flex items-center gap-2">
          {live && <span className="live-dot" />}
          {icon && <span className="text-text-muted">{icon}</span>}
        </div>
      </div>
      <div className={cn('text-3xl font-display font-bold tabular-nums relative', KPI_COLORS[color])}>
        {value}
      </div>
      {sub && <p className="text-xs text-text-muted font-body relative">{sub}</p>}
    </div>
  )
}

// ─── Delay Bar ────────────────────────────────────────────────────────────────
export function DelayBar({ value, max = 60 }: { value: number; max?: number }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex-1 h-1 bg-bg-elevated rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-700', delayBarColor(value))}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn('text-[11px] font-mono w-12 text-right tabular-nums', delayBarColor(value))}>
        {value.toFixed(1)}m
      </span>
    </div>
  )
}

// ─── Congestion Bar ───────────────────────────────────────────────────────────
export function CongestionBar({ value }: { value: number }) {
  const pct = Math.min(100, value * 100)
  const label = congestionLabel(value)
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex-1 h-1 bg-bg-elevated rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-700', congestionBarColor(value))}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn('text-[10px] font-mono w-14 text-right', congestionColor(value))}>
        {label}
      </span>
    </div>
  )
}

// ─── Incident Badge ───────────────────────────────────────────────────────────
export function IncidentBadge({ severity }: { severity: string }) {
  const cls = severity === 'MAJOR' ? 'pill-red' : severity === 'MODERATE' ? 'pill-amber' : 'pill-cyan'
  return <span className={cn('pill', cls)}>{severity}</span>
}

// ─── Empty State ──────────────────────────────────────────────────────────────
export function EmptyState({ message = 'No data' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-text-muted gap-2">
      <div className="w-8 h-8 rounded-full border border-bg-border flex items-center justify-center text-text-muted text-sm">○</div>
      <p className="text-sm font-body">{message}</p>
    </div>
  )
}

// ─── Chart Tooltip ────────────────────────────────────────────────────────────
interface ChartTooltipProps {
  active?: boolean
  payload?: Array<{ value: number; name: string; color: string }>
  label?: string | number
  labelFormat?: (l: string | number) => string
  valueFormat?: (v: number) => string
}
export function ChartTooltip({ active, payload, label, labelFormat, valueFormat }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-bg-elevated border border-bg-border rounded-xl px-3 py-2.5 text-xs shadow-xl">
      {label != null && (
        <p className="text-text-muted font-mono mb-1.5">{labelFormat ? labelFormat(label) : label}</p>
      )}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="font-mono">
          {p.name}: <span className="font-semibold">{valueFormat ? valueFormat(p.value) : p.value}</span>
        </p>
      ))}
    </div>
  )
}
