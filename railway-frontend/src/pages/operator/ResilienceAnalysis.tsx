import { useEffect, useState } from 'react';
import { resilienceAPI } from '../../services/api';
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip, ScatterChart, Scatter, XAxis, YAxis, ZAxis, CartesianGrid } from 'recharts';

export default function ResilienceAnalysis() {
  const [resilienceData, setResilienceData] = useState<any>(null);
  const [criticalNodes, setCriticalNodes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [n, r] = await Promise.all([
          resilienceAPI.getCriticalNodes(6),
          resilienceAPI.getSummary(),
        ]);
        setCriticalNodes((n as any).nodes ?? []);
        setResilienceData(r);
      } catch (error) {
        console.error("Failed to load resilience data:", error);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const radarData = resilienceData ? [
    { metric: 'Resilience', value: Math.round((resilienceData.overall_resilience_score ?? 0.73) * 100) },
    { metric: 'Connectivity', value: 78 },
    { metric: 'Redundancy', value: 65 },
    { metric: 'Recovery Speed', value: 71 },
    { metric: 'Load Balance', value: 58 },
    { metric: 'Path Diversity', value: 82 },
  ] : [];

  const communityData = [
    { name: 'Northern Zone', stations: 45, resilience: 78, size: 200 },
    { name: 'Western Zone', stations: 38, resilience: 71, size: 160 },
    { name: 'Eastern Zone', stations: 52, resilience: 65, size: 240 },
    { name: 'Southern Zone', stations: 41, resilience: 82, size: 185 },
    { name: 'Central Zone', stations: 35, resilience: 68, size: 150 },
  ];

  if (loading) return <div className="flex items-center justify-center h-64"><span className="spinner w-8 h-8" /></div>;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-display tracking-widest text-white mb-1">RESILIENCE ANALYSIS</h1>
        <p className="text-rail-ghost text-sm">Network failure analysis, critical node detection, and community structure</p>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: 'Resilience Score', value: `${Math.round((resilienceData?.overall_resilience_score ?? 0.73) * 100)}%`, color: '#00d4ff' },
          { label: 'Critical Stations', value: resilienceData?.critical_stations_count ?? 12, color: '#ff3b3b' },
          { label: 'Avg Path Length', value: resilienceData?.average_path_length ?? '4.2', color: '#ffd700' },
          { label: 'Network Diameter', value: resilienceData?.network_diameter ?? 11, color: '#00ff88' },
          { label: 'Clustering Coeff', value: (resilienceData?.clustering_coefficient ?? 0.34).toFixed(2), color: '#ff6b00' },
        ].map(s => (
          <div key={s.label} className="glass rounded-xl p-4 text-center">
            <div className="text-2xl font-display mb-1" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs font-mono text-rail-ghost/60 uppercase leading-tight">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar */}
        <div className="glass rounded-2xl p-6">
          <h2 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-4">Network Health Radar</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(139,168,200,0.1)" />
                <PolarAngleAxis
                  dataKey="metric"
                  tick={{ fill: 'rgba(139,168,200,0.6)', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                />
                <Radar
                  dataKey="value"
                  stroke="#00d4ff"
                  fill="#00d4ff"
                  fillOpacity={0.15}
                />
                <Tooltip
                  contentStyle={{ background: 'rgba(13,32,68,0.95)', border: '1px solid rgba(0,212,255,0.3)', borderRadius: 8 }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Critical nodes */}
        <div className="glass rounded-2xl p-6">
          <h2 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-4">Critical Infrastructure Nodes</h2>
          <div className="space-y-3">
            {criticalNodes.slice(0, 6).map((node: any, i) => {
              const impact = node.congestion_score ?? 0;
              const color = impact > 0.75 ? '#ff3b3b' : impact > 0.5 ? '#ff6b00' : '#ffd700';
              return (
                <div key={i} className="flex items-center gap-3 p-3 glass-light rounded-lg">
                  <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono flex-shrink-0"
                    style={{ background: `${color}20`, border: `1px solid ${color}40`, color }}>
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-white truncate">{node.station}</div>
                    <div className="h-1 bg-rail-steel/30 rounded-full mt-1 overflow-hidden">
                      <div className="h-full rounded-full" style={{
                        width: `${Math.round(impact * 100)}%`,
                        background: color,
                        boxShadow: `0 0 4px ${color}60`,
                      }} />
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-xs font-mono" style={{ color }}>{Math.round(impact * 100)}%</div>
                    <div className="text-xs text-rail-ghost/40">impact</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Communities / zones */}
      <div className="glass rounded-2xl p-6">
        <h2 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-5">Railway Communities / Zones</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {communityData.map((c, i) => {
            const colors = ['#00d4ff', '#ffd700', '#00ff88', '#ff6b00', '#ff3b3b'];
            const color = colors[i];
            return (
              <div key={c.name} className="glass-light rounded-xl p-4 text-center border"
                style={{ borderColor: `${color}20` }}>
                <div className="w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center"
                  style={{ background: `${color}15`, border: `2px solid ${color}40` }}>
                  <span className="text-sm font-display" style={{ color }}>{c.stations}</span>
                </div>
                <div className="text-xs text-white font-medium mb-1">{c.name}</div>
                <div className="text-xs text-rail-ghost/60">{c.stations} stations</div>
                <div className="mt-2">
                  <div className="text-xs font-mono" style={{ color }}>{c.resilience}%</div>
                  <div className="text-xs text-rail-ghost/40">resilience</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Failure impact simulation */}
      <div className="glass rounded-2xl p-6">
        <h2 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-4">Failure Impact Matrix</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-left py-2 pr-4 text-rail-ghost/60 uppercase">Station</th>
                <th className="text-right py-2 px-4 text-rail-ghost/60 uppercase">Routes Affected</th>
                <th className="text-right py-2 px-4 text-rail-ghost/60 uppercase">Passengers/Day</th>
                <th className="text-right py-2 px-4 text-rail-ghost/60 uppercase">Recovery Time</th>
                <th className="text-right py-2 pl-4 text-rail-ghost/60 uppercase">Criticality</th>
              </tr>
            </thead>
            <tbody>
              {[
                { station: 'New Delhi', routes: 48, passengers: 450000, recovery: '6h', criticality: 'EXTREME' },
                { station: 'Howrah Jn', routes: 38, passengers: 380000, recovery: '5h', criticality: 'EXTREME' },
                { station: 'Mumbai Central', routes: 34, passengers: 340000, recovery: '5h', criticality: 'HIGH' },
                { station: 'Nagpur', routes: 28, passengers: 210000, recovery: '4h', criticality: 'HIGH' },
                { station: 'Bhopal Jn', routes: 22, passengers: 175000, recovery: '3h', criticality: 'MEDIUM' },
              ].map((row, i) => {
                const critColor = { EXTREME: '#ff3b3b', HIGH: '#ff6b00', MEDIUM: '#ffd700', LOW: '#00ff88' }[row.criticality] ?? '#00ff88';
                return (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                    <td className="py-2.5 pr-4 text-white">{row.station}</td>
                    <td className="py-2.5 px-4 text-right text-rail-cyan">{row.routes}</td>
                    <td className="py-2.5 px-4 text-right text-rail-ghost">{(row.passengers / 1000).toFixed(0)}K</td>
                    <td className="py-2.5 px-4 text-right text-rail-ghost">{row.recovery}</td>
                    <td className="py-2.5 pl-4 text-right">
                      <span className="px-2 py-0.5 rounded text-xs" style={{ color: critColor, background: `${critColor}15`, border: `1px solid ${critColor}30` }}>
                        {row.criticality}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
