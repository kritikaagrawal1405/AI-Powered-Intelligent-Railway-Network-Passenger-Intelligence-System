import { NavLink } from 'react-router-dom'
import { useLiveStore } from '../../store/liveStore'
import { useAuthStore } from '../../store/authStore'
import { cn } from '../../utils/helpers'
import {
  Users, Cog, Network, Clock, Flame,
  ShieldAlert, Ticket, Route, Bot, BarChart3,
  Wifi, WifiOff, AlertTriangle
} from 'lucide-react'

interface NavItem {
  to: string
  icon: React.ElementType
  label: string
  group?: string
  roles?: Array<'passenger' | 'operator'>
}

const NAV_ITEMS: NavItem[] = [
  // Dashboards
  { to: '/passenger',     icon: Users,         label: 'Passenger',     group: 'DASHBOARDS', roles: ['passenger'] },
  { to: '/operator',      icon: Cog,           label: 'Operator',      group: 'DASHBOARDS', roles: ['operator'] },
  // Tools
  { to: '/network',       icon: Network,       label: 'Network Map',   group: 'TOOLS', roles: ['passenger', 'operator'] },
  { to: '/operator-topology', icon: Network,   label: 'Topology',      group: 'TOOLS', roles: ['operator'] },
  { to: '/delay',         icon: Clock,         label: 'Delay Radar',   group: 'TOOLS', roles: ['operator'] },
  { to: '/congestion',    icon: Flame,         label: 'Congestion',    group: 'TOOLS', roles: ['operator'] },
  { to: '/vulnerability', icon: ShieldAlert,   label: 'Vulnerability', group: 'TOOLS', roles: ['operator'] },
  // Planning
  { to: '/ticket',        icon: Ticket,        label: 'Ticket AI',     group: 'PLANNING', roles: ['passenger'] },
  { to: '/routes',        icon: Route,         label: 'Routes',        group: 'PLANNING', roles: ['passenger'] },
  { to: '/assistant',     icon: Bot,           label: 'AI Assistant',  group: 'PLANNING', roles: ['passenger', 'operator'] },
  { to: '/analytics',     icon: BarChart3,     label: 'Analytics',     group: 'PLANNING', roles: ['operator'] },
]

export default function Sidebar() {
  const { connected, wsError, tick, systemDelay, incidents } = useLiveStore()
  const { user, logout } = useAuthStore()

  const groups = [...new Set(NAV_ITEMS.map((n) => n.group))]

  return (
    <aside className="fixed inset-y-0 left-0 w-56 bg-bg-secondary border-r border-bg-border flex flex-col z-50">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-bg-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-rail-cyan/10 border border-rail-cyan/30 flex items-center justify-center">
            <span className="text-rail-cyan font-display font-bold text-sm">R</span>
          </div>
          <div>
            <p className="text-text-primary font-display font-bold text-sm tracking-tight">RailIQ</p>
            <p className="text-[10px] font-mono text-text-muted">AI Intelligence v3.1</p>
          </div>
        </div>
        {user && (
          <div className="mt-3 flex items-center justify-between">
            <div className="text-[10px] font-mono text-text-muted flex flex-col">
              <span className="text-text-primary">{user.name}</span>
              <span className="uppercase tracking-[0.12em] text-text-muted/70">
                {user.role} VIEW
              </span>
            </div>
            <button
              onClick={logout}
              className="text-[9px] font-mono text-text-muted hover:text-rail-cyan"
            >
              LOG OUT
            </button>
          </div>
        )}
      </div>

      {/* WS Status */}
      <div className="px-4 py-3 border-b border-bg-border space-y-2">
        <div className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-xl text-[11px] font-mono',
          connected ? 'bg-rail-green/10 text-rail-green border border-rail-green/20'
          : wsError  ? 'bg-rail-red/10 text-rail-red border border-rail-red/20'
                     : 'bg-bg-elevated text-text-muted border border-bg-border'
        )}>
          {connected ? <Wifi size={11} /> : <WifiOff size={11} />}
          {connected ? `LIVE · T${tick}` : wsError ? 'WS ERROR' : 'CONNECTING...'}
        </div>
        {incidents.length > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rail-red/10 border border-rail-red/20 text-[10px] font-mono text-rail-red">
            <AlertTriangle size={10} />
            {incidents.length} INCIDENT{incidents.length > 1 ? 'S' : ''} ACTIVE
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto px-2 space-y-4">
        {user && groups.map((group) => {
          const items = NAV_ITEMS.filter((n) =>
            n.group === group && (!n.roles || n.roles.includes(user.role))
          )
          if (!items.length) return null
          return (
            <div key={group}>
              <p className="px-3 mb-1 text-[9px] font-mono font-semibold text-text-muted/60 uppercase tracking-widest">
                {group}
              </p>
              <div className="space-y-0.5">
                {items.map(({ to, icon: Icon, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    className={({ isActive }) => cn(
                      'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-body transition-all duration-150',
                      isActive
                        ? 'bg-rail-cyan/10 text-rail-cyan border border-rail-cyan/20'
                        : 'text-text-muted hover:text-text-secondary hover:bg-bg-elevated'
                    )}
                  >
                    {({ isActive }) => (
                      <>
                        <Icon size={15} className={isActive ? 'text-rail-cyan' : ''} />
                        <span className="font-medium">{label}</span>
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          )
        })}
      </nav>

      {/* Footer stats */}
      <div className="px-4 py-4 border-t border-bg-border space-y-2">
        <div className="flex justify-between text-[10px] font-mono text-text-muted">
          <span>SYS DELAY</span>
          <span className={cn(
            systemDelay > 20 ? 'text-rail-red' : systemDelay > 10 ? 'text-rail-amber' : 'text-rail-green'
          )}>
            {systemDelay.toFixed(1)}m
          </span>
        </div>
        <p className="text-[9px] font-mono text-text-muted/40">© 2025 RailIQ · Indian Railways AI</p>
      </div>
    </aside>
  )
}
