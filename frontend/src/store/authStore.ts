import { create } from 'zustand'
import { apiEndpoints } from '../lib/api'

type Role = 'passenger' | 'operator'

interface User {
  id: string
  name: string
  role: Role
}

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  hydrate: () => Promise<void>
}

const DUMMY_USERS: Array<{ email: string; password: string; user: User }> = [
  {
    email: 'passenger@demo.com',
    password: 'pass123',
    user: { id: 'u-passenger', name: 'Demo Passenger', role: 'passenger' },
  },
  {
    email: 'operator@demo.com',
    password: 'ops123',
    user: { id: 'u-operator', name: 'Demo Operator', role: 'operator' },
  },
]

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  loading: false,
  error: null,

  async login(email, password) {
    set({ loading: true, error: null })

    // First try local dummy accounts so you can explore without backend auth
    const dummy = DUMMY_USERS.find(
      (d) => d.email.toLowerCase() === email.toLowerCase() && d.password === password,
    )
    if (dummy) {
      set({ user: dummy.user, token: null, loading: false, error: null })
      return
    }

    // Fall back to real backend auth if available
    try {
      const { data } = await apiEndpoints.login(email, password)
      window.localStorage.setItem('railiq_token', data.token)
      set({ user: data.user, token: data.token, loading: false })
    } catch (e: any) {
      const msg = e?.response?.data?.detail ?? 'Invalid credentials'
      set({ error: msg, loading: false })
    }
  },

  logout() {
    try {
      window.localStorage.removeItem('railiq_token')
    } catch {
      // ignore
    }
    set({ user: null, token: null })
    try {
      apiEndpoints.logout().catch(() => {})
    } catch {
      // ignore
    }
  },

  async hydrate() {
    const token = (() => {
      try {
        return window.localStorage.getItem('railiq_token')
      } catch {
        return null
      }
    })()
    if (!token || get().user) return
    set({ loading: true, error: null })
    try {
      const { data } = await apiEndpoints.me()
      set({ user: data, token, loading: false })
    } catch {
      set({ user: null, token: null, loading: false })
    }
  },
}))

