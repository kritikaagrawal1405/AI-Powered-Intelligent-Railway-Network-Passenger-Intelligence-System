"""
RailIQ v3.1 — Fixed Backend
- ML models called with proper pandas DataFrames (no feature-name warnings)
- No hardcoded random improvement percentages
- Real network topology (170 edges, strongly connected)
- Dual dashboards: passenger + operator
- All dynamic — live simulation state on every call
"""
import asyncio, json, math, os, pickle, random
from datetime import datetime, timedelta
from typing import Optional, List, Dict

import numpy as np
import pandas as pd
import networkx as nx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import warnings
warnings.filterwarnings("ignore")

app = FastAPI(title="RailIQ API", version="3.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── LOAD ASSETS ──────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(__file__))

with open(f"{BASE}/data/stations.json")       as f: STATIONS     = json.load(f)
with open(f"{BASE}/data/trains.json")         as f: TRAINS       = json.load(f)
with open(f"{BASE}/data/routes.json")         as f: ROUTES       = json.load(f)
with open(f"{BASE}/data/network_metrics.json")as f: NET_METRICS  = json.load(f)

with open(f"{BASE}/models/delay_model.pkl",    "rb") as f:
    _dm = pickle.load(f)
    delay_model    = _dm["model"]
    delay_features = _dm["features"]

with open(f"{BASE}/models/ticket_model.pkl",   "rb") as f:
    _tm = pickle.load(f)
    ticket_clf      = _tm["clf"]
    ticket_reg      = _tm["reg"]
    ticket_features = _tm["features"]

with open(f"{BASE}/models/congestion_model.pkl","rb") as f:
    _cm = pickle.load(f)
    cong_model    = _cm["model"]
    cong_features = _cm["features"]

with open(f"{BASE}/models/railway_graph.pkl",  "rb") as f:
    G = pickle.load(f)

TRAIN_IDX = {t["number"]: t for t in TRAINS}

# ── HELPER: ML PREDICTION (always use DataFrame) ──────────────────────────────
def predict_delay(hour: int, month: int, dow: int, station_code: str) -> float:
    info = STATIONS.get(station_code, {})
    cat_score = {"A1": 5, "A": 4, "B": 3, "C": 2}.get(info.get("category", "B"), 3)
    row = pd.DataFrame([[
        hour, month, dow,
        int(dow >= 5),
        int(hour in [7,8,9,17,18,19]),
        int(month in [10,11,12,1,3,4]),
        info.get("platforms", 4),
        info.get("daily_footfall", 100000),
        cat_score,
    ]], columns=delay_features)
    return float(delay_model.predict(row)[0])

def predict_congestion(hour: int, month: int, station_code: str) -> float:
    info = STATIONS.get(station_code, {})
    cat_score = {"A1": 5, "A": 4, "B": 3}.get(info.get("category", "B"), 3)
    row = pd.DataFrame([[
        hour, month,
        info.get("platforms", 4),
        info.get("daily_footfall", 100000),
        cat_score,
    ]], columns=cong_features)
    return float(np.clip(cong_model.predict(row)[0], 0.02, 0.98))

def predict_ticket(days_advance: int, month: int, dow: int,
                   wl_number: int, station_code: str,
                   travel_class: str, train_type: str) -> float:
    info = STATIONS.get(station_code, {})
    cat_score   = {"A1": 5, "A": 4, "B": 3, "C": 2}.get(info.get("category", "B"), 3)
    class_code  = {"1A": 6, "2A": 5, "3A": 4, "SL": 3, "CC": 5, "EC": 6, "2S": 2}.get(travel_class, 3)
    train_code  = {"Rajdhani": 5, "Shatabdi": 5, "Duronto": 4, "Superfast": 3, "Express": 2}.get(train_type, 3)
    row = pd.DataFrame([[
        days_advance, month, dow,
        int(month in [10, 11, 12, 1]),   # is_festive
        int(month in [4, 5, 6]),          # is_summer
        wl_number,
        cat_score, class_code, train_code,
    ]], columns=ticket_features)
    return float(np.clip(ticket_reg.predict(row)[0], 0.02, 0.98))


# ── LIVE SIMULATION STATE ──────────────────────────────────────────────────────
class LiveState:
    def __init__(self):
        self.tick = 0
        self.sim_time = datetime.now()
        self.station_delays:     Dict[str, float] = {}
        self.station_congestion: Dict[str, float] = {}
        self.train_positions:    Dict[str, dict]  = {}
        self.active_incidents:   List[dict] = []
        self.cascade_events:     List[dict] = []
        self.history:            Dict[str, List[float]] = {c: [] for c in STATIONS}
        self._init()

    def _init(self):
        now = datetime.now()
        for code in STATIONS:
            # Use ML model for base values, not random
            base_d = predict_delay(now.hour, now.month, now.weekday(), code)
            base_c = predict_congestion(now.hour, now.month, code)
            self.station_delays[code]     = max(0.0, base_d + random.gauss(0, 1.5))
            self.station_congestion[code] = float(np.clip(base_c + random.gauss(0, 0.03), 0.02, 0.97))
        for t in TRAINS:
            self._init_train(t)

    def _init_train(self, t: dict):
        src = STATIONS.get(t["from"]); dst = STATIONS.get(t["to"])
        if not src or not dst: return
        prog = random.random()
        self.train_positions[t["number"]] = {
            "number": t["number"], "name": t["name"], "type": t["type"],
            "from": t["from"], "to": t["to"],
            "from_name": src["name"], "to_name": dst["name"],
            "lat": src["lat"] + (dst["lat"] - src["lat"]) * prog,
            "lon": src["lon"] + (dst["lon"] - src["lon"]) * prog,
            "progress": prog,
            "delay": max(0.0, random.gauss(4, 6)),
            "speed": t["avg_speed"] * (0.75 + random.random() * 0.3),
            "status": "ON_TIME",
        }

STATE = LiveState()

# ── SIMULATION ENGINE ─────────────────────────────────────────────────────────
async def sim_loop():
    while True:
        await asyncio.sleep(2)
        _tick_world()
        await _broadcast_live()

def _tick_world():
    STATE.tick += 1
    STATE.sim_time += timedelta(seconds=120)
    h = STATE.sim_time.hour
    m = STATE.sim_time.month

    # Probabilistic incident spawn (3% per tick, max 3 concurrent)
    if random.random() < 0.03 and len(STATE.active_incidents) < 3:
        victim = random.choice(list(STATIONS.keys()))
        severity = random.choices(
            ["MINOR", "MODERATE", "MAJOR"],
            weights=[0.55, 0.30, 0.15]
        )[0]
        spike = {"MINOR": 8, "MODERATE": 22, "MAJOR": 55}[severity]
        STATE.active_incidents.append({
            "id": f"INC-{STATE.tick}",
            "station": victim,
            "station_name": STATIONS[victim]["name"],
            "type": random.choice(["Signal failure", "Track obstruction", "Platform congestion", "Equipment fault", "Power disruption"]),
            "severity": severity,
            "delay_added": spike,
            "started_at": STATE.sim_time.isoformat(),
            "ttl": random.randint(6, 25),
        })
        _cascade(victim, spike)

    # Age incidents, recover resolved ones
    remaining = []
    for inc in STATE.active_incidents:
        inc["ttl"] -= 1
        if inc["ttl"] > 0:
            remaining.append(inc)
        else:
            # Gradual recovery
            STATE.station_delays[inc["station"]] *= 0.55
    STATE.active_incidents = remaining

    # Update station delays — ML base + mean reversion + small Gaussian noise
    for code in STATIONS:
        ml_base = predict_delay(h, m, STATE.sim_time.weekday(), code)
        current = STATE.station_delays.get(code, ml_base)
        # Mean-revert toward ML base
        drift = (ml_base - current) * 0.12 + random.gauss(0, 0.9)
        STATE.station_delays[code] = max(0.0, current + drift)
        hist = STATE.history[code]
        hist.append(round(STATE.station_delays[code], 2))
        if len(hist) > 60:
            hist.pop(0)

    # Update congestion — ML base + mean reversion
    for code in STATIONS:
        ml_base = predict_congestion(h, m, code)
        current = STATE.station_congestion.get(code, ml_base)
        STATE.station_congestion[code] = float(np.clip(
            current + (ml_base - current) * 0.10 + random.gauss(0, 0.012),
            0.02, 0.97
        ))

    # Move trains
    for t in TRAINS:
        tp = STATE.train_positions.get(t["number"])
        if not tp: continue
        src = STATIONS.get(t["from"]); dst = STATIONS.get(t["to"])
        if not src or not dst: continue
        step = 0.0018 * max(0.2, 1.0 - tp["delay"] / 180)
        tp["progress"] = min(1.0, tp["progress"] + step)
        if tp["progress"] >= 1.0:
            tp["progress"] = 0.0
        tp["lat"] = src["lat"] + (dst["lat"] - src["lat"]) * tp["progress"]
        tp["lon"] = src["lon"] + (dst["lon"] - src["lon"]) * tp["progress"]
        src_delay = STATE.station_delays.get(t["from"], 0)
        tp["delay"] = max(0, tp["delay"] + src_delay * 0.08 - tp["delay"] * 0.04 + random.gauss(0, 0.4))
        tp["speed"] = t["avg_speed"] * max(0.3, 1 - tp["delay"] / 280) * (0.93 + random.random() * 0.14)
        tp["status"] = (
            "ON_TIME"       if tp["delay"] < 5  else
            "SLIGHTLY_LATE" if tp["delay"] < 15 else
            "LATE"          if tp["delay"] < 45 else "VERY_LATE"
        )

def _cascade(source: str, initial: float, depth: int = 4):
    visited = {source}
    queue   = [(source, initial, 0)]
    events  = []
    while queue:
        node, delay, d = queue.pop(0)
        if d >= depth or delay < 2: continue
        for nbr in G.successors(node):
            if nbr in visited: continue
            edge = G[node][nbr]
            att  = 0.55 * math.exp(-edge.get("distance", 300) / 600)
            prop = delay * att * (0.45 + random.random() * 0.45)
            if prop > 1.5:
                STATE.station_delays[nbr] = STATE.station_delays.get(nbr, 0) + prop
                events.append({"station": nbr, "added": round(prop, 1)})
                queue.append((nbr, prop, d + 1))
                visited.add(nbr)
    if events:
        STATE.cascade_events = events[-20:]

# ── WEBSOCKET ─────────────────────────────────────────────────────────────────
class WSManager:
    def __init__(self): self.active: List[WebSocket] = []
    async def connect(self, ws: WebSocket):
        await ws.accept(); self.active.append(ws)
    def disconnect(self, ws: WebSocket):
        if ws in self.active: self.active.remove(ws)
    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try: await ws.send_json(data)
            except: dead.append(ws)
        for d in dead:
            if d in self.active: self.active.remove(d)

WS = WSManager()

async def _broadcast_live():
    if not WS.active: return
    await WS.broadcast({
        "type": "tick",
        "tick": STATE.tick,
        "sim_time": STATE.sim_time.isoformat(),
        "trains": list(STATE.train_positions.values()),
        "incidents": STATE.active_incidents,
        "top_delays": sorted(
            [{"code": c, "name": STATIONS[c]["name"], "delay": round(v, 1)}
             for c, v in STATE.station_delays.items() if c in STATIONS],
            key=lambda x: -x["delay"]
        )[:10],
        "system_delay":       round(float(np.mean(list(STATE.station_delays.values()))), 2),
        "congested_count":    sum(1 for v in STATE.station_congestion.values() if v > 0.65),
        "station_delays":     {c: round(v, 1) for c, v in STATE.station_delays.items()},
        "station_congestion": {c: round(v, 3) for c, v in STATE.station_congestion.items()},
    })

@app.on_event("startup")
async def startup():
    asyncio.create_task(sim_loop())

# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok", "tick": STATE.tick,
        "sim_time": STATE.sim_time.isoformat(),
        "active_ws": len(WS.active),
        "incidents": len(STATE.active_incidents),
        "stations": len(STATIONS),
        "graph_nodes": G.number_of_nodes(),
        "graph_edges": G.number_of_edges(),
    }

