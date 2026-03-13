import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, Cell,
  ReferenceLine,
} from 'recharts'
import { ChartTooltip } from '../ui'

// ─── Area Chart ───────────────────────────────────────────────────────────────
interface AreaProps {
  data: any[]
  dataKey: string
  xKey: string
  color?: string
  gradientId?: string
  height?: number
  xFormatter?: (v: unknown) => string
  yFormatter?: (v: number) => string
  tooltipFormatter?: (v: number) => string
  referenceLine?: number
}

export function StyledAreaChart({
  data, dataKey, xKey, color = '#00d4ff', gradientId = 'areaGrad',
  height = 180, xFormatter, yFormatter, tooltipFormatter, referenceLine,
}: AreaProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={color} stopOpacity={0.25} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1a2d47" vertical={false} />
        <XAxis
          dataKey={xKey}
          tick={{ fill: '#4a6080', fontSize: 10, fontFamily: 'IBM Plex Mono' }}
          tickFormatter={xFormatter as (v: unknown) => string}
          axisLine={false} tickLine={false} interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fill: '#4a6080', fontSize: 10 }}
          tickFormatter={yFormatter}
          axisLine={false} tickLine={false} width={32}
        />
        <Tooltip content={<ChartTooltip valueFormat={tooltipFormatter} labelFormat={xFormatter} />} />
        {referenceLine && (
          <ReferenceLine y={referenceLine} stroke="#1a2d47" strokeDasharray="4 4" />
        )}
        <Area
          type="monotone" dataKey={dataKey} stroke={color}
          strokeWidth={2} fill={`url(#${gradientId})`} dot={false} activeDot={{ r: 4, fill: color }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

// ─── Bar Chart ────────────────────────────────────────────────────────────────
interface BarProps {
  data: any[]
  dataKey: string
  xKey: string
  color?: string
  height?: number
  barSize?: number
  xFormatter?: (v: unknown) => string
  tooltipFormatter?: (v: number) => string
  cellColors?: string[]
}

export function StyledBarChart({
  data, dataKey, xKey, color = '#00d4ff', height = 180,
  barSize = 24, xFormatter, tooltipFormatter, cellColors,
}: BarProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} barSize={barSize} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1a2d47" vertical={false} />
        <XAxis
          dataKey={xKey}
          tick={{ fill: '#4a6080', fontSize: 10, fontFamily: 'IBM Plex Mono' }}
          tickFormatter={xFormatter as (v: unknown) => string}
          axisLine={false} tickLine={false}
        />
        <YAxis tick={{ fill: '#4a6080', fontSize: 10 }} axisLine={false} tickLine={false} width={32} />
        <Tooltip content={<ChartTooltip valueFormat={tooltipFormatter} labelFormat={xFormatter} />} />
        <Bar dataKey={dataKey} radius={[4, 4, 0, 0]}>
          {cellColors
            ? data.map((_, i) => <Cell key={i} fill={cellColors[i % cellColors.length]} />)
            : <Cell fill={color} />
          }
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ─── Horizontal Bar Chart ─────────────────────────────────────────────────────
interface HBarProps {
  data: any[]
  dataKey: string
  labelKey: string
  height?: number
  colorFn?: (entry: any) => string
}

export function HorizontalBarChart({ data, dataKey, labelKey, height = 200, colorFn }: HBarProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" barSize={14} margin={{ top: 0, right: 20, bottom: 0, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1a2d47" horizontal={false} />
        <XAxis type="number" tick={{ fill: '#4a6080', fontSize: 10 }} axisLine={false} tickLine={false} />
        <YAxis
          type="category" dataKey={labelKey}
          tick={{ fill: '#8ba3bc', fontSize: 10, fontFamily: 'IBM Plex Mono' }}
          axisLine={false} tickLine={false} width={36}
        />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey={dataKey} radius={[0, 4, 4, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={colorFn ? colorFn(entry) : '#00d4ff'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ─── Radar Chart ──────────────────────────────────────────────────────────────
interface RadarProps {
  data: any[]
  angleKey: string
  series: Array<{ key: string; color: string; name: string }>
  height?: number
}

export function StyledRadarChart({ data, angleKey, series, height = 280 }: RadarProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data}>
        <PolarGrid stroke="#1a2d47" />
        <PolarAngleAxis
          dataKey={angleKey}
          tick={{ fill: '#8ba3bc', fontSize: 10, fontFamily: 'IBM Plex Mono' }}
        />
        {series.map((s) => (
          <Radar
            key={s.key} name={s.name} dataKey={s.key}
            stroke={s.color} fill={s.color} fillOpacity={0.12}
          />
        ))}
        <Tooltip
          contentStyle={{ background: '#0a1628', border: '1px solid #1a2d47', borderRadius: 12, fontSize: 11 }}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}

// ─── Sparkline ────────────────────────────────────────────────────────────────
export function Sparkline({ data, color = '#00d4ff', height = 48 }: { data: number[]; color?: string; height?: number }) {
  const chartData = data.map((v, i) => ({ i, v }))
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
