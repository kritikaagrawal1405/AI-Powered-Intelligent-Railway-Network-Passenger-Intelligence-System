import { useEffect, useRef } from 'react'
import type { NetworkNode, NetworkEdge, LiveTrain } from '../../types'
import 'leaflet/dist/leaflet.css'

type ColorMode = 'delay' | 'congestion' | 'vulnerability'

interface NetworkMapLeafletProps {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
  mode: ColorMode
  stationDelays: Record<string, number>
  stationCongestion: Record<string, number>
  trains: LiveTrain[]
  tick: number
}

// Use dynamic import to avoid SSR / bundler issues
let L: typeof import('leaflet') | null = null

function nodeColor(
  node: NetworkNode,
  mode: ColorMode,
  delays: Record<string, number>,
  cong: Record<string, number>,
): string {
  if (mode === 'delay') {
    const d = delays[node.id] ?? node.predicted_delay ?? 0
    return d > 30 ? '#ff4757' : d > 10 ? '#ffb347' : '#00ff87'
  }
  if (mode === 'congestion') {
    const c = cong[node.id] ?? node.congestion_score ?? 0
    return c > 0.85 ? '#ff4757' : c > 0.65 ? '#ffb347' : c > 0.4 ? '#00d4ff' : '#00ff87'
  }
  const v = node.vulnerability_score ?? 0
  return v > 0.08 ? '#7c5cbf' : v > 0.05 ? '#ff4757' : '#00d4ff'
}

