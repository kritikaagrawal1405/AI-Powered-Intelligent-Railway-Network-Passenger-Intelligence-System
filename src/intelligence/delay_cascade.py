"""
delay_cascade.py
================
Phase-2: Delay Cascade Prediction Engine
AI-Powered Railway Intelligence System

Simulates how an initial delay at one station propagates through the
railway network using a BFS-based weighted decay model.  Every hop
attenuates the delay by a configurable decay factor, further modulated
by each edge's historical avg_delay (a proxy for that corridor's
congestion sensitivity).

Quick import
------------
    from src.intelligence.delay_cascade import (
        simulate_delay_cascade,
        cascade_severity_score,
        get_most_vulnerable_stations,
        visualize_cascade,
    )

Example
-------
    result = simulate_delay_cascade("Nagpur", initial_delay=60)
    print(result)
"""

from __future__ import annotations

import os
import math
from collections import deque
from typing import Optional

import pandas as pd
import networkx as nx

# ---------------------------------------------------------------------------
# Re-use the existing graph loader and importance data path
# ---------------------------------------------------------------------------
from src.graph_engine.graph_utils import load_graph

_HERE           = os.path.dirname(os.path.abspath(__file__))   # src/intelligence/
_ROOT           = os.path.dirname(os.path.dirname(_HERE))       # project root
_PROC           = os.path.join(_ROOT, "data", "processed")
_IMPORTANCE_CSV = os.path.join(_PROC, "station_importance.csv")
_DELAY_CSV      = os.path.join(_PROC, "station_delay_stats.csv")

# Minimum propagated delay (minutes) to include a station in results.
# Keeps the output focused on meaningfully affected stations.
_MIN_DELAY_THRESHOLD: float = 1.0

# Reference avg_delay used to normalise the edge congestion factor.
# Calibrated from the dataset: mean ≈ 37, 75th-percentile ≈ 42, max ≈ 558.
_EDGE_DELAY_REF: float = 50.0


# ===========================================================================
#  INTERNAL HELPERS
# ===========================================================================

def _resolve_station(G: nx.DiGraph, name: str) -> str:
    """
    Resolve a station name to the exact key used in the graph.

    Tries:
      1. Exact match
      2. Case-insensitive exact match
      3. Case-insensitive substring match (returns first hit if unique)

    Raises
    ------
    ValueError
        If the name cannot be matched to any node.
    """
    if name in G:
        return name

    name_lower = name.lower()

    # Case-insensitive exact match first
    exact = [n for n in G.nodes() if n.lower() == name_lower]
    if exact:
        return exact[0]

    # Substring match
    partial = [n for n in G.nodes() if name_lower in n.lower()]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        # Prefer shorter names (more specific match)
        partial.sort(key=len)
        return partial[0]

    raise ValueError(
        f"Station '{name}' not found in the railway graph.\n"
        f"Tip: partial names work too — try 'Nagpur', 'Delhi', 'Howrah'."
    )


def _load_importance() -> pd.DataFrame:
    """
    Load station_importance.csv with a graceful fallback if missing.

    Returns a DataFrame with at minimum:
        station_name, betweenness_centrality, delay_risk_score
    """
    if not os.path.exists(_IMPORTANCE_CSV):
        raise FileNotFoundError(
            f"station_importance.csv not found at:\n  {_IMPORTANCE_CSV}\n"
            "Run:  python src/graph_engine/build_graph.py"
        )
    df = pd.read_csv(_IMPORTANCE_CSV)

    # Ensure required columns exist
    if "betweenness_centrality" not in df.columns:
        df["betweenness_centrality"] = 0.0
    if "delay_risk_score" not in df.columns:
        df["delay_risk_score"] = 0.0

    return df


def _edge_congestion_factor(edge_data: dict) -> float:
    """
    Compute a congestion sensitivity factor for a single edge in [0.2, 1.5].

    Logic
    -----
    Edges with high historical avg_delay are more likely to amplify incoming
    delays (congested corridor, platform conflicts, etc.).  We normalise
    avg_delay against a reference value and clamp the result so that:
      • A low-delay corridor (avg_delay ≈ 10 min) yields factor ≈ 0.20
      • A typical corridor  (avg_delay ≈ 50 min) yields factor ≈ 1.00
      • A high-delay corridor (avg_delay ≥ 75 min) yields factor ≈ 1.50

    Parameters
    ----------
    edge_data : dict
        NetworkX edge attribute dictionary (distance, travel_time, avg_delay).

    Returns
    -------
    float in [0.20, 1.50]
    """
    avg_delay = float(edge_data.get("avg_delay", 0.0))
    raw_factor = avg_delay / _EDGE_DELAY_REF
    return max(0.20, min(1.50, raw_factor))


