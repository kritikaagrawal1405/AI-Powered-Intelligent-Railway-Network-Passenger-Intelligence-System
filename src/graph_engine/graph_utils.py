"""
graph_utils.py
==============
Graph API for the AI-Powered Railway Intelligence System.

Provides a clean interface for the ML models, dashboard, and
AI assistant to query the railway network.

Quick import:
    from src.graph_engine.graph_utils import (
        load_graph,
        shortest_route,
        top_critical_stations,
        get_delay_stats,
        get_neighbors,
    )
"""

import os
import pandas as pd
import networkx as nx
from typing import Optional

# ---------------------------------------------------------------------------
# Paths  (all relative to project root so the module works anywhere)
# ---------------------------------------------------------------------------
_HERE     = os.path.dirname(os.path.abspath(__file__))          # src/graph_engine/
_ROOT     = os.path.dirname(os.path.dirname(_HERE))             # project root
_PROC     = os.path.join(_ROOT, "data", "processed")

_EDGES_CSV      = os.path.join(_PROC, "graph_edges.csv")
_IMPORTANCE_CSV = os.path.join(_PROC, "station_importance.csv")
_DELAY_CSV      = os.path.join(_PROC, "station_delay_stats.csv")

# Module-level cache — graph is built once and reused
_GRAPH: Optional[nx.DiGraph] = None


# ===========================================================================
#  FUNCTION 1 — load_graph
# ===========================================================================

