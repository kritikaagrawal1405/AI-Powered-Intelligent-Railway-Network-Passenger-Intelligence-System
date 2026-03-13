import { useState, useEffect } from 'react'
import { useLiveStore } from '../../store/liveStore'
import { formatIST } from '../../utils/helpers'
import { Bell, AlertTriangle } from 'lucide-react'
import { cn } from '../../utils/helpers'

interface NavbarProps {
  title: string
}

export default function Navbar({ title }: NavbarProps) {
  const { incidents, tick } = useLiveStore()
  const [time, setTime] = useState(formatIST())

  useEffect(() => {
    const t = setInterval(() => setTime(formatIST()), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <header className="h-14 border-b border-bg-border flex items-center justify-between px-6 bg-bg-secondary/90 backdrop-blur-md sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-display font-semibold text-text-primary">{title}</h1>
        <span className="text-[10px] font-mono text-text-muted border border-bg-border rounded-lg px-2 py-0.5">
          T{tick}
        </span>
      </div>

      <div className="flex items-center gap-3">
        {/* IST Clock */}
        <div className="text-xs font-mono text-text-muted">
          <span className="text-text-secondary">IST</span> {time}
        </div>

        {/* Incident alert */}
        {incidents.length > 0 ? (
          <div className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-mono',
            'bg-rail-red/10 border border-rail-red/30 text-rail-red animate-pulse'
          )}>
            <AlertTriangle size={11} />
            {incidents.length} ACTIVE
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-text-muted">
            <Bell size={11} />
            NOMINAL
          </div>
        )}
      </div>
    </header>
  )
}
