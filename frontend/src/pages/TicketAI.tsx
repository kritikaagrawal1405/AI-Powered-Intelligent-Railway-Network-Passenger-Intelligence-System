import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiEndpoints } from '../lib/api'
import { useLiveStore } from '../store/liveStore'
import Navbar from '../components/navbar/Navbar'
import { LiveTicker } from '../components/ui'
import { cn, delayColor } from '../utils/helpers'
import type { TicketRequest, TicketPrediction } from '../types'
import { Ticket, Zap, CheckCircle, AlertTriangle } from 'lucide-react'

const TRAINS = [
  ['12301','Howrah Rajdhani'],['12302','New Delhi Rajdhani'],['12951','Mumbai Rajdhani'],
  ['12952','NZM-Mumbai Rajdhani'],['12011','Kalka Shatabdi'],['12013','Amritsar Shatabdi'],
  ['12019','Howrah Shatabdi'],['12213','Duronto Express'],['12261','Mumbai Duronto'],
  ['12269','Chennai Duronto'],['11019','Kochi Express'],['22627','Tamil Nadu SF'],
  ['16526','Island Express'],['22119','Mumbai CSMT SF'],['11077','Jhelum Express'],
]
const CLASSES = ['1A','2A','3A','SL','CC','EC','2S']
const STATIONS = [
  ['NDLS','New Delhi'],['CSTM','Mumbai CST'],['HWH','Howrah'],['MAS','Chennai Central'],
  ['SBC','Bangalore City'],['PUNE','Pune'],['ADI','Ahmedabad'],['BPL','Bhopal'],
  ['LKO','Lucknow'],['VSKP','Visakhapatnam'],['PNBE','Patna'],['HYB','Hyderabad'],
  ['TVC','Trivandrum'],['GHY','Guwahati'],['CNB','Kanpur'],['NZM','Hazrat Nizamuddin'],
]
const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
const DAYS = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']

function SemiGauge({ pct }: { pct: number | null }) {
  if (pct === null) return (
    <div className="flex items-center justify-center h-44 text-text-muted text-sm font-body">
      Fill the form to predict
    </div>
  )
  const r = 72, strokeW = 9
  const circ = Math.PI * r
  const progress = (pct / 100) * circ
  const color = pct > 70 ? '#00ff87' : pct > 40 ? '#ffb347' : '#ff4757'
  const label = pct > 70 ? 'LIKELY CONFIRMED' : pct > 40 ? 'UNCERTAIN' : 'HIGH RISK'

  return (
    <div className="flex flex-col items-center py-4 gap-2">
      <svg width="190" height="104" viewBox="0 0 190 104">
        <path d="M 19 95 A 76 76 0 0 1 171 95" fill="none" stroke="#1a2d47" strokeWidth={strokeW} strokeLinecap="round" />
        <path d="M 19 95 A 76 76 0 0 1 171 95" fill="none" stroke={color} strokeWidth={strokeW}
          strokeLinecap="round"
          strokeDasharray={`${progress} ${circ}`}
          style={{ transition: 'stroke-dasharray 0.8s cubic-bezier(0.16,1,0.3,1), stroke 0.4s ease' }}
        />
        <text x="95" y="82" textAnchor="middle" fill={color} fontSize="30" fontFamily="Syne" fontWeight="700">{pct}%</text>
      </svg>
      <p className="text-xs font-mono font-bold" style={{ color }}>{label}</p>
    </div>
  )
}

