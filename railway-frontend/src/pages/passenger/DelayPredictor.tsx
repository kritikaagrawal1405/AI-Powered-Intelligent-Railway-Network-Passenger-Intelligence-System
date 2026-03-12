import { useState } from 'react';
import { delayAPI, networkAPI } from '../../services/api';
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts';

interface DelayResult {
  predicted_delay_minutes: number;
  risk_level: string;
  confidence: number;
  delay_category: string;
}

const RISK_COLORS: Record<string, string> = {
  Low: '#00ff88',
  Medium: '#ffd700',
  High: '#ff6b00',
  Critical: '#ff3b3b',
};

export default function DelayPredictor() {
  const [trainNo, setTrainNo] = useState('12951');
  const [avgDelay, setAvgDelay] = useState('45');
  const [sigDelayRatio, setSigDelayRatio] = useState('0.30');
  const [onTimeRatio, setOnTimeRatio] = useState('0.65');
  const [riskScore, setRiskScore] = useState('35');
  const [stopNumber, setStopNumber] = useState('8');
  const [centrality, setCentrality] = useState('0.10');

  const [result, setResult] = useState<DelayResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handlePredict = async () => {
    setLoading(true);
    try {
      const data = await delayAPI.predict({
        avg_delay_min: parseFloat(avgDelay),
        significant_delay_ratio: parseFloat(sigDelayRatio),
        on_time_ratio: parseFloat(onTimeRatio),
        delay_risk_score: parseFloat(riskScore),
        stop_number: parseInt(stopNumber),
        betweenness_centrality: parseFloat(centrality),
      });
      setResult(data as DelayResult);
    } finally {
      setLoading(false);
    }
  };

  const radarData = result ? [
    { metric: 'Avg Delay', value: Math.min(100, parseFloat(avgDelay) / 2) },
    { metric: 'Sig Delay %', value: parseFloat(sigDelayRatio) * 100 },
    { metric: 'Risk Score', value: parseFloat(riskScore) },
    { metric: 'Network Centrality', value: parseFloat(centrality) * 100 },
    { metric: 'Stop Count', value: Math.min(100, parseInt(stopNumber) * 5) },
    { metric: 'On Time %', value: parseFloat(onTimeRatio) * 100 },
  ] : [];

  const riskColor = result ? (RISK_COLORS[result.risk_level] ?? '#00d4ff') : '#00d4ff';

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-display tracking-widest text-white mb-1">DELAY FORECAST</h1>
        <p className="text-rail-ghost text-sm">ML-powered train delay prediction with risk assessment</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input */}
        <div className="glass rounded-2xl p-6 lg:col-span-1">
          <h2 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-5">Train Parameters</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-rail-ghost/70 uppercase tracking-wider mb-1.5">Train Number</label>
              <input value={trainNo} onChange={e => setTrainNo(e.target.value)}
                className="rail-input w-full px-3 py-2 rounded-lg text-sm" placeholder="12951" />
            </div>

            {[
              { label: 'Avg Historical Delay (min)', value: avgDelay, setter: setAvgDelay },
              { label: 'Significant Delay Ratio', value: sigDelayRatio, setter: setSigDelayRatio },
              { label: 'On-Time Ratio', value: onTimeRatio, setter: setOnTimeRatio },
              { label: 'Delay Risk Score (0-100)', value: riskScore, setter: setRiskScore },
              { label: 'Stop Number', value: stopNumber, setter: setStopNumber },
              { label: 'Betweenness Centrality', value: centrality, setter: setCentrality },
            ].map(f => (
              <div key={f.label}>
                <label className="block text-xs font-mono text-rail-ghost/70 uppercase tracking-wider mb-1.5">{f.label}</label>
                <input
                  type="number"
                  step="0.01"
                  value={f.value}
                  onChange={e => f.setter(e.target.value)}
                  className="rail-input w-full px-3 py-2 rounded-lg text-sm"
                />
              </div>
            ))}
          </div>

          <button
            onClick={handlePredict}
            disabled={loading}
            className="btn-primary w-full py-3 rounded-lg text-sm mt-5 flex items-center justify-center gap-2">
            {loading ? <><span className="spinner w-4 h-4" /> Analyzing...</> : '⚡ Predict Delay'}
          </button>
        </div>

        {/* Result panels */}
        <div className="lg:col-span-2 space-y-5">
          {result ? (
            <>
              {/* Main result */}
              <div className="glass rounded-2xl p-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-4 glass-light rounded-xl">
                    <div className="text-xs font-mono text-rail-ghost/60 uppercase mb-2">Expected Delay</div>
                    <div className="text-3xl font-display" style={{ color: riskColor }}>
                      +{result.predicted_delay_minutes}
                    </div>
                    <div className="text-xs text-rail-ghost/60">minutes</div>
                  </div>

                  <div className="text-center p-4 glass-light rounded-xl">
                    <div className="text-xs font-mono text-rail-ghost/60 uppercase mb-2">Risk Level</div>
                    <div className="text-xl font-display" style={{ color: riskColor }}>
                      {result.risk_level}
                    </div>
                  </div>

                  <div className="text-center p-4 glass-light rounded-xl">
                    <div className="text-xs font-mono text-rail-ghost/60 uppercase mb-2">Category</div>
                    <div className="text-sm font-mono text-white">{result.delay_category}</div>
                  </div>

                  <div className="text-center p-4 glass-light rounded-xl">
                    <div className="text-xs font-mono text-rail-ghost/60 uppercase mb-2">Confidence</div>
                    <div className="text-2xl font-display text-rail-cyan">
                      {Math.round(result.confidence * 100)}%
                    </div>
                  </div>
                </div>
              </div>

              {/* Delay bar visualization */}
              <div className="glass rounded-2xl p-6">
                <h3 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-4">Delay Timeline Visualization</h3>
                <div className="space-y-3">
                  {['Scheduled Departure', 'Station 3', 'Station 6', 'Station 9', 'Final Destination'].map((stn, i) => {
                    const delayAtStop = Math.round((result.predicted_delay_minutes / 4) * i);
                    const pct = Math.min(100, (delayAtStop / 90) * 100);
                    return (
                      <div key={stn} className="flex items-center gap-3">
                        <span className="text-xs font-mono text-rail-ghost w-36 flex-shrink-0">{stn}</span>
                        <div className="flex-1 h-2 bg-rail-steel/30 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-1000"
                            style={{
                              width: `${pct}%`,
                              background: `linear-gradient(90deg, #00ff88, ${riskColor})`,
                              boxShadow: `0 0 8px ${riskColor}40`,
                            }}
                          />
                        </div>
                        <span className="text-xs font-mono w-16 text-right" style={{ color: delayAtStop > 0 ? riskColor : '#00ff88' }}>
                          {delayAtStop > 0 ? `+${delayAtStop}m` : 'On Time'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Radar chart */}
              <div className="glass rounded-2xl p-6">
                <h3 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-4">Risk Factor Radar</h3>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={radarData}>
                      <PolarGrid stroke="rgba(139,168,200,0.1)" />
                      <PolarAngleAxis
                        dataKey="metric"
                        tick={{ fill: 'rgba(139,168,200,0.6)', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                      />
                      <Radar
                        name="Risk"
                        dataKey="value"
                        stroke={riskColor}
                        fill={riskColor}
                        fillOpacity={0.15}
                      />
                      <Tooltip
                        contentStyle={{ background: 'rgba(13,32,68,0.95)', border: '1px solid rgba(0,212,255,0.3)', borderRadius: 8 }}
                        labelStyle={{ color: '#e0eaf8', fontFamily: 'JetBrains Mono', fontSize: 11 }}
                        itemStyle={{ color: riskColor }}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          ) : (
            <div className="glass rounded-2xl p-16 text-center h-full flex flex-col items-center justify-center relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-rail-cyan/5 to-rail-purple/5 animate-pulse"></div>
              <div className="w-24 h-24 rounded-full border border-rail-cyan/20 flex items-center justify-center mb-6 relative z-10 shadow-[0_0_30px_rgba(0,240,255,0.1)]">
                <span className="text-4xl">🔮</span>
              </div>
              <h3 className="text-lg font-display tracking-wider text-rail-cyan mb-2 relative z-10 text-glow-cyan">AWAITING PARAMETERS</h3>
              <p className="text-rail-ghost text-sm font-mono relative z-10">Enter train parameters to initialise the Neural Engine</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
