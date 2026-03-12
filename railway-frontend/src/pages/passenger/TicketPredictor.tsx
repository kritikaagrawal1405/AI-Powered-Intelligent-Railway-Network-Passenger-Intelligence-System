import { useState } from 'react';
import { ticketAPI } from '../../services/api';

interface PredictionResult {
  confirmation_probability: number;
  confidence: string;
  recommendation?: string;
}

function GaugeChart({ probability, label }: { probability: number; label: string }) {
  const pct = Math.round(probability * 100);
  const angle = -135 + (pct / 100) * 270;
  const color = pct >= 70 ? '#00ff88' : pct >= 40 ? '#ffd700' : '#ff3b3b';
  const cx = 100, cy = 100, r = 70;

  // Arc path
  function polarToXY(angleDeg: number, radius: number) {
    const rad = (angleDeg - 90) * (Math.PI / 180);
    return {
      x: cx + radius * Math.cos(rad),
      y: cy + radius * Math.sin(rad),
    };
  }

  function arcPath(startAngle: number, endAngle: number, radius: number) {
    const start = polarToXY(startAngle, radius);
    const end = polarToXY(endAngle, radius);
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`;
  }

  const fillEnd = -135 + (pct / 100) * 270;
  const needle = polarToXY(angle, 52);

  return (
    <svg viewBox="0 0 200 160" className="w-full max-w-xs mx-auto">
      {/* Tick marks */}
      {[0, 25, 50, 75, 100].map((v, i) => {
        const a = -135 + v / 100 * 270;
        const inner = polarToXY(a, 60);
        const outer = polarToXY(a, 72);
        return (
          <line key={i} x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y}
            stroke="rgba(139,168,200,0.3)" strokeWidth="1.5" />
        );
      })}

      {/* Background arc */}
      <path d={arcPath(-135, 135, r)} fill="none" stroke="rgba(26,58,92,0.8)" strokeWidth="12" strokeLinecap="round" />

      {/* Colored segments */}
      <path d={arcPath(-135, -45, r)} fill="none" stroke="rgba(255,59,59,0.3)" strokeWidth="12" />
      <path d={arcPath(-45, 45, r)} fill="none" stroke="rgba(255,215,0,0.3)" strokeWidth="12" />
      <path d={arcPath(45, 135, r)} fill="none" stroke="rgba(0,255,136,0.3)" strokeWidth="12" />

      {/* Fill arc */}
      {pct > 0 && (
        <path
          d={arcPath(-135, fillEnd, r)}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 6px ${color})`, transition: 'all 1s ease' }}
        />
      )}

      {/* Needle */}
      <line
        x1={cx} y1={cy}
        x2={needle.x} y2={needle.y}
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        style={{ filter: `drop-shadow(0 0 4px ${color})` }}
      />
      <circle cx={cx} cy={cy} r="4" fill={color} />

      {/* Center text */}
      <text x={cx} y={cy + 20} textAnchor="middle" fill={color} fontSize="22" fontFamily="Bebas Neue" letterSpacing="2">
        {pct}%
      </text>
      <text x={cx} y={cy + 36} textAnchor="middle" fill="rgba(139,168,200,0.7)" fontSize="9" fontFamily="DM Sans">
        {label}
      </text>

      {/* Labels */}
      {['LOW', 'MED', 'HIGH'].map((l, i) => {
        const angles = [-100, 0, 100];
        const pos = polarToXY(angles[i], 88);
        const colors = ['rgba(255,59,59,0.6)', 'rgba(255,215,0,0.6)', 'rgba(0,255,136,0.6)'];
        return (
          <text key={l} x={pos.x} y={pos.y + 3} textAnchor="middle" fill={colors[i]} fontSize="7" fontFamily="JetBrains Mono">
            {l}
          </text>
        );
      })}
    </svg>
  );
}

