import { useState, useEffect } from 'react';

interface NavbarProps {
  title: string;
  accentColor?: string;
}

export default function Navbar({ title, accentColor = '#00d4ff' }: NavbarProps) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-14 glass border-b border-white/5 flex items-center justify-between px-6 flex-shrink-0 z-20">
      <div className="flex items-center gap-3">
        <div className="w-1.5 h-6 rounded-full animate-pulse" style={{ background: accentColor, boxShadow: `0 0 15px ${accentColor}` }} />
        <span className="font-display tracking-widest text-lg text-white" style={{ letterSpacing: '0.15em', textShadow: `0 0 10px ${accentColor}` }}>
          {title}
        </span>
      </div>

      <div className="flex items-center gap-6">
        <div className="hidden sm:flex items-center gap-4 text-xs font-mono text-rail-ghost/60">
          <span>IND RAILWAY NETWORK</span>
          <span>|</span>
          <span>AI INTELLIGENCE v2.0</span>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg glass-light">
          <span className="w-1.5 h-1.5 rounded-full bg-rail-green animate-pulse" />
          <span className="text-xs font-mono text-rail-ghost">
            {time.toLocaleTimeString('en-IN', { hour12: false })}
          </span>
        </div>
      </div>
    </header>
  );
}
