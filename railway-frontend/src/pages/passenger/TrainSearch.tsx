import { useState } from 'react';
import { routeAPI, congestionAPI, delayAPI, ticketAPI } from '../../services/api';

const STATIONS = [
  'New Delhi', 'Mumbai Central', 'Howrah Jn', 'Chennai Central', 'Bangalore City',
  'Bhopal Jn', 'Nagpur', 'Ahmedabad Jn', 'Lucknow', 'Patna Jn', 'Hyderabad',
  'Pune Jn', 'Jaipur', 'Vijayawada Jn', 'Secunderabad Jn', 'Surat', 'Kanpur',
  'Agra Cantt', 'Varanasi', 'Amritsar', 'Indore', 'Thiruvananthapuram',
];

interface TrainResult {
  train_no: string;
  train_name: string;
  source: string;
  dest: string;
  status: string;
  delay: number;
  confirmProb?: number;
  congestionRisk?: string;
}

function RiskBadge({ level }: { level: string }) {
  const map: Record<string, string> = {
    Low: 'badge-low', Medium: 'badge-medium', High: 'badge-high', Critical: 'badge-critical',
    low: 'badge-low', medium: 'badge-medium', high: 'badge-high', critical: 'badge-critical',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-mono ${map[level] ?? 'badge-low'}`}>
      {level}
    </span>
  );
}

function ConfirmGauge({ probability }: { probability: number }) {
  const pct = Math.round(probability * 100);
  const color = pct >= 70 ? '#00ff88' : pct >= 40 ? '#ffd700' : '#ff3b3b';
  const circumference = 2 * Math.PI * 20;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="flex items-center gap-2">
      <svg width="44" height="44" viewBox="0 0 44 44">
        <circle cx="22" cy="22" r="20" fill="none" stroke="rgba(26,58,92,0.8)" strokeWidth="3" />
        <circle
          cx="22" cy="22" r="20" fill="none"
          stroke={color} strokeWidth="3"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 22 22)"
          style={{ filter: `drop-shadow(0 0 4px ${color})` }}
        />
        <text x="22" y="26" textAnchor="middle" fill={color} fontSize="9" fontFamily="JetBrains Mono" fontWeight="600">
          {pct}%
        </text>
      </svg>
      <span className="text-xs font-mono" style={{ color }}>
        {pct >= 70 ? 'Likely' : pct >= 40 ? 'Possible' : 'Unlikely'}
      </span>
    </div>
  );
}

export default function TrainSearch() {
  const [source, setSource] = useState('');
  const [destination, setDestination] = useState('');
  const [date, setDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<TrainResult[]>([]);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!source || !destination) {
      setError('Please enter both source and destination.');
      return;
    }
    setError('');
    setLoading(true);
    setSearched(false);

    try {
      // Call backend to search and rank trains by confirmation probability
      const response = await ticketAPI.rankTrainsByWL({
        source,
        destination,
        wl_number: 10,
        days_before: 5
      });

      const backendTrains = response.trains || [];

      const trains = backendTrains.map((t: any, i: number) => ({
        train_no: t.train_no || `TR${String(i).padStart(4, '0')}`,
        train_name: t.train_name || 'Express Train',
        source: source,
        dest: destination,
        status: t.delay_minutes && t.delay_minutes > 0 ? 'Delayed' : 'On Time',
        delay: t.delay_minutes || 0,
        confirmProb: t.confirmation_probability ?? 0.5,
        congestionRisk: t.congestion_risk ?? 'Low',
      }));

      setResults(trains);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch trains from the server. Please check your connection.');
      setResults([]);
    } finally {
      setLoading(false);
      setSearched(true);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-display tracking-widest text-white mb-1">TRAIN SEARCH</h1>
        <p className="text-rail-ghost text-sm">Find trains with AI-powered delay and congestion analysis</p>
      </div>

      {/* Search Form */}
      <div className="glass rounded-2xl p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs font-mono text-rail-ghost uppercase tracking-wider mb-2">From Station</label>
            <input
              list="stations-from"
              value={source}
              onChange={e => setSource(e.target.value)}
              placeholder="e.g. New Delhi"
              className="rail-input w-full px-3 py-2.5 rounded-lg text-sm"
            />
            <datalist id="stations-from">
              {STATIONS.map(s => <option key={s} value={s} />)}
            </datalist>
          </div>

          <div>
            <label className="block text-xs font-mono text-rail-ghost uppercase tracking-wider mb-2">To Station</label>
            <input
              list="stations-to"
              value={destination}
              onChange={e => setDestination(e.target.value)}
              placeholder="e.g. Mumbai Central"
              className="rail-input w-full px-3 py-2.5 rounded-lg text-sm"
            />
            <datalist id="stations-to">
              {STATIONS.filter(s => s !== source).map(s => <option key={s} value={s} />)}
            </datalist>
          </div>

          <div>
            <label className="block text-xs font-mono text-rail-ghost uppercase tracking-wider mb-2">Travel Date</label>
            <input
              type="date"
              value={date}
              onChange={e => setDate(e.target.value)}
              className="rail-input w-full px-3 py-2.5 rounded-lg text-sm"
              style={{ colorScheme: 'dark' }}
            />
          </div>
        </div>

        {error && <p className="text-rail-red text-xs mb-3">{error}</p>}

        <button
          onClick={handleSearch}
          disabled={loading}
          className="btn-primary px-8 py-2.5 rounded-lg text-sm flex items-center gap-2">
          {loading ? (
            <>
              <span className="spinner w-4 h-4" />
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <span>Search Trains</span>
            </>
          )}
        </button>
      </div>

      {/* Results */}
      {searched && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-mono text-rail-ghost uppercase tracking-wider">
              {results.length} trains found {source && destination ? `· ${source} → ${destination}` : ''}
            </h2>
            <span className="text-xs font-mono text-rail-cyan/60">AI analysis active</span>
          </div>

          <div className="space-y-3">
            {results.map((train, i) => (
              <div
                key={train.train_no}
                className="glass rounded-xl p-5 border border-white/5 hover:border-rail-cyan/20 transition-all duration-200"
                style={{ animationDelay: `${i * 60}ms` }}>
                <div className="flex items-start justify-between flex-wrap gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-xs font-mono bg-rail-cyan/10 text-rail-cyan px-2 py-0.5 rounded border border-rail-cyan/20">
                        #{train.train_no}
                      </span>
                      <h3 className="font-display tracking-wider text-white text-lg">{train.train_name}</h3>
                    </div>
                    <p className="text-rail-ghost text-sm">{train.source} → {train.dest}</p>
                  </div>

                  <div className="flex flex-wrap items-center gap-6">
                    {/* Delay status */}
                    <div className="text-center">
                      <div className="text-xs font-mono text-rail-ghost/60 uppercase mb-1">Delay Risk</div>
                      <div className={`text-lg font-display ${train.delay > 0 ? 'text-rail-yellow' : 'text-rail-green'}`}>
                        {train.delay > 0 ? `+${train.delay} min` : 'ON TIME'}
                      </div>
                    </div>

                    {/* Congestion */}
                    <div className="text-center">
                      <div className="text-xs font-mono text-rail-ghost/60 uppercase mb-1">Congestion</div>
                      <RiskBadge level={train.congestionRisk ?? 'Low'} />
                    </div>

                    {/* Confirmation */}
                    <div className="text-center">
                      <div className="text-xs font-mono text-rail-ghost/60 uppercase mb-1">Confirm Chance</div>
                      <ConfirmGauge probability={train.confirmProb ?? 0.5} />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!searched && !loading && (
        <div className="glass rounded-2xl p-16 text-center border-dashed border border-white/10">
          <div className="text-6xl mb-4 opacity-20">🚂</div>
          <p className="text-rail-ghost text-sm">Enter source and destination to search for trains</p>
        </div>
      )}
    </div>
  );
}
