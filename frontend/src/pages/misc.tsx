import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { apiEndpoints } from '../lib/api'
import { useLiveStore } from '../store/liveStore'
import Navbar from '../components/navbar/Navbar'
import { SectionHeader, LiveTicker, Skeleton, CongestionBar, DelayBar } from '../components/ui'
import { StyledBarChart, HorizontalBarChart } from '../components/charts'
import { cn, delayColor } from '../utils/helpers'
import { ArrowRight, Zap, Wind, CheckCircle, Send, Bot, User } from 'lucide-react'
import type { AssistantResponse } from '../types'

// ─── STATIONS LIST ──────────────────────────────────────────────────────────
const STATION_OPTS = [
  ['NDLS','New Delhi'],['CSTM','Mumbai CST'],['HWH','Howrah'],['MAS','Chennai Central'],
  ['SBC','Bangalore City'],['PUNE','Pune'],['ADI','Ahmedabad'],['BPL','Bhopal'],
  ['LKO','Lucknow'],['VSKP','Visakhapatnam'],['PNBE','Patna'],['HYB','Hyderabad'],
  ['TVC','Trivandrum'],['GHY','Guwahati'],['CNB','Kanpur'],['NZM','Hazrat Nizamuddin'],
  ['NGP','Nagpur'],['AGC','Agra Cantt'],['JP','Jaipur'],['INDB','Indore'],
]

// ═══════════════════════════════════════════════════════════════════════════
// ROUTES PAGE
// ═══════════════════════════════════════════════════════════════════════════

const TYPE_CFG = {
  FASTEST:         { icon: Zap,  color: 'text-rail-cyan',   border: 'border-rail-cyan/30',   bg: 'bg-rail-cyan/5'  },
  LEAST_CONGESTED: { icon: Wind, color: 'text-rail-green',  border: 'border-rail-green/30',  bg: 'bg-rail-green/5' },
}

