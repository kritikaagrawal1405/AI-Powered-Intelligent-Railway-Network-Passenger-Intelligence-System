import { useEffect, useState } from 'react'

interface OperatorAgentCardProps {
  networkHealthPct?: number
  trainsOnTimePct?: number
  cascadeRiskCount?: number
  incidents: Array<{ station_name: string; severity: string; delay_added: number }>
  zones: Array<{ zone: string; avg_delay: number; avg_congestion: number; status?: string }>
}

export function OperatorAgentCard({
  networkHealthPct,
  trainsOnTimePct,
  cascadeRiskCount,
  incidents,
  zones,
}: OperatorAgentCardProps) {
  const [loading, setLoading] = useState(false)
  const [text, setText] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  function generate() {
    if (loading) return
    setLoading(true)
    setError(null)

    const topIncidents = incidents.slice(0, 5)
    const hotZones = zones
      .slice()
      .sort((a, b) => b.avg_delay - a.avg_delay)
      .slice(0, 5)

    const lines: string[] = []

    // IMMEDIATE (0–30min)
    lines.push('IMMEDIATE (0–30min):')
    if (topIncidents.length > 0) {
      const names = topIncidents.map((i) => i.station_name).join(', ')
      lines.push(
        `• Stabilise operations around current incidents at ${names} — deploy staff to platforms, update passenger announcements, and cap further dwell-time extensions.`,
      )
    } else {
      lines.push('• No critical incidents; focus on keeping headway stable on the most delayed corridors.')
    }
    if (hotZones.length > 0) {
      const hz = hotZones[0]
      lines.push(
        `• Treat zone ${hz.zone} as the primary risk area (high delay & congestion) — temporarily prioritise through‑trains over low‑priority stopping services here.`,
      )
    }

    // SHORT TERM (30–120min)
    lines.push('\nSHORT TERM (30–120min):')
    if (hotZones.length > 1) {
      const others = hotZones.slice(1).map((z) => z.zone).join(', ')
      lines.push(
        `• Review timetable and crossing conflicts in zones ${others}; consider minor retiming or skip‑stop patterns to break congestion loops.`,
      )
    }
    if (cascadeRiskCount && cascadeRiskCount > 0) {
      lines.push(
        `• For high cascade‑risk junctions (count: ${cascadeRiskCount}), enforce strict dispatch discipline and avoid holding trains on junction platforms longer than necessary.`,
      )
    }

    // SHIFT-LEVEL (next 6–12h)
    lines.push('\nSHIFT-LEVEL (next 6–12h):')
    if (networkHealthPct != null) {
      if (networkHealthPct < 65) {
        lines.push(
          `• With network health around ${networkHealthPct.toFixed(
            0,
          )}%, plan targeted recovery windows (reduced maintenance slots, extra rakes) in the worst‑hit zones to reset delays before the next peak.`,
        )
      } else {
        lines.push(
          `• Network health (~${networkHealthPct.toFixed(
            0,
          )}%) is acceptable; focus on preventing new bottlenecks by keeping high‑throughput corridors free of non‑essential overtakes.`,
        )
      }
    }
    if (trainsOnTimePct != null) {
      lines.push(
        `• Monitor on‑time percentage (~${trainsOnTimePct.toFixed(
          0,
        )}%) every 30 minutes; if it drops by more than 5 points, trigger a review of control actions and incident handling.`,
      )
    }
    lines.push(
      '• Capture learnings from today’s hotspots (zones and stations) to update congestion playbooks and pre‑define detour or skip‑stop strategies for future peaks.',
    )

    setText(lines.join('\n'))
    setLoading(false)
  }

  // Auto-generate once when core KPIs are available so ops brief appears immediately
  useEffect(() => {
    if (!text && !error && !loading && (incidents.length > 0 || zones.length > 0 || networkHealthPct != null)) {
      void generate()
    }
  }, [incidents, zones, networkHealthPct, text, error, loading])

  return (
    <div className="card-p flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="label mb-1.5">Operator Agent</p>
          <p className="text-[11px] text-text-muted">
            Synthesizes current KPIs into a shift brief & action plan.
          </p>
        </div>
        <button
          onClick={generate}
          disabled={loading}
          className="btn-primary text-[11px] px-3 py-1.5"
        >
          {loading ? 'Generating...' : 'Generate ops brief'}
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
          Use this as a quick shift-start briefing — refresh after major incidents or pattern changes.
        </p>
      )}
    </div>
  )
}

