// ─── Station & Network ──────────────────────────────────────────────────────
export interface Station {
  name: string
  city: string
  zone: string
  lat: number
  lon: number
  category: 'A1' | 'A' | 'B' | 'C'
  platforms: number
  daily_footfall: number
  // live state (injected by API)
  predicted_delay?: number
  congestion_score?: number
  vulnerability_score?: number
  betweenness_centrality?: number
  degree_centrality?: number
  pagerank?: number
  live_delay?: number
  live_congestion?: number
}

export interface NetworkNode extends Station {
  id: string
  label: string
}

export interface NetworkEdge {
  source: string
  target: string
  distance: number
  travel_time: number
  corridor: string
}

export interface NetworkOverview {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
  tick: number
}

// ─── Trains ─────────────────────────────────────────────────────────────────
export type TrainStatus = 'ON_TIME' | 'SLIGHTLY_LATE' | 'LATE' | 'VERY_LATE'

export interface LiveTrain {
  number: string
  name: string
  type: string
  from: string
  to: string
  from_name: string
  to_name: string
  lat: number
  lon: number
  progress: number
  delay: number
  speed: number
  status: TrainStatus
}

// ─── Incidents ──────────────────────────────────────────────────────────────
export type IncidentSeverity = 'MINOR' | 'MODERATE' | 'MAJOR'

export interface Incident {
  id: string
  station: string
  station_name: string
  type: string
  severity: IncidentSeverity
  delay_added: number
  started_at: string
  ttl: number
}

// ─── Dashboard ──────────────────────────────────────────────────────────────
export interface DashboardKPIs {
  active_trains: number
  total_stations: number
  delayed_stations: number
  congested_stations: number
  avg_system_delay: number
  avg_congestion: number
  network_health: number
  on_time_pct: number
}

export interface ForecastDay {
  date: string
  day: string
  avg_delay: number
  risk: 'HIGH' | 'NORMAL'
}

export interface DashboardSummary {
  kpis: DashboardKPIs
  incidents: Incident[]
  forecast_7d: ForecastDay[]
  sim_time: string
  tick: number
}

// ─── Delay ──────────────────────────────────────────────────────────────────
export interface HourlyDelay {
  hour: number
  delay: number
}

export interface CascadeStation {
  station_code: string
  station_name: string
  delay: number
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface DelayForecast {
  station_code: string
  station_name: string
  live_delay: number
  hourly_forecast: HourlyDelay[]
  cascade: CascadeStation[]
  risk: 'HIGH' | 'MEDIUM' | 'LOW'
  history: number[]
  tick: number
}

// ─── Congestion ─────────────────────────────────────────────────────────────
export type CongestionLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export interface CongestionStation {
  station_code: string
  station_name: string
  lat: number
  lon: number
  congestion_score: number
  zone: string
  level: CongestionLevel
  estimated_crowd: number
}

export interface CongestionHeatmap {
  hour: number
  heatmap: CongestionStation[]
  tick: number
}

// ─── Vulnerability ──────────────────────────────────────────────────────────
export interface VulnerabilityStation {
  station_code: string
  station_name: string
  zone: string
  vulnerability_score: number
  betweenness_centrality: number
  pagerank: number
  live_delay: number
  risk_category: 'CRITICAL' | 'HIGH' | 'MEDIUM'
}

export interface VulnerabilityData {
  vulnerability_ranking: VulnerabilityStation[]
  tick: number
}

// ─── Ticket ─────────────────────────────────────────────────────────────────
export interface TicketRequest {
  train_number: string
  travel_class: string
  source_station: string
  dest_station: string
  days_advance: number
  month: number
  day_of_week: number
  wl_number: number
}

export interface TicketPrediction {
  train_number: string
  train_name: string
  confirmation_probability: number
  confirmation_pct: number
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH'
  optimal_booking_days: number
  advice: string[]
  route_delay_impact: number
  alternative_trains: Array<{ number: string; name: string; type: string }>
  tick: number
}

// ─── Routes ─────────────────────────────────────────────────────────────────
export interface OptimalRoute {
  rank: number
  type: 'FASTEST' | 'LEAST_CONGESTED'
  path: string[]
  path_names: string[]
  total_time_mins: number
  total_distance_km: number
  avg_congestion: number
  avg_delay: number
  recommended: boolean
}

export interface RouteResult {
  source: string
  destination: string
  routes: OptimalRoute[]
  tick: number
}

// ─── Analytics ──────────────────────────────────────────────────────────────
export interface ZoneStats {
  zone: string
  avg_delay: number
  avg_congestion: number
  station_count: number
  total_footfall: number
  performance_score: number
}

export interface ZoneAnalytics {
  zones: ZoneStats[]
  tick: number
}

// ─── WebSocket Live State ────────────────────────────────────────────────────
export interface WSTickPayload {
  type: 'tick'
  tick: number
  sim_time: string
  trains: LiveTrain[]
  incidents: Incident[]
  top_delays: Array<{ code: string; name: string; delay: number }>
  system_delay: number
  congested_count: number
  station_delays: Record<string, number>
  station_congestion: Record<string, number>
}

export interface WSInitPayload {
  type: 'init'
  trains: LiveTrain[]
  incidents: Incident[]
  stations: Array<{ code: string; delay: number; congestion: number; name: string }>
}

// ─── Assistant ───────────────────────────────────────────────────────────────
export interface AssistantResponse {
  intent: string
  confidence: number
  response: string
  data: Record<string, unknown>
  tick: number
}

// ─── Station Search ──────────────────────────────────────────────────────────
export interface StationSearchResult {
  code: string
  name: string
  city: string
  zone: string
}
