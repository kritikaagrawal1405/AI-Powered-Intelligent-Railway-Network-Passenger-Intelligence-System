import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

// Animated network background using Canvas
function NetworkCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // Nodes representing stations
    const nodes: Array<{ x: number; y: number; vx: number; vy: number; r: number; color: string }> = [];
    const count = 60;
    const colors = ['#00d4ff', '#ffd700', '#00ff88', '#ff6b00'];

    for (let i = 0; i < count; i++) {
      nodes.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        r: Math.random() * 3 + 1.5,
        color: colors[Math.floor(Math.random() * colors.length)],
      });
    }

    // Train particle
    let trainX = -50;
    const trainY = canvas.height * 0.45;
    let trainProgress = 0;

    let animId: number;
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw edges
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 130) {
            const alpha = (1 - dist / 130) * 0.25;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(0, 212, 255, ${alpha})`;
            ctx.lineWidth = 0.7;
            ctx.stroke();
          }
        }
      }

      // Draw nodes
      for (const n of nodes) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.shadowBlur = 8;
        ctx.shadowColor = n.color;
        ctx.fill();
        ctx.shadowBlur = 0;

        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
        if (n.y < 0 || n.y > canvas.height) n.vy *= -1;
      }

      // Animated train track
      ctx.beginPath();
      ctx.moveTo(0, trainY);
      ctx.lineTo(canvas.width, trainY);
      ctx.strokeStyle = 'rgba(0, 212, 255, 0.15)';
      ctx.lineWidth = 2;
      ctx.setLineDash([20, 10]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Train body
      trainProgress += 0.002;
      trainX = (trainProgress % 1.4 - 0.2) * canvas.width;
      const tx = trainX;
      const ty = trainY - 8;
      const tw = 80;
      const th = 16;

      // Glow
      const grad = ctx.createLinearGradient(tx - 20, ty, tx + tw + 20, ty);
      grad.addColorStop(0, 'rgba(0,212,255,0)');
      grad.addColorStop(0.3, 'rgba(0,212,255,0.6)');
      grad.addColorStop(0.7, 'rgba(0,212,255,0.6)');
      grad.addColorStop(1, 'rgba(0,212,255,0)');
      ctx.fillStyle = grad;
      ctx.fillRect(tx - 20, ty - 4, tw + 40, th + 8);

      // Train rectangle
      ctx.fillStyle = '#00d4ff';
      ctx.shadowBlur = 15;
      ctx.shadowColor = '#00d4ff';
      ctx.beginPath();
      ctx.roundRect(tx, ty, tw, th, 4);
      ctx.fill();
      ctx.shadowBlur = 0;

      // Windows
      for (let w = 0; w < 4; w++) {
        ctx.fillStyle = '#0a1628';
        ctx.fillRect(tx + 8 + w * 18, ty + 4, 10, 8);
      }

      animId = requestAnimationFrame(animate);
    };

    animate();
    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="fixed inset-0 z-0" />;
}

function TypingText({ text, delay = 0 }: { text: string; delay?: number }) {
  const [displayed, setDisplayed] = useState('');
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setStarted(true), delay);
    return () => clearTimeout(t);
  }, [delay]);

  useEffect(() => {
    if (!started) return;
    let i = 0;
    const interval = setInterval(() => {
      setDisplayed(text.slice(0, i + 1));
      i++;
      if (i >= text.length) clearInterval(interval);
    }, 40);
    return () => clearInterval(interval);
  }, [started, text]);

  return <span>{displayed}<span className="animate-pulse text-rail-cyan">|</span></span>;
}

export default function LandingPage() {
  const navigate = useNavigate();
  const [hoveredCard, setHoveredCard] = useState<'passenger' | 'operator' | null>(null);

  return (
    <div className="relative min-h-screen overflow-hidden bg-rail-blue">
      <NetworkCanvas />

      {/* Grid overlay */}
      <div className="fixed inset-0 z-[1] bg-grid-pattern bg-grid opacity-30" />

      {/* Scan line */}
      <div
        className="fixed top-0 left-0 right-0 h-px z-[2] pointer-events-none"
        style={{
          background: 'linear-gradient(90deg, transparent, rgba(0,212,255,0.6), transparent)',
          animation: 'scan 4s linear infinite',
        }}
      />

      {/* Main content */}
      <div className="relative z-10 min-h-screen flex flex-col items-center justify-center px-6">
        {/* Header badge */}
        <div className="mb-8 flex items-center gap-2 px-4 py-2 rounded-full border border-rail-cyan/30 bg-rail-navy/60 backdrop-blur-md">
          <span className="w-2 h-2 rounded-full bg-rail-green animate-pulse" />
          <span className="text-xs font-mono text-rail-ghost tracking-widest uppercase">
            System Online — AI Railway Intelligence Platform
          </span>
        </div>

        {/* Logo / Title */}
        <div className="text-center mb-4">
          <h1 className="text-[5rem] md:text-[8rem] font-display text-white leading-none tracking-widest text-glow-cyan"
            style={{ letterSpacing: '0.15em' }}>
            RAILMIND
          </h1>
          <div className="h-px w-full max-w-lg mx-auto my-4"
            style={{ background: 'linear-gradient(90deg, transparent, #00d4ff, transparent)' }} />
          <p className="text-rail-ghost font-mono text-sm tracking-widest uppercase">
            <TypingText text="AI-Powered Indian Railway Intelligence System" delay={400} />
          </p>
        </div>

        {/* Stats row */}
        <div className="flex gap-8 my-10 flex-wrap justify-center">
          {[
            { label: 'Stations Monitored', value: '312+' },
            { label: 'Active Routes', value: '847' },
            { label: 'ML Accuracy', value: '94.2%' },
            { label: 'Trains Tracked', value: '13,000+' },
          ].map(s => (
            <div key={s.label} className="text-center">
              <div className="text-2xl font-display text-rail-cyan text-glow-cyan">{s.value}</div>
              <div className="text-xs text-rail-ghost font-mono uppercase tracking-wider mt-1">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Dashboard selection cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl w-full mt-4">
          {/* Passenger Card */}
          <button
            onClick={() => navigate('/passenger')}
            onMouseEnter={() => setHoveredCard('passenger')}
            onMouseLeave={() => setHoveredCard(null)}
            className="relative group text-left p-8 rounded-2xl glass border transition-all duration-300 overflow-hidden"
            style={{
              borderColor: hoveredCard === 'passenger' ? 'rgba(0,212,255,0.5)' : 'rgba(0,212,255,0.15)',
              boxShadow: hoveredCard === 'passenger' ? '0 0 40px rgba(0,212,255,0.2), inset 0 0 40px rgba(0,212,255,0.03)' : 'none',
              transform: hoveredCard === 'passenger' ? 'translateY(-4px)' : 'translateY(0)',
            }}>
            {/* Background icon */}
            <div className="absolute right-4 bottom-4 opacity-5 text-[8rem] leading-none select-none">🚆</div>

            <div className="flex items-start gap-4 mb-6">
              <div className="p-3 rounded-xl border border-rail-cyan/30 bg-rail-cyan/10">
                <svg className="w-8 h-8 text-rail-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div>
                <div className="text-xs font-mono text-rail-cyan/60 uppercase tracking-widest mb-1">Dashboard 01</div>
                <h2 className="text-2xl font-display text-white tracking-widest">PASSENGER</h2>
              </div>
            </div>

            <p className="text-rail-ghost text-sm mb-6 leading-relaxed">
              Plan journeys with AI-powered insights. Check train delays, ticket confirmation chances, congestion maps, and get personalized travel guidance.
            </p>

            <div className="flex flex-wrap gap-2 mb-6">
              {['Train Search', 'WL Predictor', 'Delay Forecast', 'Route Map', 'AI Assistant'].map(f => (
                <span key={f} className="px-2 py-1 text-xs font-mono rounded border border-rail-cyan/20 text-rail-ghost bg-rail-cyan/5">
                  {f}
                </span>
              ))}
            </div>

            <div className="flex items-center gap-2 text-rail-cyan font-mono text-sm">
              <span>Enter Dashboard</span>
              <span className="transition-transform duration-200 group-hover:translate-x-2">→</span>
            </div>
          </button>

          {/* Operator Card */}
          <button
            onClick={() => navigate('/operator')}
            onMouseEnter={() => setHoveredCard('operator')}
            onMouseLeave={() => setHoveredCard(null)}
            className="relative group text-left p-8 rounded-2xl glass border transition-all duration-300 overflow-hidden"
            style={{
              borderColor: hoveredCard === 'operator' ? 'rgba(255,215,0,0.5)' : 'rgba(255,215,0,0.15)',
              boxShadow: hoveredCard === 'operator' ? '0 0 40px rgba(255,215,0,0.15), inset 0 0 40px rgba(255,215,0,0.03)' : 'none',
              transform: hoveredCard === 'operator' ? 'translateY(-4px)' : 'translateY(0)',
            }}>
            <div className="absolute right-4 bottom-4 opacity-5 text-[8rem] leading-none select-none">🛤️</div>

            <div className="flex items-start gap-4 mb-6">
              <div className="p-3 rounded-xl border border-rail-yellow/30 bg-rail-yellow/10">
                <svg className="w-8 h-8 text-rail-yellow" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" />
                </svg>
              </div>
              <div>
                <div className="text-xs font-mono text-rail-yellow/60 uppercase tracking-widest mb-1">Dashboard 02</div>
                <h2 className="text-2xl font-display text-white tracking-widest">OPERATOR</h2>
              </div>
            </div>

            <p className="text-rail-ghost text-sm mb-6 leading-relaxed">
              Command center for railway operators. Monitor network topology, simulate delay cascades, analyze congestion, and assess system resilience.
            </p>

            <div className="flex flex-wrap gap-2 mb-6">
              {['Network Map', 'Cascade Sim', 'Congestion', 'Resilience', 'Live Monitor'].map(f => (
                <span key={f} className="px-2 py-1 text-xs font-mono rounded border border-rail-yellow/20 text-rail-ghost bg-rail-yellow/5">
                  {f}
                </span>
              ))}
            </div>

            <div className="flex items-center gap-2 text-rail-yellow font-mono text-sm">
              <span>Enter Command Center</span>
              <span className="transition-transform duration-200 group-hover:translate-x-2">→</span>
            </div>
          </button>
        </div>

        {/* Footer */}
        <div className="mt-16 text-center">
          <p className="text-rail-ghost/40 text-xs font-mono">
            RAILMIND v2.0 · AI-Powered · Indian Railway Network · Built with FastAPI + React
          </p>
        </div>
      </div>
    </div>
  );
}
