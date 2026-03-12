import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, Area, AreaChart, Cell,
} from 'recharts';
import { passengerAPI } from '../../services/api';

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-lg px-3 py-2 border border-rail-cyan/20 text-xs font-mono">
      <p className="text-rail-ghost mb-1">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color }}>{p.name}: {p.value?.toLocaleString()}</p>
      ))}
    </div>
  );
};

export default function DemandInsights() {
  const [busiestStations, setBusiestStations] = useState<any[]>([]);
  const [seasonalDemand, setSeasonalDemand] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const [stations, seasonal] = await Promise.all([
        passengerAPI.getBusiestStations(8),
        passengerAPI.getSeasonalDemand(),
      ]);
      setBusiestStations(
        ((stations as any).busiest_stations ?? []).map((s: any) => ({
          name: s.station?.split(' ').slice(0, 2).join(' ') ?? s.station,
          passengers: s.daily_passengers ?? 0,
          growth: s.growth ?? 0,
        }))
      );
      setSeasonalDemand((seasonal as any).seasonal_demand ?? []);
      setLoading(false);
    }
    load();
  }, []);

  const peakRoutes = [
    { route: 'Delhi → Mumbai', demand: 98, growth: '+12%' },
    { route: 'Delhi → Kolkata', demand: 87, growth: '+8%' },
    { route: 'Mumbai → Pune', demand: 82, growth: '+22%' },
    { route: 'Delhi → Chennai', demand: 75, growth: '+6%' },
    { route: 'Bangalore → Chennai', demand: 71, growth: '+15%' },
    { route: 'Hyderabad → Mumbai', demand: 65, growth: '+11%' },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="spinner w-8 h-8" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-display tracking-widest text-white mb-1">DEMAND INSIGHTS</h1>
        <p className="text-rail-ghost text-sm">Passenger flow analytics and demand forecasting</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Daily Passengers', value: '23.4M', change: '+8.2%', color: '#00d4ff' },
          { label: 'Peak Season', value: 'Oct–Dec', change: '100% demand', color: '#ffd700' },
          { label: 'Busiest Route', value: 'DEL→MUM', change: '1.2M/day', color: '#00ff88' },
          { label: 'Overcrowded', value: '47 Routes', change: 'Needs attention', color: '#ff6b00' },
        ].map(s => (
          <div key={s.label} className="glass rounded-xl p-4">
            <div className="text-xs font-mono text-rail-ghost/60 uppercase tracking-wider mb-2">{s.label}</div>
            <div className="text-xl font-display" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-rail-ghost/50 mt-1">{s.change}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Busiest stations bar chart */}
        <div className="glass rounded-2xl p-5">
          <h2 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-5">Top Stations by Daily Passengers</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={busiestStations} barCategoryGap="30%">
                <CartesianGrid stroke="rgba(139,168,200,0.05)" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fill: 'rgba(139,168,200,0.6)', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                  axisLine={false} tickLine={false}
                />
                <YAxis
                  tick={{ fill: 'rgba(139,168,200,0.4)', fontSize: 9, fontFamily: 'JetBrains Mono' }}
                  axisLine={false} tickLine={false}
                  tickFormatter={v => `${(v / 1000).toFixed(0)}K`}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="passengers" name="Daily Passengers" radius={[4, 4, 0, 0]}>
                  {busiestStations.map((_, i) => (
                    <Cell
                      key={i}
                      fill={`rgba(0, 212, 255, ${0.4 + (busiestStations.length - i) / busiestStations.length * 0.5})`}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Seasonal demand */}
        <div className="glass rounded-2xl p-5">
          <h2 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-5">Seasonal Demand Pattern</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={seasonalDemand}>
                <defs>
                  <linearGradient id="demandGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(139,168,200,0.05)" vertical={false} />
                <XAxis
                  dataKey="month"
                  tick={{ fill: 'rgba(139,168,200,0.6)', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                  axisLine={false} tickLine={false}
                />
                <YAxis
                  tick={{ fill: 'rgba(139,168,200,0.4)', fontSize: 9, fontFamily: 'JetBrains Mono' }}
                  axisLine={false} tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="demand"
                  name="Demand Index"
                  stroke="#00d4ff"
                  strokeWidth={2}
                  fill="url(#demandGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Peak routes */}
      <div className="glass rounded-2xl p-6">
        <h2 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-5">Peak Travel Routes</h2>
        <div className="space-y-3">
          {peakRoutes.map((route, i) => (
            <div key={route.route} className="flex items-center gap-4">
              <span className="text-xs font-mono text-rail-ghost/40 w-4">{i + 1}</span>
              <span className="text-sm text-white w-44">{route.route}</span>
              <div className="flex-1 h-2 bg-rail-steel/30 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${route.demand}%`,
                    background: `linear-gradient(90deg, #00d4ff, #00ff88)`,
                    boxShadow: '0 0 8px rgba(0,212,255,0.4)',
                    transition: 'width 1s ease',
                  }}
                />
              </div>
              <span className="text-xs font-mono text-rail-cyan w-10 text-right">{route.demand}%</span>
              <span className="text-xs font-mono text-rail-green w-12 text-right">{route.growth}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
