"""
network_resilience.py
=====================
Phase-2: Network Resilience Analysis
AI-Powered Railway Intelligence System

Measures how well the Indian Railway network withstands station
failures using graph-theoretic resilience metrics:

  - Connectivity robustness  (largest connected component after removal)
  - Critical node identification  (stations whose removal most damages the network)
  - Resilience score  (composite 0–100; higher = more resilient)
  - Attack simulation  (targeted removal of high-centrality nodes)

Quick import
------------
    from src.intelligence.network_resilience import (
        compute_network_resilience,
        identify_critical_nodes,
        simulate_node_removal,
        resilience_summary,
    )

Example
-------
    result = compute_network_resilience()
    print(result["resilience_score"])
"""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd
import networkx as nx

from src.graph_engine.graph_utils import load_graph

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE           = os.path.dirname(os.path.abspath(__file__))
_ROOT           = os.path.dirname(os.path.dirname(_HERE))
_PROC           = os.path.join(_ROOT, "data", "processed")
_IMPORTANCE_CSV = os.path.join(_PROC, "station_importance.csv")

# Maximum nodes to probe in the critical-node scan (keeps it fast)
_MAX_PROBE_NODES: int = 30


# ===========================================================================
#  INTERNAL HELPERS
# ===========================================================================

def _avg_shortest_path(G: nx.DiGraph) -> float:
    """
    Compute average shortest-path length on the largest weakly-connected
    component of G. Returns 0.0 if the graph is trivial or empty.
    """
    if G.number_of_nodes() == 0:
        return 0.0

    wcc        = max(nx.weakly_connected_components(G), key=len)
    subgraph   = G.subgraph(wcc).copy()
    undirected = subgraph.to_undirected()

    if undirected.number_of_nodes() <= 1:
        return 0.0

    try:
        return nx.average_shortest_path_length(undirected)
    except nx.NetworkXError:
        # Disconnected — use harmonic approximation
        total, count = 0.0, 0
        for node in undirected.nodes():
            lengths = nx.single_source_shortest_path_length(undirected, node)
            for _, length in lengths.items():
                if length > 0:
                    total += length
                    count += 1
        return total / count if count else 0.0


def _connectivity_ratio(G: nx.DiGraph) -> float:
    """
    Fraction of stations in the largest connected component.
    1.0 = fully connected; <1.0 = some stations are isolated.
    """
    n = G.number_of_nodes()
    if n <= 1:
        return 1.0
    u       = G.to_undirected()
    largest = max(len(c) for c in nx.connected_components(u))
    return largest / n


# ===========================================================================
#  FUNCTION 1 — compute_network_resilience
# ===========================================================================

