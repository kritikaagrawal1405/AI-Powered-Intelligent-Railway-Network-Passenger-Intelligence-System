import { useEffect, useRef, useState, useCallback } from 'react';
import { networkAPI, simulationAPI } from '../../services/api';

interface Station {
  station_code: string;
  station_name: string;
  latitude: number;
  longitude: number;
  avg_delay?: number;
}

interface StationInfo {
  station_code: string;
  station_name: string;
  avg_delay?: number;
  total_trains?: number;
  congestion?: string;
}

// Use dynamic import to avoid SSR issues
let L: typeof import('leaflet') | null = null;

export default function NetworkMap() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<import('leaflet').Map | null>(null);
  const trainLayerRef = useRef<import('leaflet').LayerGroup | null>(null);
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStation, setSelectedStation] = useState<StationInfo | null>(null);
  const [loading, setLoading] = useState(true);

  // Simulation State
  const initialTime = new Date();
  initialTime.setHours(8, 0, 0, 0);
  const [simTime, setSimTime] = useState<Date>(initialTime);
  const simTimeRef = useRef<Date>(initialTime);
  const [isPlaying, setIsPlaying] = useState(false);
  const [simulationSpeed, setSimulationSpeed] = useState(5); // minutes per tick

  useEffect(() => {
    let isMounted = true;

    async function initMap() {
      // Dynamically import leaflet
      if (!L) {
        try {
          L = await import('leaflet');
        } catch {
          console.error('Leaflet not available');
          setLoading(false);
          return;
        }
      }

      if (!mapRef.current || mapInstanceRef.current) return;

      // Load topology nodes and edges
      const data = await networkAPI.getTopology();
      const nodes = (data as any).nodes || [];
      const edges = (data as any).edges || [];
      const stationList: Station[] = nodes.map((n: any) => ({
        station_code: n.id,
        station_name: n.label,
        latitude: n.latitude,
        longitude: n.longitude,
      }));

      if (isMounted) setStations(stationList);

      if (isMounted) setStations(stationList);

      // Prevent "Map container is already initialized" error
      if (mapInstanceRef.current) {
        const inst = mapInstanceRef.current as any;
        if (inst.off) inst.off();
        if (inst.remove) inst.remove();
        mapInstanceRef.current = null;
      }

      // Initialize map
      const map = L.map(mapRef.current, {
        center: [22.5, 80.0],
        zoom: 5,
        zoomControl: true,
        attributionControl: false,
      });

      mapInstanceRef.current = map;

      // Dark tile layer
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© CartoDB',
        maxZoom: 18,
      }).addTo(map);

      // Draw connecting polylines from edges
      const stationMap = new Map(stationList.map(s => [s.station_code, s]));
      const drawnEdges = new Set<string>();

      for (const edge of edges) {
        const key1 = `${edge.source}-${edge.target}`;
        const key2 = `${edge.target}-${edge.source}`;
        if (drawnEdges.has(key1) || drawnEdges.has(key2)) continue;

        const s1 = stationMap.get(edge.source);
        const s2 = stationMap.get(edge.target);
        if (s1 && s2 && s1.latitude && s2.latitude) {
          L!.polyline(
            [[s1.latitude, s1.longitude], [s2.latitude, s2.longitude]],
            {
              color: '#00f0ff',
              weight: 1.5,
              opacity: 0.35,
              dashArray: '6 4',
            }
          ).addTo(map);
          drawnEdges.add(key1);
        }
      }

      // Station markers
      for (const station of stationList) {
        if (!station.latitude || !station.longitude) continue;

        const delay = station.avg_delay ?? 0;
        const color = delay > 45 ? '#ef4444' : delay > 25 ? '#fcd34d' : '#10b981';

        const icon = L!.divIcon({
          className: 'custom-station-icon',
          html: `
            <div style="
              width: 10px; height: 10px; border-radius: 50%;
              background: ${color};
              border: 2px solid rgba(255,255,255,0.4);
              box-shadow: 0 0 8px ${color}, 0 0 16px ${color}40;
              cursor: pointer;
            "></div>
          `,
          iconSize: [10, 10],
          iconAnchor: [5, 5],
        });

        const marker = L!.marker([station.latitude, station.longitude], { icon })
          .addTo(map);

        marker.on('click', async () => {
          const delayStats = await networkAPI.getDelayStats(station.station_name);
          setSelectedStation({
            station_code: station.station_code,
            station_name: station.station_name,
            avg_delay: (delayStats as { avg_delay?: number }).avg_delay ?? delay,
            total_trains: (delayStats as { total_trains?: number }).total_trains ?? 0,
            congestion: delay > 45 ? 'High' : delay > 25 ? 'Medium' : 'Low',
          });
        });

        marker.bindTooltip(station.station_name, {
          permanent: false,
          direction: 'top',
          className: 'map-tooltip',
          offset: [0, -8],
        });
      }

      if (isMounted) setLoading(false);
    }

    initMap();

    return () => {
      isMounted = false;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // --- Simulation Loop ---
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      const nextTime = new Date(simTimeRef.current.getTime() + simulationSpeed * 60000);
      simTimeRef.current = nextTime;
      setSimTime(nextTime);
    }, 1000);
    return () => clearInterval(interval);
  }, [isPlaying, simulationSpeed]);

  // --- Fetch & Render Live Trains ---
  useEffect(() => {
    if (!mapInstanceRef.current || !L) return;

    if (!trainLayerRef.current) {
      trainLayerRef.current = L.layerGroup().addTo(mapInstanceRef.current);
    }

    let isCanceled = false;

    const fetchTrains = async () => {
      try {
        const activeTrains = await simulationAPI.getLiveTrains(simTimeRef.current.toISOString());
        if (isCanceled) return;

        trainLayerRef.current?.clearLayers();

        activeTrains.forEach((t: any) => {
          const delayColor = t.delay_minutes > 15 ? '#ff3b3b' : t.delay_minutes > 5 ? '#ffd700' : '#00ffff';
          const icon = L!.divIcon({
            className: 'custom-train-icon flex items-center justify-center',
            html: `
              <div style="
                width: 14px; height: 14px; border-radius: 50%;
                background: ${delayColor};
                border: 2px solid rgba(255,255,255,0.8);
                box-shadow: 0 0 12px ${delayColor}, 0 0 20px ${delayColor}60;
                cursor: pointer;
              "></div>
            `,
            iconSize: [14, 14],
            iconAnchor: [7, 7],
          });

          const marker = L!.marker([t.lat, t.lng], { icon, zIndexOffset: 1000 });
          marker.bindTooltip(
            '<div class="font-mono text-xs">' +
            '<div class="font-bold text-white mb-1">🚆 Train ' + t.train_id + '</div>' +
            '<div class="text-rail-ghost">Status: <span class="text-white">' + t.status + '</span></div>' +
            '<div class="text-rail-ghost">Next: <span class="text-white">' + t.next_station + '</span></div>' +
            '<div style="color: ' + delayColor + '">Delay: +' + t.delay_minutes + 'm</div>' +
            '</div>',
            { className: 'map-tooltip', direction: 'top', offset: [0, -10] }
          );

          marker.on('click', async () => {
            // Trigger delay simulation
            alert('Simulating 30min delay for Train ' + t.train_id);
            await simulationAPI.simulateDelay(t.train_id, 30);
            fetchTrains(); // Refresh immediately
          });

          trainLayerRef.current?.addLayer(marker);
        });
      } catch (e) {
        console.error('Failed to fetch live trains:', e);
      }
    };

    fetchTrains();
  }, [simTime]);

  const handleManualScrub = (e: React.ChangeEvent<HTMLInputElement>) => {
    const mins = parseInt(e.target.value);
    const newDate = new Date();
    newDate.setHours(0, 0, 0, 0);
    newDate.setMinutes(mins);
    simTimeRef.current = newDate;
    setSimTime(newDate);
  };

  return (
    <div className="h-full flex flex-col space-y-4" style={{ minHeight: 'calc(100vh - 120px)' }}>
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-display tracking-widest text-white mb-1">NETWORK MAP</h1>
          <p className="text-rail-ghost text-sm">Interactive railway network with real-time status</p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 glass rounded-lg px-4 py-2">
          {[['#00ff88', 'On Time'], ['#ffd700', 'Moderate Delay'], ['#ff3b3b', 'High Delay']].map(([c, l]) => (
            <div key={l} className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: c, boxShadow: `0 0 6px ${c} ` }} />
              <span className="text-xs font-mono text-rail-ghost">{l}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 relative rounded-2xl overflow-hidden border border-white/10" style={{ minHeight: '500px' }}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-10 bg-rail-blue/80 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-3">
              <span className="spinner w-8 h-8" />
              <span className="text-xs font-mono text-rail-ghost">Loading network data...</span>
            </div>
          </div>
        )}

        <div ref={mapRef} className="w-full h-full" style={{ minHeight: '500px' }} />

        {/* Station info panel */}
        {selectedStation && (
          <div className="absolute top-4 right-4 z-20 w-56 glass rounded-xl p-4 border border-rail-cyan/20">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="text-xs font-mono text-rail-cyan/60 uppercase tracking-wider">
                  {selectedStation.station_code}
                </div>
                <div className="font-display text-white text-base tracking-wider mt-0.5">
                  {selectedStation.station_name}
                </div>
              </div>
              <button onClick={() => setSelectedStation(null)} className="text-rail-ghost hover:text-white text-lg leading-none">×</button>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-xs text-rail-ghost">Avg Delay</span>
                <span className="text-xs font-mono text-rail-yellow">+{selectedStation.avg_delay}m</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-rail-ghost">Daily Trains</span>
                <span className="text-xs font-mono text-rail-cyan">{selectedStation.total_trains}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-rail-ghost">Congestion</span>
                <span className={"text-xs font-mono " + (
                  selectedStation.congestion === 'High' ? 'text-rail-red' :
                    selectedStation.congestion === 'Medium' ? 'text-rail-yellow' : 'text-rail-green'
                )}>{selectedStation.congestion}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
