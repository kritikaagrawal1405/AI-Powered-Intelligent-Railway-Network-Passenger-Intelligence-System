/// <reference types="vite/client" />
import axios from 'axios';

// The base URL must be set in the .env file
export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Global error handler
    console.error('[API Error]:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ─── Helper methods for fetching and posting without mock fallbacks ───

async function safeGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const res = await api.get<T>(url, { params });
  return res.data;
}

async function safePost<T>(url: string, data: unknown): Promise<T> {
  const res = await api.post<T>(url, data);
  return res.data;
}

// ─── Network APIs ─────────────────────────────────────────────────────────

export const networkAPI = {
  getSummary: () => api.get('/api/v1/network/summary').then(res => res.data),
  getStations: () => api.get('/api/v1/network/stations').then(res => res.data),
  getTopology: () => api.get('/api/v1/network/topology').then(res => res.data),
  getCriticalStations: (n = 10) => api.get('/api/v1/network/critical-stations', { params: { n } }).then(res => res.data),
  getDelayStats: (station: string) => api.get(`/api/v1/network/delay-stats/${encodeURIComponent(station)}`).then(res => res.data),
  getNeighbors: (station: string) => api.get(`/api/v1/network/neighbors/${encodeURIComponent(station)}`).then(res => res.data),
};

// ─── Delay APIs ───────────────────────────────────────────────────────────

export const delayAPI = {
  predict: (data: {
    avg_delay_min?: number;
    significant_delay_ratio?: number;
    on_time_ratio?: number;
    delay_risk_score?: number;
    stop_number?: number;
    betweenness_centrality?: number;
    median_delay_min?: number;
  }) => safePost<any>('/api/v1/delay/predict', data),
};

// ─── Ticket APIs ──────────────────────────────────────────────────────────

export const ticketAPI = {
  predictConfirmation: (data: {
    seat_alloted?: number;
    duration_minutes?: number;
    km?: number;
    fair?: number;
    coaches?: number;
    age?: number;
    is_online?: number;
    is_premium_train?: number;
    meal_booked?: number;
  }) => safePost<any>('/api/v1/ticket/confirm', data),

  predictWLConfirmation: (data: { wl_number: number; days_before: number }) =>
    safePost<any>('/api/v1/ticket/wl-confirm', data),

  rankTrainsByWL: (data: { source: string; destination: string; wl_number: number; days_before: number }) =>
    safePost<any>('/api/v1/ticket/wl-rank-trains', data),
};

// ─── Cascade APIs ─────────────────────────────────────────────────────────

export const cascadeAPI = {
  simulate: (data: { station: string; initial_delay: number; max_depth?: number }) =>
    safePost<any>('/api/v1/cascade/simulate', data),
  getVulnerableStations: (n = 10) => safeGet<any>('/api/v1/cascade/vulnerable-stations', { n }),
};

// ─── Congestion APIs ──────────────────────────────────────────────────────

export const congestionAPI = {
  getSummary: () => safeGet<any>('/api/v1/congestion/summary'),
  getHotspots: (n = 10) => safeGet<any>('/api/v1/congestion/hotspots', { n }),
  getCorridors: (n = 10) => safeGet<any>('/api/v1/congestion/corridors', { n }),
  getStationCongestion: (station: string) => safePost<any>('/api/v1/congestion/station', { station }),
};

// ─── Resilience APIs ──────────────────────────────────────────────────────

export const resilienceAPI = {
  getSummary: () => safeGet<any>('/api/v1/resilience/summary'),
  getCriticalNodes: (n = 10) => safeGet<any>('/api/v1/resilience/critical-nodes', { n }),
  getCommunities: (algorithm = 'greedy_modularity') => safeGet<any>('/api/v1/resilience/communities', { algorithm }),
  simulateRemoval: (data: { stations: string[] }) =>
    safePost<any>('/api/v1/resilience/simulate-removal', data),
};

// ─── Passenger APIs ───────────────────────────────────────────────────────

export const passengerAPI = {
  getSummary: () => safeGet<any>('/api/v1/passenger/summary'),
  getDemandSummary: () => safeGet<any>('/api/v1/passenger/demand-summary'),
  getBusiestStations: (n = 10) => safeGet<any>('/api/v1/passenger/busiest-stations', { n }),
  getSeasonalDemand: () => safeGet<any>('/api/v1/passenger/seasonal-demand'),
  getOvercrowdedRoutes: (month = 11) => safeGet<any>('/api/v1/passenger/overcrowded-routes', { month }),
  getRouteDemand: (source: string, destination: string) => safePost<any>('/api/v1/passenger/route-demand', { source, destination }),
  getStationProfile: (station: string) => safePost<any>('/api/v1/passenger/station-profile', { station }),
};

// ─── Route APIs ───────────────────────────────────────────────────────────

export const routeAPI = {
  find: (source: string, destination: string) =>
    safePost<any>('/api/v1/route/find', { source, destination }),
  findAlternatives: (source: string, destination: string, blockedStations?: string[], n_alternatives = 2) =>
    safePost<any>('/api/v1/route/alternatives', {
      source, destination,
      blocked_stations: blockedStations ?? [],
      n_alternatives,
    }),
};

// ─── Travel Intelligence APIs ─────────────────────────────────────────────

export const travelAPI = {
  getAdvisory: (data: { source: string; destination: string; month?: number; wl_number?: number; days_before?: number }) =>
    safePost<any>('/api/v1/travel/advisory', data),
  getCrowdEstimate: (data: { station: string; month?: number; hour?: number }) =>
    safePost<any>('/api/v1/travel/crowd-estimate', data),
  getBookingGuidance: (data: {
    source: string; destination: string; wl_number?: number;
    days_before?: number; month?: number;
  }) => safePost<any>('/api/v1/travel/booking-guidance', data),
};

// ─── Cancellation APIs ────────────────────────────────────────────────────

export const cancellationAPI = {
  predict: (data: {
    station?: string; train_type?: string; days_before?: number;
    month?: number; wl_number?: number; occupancy_pct?: number;
  }) => safePost<any>('/api/v1/cancellation/predict', data),
};

// ─── Optimization APIs ────────────────────────────────────────────────────

export const optimizationAPI = {
  getSummary: () => safeGet<any>('/api/v1/optimize/summary'),
  getCorridors: (n = 10) => safeGet<any>('/api/v1/optimize/corridors', { n }),
};

// ─── Assistant API ────────────────────────────────────────────────────────

export const assistantAPI = {
  ask: (query: string) => safePost<any>('/api/v1/assistant/ask', { query }),
};

// ─── Live APIs ────────────────────────────────────────────────────────────

export const liveAPI = {
  getStatus: () => safeGet<any>('/api/v1/live/status'),
  getTrainStatus: (trainNumber: string) => safeGet<any>(`/api/v1/live/train/${trainNumber}`),
  getStationBoard: (stationCode: string) => safeGet<any>(`/api/v1/live/station/${stationCode}`),
  getLiveSearch: (q: string, limit = 10) => safeGet<any>('/api/v1/live/search', { q, limit }),
};

// ─── Simulation APIs ──────────────────────────────────────────────────────

export const simulationAPI = {
  getLiveTrains: (time?: string) => safeGet<any>('/api/v1/simulation/live-trains', time ? { time } : {}),
  simulateDelay: (trainId: string, delayMinutes: number) => safePost<any>('/api/v1/simulation/delay', { train_id: trainId, delay_minutes: delayMinutes }),
};

export default api;