def load_graph(force_reload: bool = False) -> nx.DiGraph:
    """
    Load the Indian Railway network as a directed NetworkX graph.

    Nodes  → station names  (str)
    Edges  → railway routes with attributes:
               distance     (km,  float)
               travel_time  (min, float)
               avg_delay    (min, float)
               weight       (used by Dijkstra — see below)

    Edge weight priority:
        1. travel_time  (if > 0)
        2. distance     (if > 0)
        3. avg_delay    (if > 0)
        4. 1.0          (fallback so graph stays fully traversable)

    Parameters
    ----------
    force_reload : bool
        Pass True to rebuild the graph from CSV even if cached.

    Returns
    -------
    nx.DiGraph
    """
    global _GRAPH
    if _GRAPH is not None and not force_reload:
        return _GRAPH

    if not os.path.exists(_EDGES_CSV):
        raise FileNotFoundError(
            f"Edge file not found: {_EDGES_CSV}\n"
            "Run the data pipeline first:\n"
            "  python run_pipeline.py"
        )

    df = pd.read_csv(_EDGES_CSV)

    # Normalise numeric columns
    for col in ("distance", "travel_time", "avg_delay"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    G = nx.DiGraph()

    for _, row in df.iterrows():
        src  = str(row["source_station"]).strip()
        dst  = str(row["destination_station"]).strip()
        dist = float(row["distance"])
        tt   = float(row["travel_time"])
        dly  = float(row["avg_delay"])

        # Choose the best available weight for Dijkstra
        if tt   > 0: w = tt
        elif dist > 0: w = dist
        elif dly > 0: w = dly
        else:          w = 1.0

        G.add_edge(src, dst,
                   distance    = dist,
                   travel_time = tt,
                   avg_delay   = dly,
                   weight      = w)

    _GRAPH = G
    return G


# ===========================================================================
#  FUNCTION 2 — shortest_route
# ===========================================================================

def shortest_route(source: str, destination: str) -> list:
    """
    Find the shortest path between two stations using Dijkstra's algorithm.

    Edge weight priority: travel_time → distance → avg_delay → 1.0
    (handled at graph-build time via the 'weight' attribute)

    Parameters
    ----------
    source      : str  — departure station name
    destination : str  — arrival station name

    Returns
    -------
    list of station name strings, e.g.:
        ["Arakkonam", "Katpadi Jn", "Salem Jn", "Erode Jn"]

    Raises
    ------
    ValueError  — if either station is not in the graph
    RuntimeError — if no path exists between the two stations
    """
    G = load_graph()

    # Fuzzy match: try exact, then case-insensitive substring
    def resolve(name: str) -> str:
        if name in G:
            return name
        name_lower = name.lower()
        candidates = [n for n in G.nodes() if name_lower in n.lower()]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            # Prefer exact case-insensitive match first
            exact = [c for c in candidates if c.lower() == name_lower]
            return exact[0] if exact else candidates[0]
        raise ValueError(
            f"Station '{name}' not found in the graph.\n"
            f"Hint: use get_station_list() to see all valid names."
        )

    src_node = resolve(source)
    dst_node = resolve(destination)

    try:
        path = nx.dijkstra_path(G, src_node, dst_node, weight="weight")
        return path
    except nx.NetworkXNoPath:
        raise RuntimeError(
            f"No route found between '{src_node}' and '{dst_node}'.\n"
            "The two stations may be in disconnected parts of the network."
        )


# ===========================================================================
#  FUNCTION 3 — top_critical_stations
# ===========================================================================

def top_critical_stations(n: int = 10) -> pd.DataFrame:
    """
    Return the N most critical stations ranked by betweenness centrality.

    A high betweenness centrality means the station lies on many shortest
    paths — disruptions here cause widespread delay cascades.

    Parameters
    ----------
    n : int  — number of stations to return (default 10)

    Returns
    -------
    pd.DataFrame with columns:
        station_name, betweenness_centrality, total_degree,
        delay_risk_score  (0–100, higher = more delay-prone)
        + importance_rank, degree_centrality, avg_delay_min (if present)

    Sorted by betweenness_centrality descending.
    """
    if not os.path.exists(_IMPORTANCE_CSV):
        raise FileNotFoundError(
            f"Importance file not found: {_IMPORTANCE_CSV}\n"
            "Run: python src/graph_engine/build_graph.py"
        )

    df = pd.read_csv(_IMPORTANCE_CSV)
    df = df.sort_values("betweenness_centrality", ascending=False).reset_index(drop=True)
    df["importance_rank"] = df.index + 1

    # Surface the most useful columns first
    priority_cols = [
        "importance_rank", "station_name",
        "betweenness_centrality", "degree_centrality",
        "total_degree", "avg_delay_min", "delay_risk_score",
    ]
    ordered = [c for c in priority_cols if c in df.columns]
    others  = [c for c in df.columns if c not in ordered]

    return df[ordered + others].head(n).reset_index(drop=True)


# ===========================================================================
#  FUNCTION 4 — get_delay_stats
# ===========================================================================

def get_delay_stats(station: str) -> pd.Series:
    """
    Return delay statistics for a specific station.

    Parameters
    ----------
    station : str — station name (case-insensitive, partial match supported)

    Returns
    -------
    pd.Series with fields:
        station_name, avg_delay_min, median_delay_min, max_delay_min,
        delay_risk_score, avg_pct_right_time, avg_pct_significant,
        num_trains, ...

    Raises
    ------
    ValueError — if no matching station is found
    """
    if not os.path.exists(_DELAY_CSV):
        raise FileNotFoundError(
            f"Delay stats file not found: {_DELAY_CSV}\n"
            "Run: python src/data_preprocessing.py"
        )

    df = pd.read_csv(_DELAY_CSV)

    # Exact match first
    mask = df["station_name"].str.lower() == station.lower()
    if mask.any():
        return df[mask].iloc[0]

    # Partial match fallback
    mask = df["station_name"].str.lower().str.contains(station.lower(), na=False)
    if mask.any():
        matches = df[mask]
        if len(matches) == 1:
            return matches.iloc[0]
        # Return best match (shortest name = most specific)
        best = matches.loc[matches["station_name"].str.len().idxmin()]
        return best

    raise ValueError(
        f"Station '{station}' not found in delay stats.\n"
        f"Available count: {len(df)} stations. "
        f"Try a partial name, e.g. 'Nagpur' or 'Delhi'."
    )


# ===========================================================================
#  FUNCTION 5 — get_neighbors
# ===========================================================================

def get_neighbors(station: str) -> list:
    """
    Return all stations directly reachable from the given station.

    Parameters
    ----------
    station : str — station name (exact or case-insensitive partial match)

    Returns
    -------
    list of str — names of adjacent stations, sorted alphabetically

    Raises
    ------
    ValueError — if the station is not in the graph
    """
    G = load_graph()

    # Resolve name
    if station not in G:
        station_lower = station.lower()
        candidates = [n for n in G.nodes() if station_lower in n.lower()]
        if not candidates:
            raise ValueError(
                f"Station '{station}' not found.\n"
                "Use get_station_list() to see all valid names."
            )
        station = candidates[0]

    return sorted(list(G.neighbors(station)))


# ===========================================================================
#  BONUS HELPERS  (used by dashboard + AI assistant)
# ===========================================================================

def get_station_list() -> list:
    """Return sorted list of all station names in the network."""
    return sorted(load_graph().nodes())


def get_route_details(source: str, destination: str) -> dict:
    """
    Return shortest path with full per-leg breakdown.

    Returns
    -------
    dict:
        path                  — list of station names
        num_stops             — total stops including source & destination
        total_distance_km     — sum of leg distances
        total_travel_time_min — sum of leg travel times
        total_delay_min       — sum of average delays on each leg
        legs                  — list of {from, to, distance_km,
                                          travel_time_min, avg_delay_min}
    """
    G    = load_graph()
    path = shortest_route(source, destination)

    legs = []
    total_dist = total_time = total_delay = 0.0

    for i in range(len(path) - 1):
        s, d = path[i], path[i + 1]
        e    = G[s][d]
        dist  = e.get("distance", 0.0)
        time  = e.get("travel_time", 0.0)
        delay = e.get("avg_delay", 0.0)
        total_dist  += dist
        total_time  += time
        total_delay += delay
        legs.append({
            "from":            s,
            "to":              d,
            "distance_km":     round(dist,  1),
            "travel_time_min": round(time,  1),
            "avg_delay_min":   round(delay, 1),
        })

    return {
        "path":                  path,
        "num_stops":             len(path),
        "total_distance_km":     round(total_dist,  1),
        "total_travel_time_min": round(total_time,  1),
        "total_delay_min":       round(total_delay, 1),
        "legs":                  legs,
    }


def graph_summary() -> dict:
    """Quick stats dict — perfect for dashboard summary cards."""
    G = load_graph()

    delay_df  = pd.read_csv(_DELAY_CSV) if os.path.exists(_DELAY_CSV) else pd.DataFrame()
    avg_delay = round(delay_df["avg_delay_min"].mean(), 1) if not delay_df.empty else None

    comps = list(nx.weakly_connected_components(G))

    return {
        "num_stations":          G.number_of_nodes(),
        "num_routes":            G.number_of_edges(),
        "num_components":        len(comps),
        "largest_component":     max(len(c) for c in comps),
        "avg_out_degree":        round(
            sum(d for _, d in G.out_degree()) / max(G.number_of_nodes(), 1), 2
        ),
        "network_avg_delay_min": avg_delay,
        "density":               round(nx.density(G), 6),
    }

def get_station_importance(n: int = None) -> pd.DataFrame:
    """
    Return station importance metrics.

    Parameters
    ----------
    n : int or None
        If provided, return only the top N stations ranked by
        betweenness centrality.

    Returns
    -------
    pd.DataFrame
    """

    if not os.path.exists(_IMPORTANCE_CSV):
        raise FileNotFoundError(
            f"Station importance file not found: {_IMPORTANCE_CSV}\n"
            "Run: python src/graph_engine/build_graph.py"
        )

    df = pd.read_csv(_IMPORTANCE_CSV)

    df = df.sort_values("betweenness_centrality", ascending=False)

    if n is not None:
        df = df.head(n)

    return df

# delay simulator
def simulate_delay_cascade(start_station, delay=30, decay=0.4, depth=3):

    G = load_graph()

    results = {}
    frontier = [(start_station, delay, 0)]

    while frontier:
        station, d, level = frontier.pop(0)

        if level > depth:
            continue

        results[station] = round(d,2)

        for nbr in G.neighbors(station):
            frontier.append((nbr, d * decay, level + 1))

    return results

# ===========================================================================
#  __main__  — quick smoke-test / demo
# ===========================================================================

if __name__ == "__main__":
    SEP = "=" * 60

    print(SEP)
    print("  graph_utils.py — Railway Graph API Demo")
    print(SEP)

    # ── 1. Load graph ──────────────────────────────────────────────────────
    print("\n📦 Loading graph …")
    G = load_graph()
    summary = graph_summary()
    print(f"   Stations : {summary['num_stations']}")
    print(f"   Routes   : {summary['num_routes']}")
    print(f"   Avg delay: {summary['network_avg_delay_min']} min (network-wide)")

    # ── 2. Shortest route ──────────────────────────────────────────────────
    print("\n🚂 shortest_route('Arakkonam', 'Erode Jn')")
    try:
        route = shortest_route("Arakkonam", "Erode Jn")
        print(f"   Path ({len(route)} stops): {' → '.join(route)}")
    except Exception as e:
        print(f"   ⚠️  {e}")

    # Second example with route details
    print("\n🚂 get_route_details('Patliputra', 'Rajamundry')")
    try:
        details = get_route_details("Patliputra", "Rajamundry")
        print(f"   Path     : {' → '.join(details['path'])}")
        print(f"   Distance : {details['total_distance_km']} km")
        print(f"   Time     : {details['total_travel_time_min']} min")
        print(f"   Delay    : {details['total_delay_min']} min (cumulative avg)")
        print(f"   Legs     : {len(details['legs'])}")
    except Exception as e:
        print(f"   ⚠️  {e}")

    # ── 3. Top critical stations ───────────────────────────────────────────
    print("\n🏆 top_critical_stations(n=5)")
    top = top_critical_stations(n=5)
    display_cols = [c for c in
                    ["importance_rank", "station_name",
                     "betweenness_centrality", "total_degree", "delay_risk_score"]
                    if c in top.columns]
    print(top[display_cols].to_string(index=False))

    # ── 4. Delay stats for a station ───────────────────────────────────────
    print("\n⏱️  get_delay_stats('Howrah')")
    try:
        stats = get_delay_stats("Howrah")
        print(f"   Station          : {stats['station_name']}")
        print(f"   Avg delay        : {stats['avg_delay_min']:.1f} min")
        print(f"   Delay risk score : {stats['delay_risk_score']:.1f} / 100")
        print(f"   % on time        : {stats['avg_pct_right_time']:.1f}%")
        print(f"   Trains observed  : {int(stats['num_trains'])}")
    except Exception as e:
        print(f"   ⚠️  {e}")

    # ── 5. Neighbours ──────────────────────────────────────────────────────
    print("\n🔗 get_neighbors('New Delhi')")
    try:
        nbrs = get_neighbors("New Delhi")
        print(f"   {len(nbrs)} neighbours: {nbrs}")
    except Exception as e:
        print(f"   ⚠️  {e}")

    print(f"\n{SEP}")
    print("  ✅  All functions working — graph_utils ready for integration")
    print(f"{SEP}\n")
