import { useEffect, useState } from 'react';
import { congestionAPI } from '../../services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid, PieChart, Pie, Legend } from 'recharts';

function CongestionMeter({ score, label }: { score: number; label: string }) {
  const pct = Math.round(score * 100);
  const color = score > 0.75 ? '#ff3b3b' : score > 0.5 ? '#ff6b00' : score > 0.25 ? '#ffd700' : '#00ff88';
  const status = score > 0.75 ? 'CRITICAL' : score > 0.5 ? 'HIGH' : score > 0.25 ? 'MEDIUM' : 'LOW';

  return (
    <div className="glass-light rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-white truncate">{label}</span>
        <span className="text-xs font-mono px-2 py-0.5 rounded" style={{
          color, background: `${color}20`, border: `1px solid ${color}40`
        }}>
          {status}
        </span>
      </div>
      <div className="h-1.5 bg-rail-steel/40 rounded-full overflow-hidden mb-1.5">
        <div
          className="h-full rounded-full transition-all duration-1000"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${color}80, ${color})`,
            boxShadow: `0 0 6px ${color}60`,
          }}
        />
      </div>
      <div className="text-right text-xs font-mono" style={{ color }}>{pct}%</div>
    </div>
  );
}

export default function CongestionPanel() {
  const [hotspots, setHotspots] = useState<any[]>([]);
  const [corridors, setCorridors] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [hs, sum] = await Promise.all([
          congestionAPI.getHotspots(8),
          congestionAPI.getSummary(),
        ]);
        setHotspots((hs as any).hotspots ?? []);
        setSummary(sum);
        // We will just use empty array or dynamic call for corridors if available from congestionAPI
        const cRes = await congestionAPI.getCorridors(5);
        setCorridors((cRes as any).corridors ?? []);
      } catch (err) {
        console.error("Failed to load congestion data:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const pieData = [
    { name: 'Normal', value: 45, fill: '#00ff88' },
    { name: 'Medium', value: 30, fill: '#ffd700' },
    { name: 'High', value: 18, fill: '#ff6b00' },
    { name: 'Critical', value: 7, fill: '#ff3b3b' },
  ];

  const barData = hotspots.map(h => ({
    name: h.station?.split(' ')[0] ?? h.station,
    score: Math.round((h.congestion_score ?? 0.5) * 100),
  }));

  if (loading) return <div className="flex items-center justify-center h-64"><span className="spinner w-8 h-8" /></div>;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-display tracking-widest text-white mb-1">CONGESTION ANALYSIS</h1>
        <p className="text-rail-ghost text-sm">Network-wide congestion monitoring and hotspot detection</p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Critical Stations', value: '3', color: '#ff3b3b' },
          { label: 'High Congestion', value: '8', color: '#ff6b00' },
          { label: 'Avg Network Load', value: '68%', color: '#ffd700' },
          { label: 'Operational', value: '89%', color: '#00ff88' },
        ].map(s => (
          <div key={s.label} className="glass rounded-xl p-4 text-center">
            <div className="text-2xl font-display mb-1" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs font-mono text-rail-ghost/60 uppercase">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Hotspot list */}
        <div className="glass rounded-2xl p-6">
          <h2 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-5">Congestion Hotspots</h2>
          <div className="space-y-3">
            {hotspots.slice(0, 8).map((h, i) => (
              <CongestionMeter
                key={i}
                score={h.congestion_score ?? 0.5}
                label={h.station}
              />
            ))}
          </div>
        </div>

        {/* Charts column */}
        <div className="lg:col-span-2 space-y-5">
          {/* Bar chart */}
          <div className="glass rounded-2xl p-5">
            <h3 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-4">Station Congestion Score</h3>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} barCategoryGap="30%">
                  <CartesianGrid stroke="rgba(139,168,200,0.05)" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: 'rgba(139,168,200,0.6)', fontSize: 9, fontFamily: 'JetBrains Mono' }}
                    axisLine={false} tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: 'rgba(139,168,200,0.4)', fontSize: 9 }}
                    axisLine={false} tickLine={false}
                    tickFormatter={v => `${v}%`}
                    domain={[0, 100]}
                  />
                  <Tooltip
                    contentStyle={{ background: 'rgba(13,32,68,0.95)', border: '1px solid rgba(255,215,0,0.3)', borderRadius: 8 }}
                    formatter={(v) => [`${v}%`, 'Congestion']}
                  />
                  <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                    {barData.map((d, i) => (
                      <Cell key={i} fill={d.score > 75 ? '#ff3b3b' : d.score > 50 ? '#ff6b00' : d.score > 25 ? '#ffd700' : '#00ff88'} fillOpacity={0.8} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Network status pie + corridors */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="glass rounded-2xl p-5">
              <h3 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-3">Network Status</h3>
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={65}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} opacity={0.85} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: 'rgba(13,32,68,0.95)', border: '1px solid rgba(0,212,255,0.3)', borderRadius: 8 }}
                    />
                    <Legend
                      iconType="circle" iconSize={8}
                      formatter={(val) => <span style={{ color: 'rgba(139,168,200,0.7)', fontSize: 10 }}>{val}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="glass rounded-2xl p-5">
              <h3 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-3">Busiest Corridors</h3>
              <div className="space-y-2.5">
                {corridors.map((c, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-white truncate">{c.corridor}</div>
                      <div className="h-1 bg-rail-steel/30 rounded-full mt-1 overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${c.congestion * 100}%`,
                            background: c.congestion > 0.75 ? '#ff3b3b' : c.congestion > 0.5 ? '#ff6b00' : '#ffd700',
                          }}
                        />
                      </div>
                    </div>
                    <span className="text-xs font-mono text-rail-ghost w-8 text-right flex-shrink-0">
                      {c.trains}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