export default function NetworkMapLeaflet({
  nodes,
  edges,
  mode,
  stationDelays,
  stationCongestion,
  trains,
  tick,
}: NetworkMapLeafletProps) {
  const mapRef = useRef<HTMLDivElement | null>(null)
  const mapInstanceRef = useRef<import('leaflet').Map | null>(null)
  const edgeLayerRef = useRef<import('leaflet').LayerGroup | null>(null)
  const stationLayerRef = useRef<import('leaflet').LayerGroup | null>(null)
  const trainLayerRef = useRef<import('leaflet').LayerGroup | null>(null)

  // Initialize map once
  useEffect(() => {
    let isMounted = true

    async function initMap() {
      if (!L) {
        try {
          L = await import('leaflet')
        } catch (e) {
          console.error('Failed to load Leaflet', e)
          return
        }
      }
      if (!mapRef.current || mapInstanceRef.current || !isMounted) return

      const map = L!.map(mapRef.current, {
        center: [22.5, 80.0],
        zoom: 5,
        zoomControl: true,
        attributionControl: false,
      })

      mapInstanceRef.current = map

      // Dark basemap covering India region
      L!.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap, © CartoDB',
        maxZoom: 18,
      }).addTo(map)

      edgeLayerRef.current = L!.layerGroup().addTo(map)
      stationLayerRef.current = L!.layerGroup().addTo(map)
      trainLayerRef.current = L!.layerGroup().addTo(map)
    }

    initMap()

    return () => {
      isMounted = false
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
      edgeLayerRef.current = null
      stationLayerRef.current = null
      trainLayerRef.current = null
    }
  }, [])

  // Draw static network (stations + edges) whenever data or mode changes
  useEffect(() => {
    if (!L || !mapInstanceRef.current || !edgeLayerRef.current || !stationLayerRef.current) return
    if (!nodes.length) return

    edgeLayerRef.current.clearLayers()
    stationLayerRef.current.clearLayers()

    const stationMap = new Map<string, NetworkNode>()
    nodes.forEach((n) => stationMap.set(n.id, n))

    const drawnEdges = new Set<string>()

    edges.forEach((edge) => {
      const key1 = `${edge.source}-${edge.target}`
      const key2 = `${edge.target}-${edge.source}`
      if (drawnEdges.has(key1) || drawnEdges.has(key2)) return

      const s1 = stationMap.get(edge.source)
      const s2 = stationMap.get(edge.target)
      if (!s1 || !s2) return
      if (s1.lat == null || s1.lon == null || s2.lat == null || s2.lon == null) return

      L!.polyline(
        [
          [s1.lat, s1.lon],
          [s2.lat, s2.lon],
        ],
        {
          color: '#00f0ff',
          weight: 1.2,
          opacity: 0.35,
          dashArray: '6 4',
        },
      ).addTo(edgeLayerRef.current!)

      drawnEdges.add(key1)
    })

    nodes.forEach((station) => {
      if (station.lat == null || station.lon == null) return

      const delay = stationDelays[station.id] ?? station.predicted_delay ?? 0
      const color = nodeColor(station, mode, stationDelays, stationCongestion)

      const sizeBase = Math.max(4, Math.min(13, station.daily_footfall / 110000 * 10))

      const icon = L!.divIcon({
        className: 'custom-station-icon',
        html: `
          <div style="
            width: ${sizeBase + 4}px;
            height: ${sizeBase + 4}px;
            border-radius: 50%;
            background: ${color};
            border: 2px solid rgba(255,255,255,0.35);
            box-shadow: 0 0 8px ${color}, 0 0 18px ${color}40;
            cursor: pointer;
          "></div>
        `,
        iconSize: [sizeBase + 4, sizeBase + 4],
        iconAnchor: [(sizeBase + 4) / 2, (sizeBase + 4) / 2],
      })

      const marker = L!.marker([station.lat, station.lon], { icon })

      const tooltipHtml = `
        <div class="font-mono text-[10px]">
          <div class="font-semibold text-white mb-1">${station.label}</div>
          <div class="text-rail-ghost">Zone: <span class="text-white">${station.zone}</span></div>
          <div class="text-rail-ghost">Category: <span class="text-white">${station.category}</span></div>
          <div class="text-rail-ghost">Footfall: <span class="text-white">${(station.daily_footfall / 1000).toFixed(0)}K/day</span></div>
          <div style="color:${delay > 30 ? '#ff4757' : delay > 10 ? '#ffb347' : '#00ff87'}">
            Live Delay: +${delay.toFixed(1)}m
          </div>
        </div>
      `

      marker.bindTooltip(tooltipHtml, {
        direction: 'top',
        offset: [0, -10],
        className: 'map-tooltip',
      })

      marker.addTo(stationLayerRef.current!)
    })
  }, [nodes, edges, mode, stationDelays, stationCongestion, tick])

  // Draw live trains over the network
  useEffect(() => {
    if (!L || !mapInstanceRef.current || !trainLayerRef.current) return

    trainLayerRef.current.clearLayers()
    if (!trains.length) return

    trains.forEach((t) => {
      if (t.lat == null || t.lon == null) return

      const delay = t.delay ?? 0
      const delayColor = delay > 30 ? '#ff3b3b' : delay > 10 ? '#ffd700' : '#00ffff'

      const icon = L!.divIcon({
        className: 'custom-train-icon',
        html: `
          <div style="
            width: 14px; height: 14px;
            border-radius: 50%;
            background: ${delayColor};
            border: 2px solid rgba(255,255,255,0.8);
            box-shadow: 0 0 12px ${delayColor}, 0 0 20px ${delayColor}60;
            cursor: pointer;
          "></div>
        `,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      })

      const marker = L!.marker([t.lat, t.lon], { icon, zIndexOffset: 1000 })

      const tooltipHtml = `
        <div class="font-mono text-[10px]">
          <div class="font-semibold text-white mb-1">Train ${t.number}</div>
          <div class="text-rail-ghost">Name: <span class="text-white">${t.name}</span></div>
          <div class="text-rail-ghost">From: <span class="text-white">${t.from_name}</span></div>
          <div class="text-rail-ghost">To: <span class="text-white">${t.to_name}</span></div>
          <div class="text-rail-ghost">Status: <span class="text-white">${t.status}</span></div>
          <div style="color:${delayColor}">Delay: +${delay.toFixed(1)}m</div>
        </div>
      `

      marker.bindTooltip(tooltipHtml, {
        direction: 'top',
        offset: [0, -10],
        className: 'map-tooltip',
      })

      marker.addTo(trainLayerRef.current!)
    })
  }, [trains])

  return (
    <div className="w-full h-full">
      <div ref={mapRef} className="w-full h-full" />
    </div>
  )
}