@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await WS.connect(ws)
    try:
        await ws.send_json({
            "type": "init",
            "trains": list(STATE.train_positions.values()),
            "incidents": STATE.active_incidents,
            "stations": [
                {"code": c, "delay": round(STATE.station_delays[c], 1),
                 "congestion": round(STATE.station_congestion[c], 3),
                 "name": STATIONS[c]["name"]}
                for c in STATIONS
            ],
        })
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        WS.disconnect(ws)

# ── DASHBOARD: PASSENGER ──────────────────────────────────────────────────────
@app.get("/api/dashboard/passenger")
def dashboard_passenger():
    now    = STATE.sim_time
    delays = STATE.station_delays
    cong   = STATE.station_congestion

    # 7-day forecast using ML model
    forecast = []
    for i in range(7):
        day = datetime.now() + timedelta(days=i)
        # Average ML predictions across major stations for this day
        major = ["NDLS", "CSTM", "HWH", "MAS", "SBC", "ADI", "PNBE"]
        avg_delays = [predict_delay(12, day.month, day.weekday(), s) for s in major]
        forecast.append({
            "date": day.strftime("%Y-%m-%d"),
            "day": day.strftime("%a"),
            "avg_delay": round(float(np.mean(avg_delays)), 1),
            "peak_delay": round(float(np.max(avg_delays)), 1),
            "risk": "HIGH" if day.weekday() >= 5 or day.month in [10,11,12,1] else "NORMAL",
        })

    # Best/worst stations for travel
    delay_sorted = sorted(delays.items(), key=lambda x: x[1])
    best_stations  = [{"code": c, "name": STATIONS.get(c,{}).get("name",""), "delay": round(v,1)}
                      for c,v in delay_sorted[:5]]
    worst_stations = [{"code": c, "name": STATIONS.get(c,{}).get("name",""), "delay": round(v,1)}
                      for c,v in delay_sorted[-5:]]

    avg_d  = float(np.mean(list(delays.values())))
    avg_c  = float(np.mean(list(cong.values())))

    return {
        "type": "passenger",
        "kpis": {
            "active_trains":       len(TRAINS),
            "on_time_pct":         round((1 - sum(1 for v in delays.values() if v > 10) / len(delays)) * 100, 1),
            "avg_delay":           round(avg_d, 1),
            "delayed_stations":    sum(1 for v in delays.values() if v > 10),
            "congested_stations":  sum(1 for v in cong.values() if v > 0.65),
            "best_travel_time":    "04:30 - 06:30",  # off-peak
            "network_reliability": round(max(0, 100 - avg_d * 1.5 - avg_c * 20), 1),
        },
        "forecast_7d":      forecast,
        "best_stations":    best_stations,
        "worst_stations":   worst_stations,
        "incidents":        STATE.active_incidents,
        "travel_advisory":  _build_travel_advisory(),
        "sim_time":         now.isoformat(),
        "tick":             STATE.tick,
    }

