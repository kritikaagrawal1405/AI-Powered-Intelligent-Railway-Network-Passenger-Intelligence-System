# RailMind — AI-Powered Railway Intelligence Platform

A modern, railway-themed frontend for the Indian Railway AI Intelligence System.

## ✨ Features

### 🚆 Passenger Dashboard
- **Train Search** — Find trains with AI delay probability, congestion risk, and ticket confirmation chance
- **Ticket Predictor** — ML-based confirmation probability with animated gauge chart
- **Delay Forecast** — Predict train delays with radar risk analysis
- **Network Map** — Interactive Leaflet map with station nodes, route overlays, real-time status
- **Demand Insights** — Charts for busiest stations, seasonal demand, peak routes
- **AI Assistant** — Chat interface powered by backend NLP assistant

### 🛤️ Operator Control Center
- **Network Topology** — Canvas-based animated graph with 15 stations, live congestion coloring, train particles
- **Cascade Simulation** — Configure delay origin, simulate propagation through network
- **Congestion Analysis** — Hotspot detection, corridor analysis, pie charts
- **Resilience Analysis** — Network health radar, critical node matrix, community structure
- **Train Monitor** — Live train tracking with delay alerts, progress bars, filter controls

## 🚀 Setup

### Prerequisites
- Node.js 18+
- Backend server running at `http://localhost:8000` (optional — falls back to mock data)

### Install & Run

```bash
cd railway-intelligence
npm install
npm run dev
```

Visit: http://localhost:5173

### Backend Setup (Optional for live data)

```bash
cd railway-backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## 🏗️ Project Structure

```
src/
├── components/
│   ├── navbar/       Navbar with live clock
│   └── sidebar/      Navigation sidebar
├── pages/
│   ├── landing/      Animated entry page
│   ├── passenger/    6 passenger features
│   └── operator/     5 operator features
├── services/
│   └── api.ts        Centralized API layer with mock fallback
└── App.tsx           Router
```

## 🎨 Design

- **Color Palette**: Deep Navy (#0a1628), Steel (#1a3a5c), Cyan (#00d4ff), Yellow (#ffd700)
- **Fonts**: Bebas Neue (display), DM Sans (body), JetBrains Mono (data)
- **Theme**: Railway command center — glassmorphism, glowing nodes, animated tracks
- **Maps**: Leaflet with dark CartoDB tiles

## 🔌 API Integration

All API calls centralized in `src/services/api.ts`:

```typescript
import { networkAPI, delayAPI, ticketAPI, congestionAPI } from './services/api';

// Auto-fallback to mock data if backend unavailable
const summary = await networkAPI.getSummary();
```

Backend: `http://localhost:8000/api/v1/...`
