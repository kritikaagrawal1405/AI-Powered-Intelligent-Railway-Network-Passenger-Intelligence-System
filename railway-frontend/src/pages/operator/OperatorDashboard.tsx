import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from '../../components/sidebar/Sidebar';
import Navbar from '../../components/navbar/Navbar';
import NetworkGraph from './NetworkGraph';
import CascadeSimulation from './CascadeSimulation';
import CongestionPanel from './CongestionPanel';
import ResilienceAnalysis from './ResilienceAnalysis';
import TrainMonitor from './TrainMonitor';

const operatorNav = [
  {
    label: 'Network Graph',
    path: '/operator/graph',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M17 12h-5v5m0-5V7m5 5a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    label: 'Cascade Sim',
    path: '/operator/cascade',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  {
    label: 'Congestion',
    path: '/operator/congestion',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    label: 'Resilience',
    path: '/operator/resilience',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
  {
    label: 'Train Monitor',
    path: '/operator/monitor',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10l1 1h10l1-1z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 8h4l3 3v4l-1 1h-2" />
      </svg>
    ),
  },
];

export default function OperatorDashboard() {
  return (
    <div className="flex h-screen overflow-hidden bg-rail-blue">
      <Sidebar
        items={operatorNav}
        title="OPERATOR"
        subtitle="Control Center"
        accentColor="#ffd700"
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar title="RAILWAY OPERATIONS CENTER" accentColor="#ffd700" />

        <main className="flex-1 overflow-auto p-6"
          style={{ background: 'radial-gradient(ellipse at top, rgba(13,32,68,0.5) 0%, transparent 70%)' }}>
          <Routes>
            <Route path="/" element={<Navigate to="graph" replace />} />
            <Route path="graph" element={<NetworkGraph />} />
            <Route path="cascade" element={<CascadeSimulation />} />
            <Route path="congestion" element={<CongestionPanel />} />
            <Route path="resilience" element={<ResilienceAnalysis />} />
            <Route path="monitor" element={<TrainMonitor />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