def compute_network_resilience() -> dict:
    """
    Compute a comprehensive resilience profile for the full railway network.

    Metrics
    -------
    resilience_score         : float [0–100]
        Composite score. Higher = more resilient.
    connectivity_ratio       : float [0–1]
        Fraction of stations in the largest connected component.
    num_components           : int
        Weakly-connected components (1 = fully connected).
    avg_path_length          : float
        Mean hop-count between pairs in the largest component.
    avg_degree               : float
        Mean connections per station (higher = more redundant paths).
    network_density          : float
        Edge density [0–1].
    single_points_of_failure : list[str]
        Top articulation points — stations whose removal splits the graph.

    Returns
    -------
    dict with keys listed above plus "summary" (str).

    Example
    -------
    >>> result = compute_network_resilience()
    >>> print(result["resilience_score"])
    """
    G = load_graph()
    n = G.number_of_nodes()
    m = G.number_of_edges()

    if n == 0:
        return {
            "resilience_score": 0.0,
            "resilience_level": "Unknown",
            "connectivity_ratio": 0.0,
            "num_components": 0,
            "avg_path_length": 0.0,
            "avg_degree": 0.0,
            "network_density": 0.0,
            "num_articulation_points": 0,
            "single_points_of_failure": [],
            "total_stations": 0,
            "total_routes": 0,
            "summary": "Empty graph — no resilience data available.",
        }

    conn_ratio = _connectivity_ratio(G)
    num_comps  = nx.number_weakly_connected_components(G)
    avg_path   = _avg_shortest_path(G)
    avg_degree = round((2 * m) / n, 3) if n > 0 else 0.0
    density    = round(nx.density(G), 6)

    # Articulation points = single points of failure
    undirected = G.to_undirected()
    try:
        artic_pts = list(nx.articulation_points(undirected))
    except Exception:
        artic_pts = []

    top_spof = sorted(artic_pts, key=lambda x: undirected.degree(x), reverse=True)[:10]

    # ── Composite score (0–100) ────────────────────────────────────────────
    # Connectivity  (0–40 pts): fraction of network that stays connected
    conn_score = conn_ratio * 40.0

    # Redundancy    (0–30 pts): avg degree ≥ 4 target = full score
    degree_score = min(avg_degree / 4.0, 1.0) * 30.0

    # Path efficiency (0–20 pts): shorter paths = more efficient routing
    path_score = max(0.0, (1.0 - (avg_path - 1) / 10.0)) * 20.0 if avg_path > 0 else 20.0

    # SPOF penalty  (0–10 pts): fewer articulation points = higher score
    spof_ratio = len(artic_pts) / max(n, 1)
    spof_score = max(0.0, (1.0 - spof_ratio * 2)) * 10.0

    resilience_score = round(conn_score + degree_score + path_score + spof_score, 2)

    level = (
        "Highly Resilient"     if resilience_score >= 70 else
        "Moderately Resilient" if resilience_score >= 45 else
        "Vulnerable"
    )

    summary = (
        f"Network resilience score: {resilience_score:.1f}/100 ({level}). "
        f"{n} stations, {m} routes, {num_comps} component(s). "
        f"Avg path length: {avg_path:.1f} hops. "
        f"Single points of failure: {len(artic_pts)}."
    )

    return {
        "resilience_score"         : resilience_score,
        "resilience_level"         : level,
        "connectivity_ratio"       : round(conn_ratio, 4),
        "num_components"           : num_comps,
        "avg_path_length"          : round(avg_path, 2),
        "avg_degree"               : avg_degree,
        "network_density"          : density,
        "num_articulation_points"  : len(artic_pts),
        "single_points_of_failure" : top_spof,
        "total_stations"           : n,
        "total_routes"             : m,
        "summary"                  : summary,
    }


# ===========================================================================
#  FUNCTION 2 — identify_critical_nodes
# ===========================================================================

def identify_critical_nodes(n: int = 10) -> list[dict]:
    """
    Find the N stations whose removal would most degrade network connectivity.

    For each candidate (top-centrality stations), temporarily removes it
    and measures the change in largest-component size and component count.

    Parameters
    ----------
    n : int — number of critical nodes to return (default 10)

    Returns
    -------
    list[dict] sorted by criticality_score descending. Each dict contains:
        rank, station, criticality_score, components_after,
        largest_comp_after, connectivity_loss_pct, degree
    """
    G          = load_graph()
    undirected = G.to_undirected()
    n_total    = G.number_of_nodes()

    base_comps = nx.number_connected_components(undirected)
    base_large = max(len(c) for c in nx.connected_components(undirected))

    # Probe the top-centrality nodes first (most likely to be critical)
    try:
        df        = pd.read_csv(_IMPORTANCE_CSV)
        top_nodes = (
            df.sort_values("betweenness_centrality", ascending=False)
            ["station_name"].head(_MAX_PROBE_NODES).tolist()
        )
        top_nodes = [nd for nd in top_nodes if nd in undirected]
    except Exception:
        top_nodes = sorted(
            undirected.nodes(), key=lambda x: undirected.degree(x), reverse=True
        )[:_MAX_PROBE_NODES]

    results = []
    for station in top_nodes:
        H     = undirected.copy()
        H.remove_node(station)
        comps = nx.number_connected_components(H)
        large = max((len(c) for c in nx.connected_components(H)), default=0)

        conn_loss  = round((base_large - large) / max(base_large, 1) * 100, 2)
        comp_delta = comps - base_comps
        crit_score = round(0.70 * conn_loss + 0.30 * min(comp_delta * 10, 30.0), 2)

        results.append({
            "station"               : station,
            "criticality_score"     : crit_score,
            "components_after"      : comps,
            "largest_comp_after"    : large,
            "connectivity_loss_pct" : conn_loss,
            "degree"                : int(undirected.degree(station)),
        })

    results.sort(key=lambda x: x["criticality_score"], reverse=True)
    for rank, r in enumerate(results[:n], start=1):
        r["rank"] = rank

    return results[:n]


# ===========================================================================
#  FUNCTION 3 — simulate_node_removal
# ===========================================================================

