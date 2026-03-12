"""
AI-Powered Railway Intelligence Dashboard
==========================================
Hackathon demo dashboard integrating:
  - Railway graph API (graph_utils)
  - Delay prediction model
  - Ticket confirmation model
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

# ── Path setup FIRST — must happen before any src.* imports ───────────────
_DASH_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT     = os.path.dirname(_DASH_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from src.intelligence.delay_cascade import (
        simulate_delay_cascade,
        get_most_vulnerable_stations,
        visualize_cascade,
    )
    CASCADE_OK = True
except Exception as e:
    CASCADE_OK = False
    CASCADE_ERR = str(e)

import pandas as pd
import numpy as np
import streamlit as st

# ── Lazy imports with helpful error messages ───────────────────────────────
try:
    from src.graph_engine.graph_utils import (
        load_graph, graph_summary, get_station_list,
        get_route_details, top_critical_stations, get_delay_stats,
    )
    GRAPH_OK = True
except Exception as e:
    GRAPH_OK = False
    GRAPH_ERR = str(e)

    #New D
try:
    from src.intelligence.congestion_predictor import (
        identify_congestion_hotspots,
        corridor_congestion_analysis,
        congestion_summary,
        calculate_station_congestion,
    )
    CONGESTION_OK = True
except Exception as e:
    CONGESTION_OK = False
    CONGESTION_ERR = str(e)

try:
    from src.ai_assistant.railway_assistant import railway_assistant as ai_ask
    # get_sample_queries is not in the new module — define inline fallback
    def get_sample_queries():
        return {
            "passenger": [
                "What are the chances my WL 20 ticket will confirm?",
                "WL 5, travelling in 3 days — will it confirm?",
                "How delayed is Howrah Jn usually?",
                "Best route from Mumbai to Delhi",
                "Which trains from Nagpur to Bhubaneswar have lowest delay?",
            ],
            "operator": [
                "Which stations are most vulnerable to delay cascades?",
                "Show network congestion hotspots",
                "If Nagpur is delayed 60 min, what stations are affected?",
                "Which routes are most congested?",
                "Give me a network status overview",
            ],
        }
    AI_OK = True
except Exception as e:
    AI_OK = False
    AI_ERR = str(e)

try:
    from src.ml_models.train_delay_model import predict_delay
    DELAY_OK = True
except Exception as e:
    DELAY_OK = False
    DELAY_ERR = str(e)

try:
    from src.ml_models.ticket_confirmation_model import predict_confirmation
    TICKET_OK = True
except Exception as e:
    TICKET_OK = False
    TICKET_ERR = str(e)
try:
    from src.passenger_flow.passenger_flow import (
        get_network_demand_summary,
        get_busiest_stations,
        get_station_crowd_profile,
        get_seasonal_demand,
        get_route_demand,
        get_transfer_congestion_stations,
        get_overcrowded_routes,
        passenger_flow_summary,
    )
    FLOW_OK = True
except Exception as e:
    FLOW_OK = False
    FLOW_ERR = str(e)

try:
    from src.routing_optimizer.routing_optimizer import (
        find_alternative_routes,
        suggest_schedule_adjustments,
        multi_objective_route,
        prioritize_corridor_trains,
        optimization_summary,
    )
    OPT_OK = True
except Exception as e:
    OPT_OK = False
    OPT_ERR = str(e)

try:
    from src.travel_intelligence.travel_intelligence import (
        get_alternative_travel,
        get_crowd_estimate,
        get_booking_guidance,
        get_travel_advisory,
        travel_intelligence_summary,
    )
    TRAVEL_OK = True
except Exception as e:
    TRAVEL_OK = False
    TRAVEL_ERR = str(e)

# ══════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG & GLOBAL STYLES
# ══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Railway Intelligence",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

/* ── Root variables ─────────────────────────────────────── */
:root {
    --bg:        #0a0e1a;
    --panel:     #111827;
    --border:    #1e293b;
    --accent:    #f97316;
    --accent2:   #38bdf8;
    --accent3:   #4ade80;
    --warn:      #facc15;
    --danger:    #f87171;
    --text:      #e2e8f0;
    --muted:     #64748b;
    --rail:      #f97316;
}

/* ── Global resets ──────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}

/* ── Sidebar ────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--panel) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* ── Header ─────────────────────────────────────────────── */
.dash-header {
    padding: 2rem 0 1.5rem 0;
    border-bottom: 2px solid var(--border);
    margin-bottom: 2rem;
}
.dash-title {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 2.6rem;
    letter-spacing: 0.08em;
    color: var(--accent);
    text-transform: uppercase;
    line-height: 1;
}
.dash-subtitle {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: var(--muted);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 0.3rem;
}
.train-icon { color: var(--accent); margin-right: 0.5rem; }

/* ── Metric cards ───────────────────────────────────────── */
[data-testid="metric-container"] {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    padding: 1rem !important;
    position: relative;
    overflow: hidden;
}
[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: var(--accent);
}
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.1em; }
[data-testid="stMetricValue"] { color: var(--text) !important; font-family: 'Rajdhani', sans-serif !important; font-size: 2rem !important; font-weight: 700 !important; }

/* ── Tabs ───────────────────────────────────────────────── */
[data-testid="stTabs"] button {
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--muted) !important;
    border-bottom: 2px solid transparent !important;
    background: transparent !important;
    padding: 0.5rem 1.5rem !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}
[data-testid="stTabs"] {
    border-bottom: 1px solid var(--border) !important;
    margin-bottom: 1.5rem;
}

/* ── Section headers ────────────────────────────────────── */
.section-head {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent2);
    border-left: 3px solid var(--accent2);
    padding-left: 0.75rem;
    margin: 1.5rem 0 1rem 0;
}

/* ── Buttons ────────────────────────────────────────────── */
[data-testid="stButton"] > button {
    background: var(--accent) !important;
    color: #000 !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 2px !important;
    padding: 0.5rem 2rem !important;
    transition: all 0.15s ease !important;
}
[data-testid="stButton"] > button:hover {
    background: #ea6c00 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(249,115,22,0.4) !important;
}

/* ── Inputs ─────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] input,
[data-testid="stSlider"] {
    background: var(--panel) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}
[data-baseweb="select"] > div {
    background: var(--panel) !important;
    border-color: var(--border) !important;
}

/* ── Tables ─────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
}
thead th {
    background: var(--panel) !important;
    color: var(--accent) !important;
    font-family: 'Rajdhani', sans-serif !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}

/* ── Result cards ───────────────────────────────────────── */
.result-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1.5rem;
    margin: 1rem 0;
    position: relative;
}
.result-card.success { border-left: 4px solid var(--accent3); }
.result-card.warning { border-left: 4px solid var(--warn); }
.result-card.danger  { border-left: 4px solid var(--danger); }
.result-card.info    { border-left: 4px solid var(--accent2); }

.result-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.4rem;
}
.result-value {
    font-family: 'Rajdhani', sans-serif;
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--text);
    line-height: 1;
}
.result-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 2px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.9rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 0.5rem;
}
.badge-low    { background: rgba(74,222,128,0.15); color: var(--accent3); border: 1px solid var(--accent3); }
.badge-med    { background: rgba(250,204,21,0.15);  color: var(--warn);    border: 1px solid var(--warn); }
.badge-high   { background: rgba(248,113,113,0.15); color: var(--danger);  border: 1px solid var(--danger); }

/* ── Route path display ─────────────────────────────────── */
.route-path {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.3rem;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1rem 1.25rem;
    margin: 1rem 0;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
}
.route-stop {
    color: var(--accent2);
    padding: 0.15rem 0.5rem;
    background: rgba(56,189,248,0.08);
    border-radius: 2px;
    border: 1px solid rgba(56,189,248,0.2);
}
.route-stop.origin, .route-stop.terminus {
    color: var(--accent);
    background: rgba(249,115,22,0.08);
    border-color: rgba(249,115,22,0.3);
    font-weight: 600;
}
.route-arrow { color: var(--muted); font-size: 0.7rem; }

/* ── Progress bar ───────────────────────────────────────── */
.prob-bar-wrap { margin: 1rem 0; }
.prob-bar-bg {
    background: var(--border);
    border-radius: 2px;
    height: 8px;
    overflow: hidden;
    width: 100%;
}
.prob-bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.5s ease;
}

/* ── Sidebar stat rows ──────────────────────────────────── */
.stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.4rem 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.8rem;
}
.stat-row:last-child { border-bottom: none; }
.stat-key { color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.7rem; }
.stat-val { color: var(--text); font-family: 'IBM Plex Mono', monospace; font-weight: 500; }

/* ── Status dot ─────────────────────────────────────────── */
.status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}
.dot-green { background: var(--accent3); box-shadow: 0 0 6px var(--accent3); }
.dot-red   { background: var(--danger);  box-shadow: 0 0 6px var(--danger); }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def cached_graph_summary():
    return graph_summary()

@st.cache_data(show_spinner=False)
def cached_station_list():
    return get_station_list()

@st.cache_data(show_spinner=False)
def cached_critical_stations(n=10):
    return top_critical_stations(n)

def _status_dot(ok: bool) -> str:
    cls = "dot-green" if ok else "dot-red"
    return f'<span class="status-dot {cls}"></span>'

def _badge(label: str, level: str) -> str:
    return f'<span class="result-badge badge-{level}">{label}</span>'

def _route_path_html(path: list) -> str:
    parts = []
    for i, stop in enumerate(path):
        cls = "route-stop"
        if i == 0: cls += " origin"
        elif i == len(path)-1: cls += " terminus"
        parts.append(f'<span class="{cls}">{stop}</span>')
        if i < len(path)-1:
            parts.append('<span class="route-arrow">▶</span>')
    return f'<div class="route-path">{"".join(parts)}</div>'

# ══════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 0.5rem 0; border-bottom:1px solid #1e293b; margin-bottom:1rem;">
        <div style="font-family:'Rajdhani',sans-serif;font-size:1.1rem;font-weight:700;
                    letter-spacing:0.12em;text-transform:uppercase;color:#f97316;">
            🚆 System Status
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Module status
    for name, ok in [("Graph Engine", GRAPH_OK), ("Delay Model", DELAY_OK), ("Ticket Model", TICKET_OK)]:
        dot = _status_dot(ok)
        st.markdown(
            f'<div class="stat-row"><span class="stat-key">{dot}{name}</span>'
            f'<span class="stat-val" style="color:{"#4ade80" if ok else "#f87171"}">'
            f'{"ONLINE" if ok else "ERROR"}</span></div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if GRAPH_OK:
        try:
            summary = cached_graph_summary()
            st.markdown('<div class="section-head" style="font-size:0.85rem">Graph Stats</div>', unsafe_allow_html=True)
            rows = [
                ("Stations", f"{summary['num_stations']:,}"),
                ("Routes",   f"{summary['num_routes']:,}"),
                ("Density",  f"{summary['density']:.6f}"),
                ("Avg Delay",f"{summary['network_avg_delay_min']} min"),
                ("Components", str(summary['num_components'])),
            ]
            for k, v in rows:
                st.markdown(
                    f'<div class="stat-row"><span class="stat-key">{k}</span>'
                    f'<span class="stat-val">{v}</span></div>',
                    unsafe_allow_html=True
                )
        except:
            pass

    st.markdown("<br>", unsafe_allow_html=True)

    try:
        edges_df = pd.read_csv(os.path.join(_ROOT, "data", "processed", "graph_edges.csv"))
        stations_df = pd.read_csv(os.path.join(_ROOT, "data", "processed", "stations_clean.csv"))
        st.markdown('<div class="section-head" style="font-size:0.85rem">Dataset Size</div>', unsafe_allow_html=True)
        for k, v in [("Edge records", f"{len(edges_df):,}"), ("Station records", f"{len(stations_df):,}")]:
            st.markdown(
                f'<div class="stat-row"><span class="stat-key">{k}</span>'
                f'<span class="stat-val">{v}</span></div>',
                unsafe_allow_html=True
            )
    except:
        pass

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.6rem;'
        'color:#374151;text-align:center;text-transform:uppercase;letter-spacing:0.1em;">'
        'AI Railway Intelligence v2.0<br>Hackathon Demo</div>',
        unsafe_allow_html=True
    )

# ══════════════════════════════════════════════════════════════════════════
#  MAIN HEADER
# ══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="dash-header">
    <div class="dash-title">🚆 AI-Powered Railway Intelligence Dashboard</div>
    <div class="dash-subtitle">Real-time network analytics · Route intelligence · ML predictions</div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "🗺️  Network Overview",
    "🧭  Route Intelligence",
    "⏱️  Delay Prediction",
    "🎟️  Ticket Confirmation",
    "🌊  Cascade Simulator",
    "🚦  Congestion Analysis",
    "🤖  AI Assistant",
    "👥  Passenger Flow",
    "⚙️  Smart Routing",
    "🧳  Travel Advisor",
])

# ──────────────────────────────────────────────────────────────────────────
#  TAB 1 — NETWORK OVERVIEW
# ──────────────────────────────────────────────────────────────────────────

with tab1:
    if not GRAPH_OK:
        st.error(f"Graph engine unavailable: {GRAPH_ERR}")
    else:
        try:
            summary = cached_graph_summary()

            st.markdown('<div class="section-head">Network Metrics</div>', unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("🏙️ Stations", f"{summary['num_stations']:,}")
            with c2:
                st.metric("🛤️ Routes", f"{summary['num_routes']:,}")
            with c3:
                st.metric("📊 Density", f"{summary['density']:.5f}")
            with c4:
                delay_val = summary.get("network_avg_delay_min")
                st.metric("⏱️ Avg Delay", f"{delay_val} min" if delay_val else "N/A")

            c5, c6, c7, c8 = st.columns(4)
            with c5:
                st.metric("🔗 Components", f"{summary['num_components']}")
            with c6:
                st.metric("🏆 Largest Component", f"{summary['largest_component']:,}")
            with c7:
                st.metric("↗️ Avg Out-Degree", f"{summary['avg_out_degree']}")
            with c8:
                connectivity = round(summary['num_routes'] / max(summary['num_stations'], 1), 1)
                st.metric("⚡ Routes/Station", f"{connectivity}")

            st.markdown('<div class="section-head">Top 10 Critical Stations</div>', unsafe_allow_html=True)
            st.markdown(
                '<p style="color:#64748b;font-size:0.8rem;margin-bottom:1rem;">'
                'Ranked by betweenness centrality — stations on many shortest paths.'
                ' Disruptions here cascade across the entire network.</p>',
                unsafe_allow_html=True
            )

            critical = cached_critical_stations(10)

            # Format for display
            display_cols = [c for c in [
                "importance_rank", "station_name", "betweenness_centrality",
                "degree_centrality", "total_degree", "avg_delay_min", "delay_risk_score"
            ] if c in critical.columns]

            styled_df = critical[display_cols].copy()
            styled_df.columns = [c.replace("_", " ").title() for c in display_cols]

            # Highlight delay risk score
            def highlight_risk(val):
                try:
                    v = float(val)
                    if v >= 60: return 'color: #f87171'
                    elif v >= 30: return 'color: #facc15'
                    else: return 'color: #4ade80'
                except:
                    return ''

            if "Delay Risk Score" in styled_df.columns:
                st.dataframe(
                    styled_df.style.applymap(highlight_risk, subset=["Delay Risk Score"]),
                    use_container_width=True, hide_index=True
                )
            else:
                st.dataframe(styled_df, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error loading network data: {e}")

# ──────────────────────────────────────────────────────────────────────────
#  TAB 2 — ROUTE INTELLIGENCE
# ──────────────────────────────────────────────────────────────────────────

with tab2:
    if not GRAPH_OK:
        st.error(f"Graph engine unavailable: {GRAPH_ERR}")
    else:
        try:
            stations = cached_station_list()

            st.markdown('<div class="section-head">Route Explorer</div>', unsafe_allow_html=True)

            col_src, col_dst = st.columns(2)
            with col_src:
                st.markdown('<p style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.3rem;">Origin Station</p>', unsafe_allow_html=True)
                source = st.selectbox(
                    "Source", stations,
                    index=stations.index("Mumbai CST") if "Mumbai CST" in stations else 0,
                    label_visibility="collapsed",
                    key="route_src"
                )
            with col_dst:
                st.markdown('<p style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.3rem;">Destination Station</p>', unsafe_allow_html=True)
                dest_default = "New Delhi" if "New Delhi" in stations else stations[min(50, len(stations)-1)]
                destination = st.selectbox(
                    "Destination", stations,
                    index=stations.index(dest_default) if dest_default in stations else 1,
                    label_visibility="collapsed",
                    key="route_dst"
                )

            st.markdown("<br>", unsafe_allow_html=True)
            find_btn = st.button("🔍 Find Best Route", key="find_route")

            if find_btn:
                if source == destination:
                    st.warning("Origin and destination cannot be the same station.")
                else:
                    with st.spinner("Computing optimal route via Dijkstra..."):
                        try:
                            details = get_route_details(source, destination)

                            # Route path
                            st.markdown('<div class="section-head">Optimal Route</div>', unsafe_allow_html=True)
                            st.markdown(_route_path_html(details["path"]), unsafe_allow_html=True)

                            # Summary metrics
                            m1, m2, m3, m4 = st.columns(4)
                            with m1:
                                st.metric("🛤️ Total Stops", details["num_stops"])
                            with m2:
                                km = details["total_distance_km"]
                                st.metric("📏 Total Distance", f"{km:,.0f} km" if km > 0 else "N/A")
                            with m3:
                                mins = details["total_travel_time_min"]
                                if mins > 0:
                                    hrs = int(mins // 60)
                                    rem = int(mins % 60)
                                    label = f"{hrs}h {rem}m" if hrs > 0 else f"{rem}m"
                                else:
                                    label = "N/A"
                                st.metric("⏰ Travel Time", label)
                            with m4:
                                st.metric("⚠️ Cumulative Delay", f"{details['total_delay_min']:.0f} min")

                            # Legs table
                            if details["legs"]:
                                st.markdown('<div class="section-head">Route Legs Breakdown</div>', unsafe_allow_html=True)
                                legs_df = pd.DataFrame(details["legs"])
                                legs_df.columns = [c.replace("_", " ").title() for c in legs_df.columns]
                                legs_df.index = range(1, len(legs_df)+1)
                                st.dataframe(legs_df, use_container_width=True)

                        except RuntimeError as e:
                            st.error(f"No route found: {e}")
                        except ValueError as e:
                            st.error(f"Station error: {e}")
                        except Exception as e:
                            st.error(f"Unexpected error: {e}")

        except Exception as e:
            st.error(f"Error initialising route explorer: {e}")

# ──────────────────────────────────────────────────────────────────────────
#  TAB 3 — DELAY PREDICTION
# ──────────────────────────────────────────────────────────────────────────

with tab3:
    if not DELAY_OK:
        st.error(f"Delay model unavailable: {DELAY_ERR}")
    else:
        st.markdown('<div class="section-head">Input Features</div>', unsafe_allow_html=True)
        st.markdown(
            '<p style="color:#64748b;font-size:0.8rem;margin-bottom:1.2rem;">'
            'Adjust the parameters below to predict expected train delay at a station.</p>',
            unsafe_allow_html=True
        )

        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown('<p style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;">Historical Avg Delay (min)</p>', unsafe_allow_html=True)
            avg_delay = st.number_input(
                "avg_delay", min_value=0.0, max_value=600.0, value=60.0,
                step=5.0, label_visibility="collapsed", key="d_avg_delay"
            )

            st.markdown('<br><p style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;">Significant Delay Ratio (0–1)</p>', unsafe_allow_html=True)
            sig_delay_ratio = st.slider(
                "sig_ratio", 0.0, 1.0, 0.3, 0.01,
                label_visibility="collapsed", key="d_sig_ratio"
            )

            st.markdown('<br><p style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;">On-Time Ratio (0–1)</p>', unsafe_allow_html=True)
            on_time_ratio = st.slider(
                "on_time", 0.0, 1.0, 0.65, 0.01,
                label_visibility="collapsed", key="d_on_time"
            )

        with col_r:
            st.markdown('<p style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;">Delay Risk Score (0–100)</p>', unsafe_allow_html=True)
            delay_risk = st.slider(
                "risk_score", 0, 100, 35,
                label_visibility="collapsed", key="d_risk"
            )

            st.markdown('<br><p style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;">Stop Number in Journey</p>', unsafe_allow_html=True)
            stop_number = st.slider(
                "stop_num", 0, 40, 8,
                label_visibility="collapsed", key="d_stop"
            )

            st.markdown('<br><p style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;">Betweenness Centrality (0–1)</p>', unsafe_allow_html=True)
            centrality = st.slider(
                "centrality", 0.0, 1.0, 0.1, 0.01,
                label_visibility="collapsed", key="d_central"
            )

        st.markdown("<br>", unsafe_allow_html=True)
        predict_delay_btn = st.button("⚡ Predict Delay", key="pred_delay")

        if predict_delay_btn:
            with st.spinner("Running delay prediction model..."):
                try:
                    features = {
                        "avg_delay_min":           avg_delay,
                        "median_delay_min":        avg_delay * 0.85,
                        "significant_delay_ratio": sig_delay_ratio,
                        "pct_significant_delay":   sig_delay_ratio * 100,
                        "on_time_ratio":           on_time_ratio,
                        "pct_right_time":          on_time_ratio * 100,
                        "delay_risk_score":        float(delay_risk),
                        "stop_number":             stop_number,
                        "betweenness_centrality":  centrality,
                    }
                    predicted = predict_delay(features)

                    # Risk label
                    if predicted < 30:
                        risk_level, badge_cls, badge_label = "low", "badge-low", "Low Delay Risk"
                        card_cls = "success"
                    elif predicted < 90:
                        risk_level, badge_cls, badge_label = "med", "badge-med", "Moderate Delay Risk"
                        card_cls = "warning"
                    else:
                        risk_level, badge_cls, badge_label = "high", "badge-high", "High Delay Risk"
                        card_cls = "danger"

                    # Result display
                    r_col1, r_col2 = st.columns([1, 2])
                    with r_col1:
                        st.markdown(f"""
                        <div class="result-card {card_cls}">
                            <div class="result-label">Predicted Delay</div>
                            <div class="result-value">{predicted:.1f}</div>
                            <div style="color:#64748b;font-size:0.75rem;margin-top:0.2rem;">minutes</div>
                            <br>
                            <span class="result-badge badge-{risk_level}">{badge_label}</span>
                        </div>
                        """, unsafe_allow_html=True)

                    with r_col2:
                        st.markdown('<div class="result-card info">', unsafe_allow_html=True)
                        st.markdown('<div class="result-label">Prediction Context</div>', unsafe_allow_html=True)
                        ctx_data = {
                            "Feature": ["Avg Historical Delay", "Significant Delay Ratio", "On-Time Ratio", "Risk Score", "Stop Number", "Betweenness"],
                            "Input": [f"{avg_delay:.1f} min", f"{sig_delay_ratio:.2f}", f"{on_time_ratio:.2f}", f"{delay_risk}/100", str(stop_number), f"{centrality:.2f}"],
                        }
                        st.dataframe(pd.DataFrame(ctx_data), use_container_width=True, hide_index=True)
                        st.markdown('</div>', unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Prediction failed: {e}")

# ──────────────────────────────────────────────────────────────────────────
#  TAB 4 — TICKET CONFIRMATION
# ──────────────────────────────────────────────────────────────────────────

with tab4:
    if not TICKET_OK:
        st.error(f"Ticket model unavailable: {TICKET_ERR}")
    else:
        st.markdown("## 🎟️ Ticket Confirmation Predictor")
        st.markdown("_Enter your waitlist number and days before travel to predict confirmation probability._")
        st.markdown("---")

        # ── Inputs — exactly as per task spec ────────────────────────────
        wl_col, days_col, btn_col = st.columns([1, 1, 1])

        with wl_col:
            wl_number = st.number_input(
                "Waitlist Number", min_value=1, max_value=100, value=20, key="t_wl"
            )

        with days_col:
            days_before = st.number_input(
                "Days Before Travel", min_value=1, max_value=120, value=7, key="t_days"
            )

        with btn_col:
            st.markdown("<br>", unsafe_allow_html=True)
            predict_ticket_btn = st.button("🎟️ Predict Confirmation", key="pred_ticket")

        # ── Output — exactly as per task spec ─────────────────────────────
        if predict_ticket_btn:
            with st.spinner("Analysing..."):
                try:
                    from src.ml_models.wl_model import predict_wl_confirmation
                    prob = predict_wl_confirmation(wl_number, days_before)
                    pct  = round(prob * 100, 1)

                    if pct >= 70:
                        color = "#4ade80"
                    elif pct >= 40:
                        color = "#facc15"
                    else:
                        color = "#f87171"

                    # Display: Probability: 76%  (as per task spec)
                    st.markdown(
                        f"<div style='text-align:center;padding:32px;"
                        f"background:#0f1f35;border-radius:12px;margin:16px 0;'>"
                        f"<span style='font-size:1.2rem;color:#94a3b8;'>Probability: </span>"
                        f"<span style='font-size:3rem;font-weight:800;color:{color};'>{pct}%</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    c1, c2, c3 = st.columns(3)
                    c1.metric("WL Number", f"WL {wl_number}")
                    c2.metric("Days Before Travel", f"{days_before} days")
                    c3.metric("Probability", f"{pct}%")

                except Exception as e:
                    st.error(f"Prediction failed: {e}")

# ── TAB 5 — DELAY CASCADE SIMULATOR ──────────────────────────────────────
with tab5:
    if not CASCADE_OK:
        st.error(f"Cascade engine unavailable: {CASCADE_ERR}")
    else:
        st.markdown("### 🌊 Delay Cascade Simulation")

        stations = get_station_list() if GRAPH_OK else []
        col1, col2, col3 = st.columns(3)

        with col1:
            source = st.selectbox("Source Station", stations,
                                  index=stations.index("Nagpur") if "Nagpur" in stations else 0)
        with col2:
            delay_val = st.slider("Initial Delay (minutes)", 10, 180, 60)
        with col3:
            depth_val = st.slider("Propagation Depth (hops)", 1, 4, 3)

        if st.button("▶ Simulate Cascade"):
            result = simulate_delay_cascade(source, delay_val, max_depth=depth_val)

            st.metric("Stations Affected", result["total_stations_affected"])
            st.metric("Avg Propagated Delay", f"{result['avg_propagated_delay']:.1f} min")
            st.metric("Severity Score", f"{result['cascade_severity_score']:.1f} / 100")

            st.markdown(f"**{result['summary']}**")

            df = pd.DataFrame(result["affected_stations"])
            st.dataframe(df[["station", "delay", "depth"]]
                           .rename(columns={"station": "Station",
                                            "delay": "Delay (min)",
                                            "depth": "Hops"}),
                         use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🎯 Most Vulnerable Stations")
        vuln_df = get_most_vulnerable_stations(10)
        st.dataframe(vuln_df, use_container_width=True, hide_index=True)

# ── TAB 6 — CONGESTION ANALYSIS ──────────────────────────────────────────
with tab6:
    if not CONGESTION_OK:
        st.error(f"Congestion engine unavailable: {CONGESTION_ERR}")
    else:
        st.markdown("## 🚦 Railway Congestion Analysis")

        # ── Row 1: Summary metric cards ──────────────────────────────
        summary = congestion_summary()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔴 High Congestion",     summary["high_congestion_stations"],     "stations")
        c2.metric("🟠 Moderate Congestion", summary["moderate_congestion_stations"], "stations")
        c3.metric("🟢 Low Congestion",      summary["low_congestion_stations"],      "stations")
        c4.metric("📍 Most Congested",      summary["most_congested_station"])

        st.markdown("---")

        # ── Row 2: Hotspots + Corridors side by side ─────────────────
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### 🏙️ Top Congested Stations")
            hotspots = identify_congestion_hotspots(n=10)
            df_hot = pd.DataFrame(hotspots)[[
                "rank", "station", "congestion_score",
                "congestion_level", "avg_delay_min"
            ]].rename(columns={
                "rank"             : "#",
                "station"          : "Station",
                "congestion_score" : "Score",
                "congestion_level" : "Level",
                "avg_delay_min"    : "Avg Delay (min)",
            })
            st.dataframe(df_hot, use_container_width=True, hide_index=True)

        with col_right:
            st.markdown("### 🛤️ Top Congested Corridors")
            corridors = corridor_congestion_analysis(top_n=10)
            df_cor = pd.DataFrame(corridors)[[
                "rank", "route", "congestion_score",
                "congestion_level", "avg_delay_min"
            ]].rename(columns={
                "rank"             : "#",
                "route"            : "Route",
                "congestion_score" : "Score",
                "congestion_level" : "Level",
                "avg_delay_min"    : "Avg Delay (min)",
            })
            st.dataframe(df_cor, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── Row 3: Single station lookup ─────────────────────────────
        st.markdown("### 🔍 Check Any Station")
        station_list = sorted([h["station"] for h in hotspots])
        selected = st.selectbox("Select a station", get_station_list())
        if st.button("Analyse Congestion"):
            result = calculate_station_congestion(selected)
            r1, r2, r3 = st.columns(3)
            r1.metric("Congestion Score", f"{result['congestion_score']} / 100")
            r2.metric("Congestion Level", result["congestion_level"])
            r3.metric("Avg Delay",        f"{result['avg_delay_min']} min")



# ── TAB 7 — AI ASSISTANT ──────────────────────────────────────────────────
with tab7:
    if not AI_OK:
        st.error(f"AI Assistant unavailable: {AI_ERR}")
        st.info("Make sure `src/ai_assistant/railway_assistant.py` exists and all models are trained.")
    else:
        st.markdown("## 🤖 AI Railway Assistant")
        st.markdown(
            "Ask anything about delays, ticket confirmation, congestion, routes, or network status. "
            "The assistant uses your trained ML models and graph analytics to answer in real time."
        )

        # ── Sample query buttons ─────────────────────────────────────────
        samples = get_sample_queries()

        col_p, col_o = st.columns(2)
        with col_p:
            st.markdown("#### 🧳 Passenger Queries")
            for q in samples["passenger"]:
                if st.button(q, key=f"pq_{q[:20]}"):
                    st.session_state["ai_query"] = q

        with col_o:
            st.markdown("#### 🛠️ Operator Queries")
            for q in samples["operator"]:
                if st.button(q, key=f"oq_{q[:20]}"):
                    st.session_state["ai_query"] = q

        st.markdown("---")

        # ── Free-text input ──────────────────────────────────────────────
        prefill = st.session_state.get("ai_query", "")
        user_query = st.text_input(
            "💬 Type your question here:",
            value=prefill,
            placeholder="e.g. What are chances my WL 20 ticket will confirm?",
            key="ai_text_input"
        )

        ask_btn = st.button("🔍 Ask Assistant", type="primary")

        if ask_btn and user_query.strip():
            with st.spinner("Thinking..."):
                try:
                    from src.ai_assistant.railway_assistant import handle_query as _handle_query
                    result      = ai_ask(user_query)        # {query, intent, response}
                    result_data = _handle_query(user_query) # raw data dict with extra fields

                    # Intent badge
                    intent_labels = {
                        "ticket_confirmation":  "🎟️ Ticket Confirmation",
                        "delay_prediction":     "⏱️ Delay Analysis",
                        "network_vulnerability":"🌊 Cascade & Vulnerability",
                        "congestion_analysis":  "🚦 Congestion Analysis",
                        "route_planning":       "🧭 Route Intelligence",
                        "unknown":              "❓ General",
                    }
                    intent_label = intent_labels.get(result["intent"], result["intent"])

                    st.markdown(
                        f"<span style='background:#1e3a5f;color:#7dd3fc;"
                        f"padding:4px 12px;border-radius:20px;font-size:0.8rem;'>"
                        f"Intent detected: {intent_label}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown("")

                    # Main answer card
                    st.markdown(
                        f"<div style='background:#0f1f35;border:1px solid #1e3a5f;"
                        f"border-radius:12px;padding:20px 24px;margin-top:8px;'>"
                        f"{result['response'].replace(chr(10), '<br>')}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    # Extra metrics for ticket confirmation
                    if result["intent"] == "ticket_confirmation" and "wl_probability" in result_data:
                        st.markdown("")
                        prob = result_data["wl_probability"]
                        pct  = round(prob * 100, 1)
                        color = "#22c55e" if prob > 0.65 else "#f59e0b" if prob > 0.35 else "#ef4444"
                        st.markdown(
                            f"<div style='text-align:center;padding:16px;"
                            f"background:#0f1f35;border-radius:12px;margin-top:8px;'>"
                            f"<span style='font-size:2.5rem;font-weight:700;color:{color};'>"
                            f"{pct}%</span><br>"
                            f"<span style='color:#94a3b8;font-size:0.9rem;'>Confirmation Probability</span>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                except Exception as e:
                    st.error(f"Assistant error: {e}")

        elif ask_btn:
            st.warning("Please type a question or click one of the sample queries above.")

        # ── Chat history ─────────────────────────────────────────────────
        if "ai_history" not in st.session_state:
            st.session_state["ai_history"] = []

        if ask_btn and user_query.strip():
            try:
                result_hist = ai_ask(user_query)
                st.session_state["ai_history"].insert(0, {
                    "q": user_query,
                    "a": result_hist["response"][:200] + "..." if len(result_hist["response"]) > 200 else result_hist["response"],
                    "intent": result_hist["intent"],
                })
                # Keep only last 5
                st.session_state["ai_history"] = st.session_state["ai_history"][:5]
            except Exception:
                pass

        if st.session_state.get("ai_history"):
            st.markdown("---")
            st.markdown("#### 🕐 Recent Questions")
            for item in st.session_state["ai_history"]:
                with st.expander(f"❓ {item['q']}", expanded=False):
                    st.markdown(item["a"])


# ── TAB 8 — PASSENGER FLOW & CROWD INTELLIGENCE ───────────────────────────
with tab8:
    if not FLOW_OK:
        st.error(f"Passenger Flow module unavailable: {FLOW_ERR}")
        st.info("Run: python src/passenger_flow/generate_passenger_data.py")
    else:
        st.markdown("## 👥 Passenger Flow & Crowd Intelligence")
        st.markdown(
            "Demand estimates, seasonal patterns, station crowding profiles, "
            "and transfer congestion — derived from network topology and schedule data."
        )

        # ── Row 1: KPI metric cards ───────────────────────────────────────
        try:
            pf = passenger_flow_summary()
            nd = get_network_demand_summary()

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("📦 Est. Annual Passengers", f"{pf['total_annual_passengers']:,}")
            k2.metric("📊 Avg Occupancy",           f"{pf['avg_occupancy_pct']}%")
            k3.metric("🔥 Peak Month",              pf["peak_month"])
            k4.metric("😌 Low Month",               pf["low_month"])
            k5.metric("⚠️ Overcrowded Runs",        pf["overcrowded_routes"])
        except Exception as e:
            st.error(f"KPI error: {e}")

        st.markdown("---")

        # ── Row 2: Busiest stations + Seasonal chart ──────────────────────
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🏙️ Busiest Stations by Crowd Score")
            try:
                busy_df = get_busiest_stations(10)
                st.dataframe(
                    busy_df.rename(columns={
                        "rank": "#",
                        "station_name": "Station",
                        "avg_crowd_score": "Crowd Score",
                        "crowd_level": "Level",
                        "peak_hour": "Peak Hour",
                        "num_trains": "Trains/Day",
                        "transfer_congestion_risk": "Transfer Risk",
                    }),
                    use_container_width=True, hide_index=True
                )
            except Exception as e:
                st.error(f"Busiest stations error: {e}")

        with col_r:
            st.markdown("### 📅 Seasonal Demand Index")
            try:
                sea_df = get_seasonal_demand()
                import altair as alt
                chart = alt.Chart(sea_df).mark_bar().encode(
                    x=alt.X("month_name:N", sort=None, title="Month"),
                    y=alt.Y("demand_index:Q", title="Demand Index"),
                    color=alt.condition(
                        alt.datum.peak == "Yes",
                        alt.value("#f97316"),
                        alt.value("#38bdf8")
                    ),
                    tooltip=["month_name","demand_index","season","festival"]
                ).properties(height=300)
                st.altair_chart(chart, use_container_width=True)
                st.caption("🟠 Peak months  🔵 Regular months")
            except Exception:
                # Fallback: plain table if altair not installed
                sea_df2 = get_seasonal_demand()[["month_name","demand_index","season","festival","peak"]]
                st.dataframe(sea_df2.rename(columns={
                    "month_name":"Month","demand_index":"Demand Index",
                    "season":"Season","festival":"Festival","peak":"Peak?"
                }), use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── Row 3: Station crowd profile ──────────────────────────────────
        st.markdown("### 🔍 Station Crowd Profile & Peak Hours")
        try:
            all_stations = get_busiest_stations(50)["station_name"].tolist()
            sel_station = st.selectbox("Select Station", all_stations, key="flow_station")

            profile = get_station_crowd_profile(sel_station)

            if "error" in profile:
                st.warning(profile["error"])
            else:
                pa, pb, pc, pd_ = st.columns(4)
                pa.metric("Avg Crowd Score",    f"{profile['avg_crowd_score']}/100")
                pb.metric("Crowd Level",        profile["crowd_level"])
                pc.metric("Peak Hour",          profile["peak_hour"])
                pd_.metric("Transfer Risk",     profile["transfer_congestion_risk"])

                # Hourly chart
                hourly_df = pd.DataFrame({
                    "Hour": [f"{h:02d}:00" for h in range(24)],
                    "Crowd Score": profile["hourly_profile"]
                })
                try:
                    import altair as alt
                    hchart = alt.Chart(hourly_df).mark_area(
                        line={"color":"#f97316"}, color=alt.Gradient(
                            gradient="linear", stops=[
                                alt.GradientStop(color="#f97316", offset=1),
                                alt.GradientStop(color="#0f1f35", offset=0)
                            ], x1=1, x2=1, y1=1, y2=0
                        )
                    ).encode(
                        x=alt.X("Hour:N", sort=None, title="Hour of Day"),
                        y=alt.Y("Crowd Score:Q", scale=alt.Scale(domain=[0,100])),
                        tooltip=["Hour","Crowd Score"]
                    ).properties(height=220, title=f"Hourly Crowd Profile — {sel_station}")
                    st.altair_chart(hchart, use_container_width=True)
                except Exception:
                    st.bar_chart(hourly_df.set_index("Hour")["Crowd Score"], height=200)

                st.markdown(
                    f"💡 **Best time to use {sel_station}:** `{profile['quietest_hour']}` — "
                    f"**Busiest day:** `{profile['busiest_day']}`"
                )
        except Exception as e:
            st.error(f"Station profile error: {e}")

        st.markdown("---")

        # ── Row 4: Transfer congestion + Overcrowded routes ───────────────
        col_tc, col_oc = st.columns(2)

        with col_tc:
            st.markdown("### 🔀 Transfer Congestion Hotspots")
            try:
                tc_df = get_transfer_congestion_stations(10)
                st.dataframe(
                    tc_df.rename(columns={
                        "rank":"#","station_name":"Station",
                        "transfer_congestion_risk":"Risk",
                        "peak_crowd_score":"Peak Score",
                        "num_trains":"Trains",
                        "betweenness_centrality":"Centrality",
                    }),
                    use_container_width=True, hide_index=True
                )
                st.caption("Stations where many trains connect — highest transfer delay risk.")
            except Exception as e:
                st.error(f"Transfer congestion error: {e}")

        with col_oc:
            st.markdown("### 🔥 Overcrowded Routes by Month")
            try:
                MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
                sel_month = st.selectbox(
                    "Select Month",
                    options=list(MONTH_NAMES.keys()),
                    format_func=lambda x: MONTH_NAMES[x],
                    index=10, key="flow_month"
                )
                oc_df = get_overcrowded_routes(sel_month)
                if oc_df.empty:
                    st.success("No overcrowded routes in this month!")
                else:
                    st.dataframe(
                        oc_df.rename(columns={
                            "rank":"#","train_name":"Train",
                            "source_station":"From","destination_station":"To",
                            "occupancy_pct":"Occupancy",
                            "estimated_passengers":"Passengers",
                            "waitlist_count":"WL Count",
                            "crowd_level":"Level",
                        }),
                        use_container_width=True, hide_index=True
                    )
            except Exception as e:
                st.error(f"Overcrowded routes error: {e}")

        st.markdown("---")

        # ── Row 5: Route demand lookup ────────────────────────────────────
        st.markdown("### 🛤️ Route Demand Lookup")
        try:
            import os as _os
            _imp_path = _os.path.join(_os.path.dirname(__file__), "..", "data", "processed", "station_importance.csv")
            _all_stations = sorted(pd.read_csv(_imp_path)["station_name"].dropna().unique().tolist())

            rc1, rc2, rc3 = st.columns([2, 2, 1])
            with rc1:
                r_src = st.selectbox("Source Station", _all_stations, key="flow_src")
            with rc2:
                r_dst = st.selectbox("Destination Station",
                                     [s for s in _all_stations if s != r_src],
                                     key="flow_dst")
            with rc3:
                st.markdown("<br>", unsafe_allow_html=True)
                go_btn = st.button("Check Demand", key="flow_go")

            if go_btn:
                rd = get_route_demand(r_src, r_dst)
                if "error" in rd:
                    st.warning(rd["error"])
                else:
                    # Show estimated badge if no direct route data
                    if rd.get("estimation_method") == "estimated":
                        st.caption(
                            "ℹ️ No direct train data found for this pair — "
                            "demand is estimated from station crowd profiles and seasonal patterns."
                        )

                    MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
                    peak_name = MONTH_NAMES.get(rd["peak_month"], str(rd["peak_month"]))

                    ra1, ra2, ra3 = st.columns(3)
                    ra1.metric("Avg Occupancy", f"{rd['avg_occupancy']*100:.0f}%")
                    ra2.metric("Crowd Level",   rd["crowd_level"])
                    ra3.metric("Peak Month",    peak_name)
                    st.info(rd["advice"])

                    month_df = pd.DataFrame(rd["monthly_demand"])
                    if "month_name" not in month_df.columns:
                        month_df["month_name"] = month_df["month"].map(MONTH_NAMES)
                    st.bar_chart(
                        month_df.set_index("month_name")["avg_occupancy"],
                        height=200
                    )

                    if rd.get("trains"):
                        st.markdown(
                            "**Direct trains:** " +
                            ", ".join(t["train_name"] for t in rd["trains"][:5])
                        )
        except Exception as e:
            st.error(f"Route demand error: {e}")

# ── TAB 9 — INTELLIGENT ROUTING & OPERATIONAL OPTIMIZATION ───────────────
with tab9:
    if not OPT_OK:
        st.error(f"Routing Optimizer unavailable: {OPT_ERR}")
        st.info("Ensure src/routing_optimizer/routing_optimizer.py is present and dependencies are installed.")
    else:
        st.markdown("## ⚙️ Intelligent Routing & Operational Optimization")
        st.markdown(
            "Alternative routing during disruptions, schedule adjustments to prevent cascades, "
            "multi-objective path scoring, and high-demand corridor prioritization."
        )

        # ── KPI Cards ────────────────────────────────────────────────────
        try:
            opt_s = optimization_summary()
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("🚉 Total Stations",       opt_s["total_stations"])
            k2.metric("🛤️ Total Routes",          opt_s["total_routes"])
            k3.metric("🔴 Critical Corridors",   opt_s["critical_corridors"])
            k4.metric("📍 Top Corridor",         opt_s["top_corridor"].split("→")[0].strip())
        except Exception as e:
            st.error(f"KPI error: {e}")

        st.markdown("---")

        # ── Section 1: Disruption & Alternative Routing ──────────────────
        st.markdown("### 🔀 Disruption & Alternative Routing")
        st.caption("Block a station or mark an edge as disrupted — the system finds the best detour automatically.")

        try:
            opt_stations = cached_station_list()
            da1, da2 = st.columns(2)
            with da1:
                alt_src = st.selectbox("Origin Station", opt_stations,
                    index=opt_stations.index("Howrah Jn") if "Howrah Jn" in opt_stations else 0,
                    key="opt_src")
            with da2:
                alt_dst = st.selectbox("Destination Station",
                    [s for s in opt_stations if s != alt_src],
                    index=0, key="opt_dst")

            st.markdown("**Blocked Stations** (hold Ctrl/Cmd to select multiple)")
            blocked_sel = st.multiselect("Select stations to block", opt_stations,
                                         default=[], key="opt_blocked")
            alt_n = st.slider("Number of alternatives", 1, 4, 2, key="opt_n_alts")

            if st.button("🔍 Find Alternative Routes", key="opt_find"):
                with st.spinner("Computing alternative routes..."):
                    try:
                        res = find_alternative_routes(
                            alt_src, alt_dst,
                            blocked_stations=blocked_sel,
                            n_alternatives=alt_n
                        )
                        if res.get("disruption_active"):
                            st.warning(f"⚠️ Primary route is disrupted! {len(res['alternatives'])} alternative(s) found.")
                        else:
                            st.success("✅ Primary route is clear.")

                        if res.get("primary"):
                            with st.expander("📍 Primary Route", expanded=not res["disruption_active"]):
                                p = res["primary"]
                                pc1, pc2, pc3 = st.columns(3)
                                pc1.metric("Stops", p["num_stops"])
                                pc2.metric("Travel Time", f"{p['total_travel_time_min']:.0f} min")
                                pc3.metric("Avg Delay", f"{p['total_delay_min']:.0f} min")
                                st.markdown("**Path:** " + " → ".join(p["path"]))

                        for i, alt in enumerate(res.get("alternatives", []), 1):
                            with st.expander(f"🔄 Alternative {i} — {alt['num_stops']} stops, +{alt['extra_time_vs_primary']:.0f} min | Reliability: {alt['reliability_score']}/100"):
                                ac1, ac2, ac3, ac4 = st.columns(4)
                                ac1.metric("Stops",       alt["num_stops"])
                                ac2.metric("Travel Time", f"{alt['total_travel_time_min']:.0f} min")
                                ac3.metric("Extra Time",  f"+{alt['extra_time_vs_primary']:.0f} min")
                                ac4.metric("Reliability", f"{alt['reliability_score']}/100")
                                st.markdown("**Path:** " + " → ".join(alt["path"]))
                                if alt.get("legs"):
                                    legs_df = pd.DataFrame(alt["legs"])
                                    legs_df.columns = [c.replace("_"," ").title() for c in legs_df.columns]
                                    st.dataframe(legs_df, use_container_width=True, hide_index=True)

                        st.info(res["recommendation"])
                    except Exception as e:
                        st.error(f"Routing error: {e}")
        except Exception as e:
            st.error(f"Alternative routing init error: {e}")

        st.markdown("---")

        # ── Section 2: Schedule Adjustment Recommendations ───────────────
        st.markdown("### 🕐 Schedule Adjustments to Reduce Cascades")
        st.caption("Enter a delayed station and delay size — get actionable hold/reschedule recommendations for connecting trains.")

        try:
            sb1, sb2, sb3 = st.columns([3, 1, 1])
            with sb1:
                sched_stn = st.selectbox("Delayed Station", opt_stations,
                    index=opt_stations.index("New Delhi") if "New Delhi" in opt_stations else 0,
                    key="sched_stn")
            with sb2:
                sched_delay = st.number_input("Delay (min)", min_value=5, max_value=240,
                                               value=45, step=5, key="sched_delay")
            with sb3:
                sched_n = st.slider("Max trains", 3, 15, 8, key="sched_n")

            if st.button("📋 Get Schedule Adjustments", key="sched_go"):
                with st.spinner("Analysing cascade impact..."):
                    try:
                        sched = suggest_schedule_adjustments(sched_stn, int(sched_delay), int(sched_n))
                        sm1, sm2, sm3, sm4 = st.columns(4)
                        sm1.metric("Trains Affected",   sched["affected_trains"])
                        sm2.metric("Congestion Factor", f"{sched['congestion_factor']}×")
                        sm3.metric("Cascade Saving",    f"{sched['total_cascade_saving_min']:.0f} min")
                        sm4.metric("High Priority",     sum(1 for a in sched["adjustments"] if a["priority"]=="High"))

                        st.info(sched["summary"])

                        adj_df = pd.DataFrame(sched["adjustments"])
                        adj_df = adj_df[["train_name","from","to","estimated_cascade_impact_min",
                                         "recommended_action","action_description","hold_minutes",
                                         "cascade_saving_min","priority"]]
                        adj_df.columns = ["Train","From","To","Cascade Impact (min)",
                                          "Action","Description","Hold (min)","Saving (min)","Priority"]

                        def _color_priority(val):
                            c = {"High":"#f97316","Medium":"#f59e0b","Low":"#22c55e"}.get(val,"")
                            return f"color:{c};font-weight:bold" if c else ""

                        st.dataframe(adj_df, use_container_width=True, hide_index=True)
                    except Exception as e:
                        st.error(f"Schedule adjustment error: {e}")
        except Exception as e:
            st.error(f"Schedule section error: {e}")

        st.markdown("---")

        # ── Section 3: Multi-Objective Route Scoring ─────────────────────
        st.markdown("### 🎯 Multi-Objective Route Optimization")
        st.caption("Score routes across Time, Congestion, and Reliability. Adjust weights to match your priority.")

        try:
            mo1, mo2 = st.columns(2)
            with mo1:
                mo_src = st.selectbox("From", opt_stations,
                    index=opt_stations.index("Chennai Central") if "Chennai Central" in opt_stations else 0,
                    key="mo_src")
                mo_dst = st.selectbox("To", [s for s in opt_stations if s != mo_src],
                    key="mo_dst")
            with mo2:
                st.markdown("**Objective Weights**")
                w_time  = st.slider("⏱️ Travel Time",   0.0, 1.0, 0.5, 0.05, key="w_time")
                w_cong  = st.slider("🚦 Congestion",    0.0, 1.0, 0.3, 0.05, key="w_cong")
                w_rel   = st.slider("✅ Reliability",   0.0, 1.0, 0.2, 0.05, key="w_rel")
                total_w = w_time + w_cong + w_rel
                st.caption(f"Weights sum: {total_w:.2f} (auto-normalised)")

            if st.button("🎯 Score Routes", key="mo_go"):
                with st.spinner("Scoring routes across objectives..."):
                    try:
                        mo_res = multi_objective_route(mo_src, mo_dst, w_time, w_cong, w_rel)
                        if not mo_res["routes"]:
                            st.warning(mo_res.get("recommendation", "No routes found."))
                        else:
                            st.info(mo_res["recommendation"])
                            for i, route in enumerate(mo_res["routes"]):
                                exp_label = f"{route['label']}  |  {route['num_stops']} stops, {route['total_travel_time_min']:.0f} min  |  Score: {route['composite_score']:.3f}"
                                with st.expander(exp_label, expanded=(i == 0)):
                                    rc1, rc2, rc3, rc4 = st.columns(4)
                                    rc1.metric("Time Score",        f"{route['time_score']:.2f}")
                                    rc2.metric("Congestion Score",  f"{route['congestion_score']:.2f}")
                                    rc3.metric("Reliability",       f"{route['reliability_score']*100:.0f}%")
                                    rc4.metric("Composite Score",   f"{route['composite_score']:.3f}")
                                    st.markdown("**Path:** " + " → ".join(route["path"]))
                    except Exception as e:
                        st.error(f"Multi-objective error: {e}")
        except Exception as e:
            st.error(f"Multi-objective section error: {e}")

        st.markdown("---")

        # ── Section 4: High-Demand Corridor Prioritization ───────────────
        st.markdown("### 🔴 High-Demand Corridor Prioritization")
        st.caption("Corridors ranked by occupancy, network centrality, and delay risk. Action recommendations for each.")

        try:
            n_corridors = st.slider("Number of corridors to show", 5, 20, 10, key="opt_corridors_n")
            if st.button("📊 Analyse Corridors", key="opt_corridors_go") or True:
                with st.spinner("Ranking corridors..."):
                    try:
                        cor_df = prioritize_corridor_trains(n_corridors)
                        if cor_df.empty:
                            st.warning("No corridor data available.")
                        else:
                            st.dataframe(
                                cor_df.rename(columns={
                                    "rank":"#",
                                    "source_station":"From",
                                    "destination_station":"To",
                                    "avg_occupancy_pct":"Occupancy %",
                                    "overcrowded_months":"Overcrowded Months",
                                    "betweenness_score":"Centrality",
                                    "delay_risk_score":"Delay Risk",
                                    "priority_score":"Priority Score",
                                    "priority_level":"Priority",
                                    "recommendation":"Recommendation",
                                }),
                                use_container_width=True, hide_index=True
                            )
                    except Exception as e:
                        st.error(f"Corridor analysis error: {e}")
        except Exception as e:
            st.error(f"Corridor section error: {e}")

# ─────────────────────────────────────────────────────────────────────────
#  TAB 10 — PASSENGER TRAVEL INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────
with tab10:
    if not TRAVEL_OK:
        st.error(f"Travel Intelligence module unavailable: {TRAVEL_ERR}")
        st.info("Ensure src/travel_intelligence/travel_intelligence.py is present.")
    else:
        st.markdown("## 🧳 Passenger Travel Intelligence System")
        st.markdown(
            "Alternative route recommendations with crowd context · "
            "Station crowd estimates with seasonal adjustment · "
            "Smart ticket booking guidance with step-by-step advice."
        )

        # ── KPI strip ─────────────────────────────────────────────────────
        try:
            ti_kpi = travel_intelligence_summary()
            kc1, kc2, kc3, kc4, kc5 = st.columns(5)
            kc1.metric("📊 Avg Occupancy",       f"{ti_kpi['avg_network_occupancy_pct']}%")
            kc2.metric("🔥 Peak Month",          ti_kpi["peak_month"])
            kc3.metric("😌 Lowest Demand",       ti_kpi["low_month"])
            kc4.metric("⚠️ Overcrowded Runs",    ti_kpi["overcrowded_train_months"])
            kc5.metric("🚆 Trains Tracked",      ti_kpi["total_trains_tracked"])
        except Exception as e:
            st.warning(f"KPI error: {e}")

        st.markdown("---")

        # ═══════════════════════════════════════════════════════════════
        #  SECTION A — Unified Travel Advisory
        # ═══════════════════════════════════════════════════════════════
        st.markdown("### 🗺️ Travel Advisory")
        st.caption(
            "Select a journey and month. Optionally enter your WL number and days "
            "before departure for a complete personalised advisory."
        )

        try:
            _all_stns = cached_station_list()
            MONTH_OPTS = {
                1:"January", 2:"February", 3:"March",   4:"April",
                5:"May",     6:"June",     7:"July",    8:"August",
                9:"September",10:"October",11:"November",12:"December"
            }

            col_s, col_d = st.columns(2)
            with col_s:
                adv_src = st.selectbox("From", _all_stns,
                    index=_all_stns.index("Chennai Central") if "Chennai Central" in _all_stns else 0,
                    key="adv_src")
            with col_d:
                adv_dst = st.selectbox("To",
                    [s for s in _all_stns if s != adv_src],
                    key="adv_dst")

            col_m, col_wl, col_db = st.columns(3)
            with col_m:
                adv_month = st.selectbox("Travel Month",
                    options=list(MONTH_OPTS.keys()),
                    format_func=lambda x: MONTH_OPTS[x],
                    index=10, key="adv_month")
            with col_wl:
                adv_wl = st.number_input("WL Number (0 = no WL)", 0, 300, 0, 1, key="adv_wl")
            with col_db:
                adv_days = st.number_input("Days Before Departure", 1, 120, 30, 1, key="adv_days")

            if st.button("🔍 Get Travel Advisory", key="adv_go"):
                with st.spinner("Analysing routes, crowd data, and booking options…"):
                    try:
                        adv = get_travel_advisory(
                            adv_src, adv_dst,
                            month=adv_month,
                            wl_number=int(adv_wl),
                            days_before=int(adv_days),
                        )

                        if adv.get("error"):
                            st.error(adv["error"])
                        else:
                            st.info(adv["route_recommendation"])

                            # ── Route options ──────────────────────────
                            all_routes = (
                                ([adv["primary_route"]] if adv.get("primary_route") else []) +
                                (adv.get("alternatives") or [])
                            )
                            if all_routes:
                                st.markdown("#### 🛤️ Route Options")
                                for i, route in enumerate(all_routes):
                                    tag   = "⭐ Primary" if i == 0 else f"🔄 Alternative {i}"
                                    extra = f" | +{route.get('extra_time_min', 0):.0f} min" if i > 0 else ""
                                    lbl = (
                                        f"{tag}{extra} — "
                                        f"{route['num_stops']} stops | "
                                        f"Crowd: {route.get('crowd_level','?')} | "
                                        f"Occupancy: {route.get('occupancy_pct',0):.0f}% | "
                                        f"Reliability: {route.get('reliability_score',0):.0f}/100"
                                    )
                                    with st.expander(lbl, expanded=(i == 0)):
                                        rc1, rc2, rc3, rc4 = st.columns(4)
                                        rc1.metric("Stops", route["num_stops"])
                                        mins = route["total_travel_time_min"]
                                        rc2.metric("Travel Time",
                                            f"{int(mins//60)}h {int(mins%60)}m" if mins > 0 else "N/A")
                                        rc3.metric("Cumulative Delay",
                                            f"{route['total_delay_min']:.0f} min")
                                        rc4.metric("Reliability",
                                            f"{route.get('reliability_score',0):.0f}/100")

                                        st.markdown("**Path:** " +
                                            " → ".join(route["path"]))

                                        if route.get("busiest_stops"):
                                            busy = ", ".join(
                                                f"{s['station']} ({s['crowd_level']})"
                                                for s in route["busiest_stops"]
                                            )
                                            st.caption(f"Busiest intermediate stops: {busy}")

                                        if route.get("legs"):
                                            legs_df = pd.DataFrame(route["legs"])
                                            legs_df.columns = [
                                                c.replace("_"," ").title()
                                                for c in legs_df.columns
                                            ]
                                            st.dataframe(legs_df,
                                                use_container_width=True,
                                                hide_index=True)

                            # ── Source station crowd ───────────────────
                            crowd = adv.get("crowd", {})
                            if crowd and "error" not in crowd:
                                st.markdown("#### 🏙️ Source Station Crowd at 18:00")
                                cc1, cc2, cc3, cc4 = st.columns(4)
                                cc1.metric("Crowd Score",
                                    f"{crowd['crowd_score']}/100")
                                cc2.metric("Crowd Level", crowd["crowd_level"])
                                cc3.metric("Best Time",
                                    crowd["offpeak_hours"][0]
                                    if crowd.get("offpeak_hours") else "—")
                                cc4.metric("Transfer Risk",
                                    crowd.get("transfer_congestion", "—"))
                                st.info(crowd["advice"])
                                if crowd.get("hourly_profile"):
                                    hr_df = pd.DataFrame({
                                        "Hour":  [f"{h:02d}:00" for h in range(24)],
                                        "Crowd Score": crowd["hourly_profile"],
                                    }).set_index("Hour")
                                    st.bar_chart(hr_df, height=180)

                            # ── Booking guidance ───────────────────────
                            bk = adv.get("booking", {})
                            if bk:
                                st.markdown("#### 🎟️ Smart Booking Guidance")
                                urg_icon = {
                                    "Critical": "🔴", "High": "🟠",
                                    "Medium": "🟡", "Low": "🟢",
                                }.get(bk.get("urgency", "Low"), "🟢")

                                bk1, bk2, bk3 = st.columns(3)
                                bk1.metric("Book at Least",
                                    f"{bk['recommended_advance_days']} days ahead")
                                bk2.metric("Urgency",
                                    f"{urg_icon} {bk.get('urgency','Low')}")
                                if bk.get("wl_confirmation_probability") is not None:
                                    bk3.metric("WL Confirm Prob",
                                        f"{bk['wl_confirmation_probability']}%")
                                else:
                                    bk3.metric("Occupancy",
                                        f"{bk['occupancy_pct']:.0f}%")

                                if bk.get("urgency") in ("High", "Critical"):
                                    st.error(bk["booking_window"])
                                else:
                                    st.warning(bk["booking_window"])

                                st.markdown("**Your booking action plan:**")
                                for step_i, step in enumerate(
                                    bk.get("step_by_step_advice", []), 1
                                ):
                                    st.markdown(f"**{step_i}.** {step}")

                    except Exception as e:
                        st.error(f"Advisory error: {e}")
        except Exception as e:
            st.error(f"Advisory section error: {e}")

        st.markdown("---")

        # ═══════════════════════════════════════════════════════════════
        #  SECTION B — Station Crowd Explorer
        # ═══════════════════════════════════════════════════════════════
        st.markdown("### 🏙️ Station Crowd Explorer")
        st.caption(
            "Hourly crowd score at any station, seasonally adjusted. "
            "Includes per-train occupancy for trains serving that station."
        )

        try:
            ce_col1, ce_col2, ce_col3 = st.columns(3)
            with ce_col1:
                crowd_stn = st.selectbox("Station", _all_stns,
                    index=_all_stns.index("New Delhi") if "New Delhi" in _all_stns else 0,
                    key="crowd_stn")
            with ce_col2:
                crowd_month = st.selectbox("Month",
                    options=list(MONTH_OPTS.keys()),
                    format_func=lambda x: MONTH_OPTS[x],
                    index=10, key="crowd_month")
            with ce_col3:
                crowd_hour = st.slider("Hour of Day", 0, 23, 18, key="crowd_hour")

            if st.button("📊 Check Crowd Level", key="crowd_go"):
                with st.spinner("Loading crowd data…"):
                    try:
                        ce = get_crowd_estimate(crowd_stn,
                                                month=crowd_month,
                                                hour=crowd_hour)
                        if "error" in ce:
                            st.warning(ce["error"])
                        else:
                            cm1, cm2, cm3, cm4 = st.columns(4)
                            cm1.metric("Crowd Score",
                                f"{ce['crowd_score']}/100")
                            cm2.metric("Crowd Level",  ce["crowd_level"])
                            cm3.metric("Season",       ce["season"])
                            cm4.metric("Seasonal Mult",f"{ce['seasonal_multiplier']}×")

                            st.info(ce["advice"])

                            ch_col, dow_col = st.columns([3, 2])
                            with ch_col:
                                st.markdown("**24-Hour Crowd Profile**")
                                hr_df = pd.DataFrame({
                                    "Hour": [f"{h:02d}:00" for h in range(24)],
                                    "Score": ce["hourly_profile"],
                                }).set_index("Hour")
                                st.bar_chart(hr_df, height=200)

                            with dow_col:
                                st.markdown("**Day-of-Week Pattern**")
                                dow_df = pd.DataFrame(
                                    list(ce["day_profile"].items()),
                                    columns=["Day", "Avg Crowd Score"]
                                )
                                st.dataframe(dow_df,
                                    use_container_width=True, hide_index=True)

                            if ce.get("train_occupancy"):
                                st.markdown(
                                    f"**Trains at {ce['station_name']} "
                                    f"in {ce['month_name']} — Occupancy:**"
                                )
                                tocc = pd.DataFrame(ce["train_occupancy"])[
                                    ["train_name","occupancy_pct",
                                     "crowd_level","waitlist_count"]
                                ]
                                tocc.columns = ["Train","Occupancy %","Level","WL Count"]
                                st.dataframe(tocc,
                                    use_container_width=True, hide_index=True)
                    except Exception as e:
                        st.error(f"Crowd estimate error: {e}")
        except Exception as e:
            st.error(f"Crowd explorer error: {e}")

        st.markdown("---")

        # ═══════════════════════════════════════════════════════════════
        #  SECTION C — Smart Ticket Booking Guidance (standalone)
        # ═══════════════════════════════════════════════════════════════
        st.markdown("### 🎟️ Smart Ticket Booking Guidance")
        st.caption(
            "Get the exact number of days you should book in advance, "
            "WL confirmation probability, and a personalised action plan."
        )

        try:
            bg1, bg2 = st.columns(2)
            with bg1:
                bg_src = st.selectbox("From", _all_stns,
                    index=_all_stns.index("Howrah Jn") if "Howrah Jn" in _all_stns else 0,
                    key="bg_src")
                bg_wl = st.number_input(
                    "WL Number (0 = asking for general advice)", 0, 300, 0, 1, key="bg_wl")
            with bg2:
                bg_dst = st.selectbox("To",
                    [s for s in _all_stns if s != bg_src], key="bg_dst")
                bg_days = st.number_input(
                    "Days Before Departure", 1, 120, 30, 1, key="bg_days")

            bg_month = st.selectbox("Travel Month",
                options=list(MONTH_OPTS.keys()),
                format_func=lambda x: MONTH_OPTS[x],
                index=10, key="bg_month")

            if st.button("💡 Get Booking Guidance", key="bg_go"):
                with st.spinner("Computing guidance…"):
                    try:
                        bg = get_booking_guidance(
                            bg_src, bg_dst,
                            wl_number=int(bg_wl),
                            days_before_travel=int(bg_days),
                            month=bg_month,
                        )
                        urg_icon = {
                            "Critical":"🔴","High":"🟠",
                            "Medium":"🟡","Low":"🟢"
                        }.get(bg["urgency"], "🟢")

                        ba1, ba2, ba3, ba4 = st.columns(4)
                        ba1.metric("Route Occupancy",
                            f"{bg['occupancy_pct']:.0f}%")
                        ba2.metric("Book at Least",
                            f"{bg['recommended_advance_days']} days ahead")
                        ba3.metric("Urgency",
                            f"{urg_icon} {bg['urgency']}")
                        if bg.get("wl_confirmation_probability") is not None:
                            ba4.metric("WL Confirm Chance",
                                f"{bg['wl_confirmation_probability']}%")
                        else:
                            ba4.metric("Demand Index", bg["demand_index"])

                        if bg.get("urgency") in ("High","Critical"):
                            st.error(bg["booking_window"])
                        else:
                            st.warning(bg["booking_window"])

                        if bg.get("festival") and bg["festival"] != "—":
                            st.info(
                                f"🎉 {bg['festival']} season in {bg['month_name']} "
                                f"— expect significantly higher demand."
                            )

                        st.markdown("**Your personalised booking plan:**")
                        for i, step in enumerate(
                            bg.get("step_by_step_advice", []), 1
                        ):
                            st.markdown(f"**{i}.** {step}")
                    except Exception as e:
                        st.error(f"Booking guidance error: {e}")
        except Exception as e:
            st.error(f"Booking section error: {e}")