def _build_travel_advisory() -> List[dict]:
    advisories = []
    h = STATE.sim_time.hour
    # Peak hour advisory
    if h in [7, 8, 9, 17, 18, 19, 20]:
        advisories.append({
            "level": "WARNING",
            "message": "Peak hours — expect 15-30% higher delays. Arrive early.",
            "type": "peak_hours",
        })
    # Incident advisories
    for inc in STATE.active_incidents:
        advisories.append({
            "level": "CRITICAL" if inc["severity"] == "MAJOR" else "WARNING",
            "message": f"{inc['station_name']}: {inc['type']} — +{inc['delay_added']}min delay",
            "type": "incident",
            "station": inc["station"],
        })
    # High congestion advisories
    high_cong = [(c, v) for c, v in STATE.station_congestion.items() if v > 0.80]
    if high_cong:
        names = [STATIONS.get(c, {}).get("name", c) for c, _ in sorted(high_cong, key=lambda x: -x[1])[:3]]
        advisories.append({
            "level": "INFO",
            "message": f"High platform congestion at: {', '.join(names)}. Arrive 30min early.",
            "type": "congestion",
        })
    return advisories

# ── DASHBOARD: OPERATOR ───────────────────────────────────────────────────────
@app.get("/api/dashboard/operator")
def dashboard_operator():
    now    = STATE.sim_time
    delays = STATE.station_delays
    cong   = STATE.station_congestion

    # Zone performance — group by zone
    zones: Dict[str, Dict] = {}
    for code, info in STATIONS.items():
        z = info["zone"]
        if z not in zones:
            zones[z] = {"delays": [], "congestion": [], "incidents": 0, "stations": []}
        zones[z]["delays"].append(delays.get(code, 0))
        zones[z]["congestion"].append(cong.get(code, 0))
        zones[z]["stations"].append(code)

    zone_stats = []
    for z, d in zones.items():
        avg_d = float(np.mean(d["delays"]))
        avg_c = float(np.mean(d["congestion"]))
        inc_count = sum(1 for i in STATE.active_incidents if STATIONS.get(i["station"],{}).get("zone","") == z)
        zone_stats.append({
            "zone": z,
            "avg_delay": round(avg_d, 1),
            "avg_congestion": round(avg_c, 3),
            "station_count": len(d["stations"]),
            "active_incidents": inc_count,
            "performance_score": round((1 - avg_c) * 100 - avg_d, 1),
            "status": "CRITICAL" if avg_d > 30 or avg_c > 0.85 else ("WARNING" if avg_d > 15 else "NOMINAL"),
        })
    zone_stats.sort(key=lambda x: -x["performance_score"])

    # Cascade risk analysis — which stations if disrupted cause most damage
    cascade_risk = []
    top_vuln = sorted(NET_METRICS.items(), key=lambda x: -x[1].get("vulnerability_score", 0))[:8]
    for code, m in top_vuln:
        nbrs = list(G.successors(code))
        cascade_risk.append({
            "station_code": code,
            "station_name": STATIONS.get(code, {}).get("name", code),
            "vulnerability_score": round(m.get("vulnerability_score", 0), 4),
            "betweenness": round(m.get("betweenness_centrality", 0), 4),
            "downstream_count": len(nbrs),
            "live_delay": round(delays.get(code, 0), 1),
            "risk_level": "CRITICAL" if m.get("vulnerability_score", 0) > 0.15 else (
                          "HIGH" if m.get("vulnerability_score", 0) > 0.08 else "MEDIUM"),
        })

    # Train performance summary
    trains_status = {
        "on_time":     sum(1 for t in STATE.train_positions.values() if t["status"] == "ON_TIME"),
        "slight_delay":sum(1 for t in STATE.train_positions.values() if t["status"] == "SLIGHTLY_LATE"),
        "late":        sum(1 for t in STATE.train_positions.values() if t["status"] == "LATE"),
        "very_late":   sum(1 for t in STATE.train_positions.values() if t["status"] == "VERY_LATE"),
    }

    # Capacity utilization per zone (congestion-based)
    capacity = {z: round(float(np.mean([cong.get(c,0) for c in d["stations"]])) * 100, 1)
                for z, d in zones.items()}

    # Ops recommendations based on live state
    recommendations = _build_operator_recommendations()

    return {
        "type": "operator",
        "kpis": {
            "total_stations":     len(STATIONS),
            "total_trains":       len(TRAINS),
            "active_incidents":   len(STATE.active_incidents),
            "avg_system_delay":   round(float(np.mean(list(delays.values()))), 1),
            "network_health_pct": round((1 - float(np.mean(list(cong.values())))) * 100, 1),
            "trains_on_time_pct": round(trains_status["on_time"] / max(1, len(TRAINS)) * 100, 1),
            "cascade_risk_count": sum(1 for m in NET_METRICS.values() if m.get("vulnerability_score",0) > 0.15),
        },
        "trains_status":      trains_status,
        "zone_performance":   zone_stats,
        "cascade_risk":       cascade_risk,
        "capacity_by_zone":   capacity,
        "recommendations":    recommendations,
        "incidents":          STATE.active_incidents,
        "cascade_events":     STATE.cascade_events[-10:],
        "sim_time":           now.isoformat(),
        "tick":               STATE.tick,
    }

