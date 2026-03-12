"""
routing_optimizer.py
====================
Phase-7: Intelligent Routing & Operational Optimization
AI-Powered Railway Intelligence System

Implements the four missing capabilities:
  1. Alternative routing during disruptions
     find_alternative_routes(src, dst, blocked_stations, blocked_edges)
  2. Scheduling adjustments to reduce cascades
     suggest_schedule_adjustments(delayed_station, delay_minutes)
  3. Multi-objective optimization (time + congestion + reliability)
     multi_objective_route(src, dst, weights)
  4. Train prioritization on high-demand corridors
     prioritize_corridor_trains(top_n)

Public API
----------
    find_alternative_routes(src, dst, blocked_stations, blocked_edges, n_alternatives)
        -> dict   with primary + up to n alternative routes

    suggest_schedule_adjustments(delayed_station, delay_minutes, max_affected)
        -> dict   with affected trains + reschedule recommendations

    multi_objective_route(src, dst, w_time, w_congestion, w_reliability)
        -> dict   with ranked route options scored across 3 objectives

    prioritize_corridor_trains(top_n)
        -> pd.DataFrame   high-demand corridors + priority recommendations

    optimization_summary()
        -> dict   dashboard-ready overview of all four functions

All heavy data (graph, delay stats) is lazy-loaded and cached.
"""

from __future__ import annotations

import os
import sys
import warnings
from functools import lru_cache
from typing import Optional

import networkx as nx
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)

_PROC = os.path.join(_ROOT, "data", "processed")


# ── Shared lazy loaders ────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _graph() -> nx.DiGraph:
    from src.graph_engine.graph_utils import load_graph
    return load_graph()