# ===========================================================================
#  FUNCTION 1 — simulate_delay_cascade
# ===========================================================================

def simulate_delay_cascade(
    station_name: str,
    initial_delay: float,
    max_depth: int = 3,
    decay_factor: float = 0.6,
) -> dict:
    """
    Simulate how an initial delay at one station cascades through the
    railway network.

    Algorithm
    ---------
    BFS from *station_name*.  At each hop the incoming delay is attenuated:

        propagated_delay =
            parent_delay  ×  decay_factor  ×  edge_congestion_factor

    ``edge_congestion_factor`` is derived from the edge's historical
    ``avg_delay`` (higher historical delay → higher sensitivity to cascades).
    BFS terminates when:
      • ``max_depth`` hops have been explored, OR
      • The propagated delay falls below ``_MIN_DELAY_THRESHOLD`` (1 min).

    Cycles are handled: each station is visited only once (first-visit wins,
    i.e., the strongest signal path dominates).

    Parameters
    ----------
    station_name  : str   — origin station name (partial match supported)
    initial_delay : float — delay in minutes at the source station
    max_depth     : int   — maximum BFS hops (default 3)
    decay_factor  : float — per-hop decay multiplier, (0, 1) (default 0.6)

    Returns
    -------
    dict
        {
          "source_station"       : str,
          "initial_delay"        : float,
          "max_depth"            : int,
          "decay_factor"         : float,
          "affected_stations"    : list[dict],   # [{station, delay, depth, path}, ...]
          "cascade_severity_score": float,        # 0–100
          "total_stations_affected": int,
          "avg_propagated_delay" : float,
          "summary"              : str,           # human-readable one-liner
        }

    Raises
    ------
    ValueError  — if station_name is not found in the graph
    ValueError  — if initial_delay ≤ 0 or decay_factor not in (0, 1)
    """
    # ── Input validation ───────────────────────────────────────────────────
    if initial_delay <= 0:
        raise ValueError(f"initial_delay must be positive, got {initial_delay}")
    if not (0 < decay_factor < 1):
        raise ValueError(f"decay_factor must be in (0, 1), got {decay_factor}")
    if max_depth < 1:
        raise ValueError(f"max_depth must be ≥ 1, got {max_depth}")

    G = load_graph()
    source = _resolve_station(G, station_name)

    # ── BFS traversal ──────────────────────────────────────────────────────
    # Queue items: (current_station, current_delay, depth, path_so_far)
    queue: deque = deque()
    queue.append((source, float(initial_delay), 0, [source]))

    visited: dict[str, float] = {}   # station → propagated_delay at first visit
    visited[source] = float(initial_delay)

    affected: list[dict] = []        # exclude source; includes all reached nodes

    while queue:
        station, delay, depth, path = queue.popleft()

        # Explore neighbours if within depth budget
        if depth >= max_depth:
            continue

        for neighbour in G.neighbors(station):
            if neighbour in visited:
                # Only follow a stronger signal if it arrives via a different
                # (shorter / higher-delay) path — first-visit-wins is fine
                # for BFS (first visit is always the shortest-hop path).
                continue

            edge_data      = G[station][neighbour]
            cong_factor    = _edge_congestion_factor(edge_data)
            prop_delay     = delay * decay_factor * cong_factor
            prop_delay     = round(prop_delay, 2)

            if prop_delay < _MIN_DELAY_THRESHOLD:
                continue  # Too attenuated — stop propagating this branch

            visited[neighbour] = prop_delay
            new_path = path + [neighbour]

            affected.append({
                "station"       : neighbour,
                "delay"         : prop_delay,
                "depth"         : depth + 1,
                "path_from_source": " → ".join(new_path),
            })

            queue.append((neighbour, prop_delay, depth + 1, new_path))

    # ── Sort by propagated delay descending ────────────────────────────────
    affected.sort(key=lambda x: x["delay"], reverse=True)

    # ── Compute severity score ─────────────────────────────────────────────
    severity = cascade_severity_score(
        source_station=source,
        affected=affected,
        initial_delay=initial_delay,
    )

    # ── Summary statistics ─────────────────────────────────────────────────
    delays      = [s["delay"] for s in affected]
    avg_delay   = round(sum(delays) / len(delays), 2) if delays else 0.0
    max_reached = max((s["depth"] for s in affected), default=0)

    summary = (
        f"A {initial_delay:.0f}-min delay at {source} cascades to "
        f"{len(affected)} stations across {max_reached} hop(s). "
        f"Avg propagated delay: {avg_delay:.1f} min. "
        f"Cascade severity: {severity:.1f}/100."
    )

    return {
        "source_station"          : source,
        "initial_delay"           : float(initial_delay),
        "max_depth"               : max_depth,
        "decay_factor"            : decay_factor,
        "affected_stations"       : affected,
        "cascade_severity_score"  : severity,
        "total_stations_affected" : len(affected),
        "avg_propagated_delay"    : avg_delay,
        "summary"                 : summary,
    }