def _build_operator_recommendations() -> List[dict]:
    recs = []
    delays = STATE.station_delays

    # Identify stations needing immediate action
    critical = [(c, v) for c, v in delays.items() if v > 35]
    if critical:
        worst = sorted(critical, key=lambda x: -x[1])[0]
        recs.append({
            "priority": "CRITICAL",
            "action": "IMMEDIATE",
            "message": f"Deploy rapid response team to {STATIONS.get(worst[0],{}).get('name',worst[0])} — {worst[1]:.0f}min delay",
            "station": worst[0],
        })

    # Cascade risk if incident station has high betweenness
    for inc in STATE.active_incidents:
        m = NET_METRICS.get(inc["station"], {})
        if m.get("betweenness_centrality", 0) > 0.1:
            nbr_count = len(list(G.successors(inc["station"])))
            recs.append({
                "priority": "HIGH",
                "action": "ALERT",
                "message": f"{inc['station_name']} is a critical junction — notify {nbr_count} downstream stations",
                "station": inc["station"],
            })

    # Resource reallocation suggestions
    high_cong = [(c, v) for c, v in STATE.station_congestion.items() if v > 0.82]
    if high_cong:
        for code, score in sorted(high_cong, key=lambda x: -x[1])[:2]:
            recs.append({
                "priority": "MEDIUM",
                "action": "RESOURCE",
                "message": f"{STATIONS.get(code,{}).get('name',code)}: {score*100:.0f}% capacity — consider adding platform staff",
                "station": code,
            })

    # Off-peak rebalancing suggestion
    h = STATE.sim_time.hour
    if h in [10, 11, 14, 15]:
        recs.append({
            "priority": "LOW",
            "action": "OPTIMIZE",
            "message": "Off-peak window — optimal time for maintenance window scheduling",
            "station": None,
        })

    return recs[:6]

