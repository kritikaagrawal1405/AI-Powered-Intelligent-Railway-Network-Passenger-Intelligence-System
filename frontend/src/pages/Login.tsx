import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function Login() {
  const { user, login, loading, error, hydrate } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    hydrate()
  }, [hydrate])

  useEffect(() => {
    if (!user) return
    if (user.role === 'operator') navigate('/operator', { replace: true })
    else navigate('/passenger', { replace: true })
  }, [user, navigate])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await login(email, password)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary grid-bg px-4">
      <div className="w-full max-w-md card-p border-bg-border/60 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="inline-flex items-center gap-2 mb-2">
            <div className="w-9 h-9 rounded-2xl bg-rail-cyan/10 border border-rail-cyan/40 flex items-center justify-center">
              <span className="text-rail-cyan font-display font-bold text-lg">R</span>
            </div>
            <div className="text-left">
              <p className="text-sm font-display font-semibold text-text-primary tracking-tight">RailIQ</p>
              <p className="text-[10px] font-mono text-text-muted">Unified Passenger & Operator Portal</p>
            </div>
          </div>
          <h1 className="text-xl font-display text-text-primary tracking-wide">Sign in</h1>
          <p className="text-[11px] text-text-muted font-mono mt-1">
            Use your operator or passenger credentials
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label mb-1.5 block">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input w-full"
              placeholder="you@example.com"
              required
            />
          </div>
          <div>
            <label className="label mb-1.5 block">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input w-full"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <div className="text-[11px] font-mono text-rail-red bg-rail-red/10 border border-rail-red/30 rounded-xl px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center mt-2"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="mt-4 space-y-1 text-[10px] text-text-muted font-mono">
          <p className="text-center">Quick demo accounts (no backend required):</p>
          <p className="text-center">
            Passenger — <span className="text-text-secondary">passenger@demo.com</span> / <span className="text-text-secondary">pass123</span>
          </p>
          <p className="text-center">
            Operator — <span className="text-text-secondary">operator@demo.com</span> / <span className="text-text-secondary">ops123</span>
          </p>
        </div>
      </div>
    </div>
  )
}

