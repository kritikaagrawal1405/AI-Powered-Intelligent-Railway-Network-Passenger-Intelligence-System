import { NavLink, useNavigate } from 'react-router-dom';
import { LucideIcon } from 'lucide-react';

interface SidebarItem {
  label: string;
  path: string;
  icon: React.ReactNode;
}

interface SidebarProps {
  items: SidebarItem[];
  title: string;
  subtitle: string;
  accentColor?: string;
  onBack?: () => void;
}

export default function Sidebar({ items, title, subtitle, accentColor = '#00d4ff', onBack }: SidebarProps) {
  const navigate = useNavigate();

  return (
    <div className="w-60 min-h-screen flex flex-col glass border-r border-white/5 relative z-10">
      {/* Logo area */}
      <div className="p-5 border-b border-white/5">
        <button
          onClick={onBack ?? (() => navigate('/'))}
          className="flex items-center gap-2 mb-4 text-rail-ghost hover:text-white transition-colors group">
          <svg className="w-4 h-4 transition-transform group-hover:-translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span className="text-xs font-mono uppercase tracking-wider">RailMind</span>
        </button>

        <div>
          <h2 className="font-display text-lg tracking-widest text-white" style={{ color: accentColor }}>
            {title}
          </h2>
          <p className="text-xs font-mono text-rail-ghost/60 mt-1 uppercase tracking-wider">{subtitle}</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 relative overflow-hidden">
        {/* Subtle scanline overlay for the sidebar nav area */}
        <div className="absolute inset-0 scanlines opacity-5 pointer-events-none"></div>
        
        <div className="space-y-1 relative z-10">
          {items.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-300 ${
                  isActive
                    ? 'bg-white/5 font-medium shadow-[inset_0_0_15px_rgba(255,255,255,0.02)]'
                    : 'text-rail-ghost hover:text-white hover:bg-white/5 hover:translate-x-1'
                }`
              }
              style={({ isActive }) =>
                isActive ? {
                  color: accentColor,
                  borderLeft: `2px solid ${accentColor}`,
                  boxShadow: `inset 4px 0 10px -4px ${accentColor}`,
                  paddingLeft: '10px',
                  textShadow: `0 0 8px ${accentColor}`,
                } : {}
              }>
              <span className="flex-shrink-0 transition-transform duration-300 group-hover:scale-110">{item.icon}</span>
              <span className="font-mono text-xs uppercase tracking-wider">{item.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Status indicator */}
      <div className="p-4 border-t border-white/5">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-rail-green animate-pulse" />
          <span className="text-xs font-mono text-rail-ghost/50">SYSTEM ONLINE</span>
        </div>
      </div>
    </div>
  );
}