# ── ORIGINAL ENDPOINTS ─────────────────────────────────────────────────────────

@app.get("/api/network/overview")
def network_overview():
    nodes = []
    for code, info in STATIONS.items():
        m = NET_METRICS.get(code, {})
        nodes.append({
            "id": code, "label": info["name"], "city": info.get("city",""),
            "zone": info["zone"], "lat": info["lat"], "lon": info["lon"],
            "category": info["category"], "platforms": info["platforms"],
            "daily_footfall": info["daily_footfall"],
            "predicted_delay":    round(STATE.station_delays.get(code, 0), 1),
            "congestion_score":   round(STATE.station_congestion.get(code, 0), 3),
            "vulnerability_score": m.get("vulnerability_score", 0),
            "betweenness_centrality": m.get("betweenness_centrality", 0),
            "degree_centrality":  m.get("degree_centrality", 0),
            "pagerank":           m.get("pagerank", 0),
        })
    edges = [{"source": r["src"], "target": r["dst"], "distance": r["distance"],
               "travel_time": r["travel_time"], "corridor": r["corridor"]}
             for r in ROUTES]
    return {"nodes": nodes, "edges": edges, "tick": STATE.tick}

@app.get("/api/network/live-trains")
def live_trains():
    return {"trains": list(STATE.train_positions.values()), "tick": STATE.tick,
            "sim_time": STATE.sim_time.isoformat()}

