import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/landing/LandingPage';
import PassengerDashboard from './pages/passenger/PassengerDashboard';
import OperatorDashboard from './pages/operator/OperatorDashboard';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/passenger/*" element={<PassengerDashboard />} />
        <Route path="/operator/*" element={<OperatorDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}
