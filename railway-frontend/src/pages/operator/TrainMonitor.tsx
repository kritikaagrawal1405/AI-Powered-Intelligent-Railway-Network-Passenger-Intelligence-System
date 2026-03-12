import { useState, useEffect } from 'react';
import { liveAPI } from '../../services/api';

interface Train {
  train_no: string;
  train_name: string;
  source: string;
  dest: string;
  status: string;
  delay: number;
}

function StatusBadge({ status, delay }: { status: string; delay: number }) {
  if (status === 'On Time' || delay === 0) {
    return <span className="badge-low px-2 py-0.5 rounded text-xs font-mono">ON TIME</span>;
  }
  if (delay > 60) {
    return <span className="badge-critical px-2 py-0.5 rounded text-xs font-mono">DELAYED +{delay}m</span>;
  }
  if (delay > 30) {
    return <span className="badge-high px-2 py-0.5 rounded text-xs font-mono">DELAYED +{delay}m</span>;
  }
  return <span className="badge-medium px-2 py-0.5 rounded text-xs font-mono">DELAYED +{delay}m</span>;
}

// Animated train tracker component
function TrainProgressBar({ train }: { train: Train }) {
  const [progress] = useState(20 + Math.random() * 70);
  const color = train.delay > 60 ? '#ff3b3b' : train.delay > 30 ? '#ff6b00' : train.delay > 0 ? '#ffd700' : '#00ff88';

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs font-mono text-rail-ghost/60">
        <span>{train.source.split(' ')[0]}</span>
        <span>{train.dest.split(' ')[0]}</span>
      </div>
      <div className="relative h-1.5 bg-rail-steel/30 rounded-full overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 rounded-full"
          style={{
            width: `${progress}%`,
            background: `linear-gradient(90deg, ${color}40, ${color})`,
          }}
        />
        {/* Train dot */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-rail-blue"
          style={{
            left: `${progress}%`,
            transform: 'translate(-50%, -50%)',
            background: color,
            boxShadow: `0 0 6px ${color}`,
          }}
        />
      </div>
    </div>
  );
}

