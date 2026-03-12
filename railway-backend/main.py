"""
main.py
=======
AI-Powered Railway Intelligence System — FastAPI Backend
=========================================================

Run:
    uvicorn main:app --reload --port 8000

All endpoints are prefixed /api/v1/
CORS is open for local frontend development.

Environment Variables
---------------------
    RAILRADAR_API_KEY   — RailRadar live API key (optional, enables live data)
                          Get yours at: https://railradar.in/indian-railway-data-api
"""

from __future__ import annotations

import os
import sys
import warnings
import logging

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Path setup ─────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List

# ── Import all backend modules ─────────────────────────────────────────────
from src.graph_engine.graph_utils import (
    graph_summary, get_station_list, top_critical_stations,
    get_route_details, get_delay_stats, get_neighbors,
    get_station_importance, load_graph,
)
from src.intelligence.delay_cascade import (
    simulate_delay_cascade, get_most_vulnerable_stations,
)
from src.intelligence.congestion_predictor import (
    identify_congestion_hotspots, corridor_congestion_analysis,
    calculate_station_congestion, congestion_summary,
)
from src.intelligence.network_resilience import (
    compute_network_resilience, identify_critical_nodes,
    simulate_node_removal, resilience_summary,
    detect_railway_communities,
)
from src.ml_models.train_delay_model import predict_delay, get_model_info as delay_model_info
from src.ml_models.wl_model import (
    predict_wl_confirmation, get_trains_by_confirmation_probability,
)
from src.ml_models.ticket_confirmation_model import predict_confirmation
from src.ml_models.cancellation_predictor import (
    predict_cancellation_probability, get_station_cancellation_stats,
    get_high_cancellation_routes, get_cancellation_summary,
)
from src.passenger_flow.passenger_flow import (
    get_network_demand_summary, get_busiest_stations,
    get_station_crowd_profile, get_seasonal_demand,
    get_route_demand, get_transfer_congestion_stations,
    get_overcrowded_routes, passenger_flow_summary,
)
from src.routing_optimizer.routing_optimizer import (
    find_alternative_routes, suggest_schedule_adjustments,
    multi_objective_route, prioritize_corridor_trains, optimization_summary,
)
from src.travel_intelligence.travel_intelligence import (
    get_alternative_travel, get_crowd_estimate, get_booking_guidance,
    get_travel_advisory, travel_intelligence_summary,
)
from src.ai_assistant.railway_assistant import railway_assistant
from src.live.railradar_client import (
    get_live_train_status, get_live_station_board,
    get_trains_between_live, search_trains as search_trains_live,
    build_temporal_graph_snapshot, enrich_delay_with_live_data,
    api_status as live_api_status,
)
from src.live.simulation_service import simulation_service

