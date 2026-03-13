import { useEffect, useState } from 'react'
import type { ForecastDay } from '../../types'

interface PassengerAgentCardProps {
  systemDelay: number
  onTimePct?: number
  reliabilityPct?: number
  bestStations: Array<{ code: string; name: string; delay: number }>
  worstStations: Array<{ code: string; name: string; delay: number }>
  forecast: ForecastDay[]
}

export function PassengerAgentCard({
  systemDelay,
  onTimePct,
  reliabilityPct,
  bestStations,
  worstStations,
  forecast,
}: PassengerAgentCardProps) {
  const [loading, setLoading] = useState(false)
  const [text, setText] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  function generate() {
    if (loading) return
    setLoading(true)
    setError(null)

    // Derive simple, rule-based insights from the current snapshot
    const topBest = bestStations.slice(0, 2)
    const topWorst = worstStations.slice(0, 2)
    const nextDays = forecast.slice(0, 4)

    const best = topBest[0]
    const altBest = topBest[1]
    const worst = topWorst[0]

    const avgDelay = systemDelay
    const goodDayThreshold = 10
    const riskyDays = nextDays.filter((d) => d.avg_delay > goodDayThreshold)
    const goodDays = nextDays.filter((d) => d.avg_delay <= goodDayThreshold)

    const lines: string[] = []

    // Station choice
    if (best) {
      lines.push(
        `• Prefer departing from ${best.name} (${best.code}) — it currently has one of the lowest live delays (~${best.delay.toFixed(
          1,
        )} min).`,
      )
    }
    if (altBest) {
      lines.push(
        `• If ${best?.code ?? 'your first choice'} is not convenient, ${altBest.name} (${altBest.code}) is a solid backup with similar performance.`,
      )
    }
    if (worst) {
      lines.push(
        `• Avoid starting from ${worst.name} (${worst.code}) right now unless necessary — it is among the slowest with elevated delays.`,
      )
    }

    // Timing and booking horizon
    if (avgDelay > 15) {
      lines.push(
        `• Network-wide average delay is high (~${avgDelay.toFixed(
          1,
        )} min). Book at least 2–3 days in advance and prefer earlier departures to absorb disruption.`,
      )
    } else if (avgDelay > 8) {
      lines.push(
        `• Delays are moderate (~${avgDelay.toFixed(
          1,
        )} min). Book 1–2 days in advance and prefer departures outside the morning and evening peaks.`,
      )
    } else {
      lines.push(
        `• System delay is relatively low (~${avgDelay.toFixed(
          1,
        )} min). Same‑day or next‑day bookings are reasonable, but still avoid tight connections.`,
      )
    }

    // Best day/time windows
    if (goodDays.length > 0) {
      const labels = goodDays.map((d) => d.day).join(', ')
      lines.push(
        `• For the next few days, ${labels} look like the best travel days (lower forecast delays) — target off‑peak windows such as 10:00–13:00 or 20:00–23:00 on those days.`,
      )
    }
    if (riskyDays.length > 0) {
      const labels = riskyDays.map((d) => d.day).join(', ')
      lines.push(
        `• Try to avoid non‑essential journeys on ${labels}, or at least avoid evening peaks when delays tend to compound.`,
      )
    }

    // Reliability + tips
    if (onTimePct != null) {
      if (onTimePct > 75) {
        lines.push(
          `• With an on‑time rate around ${onTimePct.toFixed(
            0,
          )}%, the network is performing fairly well — main risk is localized congestion rather than systemic disruption.`,
        )
      } else {
        lines.push(
          `• On‑time performance (~${onTimePct.toFixed(
            0,
          )}%) suggests some instability — add at least 30–45 minutes buffer before important connections or appointments.`,
        )
      }
    }
    lines.push(
      '• General tip: choose routes with fewer interchanges, arrive 20–30 minutes early, and keep an eye on live train status on the Network Map before heading out.',
    )

    setText(lines.join('\n'))
    setLoading(false)
  }

  // Auto-generate once when data is available so the brief appears without extra clicks
  useEffect(() => {
    if (!text && !error && !loading && (bestStations.length > 0 || worstStations.length > 0 || forecast.length > 0)) {
      void generate()
    }
  }, [bestStations, worstStations, forecast, text, error, loading])

  return (
    <div className="card-p flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="label mb-1.5">Passenger Agent</p>
          <p className="text-[11px] text-text-muted">
            Auto-brief based on the current dashboard — not a generic answer.
          </p>
        </div>
        <button
          onClick={generate}
          disabled={loading}
          className="btn-primary text-[11px] px-3 py-1.5"
        >
          {loading ? 'Generating...' : 'Generate trip brief'}
        </button>
      </div>

      {error && (
        <p className="text-[11px] font-mono text-rail-red bg-rail-red/5 border border-rail-red/25 rounded-xl px-3 py-2">
          {error}
        </p>
      )}

      {text && !error && (
        <div className="text-[12px] text-text-secondary font-body leading-relaxed bg-bg-elevated border border-bg-border rounded-xl px-3 py-2 whitespace-pre-line">
          {text}
        </div>
      )}

      {!text && !error && !loading && (
        <p className="text-[11px] text-text-muted">
          Tip: after comparing two stations on the cards above, click{" "}
          <span className="font-mono">Generate trip brief</span> to get a tailored suggestion.
        </p>
      )}
    </div>
  )
}