@app.get("/api/delay/forecast/{code}")
def delay_forecast(code: str):
    if code not in STATIONS: raise HTTPException(404, "Station not found")
    info = STATIONS[code]; now = STATE.sim_time
    hourly = []
    for h in range(24):
        ml_pred   = predict_delay(h, now.month, now.weekday(), code)
        # Blend live state into near-future hours
        blend_w   = math.exp(-abs(h - now.hour) / 5)
        live_offset = STATE.station_delays.get(code, 0) * 0.35 * blend_w
        hourly.append({"hour": h, "delay": round(max(0, ml_pred + live_offset), 1)})

    current = STATE.station_delays.get(code, 0)
    cascade = _compute_cascade(code, current)

    return {
        "station_code":    code,
        "station_name":    info["name"],
        "live_delay":      round(current, 1),
        "hourly_forecast": hourly,
        "cascade":         cascade,
        "risk":            "HIGH" if current > 30 else ("MEDIUM" if current > 10 else "LOW"),
        "history":         STATE.history.get(code, []),
        "tick":            STATE.tick,
    }

def _compute_cascade(source: str, initial: float, depth: int = 4) -> List[dict]:
    result = {}; visited = {source}; q = [(source, initial, 0)]
    while q:
        node, delay, d = q.pop(0)
        if d >= depth or delay < 1.5: continue
        for nbr in G.successors(node):
            if nbr not in visited and nbr in STATIONS:
                edge = G[node][nbr]
                att  = 0.55 * math.exp(-edge.get("distance", 300) / 600)
                prop = delay * att * (0.45 + random.random() * 0.45)
                if prop > 1:
                    result[nbr] = round(prop, 1)
                    q.append((nbr, prop, d + 1))
                    visited.add(nbr)
    return [
        {"station_code": c, "station_name": STATIONS.get(c, {}).get("name", c),
         "delay": v,
         "severity": "CRITICAL" if v > 45 else ("HIGH" if v > 20 else ("MEDIUM" if v > 8 else "LOW"))}
        for c, v in sorted(result.items(), key=lambda x: -x[1])
    ]

@app.get("/api/congestion/heatmap")
def congestion_heatmap(hour: Optional[int] = None):
    h = hour if hour is not None else STATE.sim_time.hour
    data = []
    for code, info in STATIONS.items():
        if hour is None:
            score = STATE.station_congestion.get(code, 0)
        else:
            score = predict_congestion(h, STATE.sim_time.month, code)
        data.append({
            "station_code": code, "station_name": info["name"],
            "lat": info["lat"], "lon": info["lon"],
            "congestion_score": round(score, 3), "zone": info["zone"],
            "level": ("CRITICAL" if score > 0.85 else "HIGH" if score > 0.65 else "MEDIUM" if score > 0.4 else "LOW"),
            "estimated_crowd": int(info["daily_footfall"] / 24 * (1 + score * 2.8)),
        })
    data.sort(key=lambda x: -x["congestion_score"])
    return {"hour": h, "heatmap": data, "tick": STATE.tick}

@app.get("/api/network/vulnerability")
def vulnerability():
    rows = []
    for code, m in NET_METRICS.items():
        info = STATIONS.get(code, {})
        rows.append({
            "station_code":          code,
            "station_name":          info.get("name", code),
            "zone":                  info.get("zone", ""),
            "vulnerability_score":   m.get("vulnerability_score", 0),
            "betweenness_centrality":m.get("betweenness_centrality", 0),
            "pagerank":              m.get("pagerank", 0),
            "live_delay":            round(STATE.station_delays.get(code, 0), 1),
            "risk_category":         ("CRITICAL" if m.get("vulnerability_score", 0) > 0.15 else
                                      "HIGH"     if m.get("vulnerability_score", 0) > 0.08 else "MEDIUM"),
        })
    rows.sort(key=lambda x: -x["vulnerability_score"])
    return {"vulnerability_ranking": rows[:20], "tick": STATE.tick}

class TicketReq(BaseModel):
    train_number:    str
    travel_class:    str
    source_station:  str
    dest_station:    str
    days_advance:    int
    month:           int
    day_of_week:     int
    wl_number:       int = 0

