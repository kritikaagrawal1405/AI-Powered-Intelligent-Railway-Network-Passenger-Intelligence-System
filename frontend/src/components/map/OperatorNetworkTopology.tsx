import { useEffect, useRef, useState } from 'react'
import type { NetworkNode, NetworkEdge } from '../../types'

interface Node {
  id: string
  label: string
  x: number
  y: number
  congestion: number
  trains?: number
  delay?: number
}

interface NodeInfo {
  id: string
  label: string
  congestion: number
  trains: number
  delay: number
}

interface NetworkStats {
  nodes: number
  edges: number
  congested: number
}

function getCongestionColor(score: number) {
  if (score > 0.75) return '#ef4444'
  if (score > 0.5) return '#fcd34d'
  if (score > 0.25) return '#f97316'
  return '#10b981'
}

interface OperatorNetworkTopologyProps {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
  stationCongestion: Record<string, number>
  stationDelays: Record<string, number>
}

export default function OperatorNetworkTopology({
  nodes,
  edges,
  stationCongestion,
  stationDelays,
}: OperatorNetworkTopologyProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const nodesRef = useRef<Node[]>([])
  const animRef = useRef<number>(0)
  const [selectedNode, setSelectedNode] = useState<NodeInfo | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [netStats, setNetStats] = useState<NetworkStats>({ nodes: 0, edges: 0, congested: 0 })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !nodes.length) return

    let active = true
    let t = 0

    const initNodes = () => {
      const w = canvas.width
      const h = canvas.height

      const lats = nodes.map((n) => n.lat).filter((n) => typeof n === 'number' && !Number.isNaN(n))
      const lngs = nodes.map((n) => n.lon).filter((n) => typeof n === 'number' && !Number.isNaN(n))
      const minLat = Math.min(...lats)
      const maxLat = Math.max(...lats)
      const minLng = Math.min(...lngs)
      const maxLng = Math.max(...lngs)

      nodesRef.current = nodes.map((n) => {
        let rx = 0.5
        let ry = 0.5
        if (maxLng > minLng && typeof n.lon === 'number') {
          rx = (n.lon - minLng) / (maxLng - minLng)
        }
        if (maxLat > minLat && typeof n.lat === 'number') {
          ry = 1 - ((n.lat - minLat) / (maxLat - minLat))
        }

        const cong = stationCongestion[n.id] ?? n.congestion_score ?? 0
        const delay = stationDelays[n.id] ?? n.predicted_delay ?? 0

        return {
          id: n.id,
          label: n.label,
          x: rx * w * 0.9 + w * 0.05,
          y: ry * h * 0.9 + h * 0.05,
          congestion: cong,
          trains: n.live_delay ? 1 : 0,
          delay,
        }
      })

      const congested = nodesRef.current.filter((n) => n.congestion > 0.5).length
      if (active) {
        setNetStats({
          nodes: nodes.length,
          edges: edges.length,
          congested,
        })
        setLoaded(true)
      }
    }

    const resize = () => {
      if (!canvas) return
      const ratio = window.devicePixelRatio || 1
      const rect = canvas.getBoundingClientRect()
      canvas.width = rect.width * ratio
      canvas.height = rect.height * ratio
      const ctx = canvas.getContext('2d')
      if (ctx) ctx.scale(ratio, ratio)
      initNodes()
    }

    resize()

    const draw = () => {
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      const W = canvas.offsetWidth
      const H = canvas.offsetHeight

      ctx.clearRect(0, 0, W, H)

      const nodeMap = new Map(nodesRef.current.map((n) => [n.id, n]))

      for (const edge of edges) {
        const src = nodeMap.get(edge.source)
        const tgt = nodeMap.get(edge.target)
        if (!src || !tgt) continue

        const avgCongestion = (src.congestion + tgt.congestion) / 2
        const alpha = 0.2 + Math.sin(t * 0.02 + src.x * 0.01) * 0.05

        ctx.beginPath()
        ctx.moveTo(src.x, src.y)
        ctx.lineTo(tgt.x, tgt.y)
        ctx.strokeStyle = `rgba(0, 240, 255, ${alpha})`
        ctx.lineWidth = 1
        ctx.stroke()

        const particlePos =
          (t * 0.003 + (edge.source.charCodeAt(0) + edge.target.charCodeAt(0)) * 0.01) % 1
        const px = src.x + (tgt.x - src.x) * particlePos
        const py = src.y + (tgt.y - src.y) * particlePos
        ctx.beginPath()
        ctx.arc(px, py, 2, 0, Math.PI * 2)
        ctx.fillStyle = '#00f0ff'
        ctx.shadowBlur = 6
        ctx.shadowColor = '#00f0ff'
        ctx.fill()
        ctx.shadowBlur = 0
      }

      const hexToRgba = (hex: string, a: number) => {
        const r = parseInt(hex.slice(1, 3), 16)
        const g = parseInt(hex.slice(3, 5), 16)
        const b = parseInt(hex.slice(5, 7), 16)
        return `rgba(${r},${g},${b},${a})`
      }

      for (const node of nodesRef.current) {
        const color = getCongestionColor(node.congestion)
        const pulse = 1 + Math.sin(t * 0.05 + node.x * 0.01) * 0.15
        const r = 7 * pulse

        ctx.beginPath()
        ctx.arc(node.x, node.y, r * 1.8, 0, Math.PI * 2)
        ctx.strokeStyle = hexToRgba(color, 0.3)
        ctx.lineWidth = 1.5
        ctx.stroke()

        ctx.beginPath()
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2)
        ctx.fillStyle = hexToRgba(color, 0.9)
        ctx.shadowBlur = 10
        ctx.shadowColor = color
        ctx.fill()
        ctx.shadowBlur = 0

        ctx.beginPath()
        ctx.arc(node.x, node.y, 2.5, 0, Math.PI * 2)
        ctx.fillStyle = 'rgba(10, 22, 40, 0.8)'
        ctx.fill()

        ctx.font = '9px JetBrains Mono, monospace'
        ctx.fillStyle = 'rgba(224, 234, 248, 0.75)'
        ctx.textAlign = 'center'
        ctx.fillText(node.label, node.x, node.y + r + 12)
      }

      t++
      animRef.current = requestAnimationFrame(draw)
    }

    const handleClick = (e: MouseEvent) => {
      if (!canvas) return
      const rect = canvas.getBoundingClientRect()
      const mx = e.clientX - rect.left
      const my = e.clientY - rect.top

      for (const node of nodesRef.current) {
        const dist = Math.sqrt((node.x - mx) ** 2 + (node.y - my) ** 2)
        if (dist < 16) {
          setSelectedNode({
            id: node.id,
            label: node.label,
            congestion: node.congestion,
            trains: node.trains ?? 0,
            delay: node.delay ?? 0,
          })
          return
        }
      }
      setSelectedNode(null)
    }

    canvas.addEventListener('click', handleClick)
    window.addEventListener('resize', resize)

    draw()

    return () => {
      active = false
      cancelAnimationFrame(animRef.current)
      canvas.removeEventListener('click', handleClick)
      window.removeEventListener('resize', resize)
    }
  }, [nodes, edges, stationCongestion, stationDelays])

  return (
    <div className="flex-1 relative glass rounded-2xl overflow-hidden border border-white/5" style={{ minHeight: '500px' }}>
      {!loaded && (
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <span className="spinner w-8 h-8" />
        </div>
      )}

      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-crosshair"
        style={{ minHeight: '500px' }}
      />

      <div className="absolute top-4 left-4 flex gap-3">
        {[
          { label: 'Nodes', value: netStats.nodes || '…', color: '#00d4ff' },
          { label: 'Edges', value: netStats.edges || '…', color: '#ffd700' },
          { label: 'Congested', value: netStats.congested || '…', color: '#ff3b3b' },
        ].map((s) => (
          <div key={s.label} className="glass rounded-lg px-3 py-1.5 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.color }} />
            <span className="text-xs font-mono text-rail-ghost">{s.label}:</span>
            <span className="text-xs font-mono" style={{ color: s.color }}>{s.value}</span>
          </div>
        ))}
      </div>

      {selectedNode && (
        <div className="absolute bottom-4 right-4 w-52 glass rounded-xl p-4 border border-rail-yellow/20">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-xs font-mono text-rail-yellow/60 uppercase tracking-wider">Station</div>
              <div className="font-display text-white text-base tracking-wider">{selectedNode.label}</div>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-rail-ghost hover:text-white"
            >
              ×
            </button>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-rail-ghost">Congestion</span>
              <div className="flex items-center gap-1.5">
                <div className="w-16 h-1.5 bg-rail-steel/50 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${selectedNode.congestion * 100}%`,
                      background: getCongestionColor(selectedNode.congestion),
                    }}
                  />
                </div>
                <span
                  className="text-xs font-mono"
                  style={{ color: getCongestionColor(selectedNode.congestion) }}
                >
                  {Math.round(selectedNode.congestion * 100)}%
                </span>
              </div>
            </div>

            <div className="flex justify-between">
              <span className="text-xs text-rail-ghost">Active Trains</span>
              <span className="text-xs font-mono text-rail-cyan">{selectedNode.trains}</span>
            </div>

            <div className="flex justify-between">
              <span className="text-xs text-rail-ghost">Avg Delay</span>
              <span className="text-xs font-mono text-rail-yellow">
                +{selectedNode.delay.toFixed(1)}m
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="absolute bottom-4 left-4 text-xs font-mono text-rail-ghost/40">
        Click any station node to view line details
      </div>
    </div>
  )
}