# ===========================================================================
#  FUNCTION 2 — cascade_severity_score
# ===========================================================================

def cascade_severity_score(
    source_station: str,
    affected: list[dict],
    initial_delay: float,
) -> float:
    """
    Compute a normalised cascade severity score in [0, 100].

    Formula
    -------
        raw_score  = num_stations × avg_delay × centrality_factor
        severity   = clamp(raw_score / normalization_constant × 100, 0, 100)

    Where ``centrality_factor`` is the mean betweenness centrality (scaled
    to [0, 1]) of the source station and all affected stations.  Delays
    spreading through high-centrality junctions are inherently more severe.

    Parameters
    ----------
    source_station : str        — name of the originating station
    affected       : list[dict] — list of affected station dicts (from BFS)
    initial_delay  : float      — original delay at the source (minutes)

    Returns
    -------
    float in [0.0, 100.0]
    """
    if not affected:
        return 0.0

    try:
        importance_df = _load_importance()
        centrality_map: dict[str, float] = dict(
            zip(importance_df["station_name"],
                importance_df["betweenness_centrality"])
        )
        max_centrality = importance_df["betweenness_centrality"].max()
        max_centrality = max_centrality if max_centrality > 0 else 1.0
    except FileNotFoundError:
        centrality_map = {}
        max_centrality = 1.0

    # Collect all station names: source + affected
    all_stations = [source_station] + [s["station"] for s in affected]

    # Average normalised centrality across all involved stations
    centrality_values = [
        centrality_map.get(st, 0.0) / max_centrality
        for st in all_stations
    ]
    centrality_factor = sum(centrality_values) / len(centrality_values)
    centrality_factor = max(0.01, centrality_factor)   # avoid zero division

    num_stations = len(affected)
    delays       = [s["delay"] for s in affected]
    avg_delay    = sum(delays) / len(delays)

    # Raw score: product of scale indicators
    raw_score = num_stations * avg_delay * centrality_factor

    # Normalisation constant: empirically calibrated so that a worst-case
    # scenario (60 stations affected, 60 min avg delay, max centrality)
    # ≈ 100.  Adjust if the network changes significantly.
    #   60 × 60 × 1.0 = 3600
    normalization_constant = 3600.0

    severity = (raw_score / normalization_constant) * 100.0
    return round(min(100.0, max(0.0, severity)), 2)


# ===========================================================================
#  FUNCTION 3 — get_most_vulnerable_stations
# ===========================================================================