@app.post("/api/ticket/predict")
def ticket_predict(req: TicketReq):
    train = TRAIN_IDX.get(req.train_number)
    if not train: raise HTTPException(404, "Train not found")

    # PROPER ML PREDICTION (not random)
    prob = predict_ticket(
        days_advance   = req.days_advance,
        month          = req.month,
        dow            = req.day_of_week,
        wl_number      = req.wl_number,
        station_code   = req.source_station,
        travel_class   = req.travel_class,
        train_type     = train["type"],
    )

    # Apply live delay penalty (small but real)
    route_delay = STATE.station_delays.get(req.source_station, 0)
    delay_penalty = min(0.08, route_delay * 0.0015)  # cap at -8%
    prob = float(np.clip(prob - delay_penalty, 0.03, 0.97))

    # ML-derived optimal booking window
    # Test several advance-day values to find optimal
    test_days = [7, 14, 21, 30, 45, 60, 75, 90]
    best_days  = req.days_advance
    best_prob  = prob
    for d in test_days:
        p = predict_ticket(d, req.month, req.day_of_week, max(0, req.wl_number - 1),
                           req.source_station, req.travel_class, train["type"])
        if p > best_prob:
            best_prob = p; best_days = d

    # Build data-driven advice
    advice = []
    if req.wl_number > 0:
        if prob < 0.35:
            advice.append(f"High risk — WL{req.wl_number} has low confirmation probability. Consider alternative trains.")
        elif prob < 0.60:
            advice.append(f"WL{req.wl_number} has moderate confirmation probability. Keep backup option.")

    if best_days > req.days_advance:
        improvement = round((best_prob - prob) * 100, 1)
        if improvement > 1:
            advice.append(f"Booking {best_days} days ahead would improve probability by +{improvement}% (model prediction).")

    festive = req.month in [10, 11, 12, 1]
    summer  = req.month in [4, 5, 6]
    if festive:
        advice.append("Festive season — demand is 2-3× normal. Book at least 60 days ahead.")
    elif summer:
        advice.append("Summer peak — demand elevated. Book 45+ days ahead.")

    if route_delay > 10:
        advice.append(f"Live delay at {req.source_station}: {route_delay:.0f}min — factor this into connections.")

    # Alternative trains
    alts = [t for t in TRAINS
            if t["type"] in ["Rajdhani", "Shatabdi"] and t["number"] != req.train_number][:3]

    return {
        "train_number":           req.train_number,
        "train_name":             train["name"],
        "confirmation_probability": round(prob, 3),
        "confirmation_pct":       round(prob * 100, 1),
        "risk_level":             "LOW" if prob > 0.70 else ("MEDIUM" if prob > 0.40 else "HIGH"),
        "optimal_booking_days":   best_days,
        "advice":                 advice,
        "route_delay_impact":     round(delay_penalty, 3),
        "alternative_trains":     [{"number": t["number"], "name": t["name"], "type": t["type"]} for t in alts],
        "tick":                   STATE.tick,
    }

@app.get("/api/routes/optimal")
def optimal_route(src: str, dst: str):
    if src not in G or dst not in G:
        raise HTTPException(404, f"Station not in graph: {src if src not in G else dst}")
    routes = []
    try:
        path = nx.shortest_path(G, src, dst, weight="travel_time")
        tt   = sum(G[path[i]][path[i+1]]["travel_time"] for i in range(len(path)-1))
        dist = sum(G[path[i]][path[i+1]]["distance"]    for i in range(len(path)-1))
        routes.append({
            "rank": 1, "type": "FASTEST", "path": path,
            "path_names":        [STATIONS.get(s, {}).get("name", s) for s in path],
            "total_time_mins":   tt,
            "total_distance_km": dist,
            "avg_congestion":    round(float(np.mean([STATE.station_congestion.get(s, 0) for s in path])), 3),
            "avg_delay":         round(float(np.mean([STATE.station_delays.get(s, 0)    for s in path])), 1),
            "recommended":       True,
        })
    except nx.NetworkXNoPath:
        pass

    try:
        def w_cong(u, v, d):
            return d.get("travel_time", 60) * (1 + STATE.station_congestion.get(v, 0) * 2.2)
        path2 = nx.shortest_path(G, src, dst, weight=w_cong)
        if path2 != (routes[0]["path"] if routes else []):
            tt2 = sum(G[path2[i]][path2[i+1]]["travel_time"] for i in range(len(path2)-1))
            routes.append({
                "rank": 2, "type": "LEAST_CONGESTED", "path": path2,
                "path_names":        [STATIONS.get(s, {}).get("name", s) for s in path2],
                "total_time_mins":   tt2,
                "total_distance_km": sum(G[path2[i]][path2[i+1]]["distance"] for i in range(len(path2)-1)),
                "avg_congestion":    round(float(np.mean([STATE.station_congestion.get(s, 0) for s in path2])), 3),
                "avg_delay":         round(float(np.mean([STATE.station_delays.get(s, 0)    for s in path2])), 1),
                "recommended":       False,
            })
    except (nx.NetworkXNoPath, KeyError):
        pass

    return {"source": src, "destination": dst, "routes": routes, "tick": STATE.tick}

@app.get("/api/analytics/zones")
def zone_analytics():
    zones: Dict[str, dict] = {}
    for code, info in STATIONS.items():
        z = info["zone"]
        if z not in zones:
            zones[z] = {"delays": [], "congestion": [], "stations": [], "footfall": []}
        zones[z]["delays"].append(STATE.station_delays.get(code, 0))
        zones[z]["congestion"].append(STATE.station_congestion.get(code, 0))
        zones[z]["stations"].append(code)
        zones[z]["footfall"].append(info["daily_footfall"])
    result = [
        {
            "zone": z,
            "avg_delay":         round(float(np.mean(d["delays"])), 1),
            "avg_congestion":    round(float(np.mean(d["congestion"])), 3),
            "station_count":     len(d["stations"]),
            "total_footfall":    sum(d["footfall"]),
            "performance_score": round((1 - float(np.mean(d["congestion"]))) * 100 - float(np.mean(d["delays"])), 1),
        }
        for z, d in zones.items()
    ]
    result.sort(key=lambda x: -x["performance_score"])
    return {"zones": result, "tick": STATE.tick}

