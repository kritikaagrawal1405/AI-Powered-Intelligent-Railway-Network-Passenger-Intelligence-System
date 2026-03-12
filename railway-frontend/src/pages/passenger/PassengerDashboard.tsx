import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from '../../components/sidebar/Sidebar';
import Navbar from '../../components/navbar/Navbar';
import TrainSearch from './TrainSearch';
import TicketPredictor from './TicketPredictor';
import DelayPredictor from './DelayPredictor';
import NetworkMap from './NetworkMap';
import DemandInsights from './DemandInsights';
import AIAssistant from './AIAssistant';

const passengerNav = [
  {
    label: 'Train Search',
    path: '/passenger/search',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    ),
  },
  {
    label: 'Ticket Predictor',
    path: '/passenger/ticket',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
      </svg>
    ),
  },
  {
    label: 'Delay Forecast',
    path: '/passenger/delay',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    label: 'Network Map',
    path: '/passenger/map',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
      </svg>
    ),
  },
  {
    label: 'Demand Insights',
    path: '/passenger/demand',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    label: 'AI Assistant',
    path: '/passenger/assistant',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
      </svg>
    ),
  },
];

export default function PassengerDashboard() {
  return (
    <div className="flex h-screen overflow-hidden bg-rail-blue">
      <Sidebar
        items={passengerNav}
        title="PASSENGER"
        subtitle="Travel Intelligence"
        accentColor="#00d4ff"
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar title="PASSENGER DASHBOARD" accentColor="#00d4ff" />

        <main className="flex-1 overflow-auto p-6">
          <Routes>
            <Route path="/" element={<Navigate to="search" replace />} />
            <Route path="search" element={<TrainSearch />} />
            <Route path="ticket" element={<TicketPredictor />} />
            <Route path="delay" element={<DelayPredictor />} />
            <Route path="map" element={<NetworkMap />} />
            <Route path="demand" element={<DemandInsights />} />
            <Route path="assistant" element={<AIAssistant />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