export default function TicketAI() {
  const { tick, stationDelays } = useLiveStore()
  const now = new Date()
  const [form, setForm] = useState<TicketRequest>({
    train_number: '12301', travel_class: '3A',
    source_station: 'NDLS', dest_station: 'HWH',
    days_advance: 45, month: now.getMonth() + 1,
    day_of_week: now.getDay(), wl_number: 0,
  })

  const mutation = useMutation({
    mutationFn: (data: TicketRequest) => apiEndpoints.ticketPredict(data).then((r) => r.data),
  })

  const result: TicketPrediction | undefined = mutation.data
  const liveDelay = stationDelays[form.source_station] ?? 0

  function set<K extends keyof TicketRequest>(k: K, v: TicketRequest[K]) {
    setForm((p) => ({ ...p, [k]: v }))
  }

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Ticket AI" />
      <div className="flex-1 overflow-y-auto p-6 grid-bg">
        <div className="grid grid-cols-5 gap-5">

          {/* Form */}
          <div className="col-span-2 card-p space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-display font-semibold text-text-primary">Journey Details</h3>
              <LiveTicker tick={tick} />
            </div>

            {([
              { label: 'Train', key: 'train_number' as const, opts: TRAINS },
              { label: 'Travel Class', key: 'travel_class' as const, opts: CLASSES.map((c) => [c, c]) },
              { label: 'From Station', key: 'source_station' as const, opts: STATIONS },
              { label: 'To Station', key: 'dest_station' as const, opts: STATIONS },
            ] as const).map(({ label, key, opts }) => (
              <div key={key}>
                <p className="label mb-1.5">{label}</p>
                <select value={form[key]} onChange={(e) => set(key, e.target.value)} className="select w-full">
                  {(opts as string[][]).map((o) => (
                    <option key={o[0]} value={o[0]}>{o[1]}{o[0] !== o[1] ? ` (${o[0]})` : ''}</option>
                  ))}
                </select>
              </div>
            ))}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="label mb-1.5">Days in Advance</p>
                <input type="number" min={1} max={120} value={form.days_advance}
                  onChange={(e) => set('days_advance', Number(e.target.value))} className="input w-full" />
              </div>
              <div>
                <p className="label mb-1.5">WL Number (0=CNF)</p>
                <input type="number" min={0} max={300} value={form.wl_number}
                  onChange={(e) => set('wl_number', Number(e.target.value))} className="input w-full" />
              </div>
              <div>
                <p className="label mb-1.5">Travel Month</p>
                <select value={form.month} onChange={(e) => set('month', Number(e.target.value))} className="select w-full">
                  {MONTHS.map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
                </select>
              </div>
              <div>
                <p className="label mb-1.5">Day of Week</p>
                <select value={form.day_of_week} onChange={(e) => set('day_of_week', Number(e.target.value))} className="select w-full">
                  {DAYS.map((d, i) => <option key={i} value={i}>{d}</option>)}
                </select>
              </div>
            </div>

            {liveDelay > 5 && (
              <div className="flex items-start gap-2 bg-rail-amber/10 border border-rail-amber/20 rounded-xl p-3 text-[11px] text-rail-amber">
                <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                Live delay at {form.source_station}: {liveDelay.toFixed(1)}min — factored into prediction
              </div>
            )}

            <button
              onClick={() => mutation.mutate(form)}
              disabled={mutation.isPending}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              <Ticket size={14} />
              {mutation.isPending ? 'Predicting...' : 'Predict Confirmation'}
            </button>
          </div>

          {/* Result */}
          <div className="col-span-3 space-y-4">
            <div className="card-p">
              <h3 className="text-sm font-display font-semibold text-text-primary mb-1">Confirmation Probability</h3>
              <SemiGauge pct={result ? result.confirmation_pct : null} />
            </div>

            {result && (
              <>
                <div className="card-p space-y-3 animate-[fadeIn_0.3s_ease-out]">
                  <h3 className="text-sm font-display font-semibold text-text-primary">AI Insights</h3>
                  {result.advice.length === 0 ? (
                    <div className="flex items-center gap-2 text-rail-green text-sm font-body">
                      <CheckCircle size={14} /> Good booking conditions
                    </div>
                  ) : result.advice.map((a, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-text-secondary font-body">
                      <Zap size={12} className="text-rail-cyan shrink-0 mt-0.5" />
                      {a}
                    </div>
                  ))}
                  <div className="pt-3 border-t border-bg-border grid grid-cols-2 gap-2 text-[10px] font-mono">
                    <div className="flex justify-between text-text-muted">
                      <span>Optimal booking</span>
                      <span className="text-text-secondary">{result.optimal_booking_days} days ahead</span>
                    </div>
                    <div className="flex justify-between text-text-muted">
                      <span>Route delay factor</span>
                      <span className="text-rail-amber">-{(result.route_delay_impact * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                </div>

                {result.alternative_trains.length > 0 && (
                  <div className="card-p animate-[fadeIn_0.3s_ease-out]">
                    <h3 className="text-sm font-display font-semibold text-text-primary mb-3">Alternative Trains</h3>
                    <div className="divide-y divide-bg-border">
                      {result.alternative_trains.map((t) => (
                        <div key={t.number} className="flex items-center justify-between py-2.5">
                          <div>
                            <p className="text-xs font-medium text-text-secondary">{t.name}</p>
                            <p className="text-[10px] font-mono text-text-muted">{t.number}</p>
                          </div>
                          <span className="pill pill-cyan">{t.type}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