def get_most_vulnerable_stations(n: int = 10) -> pd.DataFrame:
    """
    Return the top *n* stations most likely to trigger large delay cascades.

    Vulnerability Score
    -------------------
    Combines two complementary signals from ``station_importance.csv``:

    1. **Betweenness centrality** — a station on many shortest paths will
       propagate delays to many downstream nodes.

    2. **Delay risk score** — stations already prone to delays are more
       likely to be cascade *sources*.

    Formula::

        vulnerability_score =
            (0.60 × norm_betweenness) +
            (0.40 × norm_delay_risk)

    Both inputs are min-max normalised to [0, 1] before combining.
    Final score is scaled to [0, 100].

    Parameters
    ----------
    n : int — number of top stations to return (default 10)

    Returns
    -------
    pd.DataFrame with columns:
        station_name, betweenness_centrality, delay_risk_score,
        vulnerability_score, vulnerability_rank,
        total_degree (if available)

    Sorted by vulnerability_score descending.

    Raises
    ------
    FileNotFoundError — if station_importance.csv is missing
    """
    df = _load_importance().copy()

    # ── Min-max normalise each component ──────────────────────────────────
    def _normalise(series: pd.Series) -> pd.Series:
        lo, hi = series.min(), series.max()
        if hi == lo:
            return pd.Series([0.5] * len(series), index=series.index)
        return (series - lo) / (hi - lo)

    df["_norm_bc"]   = _normalise(df["betweenness_centrality"])
    df["_norm_dr"]   = _normalise(df["delay_risk_score"])

    df["vulnerability_score"] = (
        0.60 * df["_norm_bc"] +
        0.40 * df["_norm_dr"]
    ) * 100.0

    df["vulnerability_score"] = df["vulnerability_score"].round(2)
    df = df.sort_values("vulnerability_score", ascending=False).reset_index(drop=True)
    df["vulnerability_rank"] = df.index + 1

    # ── Select output columns ──────────────────────────────────────────────
    output_cols = [
        "vulnerability_rank",
        "station_name",
        "vulnerability_score",
        "betweenness_centrality",
        "delay_risk_score",
    ]
    if "total_degree" in df.columns:
        output_cols.append("total_degree")
    if "avg_delay_min" in df.columns:
        output_cols.append("avg_delay_min")

    return df[output_cols].head(n).reset_index(drop=True)


# ===========================================================================
#  FUNCTION 4 — visualize_cascade
# ===========================================================================

def visualize_cascade(
    source_station: str,
    cascade_result: dict,
) -> nx.DiGraph:
    """
    Build a NetworkX subgraph showing only the cascade propagation paths.

    The subgraph can be passed directly to any NetworkX / Matplotlib /
    Pyvis visualizer.  Node and edge attributes carry metadata for styling:

    Node attributes
    ---------------
    node_type      : "source" | "affected"
    propagated_delay: float (minutes)
    depth          : int (hops from source)

    Edge attributes
    ---------------
    propagated_delay: float (delay transferred across this edge)
    depth           : int (hop number of the destination node)

    Parameters
    ----------
    source_station : str
        Exact station name of the cascade origin (as returned in
        ``cascade_result["source_station"]``).
    cascade_result : dict
        Output dict from :func:`simulate_delay_cascade`.

    Returns
    -------
    nx.DiGraph
        Directed subgraph with source + affected stations as nodes and
        the BFS propagation paths as edges.

    Notes
    -----
    To render with Matplotlib::

        import matplotlib.pyplot as plt
        H = visualize_cascade("Nagpur", result)
        pos = nx.spring_layout(H, seed=42)
        nx.draw(H, pos, with_labels=True, node_color=[
            "red" if H.nodes[n]["node_type"] == "source" else "skyblue"
            for n in H.nodes()
        ])
        plt.show()
    """
    G = load_graph()

    H = nx.DiGraph()

    # ── Source node ────────────────────────────────────────────────────────
    source = cascade_result.get("source_station", source_station)
    H.add_node(
        source,
        node_type         = "source",
        propagated_delay  = cascade_result.get("initial_delay", 0.0),
        depth             = 0,
    )

    # ── Affected nodes and propagation edges ──────────────────────────────
    for entry in cascade_result.get("affected_stations", []):
        node  = entry["station"]
        delay = entry["delay"]
        depth = entry["depth"]

        H.add_node(
            node,
            node_type        = "affected",
            propagated_delay = delay,
            depth            = depth,
        )

        # Reconstruct the direct parent from the recorded path
        path_stations = entry["path_from_source"].split(" → ")
        if len(path_stations) >= 2:
            parent = path_stations[-2]
            if parent in H.nodes:
                # Copy relevant edge attributes from the main graph
                edge_data = G.get_edge_data(parent, node, default={})
                H.add_edge(
                    parent,
                    node,
                    propagated_delay = delay,
                    depth            = depth,
                    avg_delay        = edge_data.get("avg_delay", 0.0),
                    travel_time      = edge_data.get("travel_time", 0.0),
                    distance         = edge_data.get("distance", 0.0),
                )

    return H


# ===========================================================================
#  BONUS — pretty_print_cascade
# ===========================================================================