export function Routes() {
  const [src, setSrc] = useState('NDLS')
  const [dst, setDst] = useState('MAS')
  const [enabled, setEnabled] = useState(false)
  const { tick } = useLiveStore()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['routes', src, dst, Math.floor(tick / 20)],
    queryFn: () => apiEndpoints.routes(src, dst).then((r) => r.data),
    enabled,
    staleTime: 25_000,
  })

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Route Optimizer" />
      <div className="flex-1 overflow-y-auto p-6 space-y-5 grid-bg">

        <div className="card-p flex items-end gap-3 flex-wrap">
          {[
            { lbl: 'From', val: src, setter: setSrc },
            { lbl: 'To', val: dst, setter: setDst },
          ].map(({ lbl, val, setter }) => (
            <div key={lbl}>
              <p className="label mb-1.5">{lbl}</p>
              <select value={val} onChange={(e) => setter(e.target.value)} className="select w-52">
                {STATION_OPTS.map(([c, n]) => <option key={c} value={c}>{n} ({c})</option>)}
              </select>
            </div>
          ))}
          <button
            onClick={() => { setEnabled(true); refetch() }}
            disabled={isLoading || src === dst}
            className="btn-primary flex items-center gap-2"
          >
            <Zap size={14} />
            {isLoading ? 'Routing...' : 'Find Routes'}
          </button>
          <LiveTicker tick={tick} />
        </div>

        {(data?.routes ?? []).map((route) => {
          const cfg = TYPE_CFG[route.type] ?? TYPE_CFG.FASTEST
          const Icon = cfg.icon
          return (
            <div key={route.rank} className={cn('card-p border', cfg.border, cfg.bg, 'animate-[fadeIn_0.3s_ease-out]')}>
              <div className="flex items-start justify-between mb-4 flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <Icon size={15} className={cfg.color} />
                  <span className={cn('text-sm font-display font-semibold', cfg.color)}>
                    Route #{route.rank} — {route.type.replace('_',' ')}
                  </span>
                  {route.recommended && (
                    <span className="flex items-center gap-1 text-[10px] font-mono text-rail-green bg-rail-green/10 border border-rail-green/20 px-2 py-0.5 rounded-full">
                      <CheckCircle size={9} /> RECOMMENDED
                    </span>
                  )}
                </div>
                <div className="flex gap-4 text-xs font-mono text-text-muted">
                  <span>{route.total_distance_km} km</span>
                  <span>{Math.floor(route.total_time_mins / 60)}h {route.total_time_mins % 60}m</span>
                </div>
              </div>

              {/* Path */}
              <div className="flex items-center gap-1 flex-wrap mb-4">
                {route.path_names.map((name, i) => (
                  <div key={i} className="flex items-center gap-1">
                    <div className="bg-bg-elevated border border-bg-border rounded-xl px-2.5 py-1.5 text-xs text-text-secondary">
                      {name.split(' ')[0]}
                      <span className="text-text-muted ml-1 font-mono text-[9px]">{route.path[i]}</span>
                    </div>
                    {i < route.path_names.length - 1 && <ArrowRight size={11} className="text-text-muted shrink-0" />}
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div><p className="label mb-1.5">Avg Delay</p><DelayBar value={route.avg_delay} /></div>
                <div><p className="label mb-1.5">Avg Congestion</p><CongestionBar value={route.avg_congestion} /></div>
              </div>
            </div>
          )
        })}

        {enabled && !isLoading && !data?.routes?.length && (
          <div className="card-p text-center text-text-muted py-12 text-sm font-body">
            No route found between {src} and {dst}
          </div>
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// AI ASSISTANT PAGE
// ═══════════════════════════════════════════════════════════════════════════

interface Message {
  role: 'user' | 'assistant'
  text: string
  intent?: string
  tick?: number
}

const QUICK_Q = [
  'Which stations have the most delays?',
  'Most congested stations right now?',
  'Most vulnerable nodes?',
  'How to improve waitlist confirmation?',
  'Any active incidents?',
]

const INTENT_COLOR: Record<string, string> = {
  delay: 'text-rail-amber', congestion: 'text-rail-red',
  ticket: 'text-rail-cyan', vulnerability: 'text-rail-purple', general: 'text-text-muted',
}

export function Assistant() {
  const { tick, systemDelay, incidents } = useLiveStore()
  const [msgs, setMsgs] = useState<Message[]>([{
    role: 'assistant',
    text: `RailIQ AI online — live network state loaded. I have real-time access to all 40 stations, 20 trains, delay forecasts, cascade models, and congestion heatmaps. Ask me anything.`,
    intent: 'general', tick: 0,
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  async function send(q = input) {
    if (!q.trim() || loading) return
    setMsgs((m) => [...m, { role: 'user', text: q }])
    setInput('')
    setLoading(true)
    try {
      const { data } = await apiEndpoints.assistant(q)
      setMsgs((m) => [...m, { role: 'assistant', text: data.response, intent: data.intent, tick: data.tick }])
    } catch {
      setMsgs((m) => [...m, { role: 'assistant', text: 'Network error — is the backend running?', intent: 'general', tick }])
    }
    setLoading(false)
  }

  return (
    <div className="flex flex-col h-full">
      <Navbar title="AI Assistant" />
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col">

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {msgs.map((m, i) => (
              <div key={i} className={cn('flex gap-3 animate-[fadeIn_0.3s_ease-out]', m.role === 'user' ? 'flex-row-reverse' : '')}>
                <div className={cn('w-7 h-7 rounded-xl flex items-center justify-center shrink-0',
                  m.role === 'user' ? 'bg-rail-cyan/15 border border-rail-cyan/30' : 'bg-bg-elevated border border-bg-border')}>
                  {m.role === 'user' ? <User size={12} className="text-rail-cyan" /> : <Bot size={12} className="text-text-muted" />}
                </div>
                <div className="flex flex-col gap-1 max-w-xl">
                  <div className={cn('rounded-2xl px-4 py-3 text-sm leading-relaxed font-body',
                    m.role === 'user'
                      ? 'bg-rail-cyan/10 border border-rail-cyan/20 text-text-primary rounded-tr-none'
                      : 'bg-bg-elevated border border-bg-border text-text-secondary rounded-tl-none'
                  )}>
                    {m.text}
                  </div>
                  {m.intent && m.intent !== 'general' && (
                    <span className={cn('text-[9px] font-mono self-start', INTENT_COLOR[m.intent])}>
                      INTENT: {m.intent.toUpperCase()} · T{m.tick}
                    </span>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-xl bg-bg-elevated border border-bg-border flex items-center justify-center">
                  <Bot size={12} className="text-text-muted" />
                </div>
                <div className="bg-bg-elevated border border-bg-border rounded-2xl rounded-tl-none px-4 py-3 flex gap-1">
                  {[0,1,2].map((i) => (
                    <span key={i} className="w-1.5 h-1.5 rounded-full bg-text-muted animate-pulse" style={{ animationDelay: `${i*150}ms` }} />
                  ))}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Quick suggestions */}
          <div className="px-6 pb-3 flex gap-2 flex-wrap">
            {QUICK_Q.map((q, i) => (
              <button key={i} onClick={() => send(q)}
                className="text-[10px] font-mono text-text-muted hover:text-rail-cyan border border-bg-border hover:border-rail-cyan/30 bg-bg-elevated rounded-full px-3 py-1.5 transition-all">
                {q}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="px-6 pb-6">
            <div className="flex gap-2 bg-bg-elevated border border-bg-border rounded-2xl p-2 focus-within:border-rail-cyan/40 transition-colors">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
                placeholder="Ask about delays, congestion, routes, ticket confirmation..."
                rows={2}
                className="flex-1 bg-transparent text-sm text-text-primary placeholder-text-muted resize-none focus:outline-none px-2 py-1 font-body"
              />
              <button onClick={() => send()} disabled={loading || !input.trim()}
                className="btn-primary self-end h-9 w-9 p-0 flex items-center justify-center">
                <Send size={13} />
              </button>
            </div>
            <div className="flex justify-between mt-1.5">
              <span className="text-[9px] font-mono text-text-muted">Enter to send · Shift+Enter for newline</span>
              <LiveTicker tick={tick} />
            </div>
          </div>
        </div>

        {/* Side panel */}
        <div className="w-52 border-l border-bg-border p-4 space-y-4 shrink-0 overflow-y-auto bg-bg-secondary">
          <div>
            <p className="label mb-3">Network State</p>
            <div className="space-y-2 text-[11px] font-mono">
              {[
                ['Avg Delay', `${systemDelay.toFixed(1)}m`, delayColor(systemDelay)],
                ['Incidents', incidents.length.toString(), incidents.length ? 'text-rail-red' : 'text-rail-green'],
                ['Tick', tick.toString(), 'text-text-secondary'],
              ].map(([k, v, c]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-text-muted">{k}</span>
                  <span className={c}>{v}</span>
                </div>
              ))}
            </div>
          </div>
          {incidents.map((inc) => (
            <div key={inc.id} className="bg-rail-red/10 border border-rail-red/20 rounded-xl p-3 text-[10px]">
              <p className="font-semibold text-text-primary mb-1">{inc.station_name}</p>
              <p className="text-text-muted">{inc.type}</p>
              <p className="font-mono text-rail-red mt-1">+{inc.delay_added}min</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// ANALYTICS PAGE
// ═══════════════════════════════════════════════════════════════════════════

const ZONE_COLORS = ['#00d4ff','#00ff87','#ffb347','#ff4757','#7c5cbf','#79c0ff','#56d364','#ffa657']

export function Analytics() {
  const { tick } = useLiveStore()
  const { data, isLoading } = useQuery({
    queryKey: ['zones', Math.floor(tick / 20)],
    queryFn: () => apiEndpoints.zones().then((r) => r.data),
    staleTime: 35_000,
    refetchInterval: 45_000,
  })

  const zones = data?.zones ?? []

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Zone Analytics" />
      <div className="flex-1 overflow-y-auto p-6 space-y-5 grid-bg">

        <div className="flex items-center justify-between">
          <p className="text-xs text-text-muted font-body">Live zone-level aggregated performance across Indian Railway zones</p>
          <LiveTicker tick={tick} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="card-p">
            <SectionHeader title="Avg Delay by Zone" sub="Live aggregated" />
            {isLoading ? <Skeleton className="h-52" /> : (
              <HorizontalBarChart
                data={zones} dataKey="avg_delay" labelKey="zone" height={200}
                colorFn={(e) => (e.avg_delay as number) > 20 ? '#ff4757' : (e.avg_delay as number) > 10 ? '#ffb347' : '#00ff87'}
              />
            )}
          </div>
          <div className="card-p">
            <SectionHeader title="Avg Congestion by Zone" sub="Live aggregated" />
            {isLoading ? <Skeleton className="h-52" /> : (
              <HorizontalBarChart
                data={zones.map((z) => ({ ...z, cong_pct: Math.round(z.avg_congestion * 100) }))}
                dataKey="cong_pct" labelKey="zone" height={200}
                colorFn={(e) => (e.avg_congestion as number) > 0.65 ? '#ff4757' : (e.avg_congestion as number) > 0.4 ? '#ffb347' : '#00ff87'}
              />
            )}
          </div>
        </div>

        {/* Table */}
        <div className="card-p">
          <SectionHeader title="Zone Performance Matrix" sub="Higher score = better performance" />
          {isLoading ? <Skeleton className="h-40" /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-bg-border">
                    {['Zone','Stations','Avg Delay','Congestion','Total Footfall','Score'].map((h) => (
                      <th key={h} className="text-left py-2.5 px-3 label">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {zones.map((z, i) => (
                    <tr key={z.zone} className="border-b border-bg-border/50 hover:bg-bg-elevated transition-colors">
                      <td className="py-2.5 px-3 font-mono font-semibold text-text-primary">{z.zone}</td>
                      <td className="py-2.5 px-3 text-text-secondary font-body">{z.station_count}</td>
                      <td className={cn('py-2.5 px-3 font-mono', z.avg_delay > 20 ? 'text-rail-red' : z.avg_delay > 10 ? 'text-rail-amber' : 'text-rail-green')}>
                        {z.avg_delay.toFixed(1)}m
                      </td>
                      <td className={cn('py-2.5 px-3 font-mono', z.avg_congestion > 0.65 ? 'text-rail-red' : z.avg_congestion > 0.4 ? 'text-rail-amber' : 'text-rail-green')}>
                        {(z.avg_congestion * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3 font-mono text-text-secondary">{(z.total_footfall / 1_000_000).toFixed(2)}M</td>
                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-20 h-1.5 bg-bg-elevated rounded-full overflow-hidden">
                            <div className="h-full bg-rail-green rounded-full" style={{ width: `${Math.max(0, Math.min(100, z.performance_score))}%` }} />
                          </div>
                          <span className="font-mono text-rail-green text-[10px]">{z.performance_score.toFixed(0)}</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
