import { create } from 'zustand'
import type { LiveTrain, Incident, WSTickPayload, WSInitPayload } from '../types'

interface LiveState {
  // Connection
  connected: boolean
  wsError: boolean

  // Live sim state — updated every 2s
  tick: number
  simTime: string | null
  trains: LiveTrain[]
  incidents: Incident[]
  topDelays: Array<{ code: string; name: string; delay: number }>
  systemDelay: number
  congestedCount: number
  stationDelays: Record<string, number>
  stationCongestion: Record<string, number>

  // Actions
  setConnected: (v: boolean) => void
  setError: () => void
  applyTick: (data: WSTickPayload) => void
  applyInit: (data: WSInitPayload) => void
}

const SMOOTH_ALPHA_DELAY = 0.25
const SMOOTH_ALPHA_CONG = 0.25

export const useLiveStore = create<LiveState>((set) => ({
  connected: false,
  wsError: false,
  tick: 0,
  simTime: null,
  trains: [],
  incidents: [],
  topDelays: [],
  systemDelay: 0,
  congestedCount: 0,
  stationDelays: {},
  stationCongestion: {},

  setConnected: (v) => set({ connected: v, wsError: false }),
  setError: () => set({ connected: false, wsError: true }),

  applyTick: (data) => set((prev) => {
    const smoothDelays: Record<string, number> = {}
    const smoothCong: Record<string, number> = {}
    const MAX_STEP_DELAY = 1.2      // max minutes change per tick
    const MAX_STEP_CONG  = 0.04     // max congestion change per tick (0–1)

    Object.entries(data.station_delays).forEach(([code, val]) => {
      const prevVal = prev.stationDelays[code] ?? val
      const delta = val - prevVal
      const clamped = Math.abs(delta) > MAX_STEP_DELAY
        ? prevVal + Math.sign(delta) * MAX_STEP_DELAY
        : val
      smoothDelays[code] = prevVal * (1 - SMOOTH_ALPHA_DELAY) + clamped * SMOOTH_ALPHA_DELAY
    })
    Object.entries(data.station_congestion).forEach(([code, val]) => {
      const prevVal = prev.stationCongestion[code] ?? val
      const delta = val - prevVal
      const clamped = Math.abs(delta) > MAX_STEP_CONG
        ? prevVal + Math.sign(delta) * MAX_STEP_CONG
        : val
      smoothCong[code] = prevVal * (1 - SMOOTH_ALPHA_CONG) + clamped * SMOOTH_ALPHA_CONG
    })

    const sysPrev = prev.systemDelay ?? data.system_delay
    const sysDelta = data.system_delay - sysPrev
    const sysClamped = Math.abs(sysDelta) > MAX_STEP_DELAY
      ? sysPrev + Math.sign(sysDelta) * MAX_STEP_DELAY
      : data.system_delay
    const sysSmooth = sysPrev * 0.6 + sysClamped * 0.4

    return {
      tick: data.tick,
      simTime: data.sim_time,
      trains: data.trains,
      incidents: data.incidents,
      topDelays: data.top_delays,
      systemDelay: sysSmooth,
      congestedCount: data.congested_count,
      stationDelays: smoothDelays,
      stationCongestion: smoothCong,
    }
  }),

  applyInit: (data) => set({
    trains: data.trains,
    incidents: data.incidents,
    stationDelays: Object.fromEntries((data.stations || []).map((s) => [s.code, s.delay])),
    stationCongestion: Object.fromEntries((data.stations || []).map((s) => [s.code, s.congestion])),
  }),
}))
