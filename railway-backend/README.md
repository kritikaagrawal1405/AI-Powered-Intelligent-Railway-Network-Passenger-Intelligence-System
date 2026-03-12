# AI Railway Intelligence — Backend

FastAPI backend serving all analytics, ML models, and live data endpoints.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run (development)
uvicorn main:app --reload --port 8000

# Run (production)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

**API Docs:** http://localhost:8000/docs  
**ReDoc:** http://localhost:8000/redoc

## Live Data (RailRadar)

Set your API key to enable real-time train tracking:

```bash
export RAILRADAR_API_KEY="your_key_here"
```

Get a key at: https://railradar.in/indian-railway-data-api  
Without a key, all endpoints still work using static historical data.

## Project Structure

```
railway-backend/
├── main.py                          # FastAPI app — all 30 endpoints
├── requirements.txt
├── models/                          # Trained .pkl files
│   ├── delay_prediction_model.pkl
│   ├── ticket_confirmation_model.pkl
│   ├── wl_confirmation_model.pkl
│   └── cancellation_model.pkl       # NEW — Gap G3 fix
├── data/
│   ├── processed/                   # Cleaned CSVs used by modules
│   └── raw/                         # Original datasets
└── src/
    ├── graph_engine/
    │   ├── graph_utils.py           # Core graph, Dijkstra routing
    │   └── build_graph.py
    ├── intelligence/
    │   ├── delay_cascade.py         # BFS cascade simulation
    │   ├── congestion_predictor.py  # Hotspot detection
    │   └── network_resilience.py    # Resilience + community detection (Gap G5 fix)
    ├── ml_models/
    │   ├── train_delay_model.py     # RandomForest delay prediction
    │   ├── wl_model.py              # WL confirmation + per-train ranking (Gap G4 fix)
    │   ├── ticket_confirmation_model.py
    │   └── cancellation_predictor.py  # NEW — Gap G3 fix
    ├── passenger_flow/
    │   └── passenger_flow.py
    ├── routing_optimizer/
    │   └── routing_optimizer.py
    ├── travel_intelligence/
    │   └── travel_intelligence.py
    ├── ai_assistant/
    │   └── railway_assistant.py
    ├── knowledge/
    │   ├── railway_knowledge_base.json
    │   └── knowledge_retrieval.py
    └── live/                        # NEW — RailRadar live API integration
        ├── __init__.py
        └── railradar_client.py
```

## Endpoint Summary (30 total)

| Group | Endpoints |
|---|---|
| Health | `GET /` · `GET /api/v1/health` |
| Network | `GET /network/summary` · `/stations` · `/critical-stations` · `/station-importance` · `/delay-stats/{station}` · `/neighbors/{station}` |
| Routing | `POST /route/find` · `/route/alternatives` · `/route/multi-objective` |
| Delay | `POST /delay/predict` · `GET /delay/model-info` |
| Ticket | `POST /ticket/wl-confirm` · `/ticket/wl-rank-trains` · `/ticket/confirm` |
| Cancellation | `POST /cancellation/predict` · `GET /cancellation/station/{s}` · `/cancellation/high-risk-routes` · `/cancellation/summary` |
| Cascade | `POST /cascade/simulate` · `GET /cascade/vulnerable-stations` |
| Congestion | `GET /congestion/summary` · `/congestion/hotspots` · `/congestion/corridors` · `POST /congestion/station` |
| Resilience | `GET /resilience/summary` · `/resilience/compute` · `/resilience/critical-nodes` · `/resilience/communities` · `POST /resilience/simulate-removal` |
| Passenger | `GET /passenger/summary` · `/passenger/busiest-stations` · `/passenger/seasonal-demand` · `/passenger/transfer-congestion` · `/passenger/overcrowded-routes` · `POST /passenger/station-profile` · `/passenger/route-demand` |
| Optimization | `GET /optimize/summary` · `/optimize/corridors` · `POST /optimize/schedule-adjust` |
| Travel | `GET /travel/summary` · `POST /travel/advisory` · `/travel/crowd-estimate` · `/travel/booking-guidance` · `/travel/alternative-routes` |
| Assistant | `POST /assistant/ask` |
| Live | `GET /live/status` · `/live/train/{number}` · `/live/station/{code}` · `/live/trains-between` · `/live/search` · `/live/delay/{station}` · `/live/temporal-graph-snapshot` |

## Gaps Fixed vs Original Streamlit App

| Gap | Status | Fix |
|---|---|---|
| G3 — Cancellation predictor | ✅ Fixed | `src/ml_models/cancellation_predictor.py` |
| G4 — Per-train WL ranking | ✅ Fixed | `get_trains_by_confirmation_probability()` in `wl_model.py` |
| G5 — Community detection | ✅ Fixed | `detect_railway_communities()` in `network_resilience.py` |
| Live temporal graph | ✅ New | `src/live/railradar_client.py` — RailRadar API integration |