@app.get("/api/assistant/query")
def assistant(q: str):
    ql = q.lower()
    avg_d  = round(float(np.mean(list(STATE.station_delays.values()))), 1)
    top_d  = sorted(STATE.station_delays.items(),    key=lambda x: -x[1])[:3]
    top_c  = sorted(STATE.station_congestion.items(), key=lambda x: -x[1])[:3]
    top_v  = sorted(NET_METRICS.keys(), key=lambda c: -NET_METRICS[c].get("vulnerability_score", 0))[:3]

    if any(w in ql for w in ["waitlist", "wl", "confirm", "ticket"]):
        return {"intent": "ticket", "confidence": 0.91,
            "response": (f"Live network delay avg: {avg_d}min. "
                         f"WL confirmation depends on days ahead, season, class, and train type. "
                         f"Rajdhani/Shatabdi have dedicated quota. Book 60+ days ahead in festive season. "
                         f"Tatkal opens 24h before departure for near-certain confirmation."),
            "data": {"avg_delay": avg_d}, "tick": STATE.tick}

    if any(w in ql for w in ["delay", "late", "on time", "punctual"]):
        names = [STATIONS.get(c, {}).get("name", c) for c, _ in top_d]
        return {"intent": "delay", "confidence": 0.93,
            "response": (f"Live top delays: {', '.join(names)}. System avg: {avg_d}min. "
                         f"{len(STATE.active_incidents)} active incident(s). "
                         f"{'🔴 Active cascade propagation!' if STATE.cascade_events else '✅ No active cascades.'}"),
            "data": {"top_delayed": [c for c, _ in top_d], "incidents": len(STATE.active_incidents)},
            "tick": STATE.tick}

    if any(w in ql for w in ["congestion", "crowd", "crowded", "busy", "platform"]):
        names = [STATIONS.get(c, {}).get("name", c) for c, _ in top_c]
        return {"intent": "congestion", "confidence": 0.90,
            "response": (f"Most congested now: {', '.join(names)}. "
                         f"{sum(1 for v in STATE.station_congestion.values() if v > 0.65)} stations above threshold. "
                         f"Arrive 45min early at peak hubs."),
            "data": {"congested_count": sum(1 for v in STATE.station_congestion.values() if v > 0.65)},
            "tick": STATE.tick}

    if any(w in ql for w in ["vulnerable", "critical", "cascade", "risk", "junction"]):
        names = [STATIONS.get(c, {}).get("name", c) for c in top_v]
        return {"intent": "vulnerability", "confidence": 0.89,
            "response": (f"Critical nodes: {', '.join(names)}. "
                         f"A disruption at {names[0]} cascades to {len(list(G.successors(top_v[0])))} downstream stations."),
            "data": {"critical_nodes": top_v}, "tick": STATE.tick}

    return {"intent": "general", "confidence": 0.75,
        "response": (f"RailIQ: {len(STATIONS)} stations, {len(TRAINS)} trains tracked. "
                     f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges. "
                     f"Avg delay: {avg_d}min. Incidents: {len(STATE.active_incidents)}."),
        "data": {}, "tick": STATE.tick}

@app.get("/api/stations/search")
def search_stations(q: str = ""):
    ql = q.lower()
    return {"results": [
        {"code": c, "name": i["name"], "city": i.get("city",""), "zone": i["zone"]}
        for c, i in STATIONS.items()
        if ql in c.lower() or ql in i["name"].lower() or ql in i.get("city","").lower()
    ][:12]}

@app.get("/api/stations/{code}")
def station_detail(code: str):
    if code not in STATIONS: raise HTTPException(404)
    info = STATIONS[code]; m = NET_METRICS.get(code, {}); now = STATE.sim_time
    hourly = [{"hour": h, "delay": round(max(0, predict_delay(h, now.month, now.weekday(), code) +
                STATE.station_delays.get(code, 0) * 0.35 * math.exp(-abs(h - now.hour) / 5)), 1)}
               for h in range(24)]
    cong24 = [{"hour": h, "score": round(predict_congestion(h, now.month, code), 3)} for h in range(24)]
    return {
        **info, "code": code,
        "live_delay":      round(STATE.station_delays.get(code, 0), 1),
        "live_congestion": round(STATE.station_congestion.get(code, 0), 3),
        "delay_history":   STATE.history.get(code, []),
        "hourly_forecast": hourly,
        "congestion_24h":  cong24,
        "network_metrics": m,
        "connected":       list(G.successors(code)),
        "trains":          [{"number": t["number"], "name": t["name"], "type": t["type"]}
                            for t in TRAINS if t["from"] == code or t["to"] == code],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