# ══════════════════════════════════════════════════════════════════════════
#  APP SETUP
# ══════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="AI Railway Intelligence API",
    description=(
        "REST API for the AI-Powered Indian Railway Intelligence System. "
        "Covers network analytics, ML-based delay/ticket prediction, "
        "congestion analysis, passenger flow, routing optimization, "
        "and live data via RailRadar API."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════
#  REQUEST / RESPONSE MODELS
# ══════════════════════════════════════════════════════════════════════════

class RouteRequest(BaseModel):
    source: str
    destination: str

class AlternativeRouteRequest(BaseModel):
    source: str
    destination: str
    blocked_stations: List[str] = Field(default_factory=list)
    n_alternatives: int = Field(default=2, ge=1, le=4)

class MultiObjectiveRequest(BaseModel):
    source: str
    destination: str
    weight_time: float        = Field(default=0.5, ge=0.0, le=1.0)
    weight_congestion: float  = Field(default=0.3, ge=0.0, le=1.0)
    weight_reliability: float = Field(default=0.2, ge=0.0, le=1.0)

class DelayPredictRequest(BaseModel):
    avg_delay_min: float            = Field(default=60.0)
    significant_delay_ratio: float  = Field(default=0.3)
    on_time_ratio: float            = Field(default=0.65)
    delay_risk_score: float         = Field(default=35.0)
    stop_number: int                = Field(default=8)
    betweenness_centrality: float   = Field(default=0.1)
    median_delay_min: Optional[float] = None

class WLConfirmRequest(BaseModel):
    wl_number: int   = Field(..., ge=1, le=300)
    days_before: int = Field(default=7, ge=1, le=120)

class WLRankRequest(BaseModel):
    source: str
    destination: str
    wl_number: int   = Field(default=20, ge=1, le=300)
    days_before: int = Field(default=7, ge=1, le=120)

class TicketConfirmRequest(BaseModel):
    seat_alloted: int       = Field(default=5)
    duration_minutes: float = Field(default=240.0)
    km: float               = Field(default=350.0)
    fair: float             = Field(default=650.0)
    coaches: int            = Field(default=20)
    age: int                = Field(default=28)
    is_online: int          = Field(default=1)
    is_premium_train: int   = Field(default=0)
    meal_booked: int        = Field(default=0)

class CascadeRequest(BaseModel):
    station: str
    initial_delay: float = Field(default=60.0, ge=5.0, le=300.0)
    max_depth: int       = Field(default=3, ge=1, le=5)

class NodeRemovalRequest(BaseModel):
    stations: List[str]

class ScheduleAdjustRequest(BaseModel):
    station: str
    delay_minutes: int = Field(default=45, ge=5, le=300)
    n_trains: int      = Field(default=8, ge=3, le=20)

class CancellationRequest(BaseModel):
    station: str        = Field(default="")
    train_type: str     = Field(default="express")  # premium | express | passenger
    days_before: int    = Field(default=30, ge=1, le=120)
    month: int          = Field(default=6, ge=1, le=12)
    wl_number: int      = Field(default=0, ge=0)
    occupancy_pct: float = Field(default=70.0, ge=0.0, le=100.0)

class CrowdEstimateRequest(BaseModel):
    station: str
    month: int = Field(default=11, ge=1, le=12)
    hour: int  = Field(default=18, ge=0, le=23)

class BookingGuidanceRequest(BaseModel):
    source: str
    destination: str
    wl_number: int   = Field(default=0, ge=0)
    days_before: int = Field(default=30, ge=1, le=120)
    month: int       = Field(default=6, ge=1, le=12)

class TravelAdvisoryRequest(BaseModel):
    source: str
    destination: str
    month: int       = Field(default=11, ge=1, le=12)
    wl_number: int   = Field(default=0, ge=0)
    days_before: int = Field(default=30, ge=1, le=120)

class AssistantRequest(BaseModel):
    query: str

class RouteDemandRequest(BaseModel):
    source: str
    destination: str

class StationCongestionRequest(BaseModel):
    station: str

class StationCrowdRequest(BaseModel):
    station: str

class DelaySimulateRequest(BaseModel):
    train_id: str
    delay_minutes: int
# ══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _safe(fn, *args, **kwargs):
    """Wrap any backend call, raising 500 with message on failure."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.error(f"Backend error in {fn.__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _df_to_list(df) -> list:
    if df is None:
        return []
    try:
        return df.fillna("").to_dict(orient="records")
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════
#  HEALTH & STATUS
# ══════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["health"])
def root():
    return {
        "service": "AI Railway Intelligence API",
        "version": "2.0.0",
        "docs":    "/docs",
        "status":  "running",
    }

@app.get("/api/v1/health", tags=["health"])
def health():
    """System health — checks all backend modules."""
    modules = {}
    checks = [
        ("graph_engine",   graph_summary),
        ("delay_model",    delay_model_info),
        ("resilience",     resilience_summary),
        ("congestion",     congestion_summary),
        ("passenger_flow", passenger_flow_summary),
    ]
    for name, fn in checks:
        try:
            fn()
            modules[name] = "ok"
        except Exception as e:
            modules[name] = f"error: {str(e)[:60]}"

    live = live_api_status()
    return {
        "status":     "healthy" if all(v == "ok" for v in modules.values()) else "degraded",
        "modules":    modules,
        "live_api":   live,
    }


# ══════════════════════════════════════════════════════════════════════════
#  1. NETWORK GRAPH
# ══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/network/summary", tags=["network"])
def api_network_summary():
    """Overall graph metrics: stations, routes, density, avg delay, components."""
    return _safe(graph_summary)

@app.get("/api/v1/network/stations", tags=["network"])
def api_station_list():
    """Full sorted list of all station names."""
    return {"stations": _safe(get_station_list)}

@app.get("/api/v1/network/topology", tags=["network"])
def api_network_topology():
    """Full network graph topology with coordinates designed for React Flow / Leaflet mapping."""
    import os
    import pandas as pd
    try:
        G = load_graph()
        nodes = []
        edges = []
        
        # Build edges list
        for u, v, data in G.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "distance": data.get("distance", 0),
                "travel_time": data.get("travel_time", 0),
                "avg_delay": data.get("avg_delay", 0)
            })
            
        # Get coordinates for nodes
        base_dir = os.path.dirname(os.path.abspath(__file__))
        stations_csv = os.path.join(base_dir, "data", "processed", "stations_clean.csv")
        coords = {}
        if os.path.exists(stations_csv):
            df = pd.read_csv(stations_csv)
            for _, row in df.iterrows():
                try:
                    if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
                        coords[str(row["station_name"])] = {
                            "lat": float(row["latitude"]),
                            "lng": float(row["longitude"])
                        }
                except:
                    pass
        
        # Build nodes list
        for node in G.nodes():
            c = coords.get(node, {"lat": 22.0, "lng": 80.0}) # India center fallback
            nodes.append({
                "id": node,
                "label": node,
                "latitude": c["lat"],
                "longitude": c["lng"]
            })
            
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        logger.error(f"Topology error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/network/critical-stations", tags=["network"])
def api_critical_stations(n: int = Query(default=10, ge=1, le=50)):
    """Top-N stations by betweenness centrality + delay risk."""
    df = _safe(top_critical_stations, n)
    return {"stations": _df_to_list(df)}

@app.get("/api/v1/network/station-importance", tags=["network"])
def api_station_importance(n: int = Query(default=20, ge=1, le=200)):
    """Full station importance rankings with centrality metrics."""
    df = _safe(get_station_importance, n)
    return {"stations": _df_to_list(df)}

@app.get("/api/v1/network/delay-stats/{station}", tags=["network"])
def api_station_delay_stats(station: str):
    """Historical delay statistics for a specific station."""
    try:
        stats = get_delay_stats(station)
        return dict(stats)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/v1/network/neighbors/{station}", tags=["network"])
def api_station_neighbors(station: str):
    """Adjacent stations connected to a given station."""
    try:
        return {"station": station, "neighbors": get_neighbors(station)}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════
#  2. ROUTING
# ══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/route/find", tags=["routing"])
def api_find_route(req: RouteRequest):
    """Optimal route between two stations (Dijkstra). Returns path, legs, timings."""
    try:
        return _safe(get_route_details, req.source, req.destination)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/v1/route/alternatives", tags=["routing"])
def api_alternative_routes(req: AlternativeRouteRequest):
    """
    Find alternative routes with blocked stations.
    Returns primary route + up to N alternatives with reliability scores.
    """
    return _safe(
        find_alternative_routes,
        req.source, req.destination,
        blocked_stations=req.blocked_stations,
        n_alternatives=req.n_alternatives,
    )

@app.post("/api/v1/route/multi-objective", tags=["routing"])
def api_multi_objective_route(req: MultiObjectiveRequest):
    """Score routes by composite time / congestion / reliability weights."""
    return _safe(
        multi_objective_route,
        req.source, req.destination,
        req.weight_time, req.weight_congestion, req.weight_reliability,
    )


# ══════════════════════════════════════════════════════════════════════════
#  3. DELAY PREDICTION
# ══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/delay/predict", tags=["delay"])
def api_predict_delay(req: DelayPredictRequest):
    """Predict expected delay in minutes using the RandomForest model."""
    features = req.dict()
    if features.get("median_delay_min") is None:
        features["median_delay_min"] = features["avg_delay_min"] * 0.85
    predicted = _safe(predict_delay, features)
    level = "high" if predicted >= 90 else "medium" if predicted >= 30 else "low"
    return {
        "predicted_delay_minutes": predicted,
        "risk_level": level,
        "inputs": features,
    }

@app.get("/api/v1/delay/model-info", tags=["delay"])
def api_delay_model_info():
    """Delay model metadata, features, and evaluation metrics."""
    return _safe(delay_model_info)


# ══════════════════════════════════════════════════════════════════════════
#  4. TICKET & WL CONFIRMATION
# ══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/ticket/wl-confirm", tags=["ticket"])
def api_wl_confirm(req: WLConfirmRequest):
    """
    Predict WL ticket confirmation probability.
    Returns probability 0–1 with context.
    """
    prob = _safe(predict_wl_confirmation, req.wl_number, req.days_before)
    pct  = round(prob * 100, 1)
    level = "high" if prob >= 0.70 else "medium" if prob >= 0.40 else "low"
    return {
        "wl_number":             req.wl_number,
        "days_before":           req.days_before,
        "confirmation_probability": prob,
        "confirmation_pct":      pct,
        "confidence_level":      level,
        "recommendation": (
            "Good chance of confirmation — proceed with booking." if prob >= 0.70
            else "Moderate chance — book early or consider alternatives." if prob >= 0.40
            else "Low chance — consider alternative trains or routes."
        ),
    }

@app.post("/api/v1/ticket/wl-rank-trains", tags=["ticket"])
def api_wl_rank_trains(req: WLRankRequest):
    """
    Rank trains between two stations by WL confirmation probability.
    Fixes Gap G4 from audit — per-train confirmation comparison.
    """
    trains = _safe(
        get_trains_by_confirmation_probability,
        req.source, req.destination,
        req.wl_number, req.days_before,
    )
    return {
        "source":      req.source,
        "destination": req.destination,
        "wl_number":   req.wl_number,
        "days_before": req.days_before,
        "trains":      trains,
        "count":       len(trains),
    }

@app.post("/api/v1/ticket/confirm", tags=["ticket"])
def api_ticket_confirm(req: TicketConfirmRequest):
    """Predict confirmation probability from booking-level features."""
    features = req.dict()
    prob = _safe(predict_confirmation, features)
    return {
        "confirmation_probability": prob,
        "confirmation_pct": round(prob * 100, 1),
        "inputs": features,
    }


# ══════════════════════════════════════════════════════════════════════════
#  5. CANCELLATION PREDICTOR  (Gap G3 fix)
# ══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/cancellation/predict", tags=["cancellation"])
def api_predict_cancellation(req: CancellationRequest):
    """
    Predict the probability that a booking will be cancelled.
    New module — addresses audit Gap G3.
    """
    prob = _safe(
        predict_cancellation_probability,
        req.station, req.train_type, req.days_before,
        req.month, req.wl_number, req.occupancy_pct,
    )
    level = "High" if prob >= 0.25 else "Medium" if prob >= 0.12 else "Low"
    return {
        "cancellation_probability": prob,
        "cancellation_pct":         round(prob * 100, 1),
        "risk_level":               level,
        "inputs":                   req.dict(),
    }

@app.get("/api/v1/cancellation/station/{station}", tags=["cancellation"])
def api_station_cancellation(station: str):
    """Historical cancellation stats for a specific station."""
    result = _safe(get_station_cancellation_stats, station)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.get("/api/v1/cancellation/high-risk-routes", tags=["cancellation"])
def api_high_cancel_routes(n: int = Query(default=10, ge=1, le=50)):
    """Top-N stations/routes with highest historical cancellation rates."""
    return {"routes": _safe(get_high_cancellation_routes, n)}

@app.get("/api/v1/cancellation/summary", tags=["cancellation"])
def api_cancellation_summary():
    """Network-wide cancellation summary."""
    return _safe(get_cancellation_summary)


# ══════════════════════════════════════════════════════════════════════════
#  6. CASCADE SIMULATION
# ══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/cascade/simulate", tags=["cascade"])
def api_cascade_simulate(req: CascadeRequest):
    """
    Simulate delay cascade from a source station.
    Returns affected stations, severity score, avg propagated delay.
    """
    return _safe(
        simulate_delay_cascade,
        req.station, req.initial_delay, max_depth=req.max_depth,
    )

@app.get("/api/v1/cascade/vulnerable-stations", tags=["cascade"])
def api_vulnerable_stations(n: int = Query(default=10, ge=1, le=50)):
    """Top-N stations most vulnerable to initiating cascade events."""
    df = _safe(get_most_vulnerable_stations, n)
    return {"stations": _df_to_list(df)}


# ══════════════════════════════════════════════════════════════════════════
#  7. CONGESTION ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/congestion/summary", tags=["congestion"])
def api_congestion_summary():
    """Network-wide congestion summary: high/medium/low station counts."""
    return _safe(congestion_summary)

@app.get("/api/v1/congestion/hotspots", tags=["congestion"])
def api_congestion_hotspots(n: int = Query(default=10, ge=1, le=50)):
    """Top-N most congested stations with scores and levels."""
    return {"hotspots": _safe(identify_congestion_hotspots, n)}

@app.get("/api/v1/congestion/corridors", tags=["congestion"])
def api_congestion_corridors(n: int = Query(default=10, ge=1, le=50)):
    """Top-N most congested rail corridors."""
    return {"corridors": _safe(corridor_congestion_analysis, n)}

@app.post("/api/v1/congestion/station", tags=["congestion"])
def api_station_congestion(req: StationCongestionRequest):
    """Congestion score and level for a specific station."""
    result = _safe(calculate_station_congestion, req.station)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ══════════════════════════════════════════════════════════════════════════
#  8. NETWORK RESILIENCE
# ══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/resilience/summary", tags=["resilience"])
def api_resilience_summary():
    """Network resilience score, connectivity ratio, critical nodes."""
    return _safe(resilience_summary)

@app.get("/api/v1/resilience/compute", tags=["resilience"])
def api_resilience_compute():
    """Full resilience computation with all metrics."""
    return _safe(compute_network_resilience)

@app.get("/api/v1/resilience/critical-nodes", tags=["resilience"])
def api_critical_nodes(n: int = Query(default=10, ge=1, le=50)):
    """Top-N critical infrastructure nodes (removal causes most disruption)."""
    return {"nodes": _safe(identify_critical_nodes, n)}

@app.post("/api/v1/resilience/simulate-removal", tags=["resilience"])
def api_simulate_removal(req: NodeRemovalRequest):
    """Simulate what happens if specific stations are removed from the network."""
    return _safe(simulate_node_removal, req.stations)

@app.get("/api/v1/resilience/communities", tags=["resilience"])
def api_communities(
    algorithm: str = Query(
        default="greedy_modularity",
        enum=["greedy_modularity", "label_propagation"]
    )
):
    """
    Detect railway network communities / operational clusters.
    Fixes Gap G5 from audit — community detection now fully implemented.
    """
    return _safe(detect_railway_communities, algorithm)


# ══════════════════════════════════════════════════════════════════════════
#  9. PASSENGER FLOW
# ══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/passenger/summary", tags=["passenger"])
def api_passenger_summary():
    """Network-wide passenger flow KPIs."""
    return _safe(passenger_flow_summary)

@app.get("/api/v1/passenger/demand-summary", tags=["passenger"])
def api_demand_summary():
    """Detailed demand summary including annual passengers estimate."""
    return _safe(get_network_demand_summary)

@app.get("/api/v1/passenger/busiest-stations", tags=["passenger"])
def api_busiest_stations(n: int = Query(default=10, ge=1, le=100)):
    """Top-N stations ranked by crowd score with peak hours."""
    df = _safe(get_busiest_stations, n)
    return {"stations": _df_to_list(df)}

@app.post("/api/v1/passenger/station-profile", tags=["passenger"])
def api_station_crowd_profile(req: StationCrowdRequest):
    """Hourly + weekly crowd profile for a station."""
    result = _safe(get_station_crowd_profile, req.station)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.get("/api/v1/passenger/seasonal-demand", tags=["passenger"])
def api_seasonal_demand():
    """12-month demand index with festival flags and peak indicators."""
    df = _safe(get_seasonal_demand)
    return {"months": _df_to_list(df)}

@app.post("/api/v1/passenger/route-demand", tags=["passenger"])
def api_route_demand(req: RouteDemandRequest):
    """Monthly occupancy, crowd level, and direct trains for a route."""
    result = _safe(get_route_demand, req.source, req.destination)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.get("/api/v1/passenger/transfer-congestion", tags=["passenger"])
def api_transfer_congestion(n: int = Query(default=10, ge=1, le=50)):
    """Top-N transfer congestion hotspots."""
    df = _safe(get_transfer_congestion_stations, n)
    return {"stations": _df_to_list(df)}

@app.get("/api/v1/passenger/overcrowded-routes", tags=["passenger"])
def api_overcrowded_routes(month: int = Query(default=11, ge=1, le=12)):
    """Overcrowded routes for a specific month."""
    df = _safe(get_overcrowded_routes, month)
    return {"month": month, "routes": _df_to_list(df)}


# ══════════════════════════════════════════════════════════════════════════
#  10. ROUTING OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/optimize/summary", tags=["optimization"])
def api_optimization_summary():
    """Optimization module KPIs: total stations, routes, critical corridors."""
    return _safe(optimization_summary)

@app.post("/api/v1/optimize/schedule-adjust", tags=["optimization"])
def api_schedule_adjust(req: ScheduleAdjustRequest):
    """
    Schedule hold/reschedule recommendations for trains connecting to
    a delayed station. Reduces cascade propagation.
    """
    return _safe(
        suggest_schedule_adjustments,
        req.station, req.delay_minutes, req.n_trains,
    )

@app.get("/api/v1/optimize/corridors", tags=["optimization"])
def api_corridor_priority(n: int = Query(default=10, ge=1, le=30)):
    """High-demand corridor prioritization with action recommendations."""
    df = _safe(prioritize_corridor_trains, n)
    return {"corridors": _df_to_list(df)}


# ══════════════════════════════════════════════════════════════════════════
#  11. TRAVEL INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/travel/summary", tags=["travel"])
def api_travel_summary():
    """Travel intelligence KPIs."""
    return _safe(travel_intelligence_summary)

@app.post("/api/v1/travel/advisory", tags=["travel"])
def api_travel_advisory(req: TravelAdvisoryRequest):
    """
    Full travel advisory: routes, crowd estimates, booking guidance.
    One-stop endpoint for passenger journey planning.
    """
    return _safe(
        get_travel_advisory,
        req.source, req.destination,
        month=req.month,
        wl_number=req.wl_number,
        days_before=req.days_before,
    )

@app.post("/api/v1/travel/crowd-estimate", tags=["travel"])
def api_crowd_estimate(req: CrowdEstimateRequest):
    """Crowd level estimate for a station at a given month and hour."""
    result = _safe(get_crowd_estimate, req.station, month=req.month, hour=req.hour)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.post("/api/v1/travel/booking-guidance", tags=["travel"])
def api_booking_guidance(req: BookingGuidanceRequest):
    """
    Smart ticket booking guidance: advance days, urgency level,
    WL confirmation probability, step-by-step action plan.
    """
    return _safe(
        get_booking_guidance,
        req.source, req.destination,
        wl_number=req.wl_number,
        days_before_travel=req.days_before,
        month=req.month,
    )

@app.post("/api/v1/travel/alternative-routes", tags=["travel"])
def api_alternative_travel(req: TravelAdvisoryRequest):
    """Alternative travel options with crowd and reliability context."""
    return _safe(
        get_alternative_travel,
        req.source, req.destination,
        month=req.month,
    )


# ══════════════════════════════════════════════════════════════════════════
#  12. AI ASSISTANT
# ══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/assistant/ask", tags=["assistant"])
def api_assistant(req: AssistantRequest):
    """
    Natural language railway assistant.
    Detects intent and routes to correct analytics module.
    Supports: delay, ticket, congestion, cascade, routing, passenger flow queries.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return _safe(railway_assistant, req.query)


# ══════════════════════════════════════════════════════════════════════════
#  13. LIVE DATA (RailRadar API)
# ══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/live/status", tags=["live"])
def api_live_status():
    """
    Check RailRadar API connectivity and key status.
    Set RAILRADAR_API_KEY env var to enable live data.
    """
    return live_api_status()

@app.get("/api/v1/live/train/{train_number}", tags=["live"])
def api_live_train(train_number: str):
    """
    Real-time train status: position, delay, next station.
    Falls back to static data if API key not set.
    Powered by RailRadar API (https://railradar.in).
    """
    return get_live_train_status(train_number)

@app.get("/api/v1/live/station/{station_code}", tags=["live"])
def api_live_station_board(station_code: str):
    """
    Live arrivals and departures board for a station (use station code e.g. NDLS, HWH).
    Falls back gracefully if API unavailable.
    """
    return get_live_station_board(station_code)

@app.get("/api/v1/live/trains-between", tags=["live"])
def api_live_trains_between(
    from_station: str = Query(...),
    to_station: str   = Query(...),
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD, defaults to today"),
):
    """
    Live schedule of trains running between two stations.
    Falls back to static data if API key not configured.
    """
    return get_trains_between_live(from_station, to_station, date)

@app.get("/api/v1/live/search", tags=["live"])
def api_live_search(q: str = Query(..., min_length=2), limit: int = Query(default=10, ge=1, le=20)):
    """Train search/autocomplete using RailRadar live data."""
    return {"query": q, "results": search_trains_live(q, limit)}

@app.get("/api/v1/live/delay/{station}", tags=["live"])
def api_live_delay(station: str):
    """
    Best available delay estimate for a station.
    Uses live station board if API key set, otherwise static historical data.
    """
    return enrich_delay_with_live_data(station)

@app.get("/api/v1/live/temporal-graph-snapshot", tags=["live"])
def api_temporal_graph_snapshot():
    """
    Build a live-enriched temporal graph snapshot.
    Queries real-time delays for major trains and re-weights the graph edges.
    Returns summary stats — the enriched graph is used internally for routing.
    """
    try:
        G = build_temporal_graph_snapshot()
        live_nodes = sum(
            1 for n in G.nodes(data=True)
            if n[1].get("has_live_data")
        )
        live_edges = sum(
            1 for u, v, d in G.edges(data=True)
            if d.get("is_live")
        )
        return {
            "total_nodes":     G.number_of_nodes(),
            "total_edges":     G.number_of_edges(),
            "live_data_nodes": live_nodes,
            "live_data_edges": live_edges,
            "coverage_pct":    round(live_nodes / max(G.number_of_nodes(), 1) * 100, 1),
            "note": (
                "Graph re-weighted with live delays (70% live, 30% historical). "
                "Set RAILRADAR_API_KEY for live data."
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════
#  14. SIMULATION
# ══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/simulation/live-trains", tags=["simulation"])
def api_simulation_live_trains(time: Optional[str] = None):
    """
    Get simulated positions of all active trains at a given time or current time.
    """
    return _safe(simulation_service.get_live_trains, time)

@app.post("/api/v1/simulation/delay", tags=["simulation"])
def api_simulation_delay(req: DelaySimulateRequest):
    """
    Inject delay into the simulated train.
    """
    return _safe(simulation_service.simulate_delay, req.train_id, req.delay_minutes)
