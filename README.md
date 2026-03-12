# 🚂 AI-Powered Railway Intelligence System
### Data & Graph Layer — Person 1 Module  |  v2 — Real Data

---

## Datasets Used

| Dataset | File | Records | Source |
|---------|------|---------|--------|
| Train delay statistics | `etrain_delays.csv` | 1,900 rows — 90 trains, 480 stations | etrain.info (scraped Sep 2025) |
| Long-distance routes | `IRI-longestroutes.pdf` | 78 routes with distance + duration | IndiaRailInfo, Mar 2026 |
| Ticket reservations | `railway_reservation_dataset.csv` | 14 rows | For ML ticket prediction team |

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run full pipeline (one command)
python run_pipeline.py
```

---

## Pipeline Steps

| Step | Script | What it does |
|------|--------|-------------|
| 1 | `src/parse_pdf_routes.py` | Parses IRI PDF → 78 routes with distances |
| 2 | `src/data_preprocessing.py` | Cleans etrain + PDF → stations, routes, delay stats, ML features |
| 3-4 | `src/graph_engine/build_graph.py` | Builds NetworkX graph + centrality analytics |
| 5 | `src/graph_engine/visualize_graph.py` | Interactive HTML + static PNG |

---

## Graph Stats (Real Data)

- **513 stations** across India
- **1,324 directed routes** (from consecutive train stops + PDF long-distance arcs)
- **Delay data** on edges from real etrain observations
- **Top bottleneck station**: Howrah Jn (betweenness = 0.41)

---

## Integration API

```python
from src.graph_engine.graph_utils import (
    load_graph, get_station_list, get_neighbors,
    shortest_route, get_route_details,
    get_station_importance, get_delay_stats,
    get_delay_prone_stations, graph_summary,
)

G = load_graph()

# Summary for dashboard cards
print(graph_summary())
# → {"num_stations": 513, "num_routes": 1324, "network_avg_delay_min": 28.4, ...}

# Shortest route (distance)
path, km = shortest_route("Arakkonam", "Erode Jn")

# Delay-aware routing (minimise accumulated delay)
path, delay = shortest_route("Howrah", "Chennai Central", weight="avg_delay")

# Detailed breakdown
details = get_route_details("Arakkonam", "Erode Jn")
# → {"path": [...], "total_distance_km": ..., "total_travel_time_min": ...,
#    "total_delay_min": ..., "legs": [...]}

# High-risk stations
risky = get_delay_prone_stations(threshold=30.0)
```

---

## Files for Teammates

### ML Delay Prediction Team
| File | Description | Key Columns |
|------|-------------|-------------|
| `schedule_features.csv` | 1,900 ML-ready records | is_delayed, delay_category, on_time_ratio, significant_delay_ratio |
| `station_delay_stats.csv` | Per-station aggregates | avg_delay_min, delay_risk_score, num_trains |
| `station_importance.csv` | Graph centrality + delay risk | betweenness_centrality, delay_risk_score |
| `graph_edges.csv` | Route-level delay averages | avg_delay_on_edge, distance, travel_time |

### ML Ticket Prediction Team
| File | Description |
|------|-------------|
| `data/raw/railway_reservation_dataset.csv` | Booking_status, Train, PNR, passenger info |

### Dashboard Team
| File | Description |
|------|-------------|
| `stations_clean.csv` | 513 stations with lat/lon |
| `graph_edges.csv` | 1,324 routes for network graph |
| `railway_network.html` | Pre-built interactive graph (open in browser) |
| `station_importance.csv` | Colour-code stations by criticality |

---

## Project Structure

```
railway-intelligence-system/
├── run_pipeline.py
├── requirements.txt
├── README.md
├── data/
│   ├── raw/
│   │   ├── etrain_delays.csv              ← PRIMARY DATASET
│   │   ├── IRI-longestroutes.pdf          ← ROUTE DISTANCES
│   │   ├── railway_reservation_dataset.csv← FOR ML TICKET TEAM
│   │   ├── pdf_routes.csv                 ← parsed from PDF
│   │   └── pdf_stations.csv               ← parsed from PDF
│   └── processed/
│       ├── graph_edges.csv                ← FOR ALL TEAMS
│       ├── stations_clean.csv             ← FOR DASHBOARD
│       ├── station_importance.csv         ← FOR ML + DASHBOARD
│       ├── station_delay_stats.csv        ← FOR ML TEAM
│       ├── schedule_features.csv          ← FOR ML TEAM
│       ├── routes.csv
│       ├── stations.csv
│       ├── railway_network.html           ← INTERACTIVE VIZ
│       └── railway_network.png
└── src/
    ├── parse_pdf_routes.py
    ├── data_preprocessing.py
    └── graph_engine/
        ├── build_graph.py
        ├── graph_utils.py      ← PUBLIC API
        └── visualize_graph.py
```