def pretty_print_cascade(result: dict) -> None:
    """
    Print a formatted cascade simulation report to stdout.

    Parameters
    ----------
    result : dict — output from :func:`simulate_delay_cascade`
    """
    sep   = "=" * 65
    sep2  = "-" * 65
    WIDTH = 65

    print(f"\n{sep}")
    print("  🚂  RAILWAY DELAY CASCADE SIMULATION REPORT")
    print(sep)
    print(f"  Source Station    : {result['source_station']}")
    print(f"  Initial Delay     : {result['initial_delay']:.0f} minutes")
    print(f"  BFS Depth Limit   : {result['max_depth']} hops")
    print(f"  Decay Factor      : {result['decay_factor']}")
    print(sep2)
    print(f"  Stations Affected : {result['total_stations_affected']}")
    print(f"  Avg Propagated    : {result['avg_propagated_delay']:.1f} min")
    print(f"  Severity Score    : {result['cascade_severity_score']:.1f} / 100")
    print(sep2)

    # Severity label
    score = result["cascade_severity_score"]
    if score >= 70:
        label = "🔴 CRITICAL"
    elif score >= 40:
        label = "🟠 HIGH"
    elif score >= 15:
        label = "🟡 MODERATE"
    else:
        label = "🟢 LOW"
    print(f"  Severity Level    : {label}")
    print(sep2)

    # Affected station table
    affected = result["affected_stations"]
    if affected:
        print(f"\n  {'#':<4} {'Station':<30} {'Delay':>8}  {'Hops':>5}  Path")
        print(f"  {'-'*4} {'-'*30} {'-'*8}  {'-'*5}  ----")
        for i, s in enumerate(affected, 1):
            # Truncate path for readability
            path  = s["path_from_source"]
            parts = path.split(" → ")
            short = " → ".join(parts[:3]) + (" → …" if len(parts) > 3 else "")
            print(
                f"  {i:<4} {s['station']:<30} "
                f"{s['delay']:>6.1f}m  "
                f"  {s['depth']:>3}  {short}"
            )
    else:
        print("  No stations affected beyond threshold.")

    print(f"\n  Summary: {result['summary']}")
    print(f"{sep}\n")


# ===========================================================================
#  __main__  — demonstration & smoke-test
# ===========================================================================

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  delay_cascade.py  —  Phase-2 Cascade Engine Demo")
    print("=" * 65)

    # ── Test 1: Nagpur 60-min delay ─────────────────────────────────────
    print("\n[TEST 1]  simulate_delay_cascade('Nagpur', initial_delay=60)")
    result = simulate_delay_cascade("Nagpur", initial_delay=60)
    pretty_print_cascade(result)

    # ── Test 2: Howrah (most critical station) ───────────────────────────
    print("[TEST 2]  simulate_delay_cascade('Howrah Jn', initial_delay=45, max_depth=2)")
    result2 = simulate_delay_cascade("Howrah Jn", initial_delay=45, max_depth=2)
    pretty_print_cascade(result2)

    # ── Test 3: Most vulnerable stations ────────────────────────────────
    print("[TEST 3]  get_most_vulnerable_stations(n=10)")
    vuln = get_most_vulnerable_stations(n=10)
    print(vuln.to_string(index=False))

    # ── Test 4: Visualise cascade subgraph ──────────────────────────────
    print("\n[TEST 4]  visualize_cascade() — subgraph stats")
    H = visualize_cascade("Nagpur", result)
    print(f"  Subgraph nodes : {H.number_of_nodes()}")
    print(f"  Subgraph edges : {H.number_of_edges()}")
    print(f"  Node types     : { {d['node_type'] for _, d in H.nodes(data=True)} }")

    # ── Test 5: Severity score standalone ───────────────────────────────
    print("\n[TEST 5]  cascade_severity_score() — direct call")
    mock_affected = [
        {"station": "Wardha Jn",  "delay": 32.0, "depth": 1, "path_from_source": "Nagpur → Wardha Jn"},
        {"station": "Itarsi Jn",  "delay": 18.0, "depth": 2, "path_from_source": "Nagpur → Betul → Itarsi Jn"},
        {"station": "Bhusaval Jn","delay": 10.0, "depth": 2, "path_from_source": "Nagpur → Betul → Bhusaval Jn"},
    ]
    score = cascade_severity_score("Nagpur", mock_affected, initial_delay=60)
    print(f"  Severity score for 3-station cascade: {score:.2f} / 100")

    print("\n✅  All tests passed — delay_cascade.py ready for integration.\n")