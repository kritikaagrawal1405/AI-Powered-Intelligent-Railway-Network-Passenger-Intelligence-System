import { ReactNode } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Sidebar from './components/sidebar/Sidebar'
import { useWebSocket } from './hooks/useWebSocket'
import { useAuthStore } from './store/authStore'

import PassengerDashboard from './pages/PassengerDashboard'
import OperatorDashboard  from './pages/OperatorDashboard'
import NetworkMap         from './pages/NetworkMap'
import DelayRadar         from './pages/DelayRadar'
import { Congestion }     from './pages/Congestion'
import Vulnerability      from './pages/Vulnerability'
import TicketAI           from './pages/TicketAI'
import { Routes as RoutesPage, Assistant, Analytics } from './pages/misc'
import Login              from './pages/Login'
import OperatorTopology   from './pages/OperatorTopology'

function RequireAuth({ children, role }: { children: ReactNode; role?: 'passenger' | 'operator' }) {
  const { user, hydrate, loading } = useAuthStore()

  if (!user && !loading) {
    // Kick off hydration but don't block render; redirect to login
    void hydrate()
    return <Navigate to="/login" replace />
  }

  if (role && user && user.role !== role) {
    return <Navigate to={user.role === 'operator' ? '/operator' : '/passenger'} replace />
  }

  return <>{children}</>
}

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } }
})

function AppInner() {
  useWebSocket()
  return (
    <div className="flex h-screen bg-bg-primary overflow-hidden">
      <Sidebar />
      <main className="flex-1 ml-56 overflow-hidden flex flex-col">
        <Routes>
          <Route path="/login"         element={<Login />} />

          <Route
            path="/"
            element={
              <RequireAuth>
                <Navigate to="/passenger" replace />
              </RequireAuth>
            }
          />

          <Route
            path="/passenger"
            element={
              <RequireAuth role="passenger">
                <PassengerDashboard />
              </RequireAuth>
            }
          />
          <Route
            path="/operator"
            element={
              <RequireAuth role="operator">
                <OperatorDashboard />
              </RequireAuth>
            }
          />
          <Route
            path="/operator-topology"
            element={
              <RequireAuth role="operator">
                <OperatorTopology />
              </RequireAuth>
            }
          />

          <Route
            path="/network"
            element={
              <RequireAuth>
                <NetworkMap />
              </RequireAuth>
            }
          />
          <Route
            path="/delay"
            element={
              <RequireAuth role="operator">
                <DelayRadar />
              </RequireAuth>
            }
          />
          <Route
            path="/congestion"
            element={
              <RequireAuth role="operator">
                <Congestion />
              </RequireAuth>
            }
          />
          <Route
            path="/vulnerability"
            element={
              <RequireAuth role="operator">
                <Vulnerability />
              </RequireAuth>
            }
          />
          <Route
            path="/ticket"
            element={
              <RequireAuth role="passenger">
                <TicketAI />
              </RequireAuth>
            }
          />
          <Route
            path="/routes"
            element={
              <RequireAuth role="passenger">
                <RoutesPage />
              </RequireAuth>
            }
          />
          <Route
            path="/assistant"
            element={
              <RequireAuth>
                <Assistant />
              </RequireAuth>
            }
          />
          <Route
            path="/analytics"
            element={
              <RequireAuth role="operator">
                <Analytics />
              </RequireAuth>
            }
          />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AppInner />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