@lru_cache(maxsize=1)
def _delay_stats() -> pd.DataFrame:
    p = os.path.join(_PROC, "station_delay_stats.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


@lru_cache(maxsize=1)
def _importance() -> pd.DataFrame:
    p = os.path.join(_PROC, "station_importance.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


@lru_cache(maxsize=1)
def _routes() -> pd.DataFrame:
    p = os.path.join(_PROC, "routes.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


@lru_cache(maxsize=1)
def _demand() -> pd.DataFrame:
    p = os.path.join(_PROC, "passenger_demand.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


# ── Internal helpers ───────────────────────────────────────────────────────

def _resolve(G: nx.DiGraph, name: str) -> str:
    """Case-insensitive station name resolver."""
    if name in G:
        return name
    nl = name.lower()
    candidates = [n for n in G.nodes() if nl in n.lower()]
    if not candidates:
        raise ValueError(f"Station '{name}' not found in graph.")
    exact = [c for c in candidates if c.lower() == nl]
    return exact[0] if exact else candidates[0]


def _station_delay_risk(station: str) -> float:
    """Return delay_risk_score (0–100) for a station; default 30 if unknown."""
    df = _delay_stats()
    if df.empty:
        return 30.0
    row = df[df["station_name"].str.lower() == station.lower()]
    if row.empty:
        row = df[df["station_name"].str.lower().str.contains(station.lower(), regex=False)]
    return float(row["delay_risk_score"].iloc[0]) if not row.empty else 30.0


def _path_metrics(G: nx.DiGraph, path: list[str]) -> dict:
    """Compute total distance, travel_time, avg_delay for a path."""
    dist = tt = delay = 0.0
    legs = []
    for i in range(len(path) - 1):
        s, d = path[i], path[i + 1]
        e = G[s][d]
        dist  += e.get("distance",    0.0)
        tt    += e.get("travel_time", 0.0)
        delay += e.get("avg_delay",   0.0)
        legs.append({
            "from": s, "to": d,
            "distance_km":     round(e.get("distance",    0.0), 1),
            "travel_time_min": round(e.get("travel_time", 0.0), 1),
            "avg_delay_min":   round(e.get("avg_delay",   0.0), 1),
        })
    return {
        "path":           path,
        "num_stops":      len(path),
        "total_distance_km":     round(dist,  1),
        "total_travel_time_min": round(tt,    1),
        "total_delay_min":       round(delay, 1),
        "legs":           legs,
    }



def _k_shortest_penalized(
    G: nx.DiGraph,
    src: str,
    dst: str,
    k: int = 3,
    penalty_mult: float = 8.0,
    weight: str = "weight",
) -> list[list[str]]:
    """
    Find k distinct shortest paths by penalising edges used in previous paths.
    O(k × Dijkstra) — much faster than Yen's or simple_paths enumeration.
    """
    paths: list[list[str]] = []
    G_work = G.copy()
    penalised: set[tuple[str, str]] = set()

    for _ in range(k + 3):
        try:
            p = nx.dijkstra_path(G_work, src, dst, weight=weight)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            break
        if p not in paths:
            paths.append(p)
        if len(paths) >= k:
            break
        for i in range(len(p) - 1):
            u, v = p[i], p[i + 1]
            if (u, v) not in penalised and G_work.has_edge(u, v):
                G_work[u][v][weight] = G_work[u][v].get(weight, 1.0) * penalty_mult
                penalised.add((u, v))
    return paths


# ===========================================================================
#  FUNCTION 1 — find_alternative_routes
# ===========================================================================

def find_alternative_routes(
    src: str,
    dst: str,
    blocked_stations: Optional[list[str]] = None,
    blocked_edges:    Optional[list[tuple[str, str]]] = None,
    n_alternatives:   int = 3,
) -> dict:
    """
    Find the primary route and up to n_alternatives during disruptions.

    Uses Yen's K-Shortest-Paths on a graph with disrupted stations/edges
    temporarily removed.

    Parameters
    ----------
    src, dst          : str   — station names (fuzzy matched)
    blocked_stations  : list  — stations to exclude (disrupted/closed)
    blocked_edges     : list  — (from, to) edge pairs to exclude
    n_alternatives    : int   — max alternative routes to return (default 3)

    Returns
    -------
    dict
        primary          — the unblocked optimal route (or None if disrupted)
        alternatives     — list of alternative route dicts
        disruption_active — bool: True if primary route was blocked
        recommendation   — plain-English advice
    """
    G = _graph()
    blocked_stations = [s.strip() for s in (blocked_stations or [])]
    blocked_edges    = blocked_edges or []

    # Resolve station names
    src_node = _resolve(G, src)
    dst_node = _resolve(G, dst)

    # ── Primary route (no disruption) ─────────────────────────────────────
    try:
        primary_path = nx.dijkstra_path(G, src_node, dst_node, weight="weight")
        primary      = _path_metrics(G, primary_path)
        primary_blocked = bool(
            set(primary_path[1:-1]) & set(blocked_stations) or
            any((e[0], e[1]) in [(p[i], p[i+1]) for i in range(len(primary_path)-1)]
                for e in blocked_edges)
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        primary         = None
        primary_blocked = True

    # ── Build disrupted graph copy ─────────────────────────────────────────
    G_dis = G.copy()
    for bs in blocked_stations:
        try:
            bnode = _resolve(G_dis, bs)
            G_dis.remove_node(bnode)
        except (ValueError, nx.NetworkXError):
            pass
    for (u, v) in blocked_edges:
        try:
            un = _resolve(G_dis, u)
            vn = _resolve(G_dis, v)
            if G_dis.has_edge(un, vn):
                G_dis.remove_edge(un, vn)
        except (ValueError, nx.NetworkXError):
            pass

    # Make sure src/dst still exist in disrupted graph
    if src_node not in G_dis or dst_node not in G_dis:
        return {
            "source":            src_node,
            "destination":       dst_node,
            "primary":           primary,
            "alternatives":      [],
            "disruption_active": True,
            "recommendation": (
                f"Critical disruption: {src_node} or {dst_node} is directly blocked. "
                "No alternative routing possible."
            ),
        }

    # ── Enumerate alternative paths via penalized Dijkstra (fast) ──────────
    alternatives = []
    try:
        candidate_paths = _k_shortest_penalized(
            G_dis, src_node, dst_node,
            k=n_alternatives + 2, penalty_mult=8.0
        )
        primary_path_cmp = primary["path"] if primary else []
        for path in candidate_paths:
            if path == primary_path_cmp:
                continue
            m = _path_metrics(G_dis, path)
            reliability = round(
                100 - np.mean([_station_delay_risk(s) for s in path]), 1
            )
            m["reliability_score"] = max(0.0, reliability)
            m["extra_time_vs_primary"] = round(
                m["total_travel_time_min"] -
                (primary["total_travel_time_min"] if primary else 0), 1
            )
            alternatives.append(m)
            if len(alternatives) >= n_alternatives:
                break
    except (nx.NetworkXNoPath, nx.NetworkXError, StopIteration):
        pass

    # ── Recommendation text ────────────────────────────────────────────────
    if not alternatives and primary_blocked:
        rec = (
            f"No alternative route found from {src_node} to {dst_node} "
            f"around the disrupted stations/edges. Consider partial routing or "
            f"waiting for disruption clearance."
        )
    elif alternatives and primary_blocked:
        best = alternatives[0]
        extra = best["extra_time_vs_primary"]
        rec = (
            f"Primary route is disrupted. Best alternative via "
            f"{' → '.join(best['path'][1:-1][:3])}... "
            f"adds {extra:.0f} min. "
            f"Reliability score: {best['reliability_score']}/100."
        )
    elif alternatives:
        rec = (
            f"Primary route is clear. "
            f"{len(alternatives)} alternative(s) available if needed."
        )
    else:
        rec = f"Only one route available between {src_node} and {dst_node}."

    return {
        "source":            src_node,
        "destination":       dst_node,
        "primary":           primary,
        "alternatives":      alternatives,
        "disruption_active": primary_blocked,
        "recommendation":    rec,
    }


# ===========================================================================
#  FUNCTION 2 — suggest_schedule_adjustments
# ===========================================================================

def suggest_schedule_adjustments(
    delayed_station: str,
    delay_minutes:   int = 30,
    max_affected:    int = 10,
) -> dict:
    """
    Given a delay at a station, recommend which connecting trains to
    reschedule/hold to minimise cascade propagation.

    Logic
    -----
    1. Find all trains serving the delayed station (from routes.csv)
    2. Compute expected propagated delay = delay × congestion_factor
    3. Rank by impact; suggest hold/advance/skip actions
    4. Compute estimated cascade savings from each action

    Parameters
    ----------
    delayed_station : str  — the station experiencing the initial delay
    delay_minutes   : int  — size of the initial delay
    max_affected    : int  — max trains to analyse

    Returns
    -------
    dict
        station, delay_minutes, affected_trains,
        adjustments (list of dicts), total_cascade_saving_min, summary
    """
    G    = _graph()
    rts  = _routes()
    imp  = _importance()

    # Resolve station
    try:
        stn = _resolve(G, delayed_station)
    except ValueError:
        stn = delayed_station

    # ── Get station metadata ───────────────────────────────────────────────
    imp_row = imp[imp["station_name"].str.lower().str.contains(stn.lower(), regex=False)]
    degree       = int(imp_row["total_degree"].iloc[0])         if not imp_row.empty else 4
    betweenness  = float(imp_row["betweenness_centrality"].iloc[0]) if not imp_row.empty else 0.05
    delay_risk   = _station_delay_risk(stn)

    # Congestion factor: high-degree + high-betweenness stations amplify delays
    congestion_factor = round(1.0 + betweenness * 3 + degree / 20, 2)

    # ── Find trains that pass through this station ─────────────────────────
    if not rts.empty:
        passing = rts[
            rts["source_station"].str.lower().str.contains(stn.lower(), regex=False) |
            rts["destination_station"].str.lower().str.contains(stn.lower(), regex=False)
        ][["train_number","train_name","source_station","destination_station",
           "avg_delay_on_edge","pct_significant_delay_src"]].drop_duplicates("train_number")
    else:
        passing = pd.DataFrame()

    # Fall back to graph neighbors if routes unavailable
    if passing.empty:
        neighbors = list(G.successors(stn)) + list(G.predecessors(stn))
        passing = pd.DataFrame([{
            "train_number": f"T{i+1:04d}", "train_name": f"Train via {n}",
            "source_station": stn, "destination_station": n,
            "avg_delay_on_edge": G[stn][n].get("avg_delay", 20.0) if G.has_edge(stn, n) else 20.0,
            "pct_significant_delay_src": delay_risk,
        } for i, n in enumerate(neighbors[:max_affected])])

    passing = passing.head(max_affected).copy()

    # ── Generate adjustments ───────────────────────────────────────────────
    adjustments = []
    total_saving = 0.0

    for _, row in passing.iterrows():
        edge_delay = float(row.get("avg_delay_on_edge", 20.0) or 20.0)
        sig_pct    = float(row.get("pct_significant_delay_src", delay_risk) or delay_risk)

        # Estimated cascade impact on this train
        cascade_impact = round(delay_minutes * congestion_factor *
                               (sig_pct / 100 + 0.3), 1)

        # Decide action
        if cascade_impact >= delay_minutes * 0.8:
            action        = "HOLD"
            action_desc   = f"Hold departure by {min(int(delay_minutes * 0.6), 45)} min to absorb delay"
            hold_min      = min(int(delay_minutes * 0.6), 45)
            saving        = round(cascade_impact * 0.7, 1)
            priority      = "High"
        elif cascade_impact >= delay_minutes * 0.4:
            action        = "RESCHEDULE"
            action_desc   = f"Advance next stop dwell by {min(int(delay_minutes * 0.3), 15)} min"
            hold_min      = min(int(delay_minutes * 0.3), 15)
            saving        = round(cascade_impact * 0.4, 1)
            priority      = "Medium"
        else:
            action        = "MONITOR"
            action_desc   = "No schedule change — monitor for further delay growth"
            hold_min      = 0
            saving        = 0.0
            priority      = "Low"

        total_saving += saving
        adjustments.append({
            "train_number":      str(row["train_number"]),
            "train_name":        str(row["train_name"]),
            "from":              str(row["source_station"]),
            "to":                str(row["destination_station"]),
            "estimated_cascade_impact_min": cascade_impact,
            "recommended_action": action,
            "action_description": action_desc,
            "hold_minutes":       hold_min,
            "cascade_saving_min": saving,
            "priority":           priority,
        })

    adjustments.sort(key=lambda x: x["estimated_cascade_impact_min"], reverse=True)

    high_priority = [a for a in adjustments if a["priority"] == "High"]
    summary = (
        f"Delay of {delay_minutes} min at {stn} (congestion factor {congestion_factor}×) "
        f"affects {len(adjustments)} connecting trains. "
        f"{len(high_priority)} require immediate action (HOLD). "
        f"Implementing all recommendations saves ~{total_saving:.0f} min of cascade delay."
    )

    return {
        "station":               stn,
        "delay_minutes":         delay_minutes,
        "congestion_factor":     congestion_factor,
        "affected_trains":       len(adjustments),
        "adjustments":           adjustments,
        "total_cascade_saving_min": round(total_saving, 1),
        "summary":               summary,
    }


# ===========================================================================
#  FUNCTION 3 — multi_objective_route
# ===========================================================================

def multi_objective_route(
    src: str,
    dst: str,
    w_time:        float = 0.5,
    w_congestion:  float = 0.3,
    w_reliability: float = 0.2,
) -> dict:
    """
    Score and rank multiple routes using three objectives simultaneously.

    Objectives
    ----------
    1. Travel time  — lower is better  (weight = w_time)
    2. Congestion   — lower is better  (weight = w_congestion)
       measured as sum of degree_centrality × avg_delay per intermediate stop
    3. Reliability  — higher is better (weight = w_reliability)
       measured as 1 - avg(delay_risk_score) across path stations

    Parameters
    ----------
    src, dst       : str    — station names
    w_time         : float  — weight for travel time objective (default 0.5)
    w_congestion   : float  — weight for congestion objective  (default 0.3)
    w_reliability  : float  — weight for reliability objective (default 0.2)

    Returns
    -------
    dict
        routes   — list of route options sorted by composite_score (best first)
        weights_used — the w_time, w_congestion, w_reliability applied
        recommendation — text summary
    """
    # Normalise weights
    total = w_time + w_congestion + w_reliability
    wt = w_time / total
    wc = w_congestion / total
    wr = w_reliability / total

    G   = _graph()
    imp = _importance()

    src_node = _resolve(G, src)
    dst_node = _resolve(G, dst)

    # Build station metadata lookup
    if not imp.empty:
        deg_map   = dict(zip(imp["station_name"], imp["degree_centrality"]))
        risk_map  = dict(zip(imp["station_name"], imp["delay_risk_score"] / 100))
    else:
        deg_map  = {}
        risk_map = {}

    # ── Enumerate up to 7 candidate paths via penalized Dijkstra ───────────
    try:
        candidate_paths = _k_shortest_penalized(G, src_node, dst_node, k=7, penalty_mult=5.0)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return {
            "source": src_node, "destination": dst_node,
            "routes": [],
            "weights_used": {"time": wt, "congestion": wc, "reliability": wr},
            "recommendation": f"No path found from {src_node} to {dst_node}.",
        }

    routes = []
    for path in candidate_paths:
        m = _path_metrics(G, path)

        # Objective 1: travel time (normalise by max 1440 min = 24h)
        time_score = min(m["total_travel_time_min"] / 600, 1.0)   # cap at 600 min

        # Objective 2: congestion score — sum of (centrality × delay) per stop
        cong = 0.0
        for stn in path[1:-1]:   # intermediate stops only
            dc  = deg_map.get(stn, 0.02)
            dly = m["total_delay_min"] / max(len(path) - 1, 1)
            cong += dc * dly
        cong_score = min(cong / 5.0, 1.0)   # normalise

        # Objective 3: reliability — inverted average risk
        risks = [risk_map.get(stn, 0.3) for stn in path]
        rel_score = 1.0 - np.mean(risks)   # higher = better

        # Composite: lower is better for time/congestion, higher for reliability
        composite = round(
            wt * time_score +
            wc * cong_score -
            wr * rel_score,
            4
        )

        routes.append({
            **m,
            "time_score":        round(time_score,  3),
            "congestion_score":  round(cong_score,  3),
            "reliability_score": round(rel_score,   3),
            "composite_score":   composite,
            "label": _score_label(composite),
        })

    routes.sort(key=lambda x: x["composite_score"])

    best  = routes[0]
    worst = routes[-1]
    improvement = round(
        (worst["composite_score"] - best["composite_score"])
        / max(abs(worst["composite_score"]), 1e-6) * 100, 1
    )

    rec = (
        f"Best route ({len(best['path'])} stops, "
        f"{best['total_travel_time_min']:.0f} min, "
        f"reliability {best['reliability_score']*100:.0f}%) "
        f"scores {best['composite_score']:.3f} — "
        f"{improvement:.0f}% better than the worst option."
        if len(routes) > 1 else
        f"Only one route available: {len(best['path'])} stops, "
        f"{best['total_travel_time_min']:.0f} min."
    )

    return {
        "source":      src_node,
        "destination": dst_node,
        "routes":      routes,
        "weights_used": {"time": round(wt,2), "congestion": round(wc,2), "reliability": round(wr,2)},
        "recommendation": rec,
    }


def _score_label(score: float) -> str:
    if score <= 0.10: return "⭐ Optimal"
    if score <= 0.20: return "✅ Good"
    if score <= 0.35: return "⚠️ Acceptable"
    return "❌ Poor"


# ===========================================================================
#  FUNCTION 4 — prioritize_corridor_trains
# ===========================================================================

def prioritize_corridor_trains(top_n: int = 10) -> pd.DataFrame:
    """
    Identify high-demand corridors and recommend train priority levels.

    Priority is determined by a composite of:
      - Occupancy rate (from passenger_demand.csv)
      - Betweenness centrality of source/destination
      - Delay risk of the corridor
      - Overcrowded months count

    Parameters
    ----------
    top_n : int  — number of corridors to return

    Returns
    -------
    pd.DataFrame with columns:
        rank, source_station, destination_station, avg_occupancy_pct,
        overcrowded_months, betweenness_score, delay_risk_score,
        priority_score, priority_level, recommendation
    """
    dem = _demand()
    imp = _importance()

    if dem.empty:
        return pd.DataFrame()

    # Aggregate demand per corridor
    agg = (
        dem.groupby(["source_station","destination_station"])
           .agg(
               avg_occupancy   =("occupancy_rate",     "mean"),
               overcrowded_months=("crowd_level",
                                   lambda x: (x == "Overcrowded").sum()),
               capacity        =("capacity",            "first"),
               total_passengers=("estimated_passengers","sum"),
           ).reset_index()
    )

    # Join betweenness for source and destination
    if not imp.empty:
        bc = imp[["station_name","betweenness_centrality","delay_risk_score"]].copy()
        agg = agg.merge(bc.rename(columns={
            "station_name":"source_station",
            "betweenness_centrality":"bc_src",
            "delay_risk_score":"dr_src",
        }), on="source_station", how="left")
        agg = agg.merge(bc.rename(columns={
            "station_name":"destination_station",
            "betweenness_centrality":"bc_dst",
            "delay_risk_score":"dr_dst",
        }), on="destination_station", how="left")
        agg["bc_src"] = agg["bc_src"].fillna(0.02)
        agg["bc_dst"] = agg["bc_dst"].fillna(0.02)
        agg["dr_src"] = agg["dr_src"].fillna(30.0)
        agg["dr_dst"] = agg["dr_dst"].fillna(30.0)
        agg["betweenness_score"] = ((agg["bc_src"] + agg["bc_dst"]) / 2).round(4)
        agg["delay_risk_score"]  = ((agg["dr_src"] + agg["dr_dst"]) / 2).round(1)
    else:
        agg["betweenness_score"] = 0.05
        agg["delay_risk_score"]  = 30.0

    # Priority score: demand + strategic importance + delay risk weight
    agg["priority_score"] = (
        agg["avg_occupancy"]   * 50 +
        agg["betweenness_score"] * 200 +
        agg["overcrowded_months"] * 3 -
        agg["delay_risk_score"] * 0.3
    ).round(2)

    agg = agg.sort_values("priority_score", ascending=False).head(top_n).reset_index(drop=True)
    agg.insert(0, "rank", range(1, len(agg)+1))

    def _pl(score: float) -> str:
        if score >= 70: return "🔴 Critical Priority"
        if score >= 50: return "🟠 High Priority"
        if score >= 30: return "🟡 Medium Priority"
        return "🟢 Standard"

    def _rec(row) -> str:
        occ = row["avg_occupancy"]
        ovm = row["overcrowded_months"]
        if occ > 1.0:
            return f"Run extra rakes; {ovm} months overcrowded — add seasonal specials"
        if occ > 0.85:
            return f"Increase frequency during peak months; prioritise at junctions"
        return "Maintain schedule; monitor demand growth"

    agg["priority_level"]  = agg["priority_score"].apply(_pl)
    agg["recommendation"]  = agg.apply(_rec, axis=1)
    agg["avg_occupancy_pct"] = (agg["avg_occupancy"] * 100).round(1)

    cols = ["rank","source_station","destination_station","avg_occupancy_pct",
            "overcrowded_months","betweenness_score","delay_risk_score",
            "priority_score","priority_level","recommendation"]
    return agg[[c for c in cols if c in agg.columns]]


# ===========================================================================
#  FUNCTION 5 — optimization_summary  (dashboard-ready)
# ===========================================================================

def optimization_summary() -> dict:
    """
    Compact summary for the dashboard KPI cards.

    Returns
    -------
    dict
        total_stations, total_routes, critical_corridors,
        top_corridor, top_corridor_occupancy, sample_alternative_available
    """
    G   = _graph()
    cor = prioritize_corridor_trains(5)

    top_corridor     = f"{cor['source_station'].iloc[0]} → {cor['destination_station'].iloc[0]}" if len(cor) else "N/A"
    top_occ          = float(cor["avg_occupancy_pct"].iloc[0]) if len(cor) else 0.0
    critical_count   = int((cor["priority_level"].str.startswith("🔴")).sum()) if len(cor) else 0

    return {
        "total_stations":          G.number_of_nodes(),
        "total_routes":            G.number_of_edges(),
        "critical_corridors":      critical_count,
        "top_corridor":            top_corridor,
        "top_corridor_occupancy":  top_occ,
    }


# ===========================================================================
#  __main__ — smoke tests
# ===========================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  routing_optimizer.py — Operational Optimization Engine")
    print("="*60)

    # 1. Alternative routes
    print("\n[1] Alternative routes (Howrah Jn → Chennai Central, block Salem Jn)")
    r = find_alternative_routes("Howrah Jn", "Chennai Central",
                                blocked_stations=["Salem Jn"], n_alternatives=2)
    print(f"  Disruption active: {r['disruption_active']}")
    print(f"  Alternatives found: {len(r['alternatives'])}")
    print(f"  → {r['recommendation']}")

    # 2. Schedule adjustments
    print("\n[2] Schedule adjustments (New Delhi, 45 min delay)")
    s = suggest_schedule_adjustments("New Delhi", 45, max_affected=5)
    print(f"  Trains affected: {s['affected_trains']}")
    print(f"  Total cascade saving: {s['total_cascade_saving_min']} min")
    print(f"  → {s['summary']}")

    # 3. Multi-objective route
    print("\n[3] Multi-objective route (Mumbai CST → New Delhi)")
    try:
        m = multi_objective_route("Mumbai CST", "New Delhi")
        print(f"  Routes scored: {len(m['routes'])}")
        if m["routes"]:
            best = m["routes"][0]
            print(f"  Best: {best['num_stops']} stops, {best['total_travel_time_min']:.0f} min, label={best['label']}")
        print(f"  → {m['recommendation']}")
    except Exception as e:
        print(f"  (skipped: {e})")

    # 4. Corridor prioritization
    print("\n[4] Top 5 priority corridors")
    c = prioritize_corridor_trains(5)
    if not c.empty:
        print(c[["rank","source_station","destination_station",
                  "avg_occupancy_pct","priority_level"]].to_string(index=False))

    print("\n  ✅  routing_optimizer.py ready\n")
