import { useEffect, useRef, useState } from 'react';
import { networkAPI, congestionAPI } from '../../services/api';

interface Node {
  id: string;
  label: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  congestion: number;
  trains?: number;
  delay?: number;
}

interface Edge {
  source: string;
  target: string;
  weight?: number;
}

interface NodeInfo {
  id: string;
  label: string;
  congestion: number;
  trains: number;
  delay: number;
}

function getCongestionColor(score: number) {
  if (score > 0.75) return '#ef4444'; // red
  if (score > 0.5) return '#fcd34d';  // yellow
  if (score > 0.25) return '#f97316'; // orange
  return '#10b981'; // green
}

export default function NetworkGraph() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nodesRef = useRef<Node[]>([]);
  const animRef = useRef<number>(0);
  const [selectedNode, setSelectedNode] = useState<NodeInfo | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    let nodesData: any[] = [];
    let edgesData: any[] = [];
    let congestionMap = new Map<string, number>();

    const canvas = canvasRef.current;
    if (!canvas) return;

    const initNodes = () => {
      if (nodesData.length === 0) return;
      const w = canvas.width;
      const h = canvas.height;

      // Find bounding box for scaling
      const lats = nodesData.map(n => n.latitude).filter(n => typeof n === 'number' && !isNaN(n));
      const lngs = nodesData.map(n => n.longitude).filter(n => typeof n === 'number' && !isNaN(n));
      const minLat = Math.min(...lats);
      const maxLat = Math.max(...lats);
      const minLng = Math.min(...lngs);
      const maxLng = Math.max(...lngs);

      nodesRef.current = nodesData.map(n => {
        let rx = 0.5;
        let ry = 0.5;
        if (maxLng > minLng && typeof n.longitude === 'number') {
          rx = (n.longitude - minLng) / (maxLng - minLng);
        }
        if (maxLat > minLat && typeof n.latitude === 'number') {
          // Invert lat since higher latitude is further north (top), but smaller Y is top
          ry = 1 - ((n.latitude - minLat) / (maxLat - minLat));
        }

        return {
          id: n.id,
          label: n.label,
          x: rx * w * 0.9 + w * 0.05,
          y: ry * h * 0.9 + h * 0.05,
          vx: 0, vy: 0,
          congestion: congestionMap.get(n.id) ?? 0,
          trains: n.trains ?? 0,
          delay: n.avg_delay ?? 0,
        };
      });
      if (active) setLoaded(true);
    };

    // Load data from backend concurrently
    Promise.all([
      networkAPI.getTopology(),
      congestionAPI.getHotspots()
    ]).then(([topologyRes, hotspotsRes]) => {
      if (!active) return;
      nodesData = (topologyRes as any).nodes || [];
      edgesData = (topologyRes as any).edges || [];
      const hs = (hotspotsRes as any).hotspots || [];
      congestionMap = new Map(hs.map((h: any) => [h.station, h.congestion_score]));
      initNodes();
    }).catch(console.error);

    const resize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      canvas.style.width = `${canvas.offsetWidth}px`;
      canvas.style.height = `${canvas.offsetHeight}px`;
      const ctx = canvas.getContext('2d');
      if (ctx) ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
      initNodes();
    };

    // Initial setup
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    initNodes();

    let t = 0;

    const draw = () => {
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      const W = canvas.offsetWidth;
      const H = canvas.offsetHeight;

      ctx.clearRect(0, 0, W, H);

      // Background
      ctx.fillStyle = 'rgba(10, 22, 40, 0.0)';
      ctx.fillRect(0, 0, W, H);

      const nodeMap = new Map(nodesRef.current.map(n => [n.id, n]));

      // Draw edges
      for (const edge of edgesData) {
        const src = nodeMap.get(edge.source);
        const tgt = nodeMap.get(edge.target);
        if (!src || !tgt) continue;

        const avgCongestion = (src.congestion + tgt.congestion) / 2;
        const edgeColor = getCongestionColor(avgCongestion);

        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);
        ctx.strokeStyle = edgeColor.replace(')', `, 0.25)`).replace('rgb(', 'rgba(').replace('#ef4444', 'rgba(239,68,68,0.25)').replace('#fcd34d', 'rgba(252,211,77,0.25)').replace('#10b981', 'rgba(16,185,129,0.25)').replace('#f97316', 'rgba(249,115,22,0.25)');

        // Simpler approach
        const alpha = 0.2 + Math.sin(t * 0.02 + src.x * 0.01) * 0.05;
        ctx.strokeStyle = `rgba(0, 240, 255, ${alpha})`;
        ctx.lineWidth = 1;
        ctx.stroke();

        // Train particle on edge
        const particlePos = (t * 0.003 + (edge.source.charCodeAt(0) + edge.target.charCodeAt(0)) * 0.01) % 1;
        const px = src.x + (tgt.x - src.x) * particlePos;
        const py = src.y + (tgt.y - src.y) * particlePos;
        ctx.beginPath();
        ctx.arc(px, py, 2, 0, Math.PI * 2);
        ctx.fillStyle = '#00f0ff';
        ctx.shadowBlur = 6;
        ctx.shadowColor = '#00f0ff';
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // Draw nodes
      for (const node of nodesRef.current) {
        const color = getCongestionColor(node.congestion);
        const pulse = 1 + Math.sin(t * 0.05 + node.x * 0.01) * 0.15;
        const r = 7 * pulse;

        // Outer glow ring
        ctx.beginPath();
        ctx.arc(node.x, node.y, r * 1.8, 0, Math.PI * 2);
        ctx.strokeStyle = color.replace('#', '').length === 6 ? color + '30' : color;
        const hexToRgba = (hex: string, a: number) => {
          const r = parseInt(hex.slice(1, 3), 16);
          const g = parseInt(hex.slice(3, 5), 16);
          const b = parseInt(hex.slice(5, 7), 16);
          return `rgba(${r},${g},${b},${a})`;
        };
        ctx.strokeStyle = hexToRgba(color, 0.3);
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Node fill
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
        ctx.fillStyle = hexToRgba(color, 0.9);
        ctx.shadowBlur = 10;
        ctx.shadowColor = color;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Inner dot
        ctx.beginPath();
        ctx.arc(node.x, node.y, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(10, 22, 40, 0.8)';
        ctx.fill();

        // Label
        ctx.font = '9px JetBrains Mono, monospace';
        ctx.fillStyle = 'rgba(224, 234, 248, 0.75)';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y + r + 12);
      }

      t++;
      animRef.current = requestAnimationFrame(draw);
    };

    draw();

    // Click handler
    const handleClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      for (const node of nodesRef.current) {
        const dist = Math.sqrt((node.x - mx) ** 2 + (node.y - my) ** 2);
        if (dist < 16) {
          setSelectedNode({
            id: node.id,
            label: node.label,
            congestion: node.congestion,
            trains: node.trains ?? 0,
            delay: node.delay ?? 0,
          });
          return;
        }
      }
      setSelectedNode(null);
    };

    canvas.addEventListener('click', handleClick);

    window.addEventListener('resize', resize);
    return () => {
      cancelAnimationFrame(animRef.current);
      canvas.removeEventListener('click', handleClick);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <div className="h-full flex flex-col" style={{ minHeight: 'calc(100vh - 120px)' }}>
      <div className="flex items-start justify-between mb-5 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-display tracking-widest text-white mb-1">NETWORK TOPOLOGY</h1>
          <p className="text-rail-ghost text-sm">Live railway network graph with congestion overlay</p>
        </div>

        <div className="flex items-center gap-6 glass rounded-lg px-4 py-2">
          {[['#00ff88', 'Normal'], ['#ff6b00', 'Moderate'], ['#ffd700', 'High'], ['#ff3b3b', 'Critical']].map(([c, l]) => (
            <div key={l} className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: c, boxShadow: `0 0 5px ${c}` }} />
              <span className="text-xs font-mono text-rail-ghost">{l}</span>
            </div>
          ))}
        </div>
      </div>

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

        {/* Stats overlay */}
        <div className="absolute top-4 left-4 flex gap-3">
          {[
            { label: 'Nodes', value: '15', color: '#00d4ff' },
            { label: 'Edges', value: '19', color: '#ffd700' },
            { label: 'Congested', value: '4', color: '#ff3b3b' },
          ].map(s => (
            <div key={s.label} className="glass rounded-lg px-3 py-1.5 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.color }} />
              <span className="text-xs font-mono text-rail-ghost">{s.label}:</span>
              <span className="text-xs font-mono" style={{ color: s.color }}>{s.value}</span>
            </div>
          ))}
        </div>

        {/* Selected node panel */}
        {selectedNode && (
          <div className="absolute bottom-4 right-4 w-52 glass rounded-xl p-4 border border-rail-yellow/20">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-xs font-mono text-rail-yellow/60 uppercase tracking-wider">Station</div>
                <div className="font-display text-white text-base tracking-wider">{selectedNode.id}</div>
              </div>
              <button onClick={() => setSelectedNode(null)} className="text-rail-ghost hover:text-white">×</button>
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
                  <span className="text-xs font-mono" style={{ color: getCongestionColor(selectedNode.congestion) }}>
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
                <span className="text-xs font-mono text-rail-yellow">+{selectedNode.delay}m</span>
              </div>
            </div>
          </div>
        )}

        <div className="absolute bottom-4 left-4 text-xs font-mono text-rail-ghost/30">
          Click any station node to view details
        </div>
      </div>
    </div>
  );
}