def simulate_node_removal(stations_to_remove: list[str]) -> dict:
    """
    Simulate targeted removal of specific stations and measure the
    resilience impact. Useful for "what if" scenario planning.

    Parameters
    ----------
    stations_to_remove : list[str]
        Station names to remove (partial/case-insensitive match supported).

    Returns
    -------
    dict with keys: removed_stations, stations_not_found,
        baseline_resilience, post_removal_score, resilience_drop,
        baseline_components, post_removal_components,
        largest_component_after, isolated_stations, summary
    """
    G = load_graph()
    u = G.to_undirected()

    resolved, not_found = [], []
    for name in stations_to_remove:
        if name in u:
            resolved.append(name)
        else:
            candidates = [nd for nd in u.nodes() if name.lower() in nd.lower()]
            resolved.append(candidates[0]) if candidates else not_found.append(name)

    base_large  = max(len(c) for c in nx.connected_components(u))
    base_comps  = nx.number_connected_components(u)
    base_res    = compute_network_resilience()["resilience_score"]

    H = u.copy()
    H.remove_nodes_from(resolved)

    post_comps = nx.number_connected_components(H) if H.number_of_nodes() > 0 else 0
    post_large = max((len(c) for c in nx.connected_components(H)), default=0) if H.number_of_nodes() > 0 else 0
    isolated   = [nd for nd in H.nodes() if H.degree(nd) == 0]

    conn_ratio_after = post_large / max(G.number_of_nodes(), 1)
    post_res = round(
        conn_ratio_after * 60 + max(0.0, (1.0 - post_comps / max(base_comps, 1))) * 40, 2
    )
    res_drop = round(base_res - post_res, 2)

    summary = (
        f"Removing {len(resolved)} station(s) drops resilience from "
        f"{base_res:.1f} to {post_res:.1f} (−{res_drop:.1f}). "
        f"Components: {base_comps} → {post_comps}. "
        f"Isolated stations: {len(isolated)}."
    )

    return {
        "removed_stations"        : resolved,
        "stations_not_found"      : not_found,
        "baseline_resilience"     : base_res,
        "post_removal_score"      : post_res,
        "resilience_drop"         : res_drop,
        "baseline_components"     : base_comps,
        "post_removal_components" : post_comps,
        "largest_component_after" : post_large,
        "isolated_stations"       : isolated[:10],
        "summary"                 : summary,
    }


# ===========================================================================
#  FUNCTION 4 — resilience_summary
# ===========================================================================

def resilience_summary() -> dict:
    """
    Return a concise dashboard-friendly summary of network resilience.

    Returns
    -------
    dict with keys: resilience_score, resilience_level, total_stations,
        total_routes, connectivity_ratio, avg_path_length,
        num_articulation_points, top_critical_stations, recommendation
    """
    full     = compute_network_resilience()
    critical = identify_critical_nodes(n=5)
    score    = full["resilience_score"]

    if score >= 70:
        rec = (
            "Network is well-connected with multiple redundant paths. "
            "Focus monitoring on articulation points to maintain resilience."
        )
    elif score >= 45:
        rec = (
            "Network has moderate resilience. Invest in route redundancy "
            "around the top critical stations to improve fault tolerance."
        )
    else:
        rec = (
            "Network is vulnerable. Several stations are single points of "
            "failure. Priority: add bypass routes and increase connectivity."
        )

    return {
        "resilience_score"        : score,
        "resilience_level"        : full["resilience_level"],
        "total_stations"          : full["total_stations"],
        "total_routes"            : full["total_routes"],
        "connectivity_ratio"      : full["connectivity_ratio"],
        "avg_path_length"         : full["avg_path_length"],
        "num_articulation_points" : full["num_articulation_points"],
        "top_critical_stations"   : [c["station"] for c in critical],
        "recommendation"          : rec,
    }


# ===========================================================================
#  __main__ — smoke tests
# ===========================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  network_resilience.py — Phase-2 Resilience Engine")
    print("=" * 60)

    result = compute_network_resilience()
    print(f"\n  Resilience Score : {result['resilience_score']} / 100")
    print(f"  Level            : {result['resilience_level']}")
    print(f"  Stations         : {result['total_stations']}")
    print(f"  Routes           : {result['total_routes']}")
    print(f"  Articulation pts : {result['num_articulation_points']}")
    print(f"  Summary          : {result['summary']}")
    print("\n  ✅  network_resilience.py ready\n")