export default function TicketPredictor() {
  const [mode, setMode] = useState<'ticket' | 'wl'>('ticket');

  // Ticket confirmation inputs
  const [seatAlloted, setSeatAlloted] = useState('5');
  const [duration, setDuration] = useState('240');
  const [km, setKm] = useState('350');
  const [fare, setFare] = useState('650');
  const [coaches, setCoaches] = useState('20');
  const [age, setAge] = useState('28');
  const [isOnline, setIsOnline] = useState('1');
  const [isPremium, setIsPremium] = useState('0');

  // WL inputs
  const [wlNumber, setWlNumber] = useState('15');
  const [daysBefore, setDaysBefore] = useState('7');

  const [result, setResult] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handlePredict = async () => {
    setLoading(true);
    try {
      let data: PredictionResult;
      if (mode === 'ticket') {
        data = await ticketAPI.predictConfirmation({
          seat_alloted: parseInt(seatAlloted),
          duration_minutes: parseFloat(duration),
          km: parseFloat(km),
          fair: parseFloat(fare),
          coaches: parseInt(coaches),
          age: parseInt(age),
          is_online: parseInt(isOnline),
          is_premium_train: parseInt(isPremium),
        });
      } else {
        data = await ticketAPI.predictWLConfirmation({
          wl_number: parseInt(wlNumber),
          days_before: parseInt(daysBefore),
        });
      }
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-display tracking-widest text-white mb-1">TICKET PREDICTOR</h1>
        <p className="text-rail-ghost text-sm">AI-powered confirmation probability analysis</p>
      </div>

      {/* Mode selector */}
      <div className="flex gap-2">
        {(['ticket', 'wl'] as const).map(m => (
          <button
            key={m}
            onClick={() => { setMode(m); setResult(null); }}
            className={`px-4 py-2 rounded-lg text-xs font-mono uppercase tracking-wider transition-all ${
              mode === m
                ? 'bg-rail-cyan/20 text-rail-cyan border border-rail-cyan/40'
                : 'text-rail-ghost border border-white/10 hover:border-white/20'
            }`}>
            {m === 'ticket' ? 'Ticket Confirmation' : 'Waiting List'}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input form */}
        <div className="glass rounded-2xl p-6">
          <h2 className="text-sm font-mono text-rail-ghost uppercase tracking-wider mb-5">Input Parameters</h2>

          {mode === 'ticket' ? (
            <div className="space-y-4">
              {[
                { label: 'Seat Alloted', value: seatAlloted, setter: setSeatAlloted, type: 'number' },
                { label: 'Duration (min)', value: duration, setter: setDuration, type: 'number' },
                { label: 'Distance (km)', value: km, setter: setKm, type: 'number' },
                { label: 'Fare (₹)', value: fare, setter: setFare, type: 'number' },
                { label: 'Number of Coaches', value: coaches, setter: setCoaches, type: 'number' },
                { label: 'Passenger Age', value: age, setter: setAge, type: 'number' },
              ].map(field => (
                <div key={field.label}>
                  <label className="block text-xs font-mono text-rail-ghost/70 uppercase tracking-wider mb-1.5">
                    {field.label}
                  </label>
                  <input
                    type={field.type}
                    value={field.value}
                    onChange={e => field.setter(e.target.value)}
                    className="rail-input w-full px-3 py-2 rounded-lg text-sm"
                  />
                </div>
              ))}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-rail-ghost/70 uppercase tracking-wider mb-1.5">Online Booking</label>
                  <select value={isOnline} onChange={e => setIsOnline(e.target.value)} className="rail-input w-full px-3 py-2 rounded-lg text-sm">
                    <option value="1">Yes</option>
                    <option value="0">No</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-mono text-rail-ghost/70 uppercase tracking-wider mb-1.5">Premium Train</label>
                  <select value={isPremium} onChange={e => setIsPremium(e.target.value)} className="rail-input w-full px-3 py-2 rounded-lg text-sm">
                    <option value="0">No</option>
                    <option value="1">Yes</option>
                  </select>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-rail-ghost/70 uppercase tracking-wider mb-1.5">Waiting List Number</label>
                <input type="number" value={wlNumber} onChange={e => setWlNumber(e.target.value)}
                  className="rail-input w-full px-3 py-2 rounded-lg text-sm" min="1" max="300" />
              </div>
              <div>
                <label className="block text-xs font-mono text-rail-ghost/70 uppercase tracking-wider mb-1.5">Days Before Journey</label>
                <input type="number" value={daysBefore} onChange={e => setDaysBefore(e.target.value)}
                  className="rail-input w-full px-3 py-2 rounded-lg text-sm" min="1" max="120" />
              </div>
              <div className="glass-light rounded-xl p-4 text-xs text-rail-ghost">
                <p className="mb-1">💡 <strong className="text-white">How it works:</strong></p>
                <p>Our ML model analyzes historical waiting list confirmation patterns to predict whether your ticket will confirm.</p>
              </div>
            </div>
          )}

          <button
            onClick={handlePredict}
            disabled={loading}
            className="btn-primary w-full px-6 py-3 rounded-lg text-sm mt-5 flex items-center justify-center gap-2">
            {loading ? <><span className="spinner w-4 h-4" /> Predicting...</> : '⚡ Predict Confirmation'}
          </button>
        </div>

        {/* Result */}
        <div className="glass rounded-2xl p-6 flex flex-col items-center justify-center">
          {result ? (
            <div className="text-center w-full">
              <h2 className="text-xs font-mono text-rail-ghost uppercase tracking-wider mb-6">Prediction Result</h2>

              <GaugeChart
                probability={result.confirmation_probability}
                label="Confirmation"
              />

              <div className="mt-6 space-y-3">
                <div className="flex items-center justify-between px-4 py-2.5 glass-light rounded-lg">
                  <span className="text-xs font-mono text-rail-ghost uppercase">Probability</span>
                  <span className="font-display text-xl text-rail-cyan">
                    {Math.round(result.confirmation_probability * 100)}%
                  </span>
                </div>

                <div className="flex items-center justify-between px-4 py-2.5 glass-light rounded-lg">
                  <span className="text-xs font-mono text-rail-ghost uppercase">Confidence</span>
                  <span className={`text-sm font-mono ${
                    result.confidence === 'High' ? 'text-rail-green' :
                    result.confidence === 'Medium' ? 'text-rail-yellow' : 'text-rail-red'
                  }`}>{result.confidence}</span>
                </div>

                {result.recommendation && (
                  <div className="px-4 py-3 glass-light rounded-lg text-center">
                    <p className="text-sm text-rail-ghost">{result.recommendation}</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center w-full h-full flex flex-col justify-center items-center relative overflow-hidden rounded-2xl p-8">
              <div className="absolute inset-0 bg-gradient-to-br from-rail-yellow/5 to-rail-cyan/5 animate-pulse"></div>
              <div className="w-24 h-24 rounded-full border border-rail-yellow/20 flex items-center justify-center mb-6 mx-auto relative z-10 shadow-[0_0_30px_rgba(252,211,77,0.15)]">
                <span className="text-4xl">🎫</span>
              </div>
              <h3 className="text-lg font-display tracking-wider text-rail-yellow mb-2 relative z-10 text-glow-yellow">ENTER ITINERARY</h3>
              <p className="text-rail-ghost text-sm font-mono relative z-10">Fill in the parameters and click predict</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