export default function TrainMonitor() {
  const [trains, setTrains] = useState<Train[]>([]);
  const [filter, setFilter] = useState<'all' | 'delayed' | 'ontime'>('all');
  const [liveStatus, setLiveStatus] = useState<{ status: string; mode: string } | null>(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    async function init() {
      try {
        const s = await liveAPI.getStatus();
        setLiveStatus(s as any);

        // Fetch a default search for initial dummy trains if possible or just rely on API
        const trainSearch = await liveAPI.getLiveSearch('express', 20);
        const searchResults = (trainSearch as any).results || [];
        // Maps nicely if needed
        const mappedTrains = searchResults.map((t: any) => ({
          train_no: t.train_no || '12345',
          train_name: t.train_name || 'Express Train',
          source: t.source || 'Station A',
          dest: t.dest || 'Station B',
          status: 'On Time',
          delay: 0,
        }));
        // Fallback static trains if API fails
        setTrains(mappedTrains.length > 0 ? mappedTrains : [
          { train_no: '12951', train_name: 'Rajdhani Express', source: 'Mumbai Central', dest: 'New Delhi', status: 'On Time', delay: 0 },
          { train_no: '12301', train_name: 'Howrah Rajdhani', source: 'New Delhi', dest: 'Howrah', status: 'Delayed', delay: 42 },
          { train_no: '12621', train_name: 'Tamil Nadu Express', source: 'New Delhi', dest: 'Chennai Central', status: 'Delayed', delay: 28 },
          { train_no: '12001', train_name: 'Shatabdi Express', source: 'New Delhi', dest: 'Bhopal', status: 'On Time', delay: 0 },
        ]);
        setLastUpdate(new Date());
      } catch (err) {
        console.error(err);
      }
    }

    init();

    // Real live updates should be handled by polling or websockets
    // const interval = setInterval(() => {
    //   // Polling logic here
    // }, 30000);

    // return () => clearInterval(interval);
  }, []);

  const filtered = trains.filter(t =>
    filter === 'all' ? true : filter === 'delayed' ? t.delay > 0 : t.delay === 0
  );

  const delayedCount = trains.filter(t => t.delay > 0).length;
  const criticalCount = trains.filter(t => t.delay > 60).length;
  const onTimeCount = trains.filter(t => t.delay === 0).length;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-display tracking-widest text-white mb-1">TRAIN MONITOR</h1>
          <p className="text-rail-ghost text-sm">Real-time train tracking and delay management</p>
        </div>

        <div className="flex items-center gap-2 glass rounded-lg px-3 py-2">
          {liveStatus?.status === 'ok' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-rail-green animate-pulse" />
              <span className="text-xs font-mono text-rail-green">LIVE</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-rail-yellow animate-pulse" />
              <span className="text-xs font-mono text-rail-yellow">DEMO MODE</span>
            </>
          )}
          <span className="text-xs font-mono text-rail-ghost/40 ml-1">
            {lastUpdate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Monitored', value: trains.length, color: '#00d4ff' },
          { label: 'On Time', value: onTimeCount, color: '#00ff88' },
          { label: 'Delayed', value: delayedCount, color: '#ffd700' },
          { label: 'Critical Delays', value: criticalCount, color: '#ff3b3b' },
        ].map(s => (
          <div key={s.label} className="glass rounded-xl p-4 text-center">
            <div className="text-2xl font-display mb-1" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs font-mono text-rail-ghost/60 uppercase">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Alerts */}
      {criticalCount > 0 && (
        <div className="flex items-start gap-3 p-4 rounded-xl"
          style={{ background: 'rgba(255,59,59,0.08)', border: '1px solid rgba(255,59,59,0.2)' }}>
          <span className="text-lg flex-shrink-0">⚠️</span>
          <div>
            <div className="text-sm font-mono text-rail-red font-bold mb-1">CRITICAL DELAY ALERT</div>
            <p className="text-xs text-rail-ghost">
              {criticalCount} train(s) experiencing critical delays (60+ minutes).
              Consider notifying affected passengers and checking cascade impacts.
            </p>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2">
        {(['all', 'delayed', 'ontime'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-1.5 rounded-lg text-xs font-mono uppercase tracking-wider transition-all ${filter === f
              ? 'bg-rail-yellow/20 text-rail-yellow border border-rail-yellow/40'
              : 'text-rail-ghost border border-white/10 hover:border-white/20'
              }`}>
            {f === 'all' ? 'All Trains' : f === 'delayed' ? `Delayed (${delayedCount})` : `On Time (${onTimeCount})`}
          </button>
        ))}
      </div>

      {/* Train list */}
      <div className="space-y-3">
        {filtered.map((train, i) => (
          <div
            key={train.train_no}
            className="glass rounded-xl p-5 border border-white/5 hover:border-rail-yellow/15 transition-all duration-200">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-mono bg-rail-yellow/10 text-rail-yellow px-2 py-0.5 rounded border border-rail-yellow/20">
                    {train.train_no}
                  </span>
                  <h3 className="font-display tracking-wider text-white">{train.train_name}</h3>
                </div>

                <TrainProgressBar train={train} />
              </div>

              <div className="flex items-center justify-end gap-6">
                <div className="text-center">
                  <div className="text-xs font-mono text-rail-ghost/50 uppercase mb-1">Status</div>
                  <StatusBadge status={train.status} delay={train.delay} />
                </div>

                <div className="text-center">
                  <div className="text-xs font-mono text-rail-ghost/50 uppercase mb-1">Route</div>
                  <div className="text-xs text-rail-ghost">
                    {train.source.split(' ')[0]} → {train.dest.split(' ')[0]}
                  </div>
                </div>

                {/* Mini delay bar */}
                <div className="text-center">
                  <div className="text-xs font-mono text-rail-ghost/50 uppercase mb-1">Delay</div>
                  <div className={`text-lg font-display ${train.delay > 60 ? 'text-rail-red' :
                    train.delay > 30 ? 'text-orange-400' :
                      train.delay > 0 ? 'text-rail-yellow' : 'text-rail-green'
                    }`}>
                    {train.delay > 0 ? `+${train.delay}` : '0'}
                    <span className="text-xs font-body"> min</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="glass rounded-xl p-12 text-center">
          <p className="text-rail-ghost text-sm">No trains match the selected filter</p>
        </div>
      )}
    </div>
  );
}
