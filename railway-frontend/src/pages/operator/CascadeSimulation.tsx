import { useState } from 'react';
import { cascadeAPI } from '../../services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';

const STATIONS = [
  'New Delhi', 'Mumbai Central', 'Howrah Jn', 'Chennai Central', 'Bangalore City',
  'Bhopal Jn', 'Nagpur', 'Ahmedabad Jn', 'Lucknow', 'Patna Jn', 'Hyderabad',
  'Pune Jn', 'Jaipur', 'Vijayawada Jn',
];

interface CascadeResult {
  origin_station: string;
  initial_delay: number;
  affected_stations: Array<{ station: string; delay_propagated: number; hop: number }>;
  total_affected: number;
}

export default function CascadeSimulation() {
  const [station, setStation] = useState('');
  const [delay, setDelay] = useState(60);
  const [maxDepth, setMaxDepth] = useState('3');
  const [result, setResult] = useState<CascadeResult | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [simulated, setSimulated] = useState(false);
  const [error, setError] = useState('');

  const handleSimulate = async () => {
    if (!station) {
      setError('Please select a source station');
      return;
    }
    setError('');
    setSimulating(true);
    setSimulated(false); // Reset simulated state on new simulation attempt

    try {
      const data = await cascadeAPI.simulate({
        station,
        initial_delay: delay, // delay is now a number
        max_depth: parseInt(maxDepth),
      });
      setResult(data as CascadeResult);
      setSimulated(true);
    } catch (err) {
      console.error("Simulation failed:", err);
      setError('Simulation failed to run on the server.');
      setResult(null);
      setSimulated(false); // Ensure simulated is false if an error occurs
    } finally {
      setSimulating(false);
    }
  };

  const chartData = result?.affected_stations?.map(s => ({
    name: s.station.split(' ')[0],
    delay: s.delay_propagated,
    hop: s.hop,
  })) ?? [];

  const hopColors = ['#ff3b3b', '#ff6b00', '#ffd700', '#00d4ff'];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-display tracking-widest text-white mb-1">CASCADE SIMULATION</h1>
        <p className="text-rail-ghost text-sm">Simulate delay propagation through the railway network</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Config */}
        <div className="glass rounded-2xl p-6">
          <h2 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-5">Simulation Parameters</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-rail-ghost/70 uppercase tracking-wider mb-1.5">Origin Station</label>
              <select
                value={station}
                onChange={e => setStation(e.target.value)}
                className="rail-input w-full px-3 py-2 rounded-lg text-sm">
                {STATIONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono text-rail-ghost/70 uppercase tracking-wider mb-1.5">
                Initial Delay: <span className="text-rail-yellow">{delay} min</span>
              </label>
              <input
                type="range" min="5" max="300" step="5"
                value={delay} onChange={e => setDelay(parseInt(e.target.value))}
                className="w-full accent-rail-yellow"
              />
              <div className="flex justify-between text-xs text-rail-ghost/40 mt-1">
                <span>5m</span><span>300m</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono text-rail-ghost/70 uppercase tracking-wider mb-1.5">
                Max Propagation Depth: <span className="text-rail-cyan">{maxDepth}</span>
              </label>
              <input
                type="range" min="1" max="5" step="1"
                value={maxDepth} onChange={e => setMaxDepth(e.target.value)}
                className="w-full accent-rail-cyan"
              />
              <div className="flex justify-between text-xs text-rail-ghost/40 mt-1">
                <span>1 hop</span><span>5 hops</span>
              </div>
            </div>
          </div>

          <button
            onClick={handleSimulate}
            disabled={simulating}
            className="btn-primary w-full py-3 rounded-xl font-body text-sm flex justify-center items-center gap-2">
            {simulating ? <><span className="spinner w-4 h-4" /> Simulating...</> : '⚡ Run Simulation'}
          </button>

          {result && (
            <div className="mt-5 p-4 glass-light rounded-xl">
              <div className="text-xs font-mono text-rail-ghost/60 uppercase tracking-wider mb-3">Summary</div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-xs text-rail-ghost">Origin</span>
                  <span className="text-xs font-mono text-white">{result.origin_station?.split(' ')[0]}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-rail-ghost">Initial Delay</span>
                  <span className="text-xs font-mono text-rail-red">+{result.initial_delay}m</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-rail-ghost">Stations Affected</span>
                  <span className="text-xs font-mono text-rail-yellow">{result.total_affected}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-rail-ghost">Impact Hops</span>
                  <span className="text-xs font-mono text-rail-cyan">{maxDepth}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Cascade visualization */}
        <div className="lg:col-span-2 space-y-5">
          {simulated && result ? (
            <>
              {/* Visual cascade tree */}
              <div className="glass rounded-2xl p-6">
                <h3 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-5">Propagation Chain</h3>

                <div className="space-y-4">
                  {/* Origin */}
                  <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-rail-red glow-red flex-shrink-0" style={{ boxShadow: '0 0 10px #ff3b3b' }} />
                    <div className="flex-1 flex items-center justify-between px-4 py-2.5 rounded-lg"
                      style={{ background: 'rgba(255,59,59,0.1)', border: '1px solid rgba(255,59,59,0.2)' }}>
                      <div>
                        <span className="text-xs font-mono text-rail-ghost/60 uppercase mr-2">ORIGIN</span>
                        <span className="text-sm text-white">{result.origin_station}</span>
                      </div>
                      <span className="text-sm font-mono text-rail-red font-bold">+{result.initial_delay}m</span>
                    </div>
                  </div>

                  {/* Propagation */}
                  {result.affected_stations?.map((s, i) => {
                    const hopColor = hopColors[Math.min(s.hop - 1, hopColors.length - 1)];
                    return (
                      <div key={i} className="flex items-center gap-3" style={{ paddingLeft: `${s.hop * 16}px` }}>
                        <div className="w-2 h-px bg-rail-ghost/30 flex-shrink-0" />
                        <div className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{ background: hopColor, boxShadow: `0 0 6px ${hopColor}` }} />
                        <div className="flex-1 flex items-center justify-between px-3 py-2 rounded-lg glass-light">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-rail-ghost/40">HOP {s.hop}</span>
                            <span className="text-sm text-white/80">{s.station}</span>
                          </div>
                          <span className="text-xs font-mono" style={{ color: hopColor }}>+{s.delay_propagated}m</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Bar chart */}
              <div className="glass rounded-2xl p-6">
                <h3 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-4">Delay Propagation Chart</h3>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} barCategoryGap="25%">
                      <CartesianGrid stroke="rgba(139,168,200,0.05)" vertical={false} />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: 'rgba(139,168,200,0.6)', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                        axisLine={false} tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: 'rgba(139,168,200,0.4)', fontSize: 9, fontFamily: 'JetBrains Mono' }}
                        axisLine={false} tickLine={false}
                        tickFormatter={v => `+${v}m`}
                      />
                      <Tooltip
                        contentStyle={{ background: 'rgba(13,32,68,0.95)', border: '1px solid rgba(255,215,0,0.3)', borderRadius: 8 }}
                        labelStyle={{ color: '#e0eaf8', fontFamily: 'JetBrains Mono', fontSize: 11 }}
                        formatter={(v) => [`+${v}m`, 'Propagated Delay']}
                      />
                      <Bar dataKey="delay" radius={[4, 4, 0, 0]}>
                        {chartData.map((d, i) => (
                          <Cell key={i} fill={hopColors[Math.min((d.hop ?? 1) - 1, 3)]} fillOpacity={0.8} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          ) : (
            <div className="glass rounded-2xl p-16 text-center">
              <div className="text-6xl mb-4 opacity-20">⚡</div>
              <p className="text-rail-ghost text-sm mb-2">Configure parameters and run simulation</p>
              <p className="text-rail-ghost/50 text-xs">The simulation shows how delays propagate through the network</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
