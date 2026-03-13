import { useEffect, useRef, useState, useCallback } from 'react'
import type { NetworkNode, NetworkEdge } from '../../types'

type ColorMode = 'delay' | 'congestion' | 'vulnerability'

interface NetworkMapCanvasProps {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
  mode: ColorMode
  stationDelays: Record<string, number>
  stationCongestion: Record<string, number>
  tick: number
}

function project(lat: number, lon: number, W: number, H: number) {
  const minLat = 8, maxLat = 32, minLon = 68, maxLon = 90, pad = 44
  return {
    x: pad + ((lon - minLon) / (maxLon - minLon)) * (W - pad * 2),
    y: pad + ((maxLat - lat) / (maxLat - minLat)) * (H - pad * 2),
  }
}

function nodeColor(node: NetworkNode, mode: ColorMode, delays: Record<string, number>, cong: Record<string, number>): string {
  if (mode === 'delay') {
    const d = delays[node.id] ?? node.predicted_delay ?? 0
    return d > 30 ? '#ff4757' : d > 10 ? '#ffb347' : '#00ff87'
  }
  if (mode === 'congestion') {
    const c = cong[node.id] ?? node.congestion_score ?? 0
    return c > 0.85 ? '#ff4757' : c > 0.65 ? '#ffb347' : c > 0.4 ? '#00d4ff' : '#00ff87'
  }
  const v = node.vulnerability_score ?? 0
  return v > 0.08 ? '#7c5cbf' : v > 0.05 ? '#ff4757' : '#00d4ff'
}

export default function NetworkMapCanvas({
  nodes, edges, mode, stationDelays, stationCongestion, tick
}: NetworkMapCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [hovered, setHovered] = useState<NetworkNode | null>(null)
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 })
  const posRef = useRef<Record<string, { x: number; y: number }>>({})

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas || !nodes.length) return
    const ctx = canvas.getContext('2d')!
    const W = canvas.width, H = canvas.height
    ctx.clearRect(0, 0, W, H)

    // Build positions
    const pos: Record<string, { x: number; y: number }> = {}
    nodes.forEach((n) => { pos[n.id] = project(n.lat, n.lon, W, H) })
    posRef.current = pos

    // Draw edges
    edges.forEach((e) => {
      const a = pos[e.source], b = pos[e.target]
      if (!a || !b) return
      ctx.beginPath()
      ctx.moveTo(a.x, a.y)
      ctx.lineTo(b.x, b.y)
      ctx.strokeStyle = '#1a2d4780'
      ctx.lineWidth = 0.7
      ctx.stroke()
    })

    // Draw nodes
    nodes.forEach((n) => {
      const p = pos[n.id]
      if (!p) return
      const r = Math.max(4, Math.min(13, n.daily_footfall / 110000 * 10))
      const color = nodeColor(n, mode, stationDelays, stationCongestion)
      const isHov = hovered?.id === n.id
      const isCritical = mode === 'delay' && (stationDelays[n.id] ?? 0) > 30

      // Glow
      if (isHov || isCritical) {
        const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r * 3.5)
        grad.addColorStop(0, color + '50')
        grad.addColorStop(1, 'transparent')
        ctx.beginPath()
        ctx.arc(p.x, p.y, r * 3.5, 0, Math.PI * 2)
        ctx.fillStyle = grad
        ctx.fill()
      }

      // Node
      ctx.beginPath()
      ctx.arc(p.x, p.y, isHov ? r + 2 : r, 0, Math.PI * 2)
      ctx.fillStyle = color
      ctx.fill()
      ctx.strokeStyle = isHov ? '#ffffff' : '#020408'
      ctx.lineWidth = isHov ? 2 : 1
      ctx.stroke()

      // Label for A1 or hovered
      if (n.category === 'A1' || isHov) {
        ctx.font = `${isHov ? 600 : 500} 10px DM Sans`
        ctx.fillStyle = isHov ? '#e8f4fd' : '#8ba3bc'
        ctx.textAlign = 'center'
        ctx.fillText(n.label.split(' ')[0], p.x, p.y - r - 5)
      }
    })
  }, [nodes, edges, mode, stationDelays, stationCongestion, hovered, tick])

  useEffect(() => { draw() }, [draw])

  function handleMouseMove(e: React.MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current
    if (!canvas || !nodes.length) return
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left, my = e.clientY - rect.top
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    const cx = mx * scaleX, cy = my * scaleY

    let found: NetworkNode | null = null
    for (const n of nodes) {
      const p = posRef.current[n.id]
      if (!p) continue
      const r = Math.max(4, Math.min(13, n.daily_footfall / 110000 * 10))
      if (Math.hypot(cx - p.x, cy - p.y) <= r + 6) { found = n; break }
    }
    setHovered(found)
    setTooltipPos({ x: mx + 14, y: my - 10 })
  }

  return (
    <div className="relative w-full h-full">
      <canvas
        ref={canvasRef}
        width={920} height={580}
        className="w-full h-full cursor-crosshair"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHovered(null)}
      />
      {hovered && (
        <div
          className="absolute pointer-events-none bg-bg-elevated border border-bg-border rounded-2xl p-4 shadow-2xl z-10 w-56"
          style={{ left: tooltipPos.x, top: tooltipPos.y }}
        >
          <p className="font-display font-semibold text-sm text-text-primary mb-3">{hovered.label}</p>
          <div className="space-y-1.5 text-[11px] font-mono">
            {[
              ['Zone', hovered.zone, 'text-text-secondary'],
              ['Category', hovered.category, 'text-text-secondary'],
              ['Platforms', hovered.platforms, 'text-text-secondary'],
              ['Footfall', `${(hovered.daily_footfall / 1000).toFixed(0)}K/day`, 'text-text-secondary'],
              ['Live Delay', `${(stationDelays[hovered.id] ?? 0).toFixed(1)}m`, 'text-rail-amber'],
              ['Congestion', `${((stationCongestion[hovered.id] ?? 0) * 100).toFixed(0)}%`, 'text-rail-cyan'],
            ].map(([k, v, c]) => (
              <div key={k as string} className="flex justify-between">
                <span className="text-text-muted">{k}</span>
                <span className={c as string}>{v as string}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
