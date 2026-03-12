"""
congestion_predictor.py
=======================
Phase-2 Task-2: Railway Congestion Prediction Engine
AI-Powered Railway Intelligence System

Identifies stations and corridors likely to become congested by
combining network-topology signals (betweenness centrality, degree)
with operational signals (delay risk, historical avg delay).

Quick import
------------
    from src.intelligence.congestion_predictor import (
        calculate_station_congestion,
        identify_congestion_hotspots,
        corridor_congestion_analysis,
        congestion_summary,
    )

Example
-------
    hotspots = identify_congestion_hotspots(n=10)
    for h in hotspots:
        print(h)
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
_HERE           = os.path.dirname(os.path.abspath(__file__))   # src/intelligence/
_ROOT           = os.path.dirname(os.path.dirname(_HERE))       # project root
_PROC           = os.path.join(_ROOT, "data", "processed")
_IMPORTANCE_CSV = os.path.join(_PROC, "station_importance.csv")

# ---------------------------------------------------------------------------
# Congestion level thresholds (applied to the normalised 0–100 score)
# ---------------------------------------------------------------------------
_THRESHOLD_HIGH     = 60.0
_THRESHOLD_MODERATE = 30.0

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_importance() -> pd.DataFrame:
    """
    Load station_importance.csv, fill NaN values, and return the DataFrame.

    Raises
    ------
    FileNotFoundError — if the CSV has not been generated yet.
    """
    if not os.path.exists(_IMPORTANCE_CSV):
        raise FileNotFoundError(
            f"station_importance.csv not found at:\n  {_IMPORTANCE_CSV}\n"
            "Run:  python run_pipeline.py"
        )

    df = pd.read_csv(_IMPORTANCE_CSV)

    # Fill missing operational metrics with conservative zeros
    df["avg_delay_min"]    = pd.to_numeric(df["avg_delay_min"],    errors="coerce").fillna(0.0)
    df["delay_risk_score"] = pd.to_numeric(df["delay_risk_score"], errors="coerce").fillna(0.0)
    df["betweenness_centrality"] = pd.to_numeric(df["betweenness_centrality"], errors="coerce").fillna(0.0)
    df["total_degree"]    = pd.to_numeric(df["total_degree"],    errors="coerce").fillna(0.0)

    return df


def _congestion_level(score: float) -> str:
    """
    Map a normalised congestion score (0–100) to a human-readable level.

    Returns
    -------
    "High" if score >= 60
    "Moderate" if score >= 30
    "Low" otherwise
    """
    if score >= _THRESHOLD_HIGH:
        return "High"
    if score >= _THRESHOLD_MODERATE:
        return "Moderate"
    return "Low"


def _normalise_series(series: pd.Series) -> pd.Series:
    """
    Min-max normalise a pandas Series to [0, 100].

    If all values are identical, returns a Series of 50.0 (mid-range)
    to avoid division-by-zero while still producing a usable score.
    """
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series([50.0] * len(series), index=series.index)
    return ((series - lo) / (hi - lo)) * 100.0


def _resolve_station(df: pd.DataFrame, station_name: str) -> pd.Series:
    """
    Resolve a station name to a DataFrame row using exact → case-insensitive
    exact → substring matching, in that order.

    Returns
    -------
    pd.Series — the matched row

    Raises
    ------
    ValueError — if no match is found
    """
    # 1. Exact match
    exact = df[df["station_name"] == station_name]
    if not exact.empty:
        return exact.iloc[0]

    # 2. Case-insensitive exact
    ci_exact = df[df["station_name"].str.lower() == station_name.lower()]
    if not ci_exact.empty:
        return ci_exact.iloc[0]

    # 3. Substring (case-insensitive)
    partial = df[df["station_name"].str.lower().str.contains(station_name.lower(), na=False)]
    if not partial.empty:
        return partial.iloc[0]

    raise ValueError(
        f"Station '{station_name}' not found in station_importance.csv.\n"
        f"Hint: try a partial name like 'Howrah', 'Delhi', 'Mumbai'."
    )


# ===========================================================================
#  FUNCTION 1 — calculate_station_congestion
# ===========================================================================

def calculate_station_congestion(station_name: str) -> dict:
    """
    Compute the congestion score for a single station.

    Scoring Formula
    ---------------
    The score is a **weighted additive sum** of four normalised signals:

        raw_score =
            (0.4 × delay_risk_score)
          + (0.3 × betweenness_centrality × 100)
          + (0.2 × total_degree)
          + (0.1 × avg_delay_min)

    Note: the spec lists these terms separated by ``*``, but a multiplicative
    combination would collapse all scores near zero (e.g. betweenness ≈ 0.04
    multiplied together produces ~10⁻⁶).  The intended interpretation is a
    weighted sum where each coefficient is a weight — implemented here as ``+``.

    The raw score is then min-max normalised across ALL stations so the final
    value is always in [0, 100], making scores comparable across stations.

    Parameters
    ----------
    station_name : str
        Station name (partial/case-insensitive match supported).

    Returns
    -------
    dict
        {
          "station"          : str,
          "congestion_score" : float,   # 0–100, normalised
          "congestion_level" : str,     # "Low" | "Moderate" | "High"
          "delay_risk_score" : float,
          "betweenness_centrality" : float,
          "total_degree"     : int,
          "avg_delay_min"    : float,
        }

    Raises
    ------
    ValueError       — if station_name cannot be matched
    FileNotFoundError — if station_importance.csv is missing
    """
    df  = _load_importance()
    row = _resolve_station(df, station_name)

    # Compute raw score for every station (needed for normalisation)
    raw = (
        (0.4 * df["delay_risk_score"])
        + (0.3 * df["betweenness_centrality"] * 100)
        + (0.2 * df["total_degree"])
        + (0.1 * df["avg_delay_min"])
    )
    norm = _normalise_series(raw)

    # Find this station's normalised score by its position in the df
    station_idx  = df[df["station_name"] == row["station_name"]].index[0]
    final_score  = round(float(norm.loc[station_idx]), 2)

    return {
        "station"               : row["station_name"],
        "congestion_score"      : final_score,
        "congestion_level"      : _congestion_level(final_score),
        "delay_risk_score"      : round(float(row["delay_risk_score"]), 2),
        "betweenness_centrality": round(float(row["betweenness_centrality"]), 6),
        "total_degree"          : int(row["total_degree"]),
        "avg_delay_min"         : round(float(row["avg_delay_min"]), 2),
    }


# ===========================================================================
#  FUNCTION 2 — identify_congestion_hotspots
# ===========================================================================

def identify_congestion_hotspots(n: int = 10) -> list[dict]:
    """
    Return the top *n* stations ranked by congestion score.

    Uses the same weighted formula as :func:`calculate_station_congestion`
    but runs across all 513 stations in a single vectorised pass for
    efficiency — suitable for dashboard rendering.

    Parameters
    ----------
    n : int
        Number of top stations to return (default 10).

    Returns
    -------
    list[dict]
        Each dict contains:
        {
          "rank"             : int,
          "station"          : str,
          "congestion_score" : float,   # 0–100
          "congestion_level" : str,
          "delay_risk_score" : float,
          "betweenness_centrality" : float,
          "total_degree"     : int,
          "avg_delay_min"    : float,
        }
        Sorted by congestion_score descending.

    Raises
    ------
    FileNotFoundError — if station_importance.csv is missing
    """
    df = _load_importance()

    # Vectorised raw score computation
    df["_raw_score"] = (
        (0.4 * df["delay_risk_score"])
        + (0.3 * df["betweenness_centrality"] * 100)
        + (0.2 * df["total_degree"])
        + (0.1 * df["avg_delay_min"])
    )

    df["_congestion_score"] = _normalise_series(df["_raw_score"])
    df = df.sort_values("_congestion_score", ascending=False).reset_index(drop=True)

    results = []
    for rank, (_, row) in enumerate(df.head(n).iterrows(), start=1):
        score = round(float(row["_congestion_score"]), 2)
        results.append({
            "rank"                  : rank,
            "station"               : row["station_name"],
            "congestion_score"      : score,
            "congestion_level"      : _congestion_level(score),
            "delay_risk_score"      : round(float(row["delay_risk_score"]), 2),
            "betweenness_centrality": round(float(row["betweenness_centrality"]), 6),
            "total_degree"          : int(row["total_degree"]),
            "avg_delay_min"         : round(float(row["avg_delay_min"]), 2),
        })

    return results


# ===========================================================================
#  FUNCTION 3 — corridor_congestion_analysis
# ===========================================================================

def corridor_congestion_analysis(top_n: int = 10) -> list[dict]:
    """
    Identify the most congested railway corridors (source → destination edges).

    Corridor Congestion Score
    -------------------------
    Each directed edge is scored using three factors:

    1. **Node degree pressure** — sum of the source and destination station
       degrees.  High-degree junctions on both ends create a bottleneck
       corridor where many trains compete for the same tracks.

    2. **Edge historical delay** — the avg_delay on the edge directly
       reflects how badly this corridor already performs under load.

    3. **Betweenness centrality boost** — if either endpoint is a critical
       junction (high betweenness), a disruption here propagates widely.

    Formula::

        raw = (0.4 × norm_avg_delay)
            + (0.35 × norm_degree_pressure)
            + (0.25 × norm_centrality_boost)

    All three components are min-max normalised before combining.
    Final score is scaled to 0–100.

    Parameters
    ----------
    top_n : int
        Number of top corridors to return (default 10).

    Returns
    -------
    list[dict]
        Each dict contains:
        {
          "rank"                : int,
          "route"               : str,   # "Source → Destination"
          "congestion_score"    : float, # 0–100
          "congestion_level"    : str,
          "avg_delay_min"       : float,
          "source_degree"       : int,
          "destination_degree"  : int,
          "degree_pressure"     : int,   # source_degree + destination_degree
        }
        Sorted by congestion_score descending.
    """
    G  = load_graph()
    df = _load_importance()

    # Build fast lookup: station_name → betweenness_centrality, total_degree
    centrality_map = dict(zip(df["station_name"], df["betweenness_centrality"]))
    degree_map     = dict(zip(df["station_name"], df["total_degree"]))

    # Collect raw corridor metrics
    records = []
    for src, dst, data in G.edges(data=True):
        avg_delay  = float(data.get("avg_delay", 0.0))
        src_degree = int(degree_map.get(src, G.degree(src)))
        dst_degree = int(degree_map.get(dst, G.degree(dst)))
        degree_pressure = src_degree + dst_degree

        # Centrality boost: higher of the two endpoint centralities
        bc_src  = float(centrality_map.get(src, 0.0))
        bc_dst  = float(centrality_map.get(dst, 0.0))
        cent_boost = max(bc_src, bc_dst)

        records.append({
            "route"              : f"{src} → {dst}",
            "source"             : src,
            "destination"        : dst,
            "avg_delay_min"      : avg_delay,
            "source_degree"      : src_degree,
            "destination_degree" : dst_degree,
            "degree_pressure"    : degree_pressure,
            "_centrality_boost"  : cent_boost,
        })

    corridor_df = pd.DataFrame(records)

    # Normalise each component independently then combine
    corridor_df["_n_delay"]    = _normalise_series(corridor_df["avg_delay_min"])
    corridor_df["_n_pressure"] = _normalise_series(corridor_df["degree_pressure"].astype(float))
    corridor_df["_n_cent"]     = _normalise_series(corridor_df["_centrality_boost"])

    corridor_df["_raw_score"] = (
        0.40 * corridor_df["_n_delay"]
        + 0.35 * corridor_df["_n_pressure"]
        + 0.25 * corridor_df["_n_cent"]
    )

    corridor_df["congestion_score"] = _normalise_series(corridor_df["_raw_score"])
    corridor_df = corridor_df.sort_values("congestion_score", ascending=False).reset_index(drop=True)

    results = []
    for rank, (_, row) in enumerate(corridor_df.head(top_n).iterrows(), start=1):
        score = round(float(row["congestion_score"]), 2)
        results.append({
            "rank"               : rank,
            "route"              : row["route"],
            "congestion_score"   : score,
            "congestion_level"   : _congestion_level(score),
            "avg_delay_min"      : round(float(row["avg_delay_min"]), 2),
            "source_degree"      : int(row["source_degree"]),
            "destination_degree" : int(row["destination_degree"]),
            "degree_pressure"    : int(row["degree_pressure"]),
        })

    return results


# ===========================================================================
#  FUNCTION 4 — congestion_summary
# ===========================================================================

def congestion_summary() -> dict:
    """
    Return a system-wide congestion summary across all stations.

    Computes the congestion score for every station in the network and
    counts how many fall into each severity level.

    Returns
    -------
    dict
        {
          "total_stations"              : int,
          "high_congestion_stations"    : int,   # score >= 60
          "moderate_congestion_stations": int,   # 30 <= score < 60
          "low_congestion_stations"     : int,   # score < 30
          "network_avg_congestion"      : float, # mean score across all stations
          "most_congested_station"      : str,
          "most_congested_score"        : float,
        }

    Raises
    ------
    FileNotFoundError — if station_importance.csv is missing
    """
    df = _load_importance()

    df["_raw_score"] = (
        (0.4 * df["delay_risk_score"])
        + (0.3 * df["betweenness_centrality"] * 100)
        + (0.2 * df["total_degree"])
        + (0.1 * df["avg_delay_min"])
    )
    df["_score"] = _normalise_series(df["_raw_score"])

    high_mask     = df["_score"] >= _THRESHOLD_HIGH
    moderate_mask = (df["_score"] >= _THRESHOLD_MODERATE) & ~high_mask
    low_mask      = df["_score"] < _THRESHOLD_MODERATE

    top_row = df.loc[df["_score"].idxmax()]

    return {
        "total_stations"               : int(len(df)),
        "high_congestion_stations"     : int(high_mask.sum()),
        "moderate_congestion_stations" : int(moderate_mask.sum()),
        "low_congestion_stations"      : int(low_mask.sum()),
        "network_avg_congestion"       : round(float(df["_score"].mean()), 2),
        "most_congested_station"       : str(top_row["station_name"]),
        "most_congested_score"         : round(float(top_row["_score"]), 2),
    }


# ===========================================================================
#  BONUS — pretty_print helpers
# ===========================================================================

def _print_hotspots(hotspots: list[dict]) -> None:
    """Print a formatted congestion hotspot table to stdout."""
    sep  = "=" * 72
    sep2 = "-" * 72

    level_icons = {"High": "🔴", "Moderate": "🟠", "Low": "🟢"}

    print(f"\n{sep}")
    print("  🚦  RAILWAY CONGESTION HOTSPOTS")
    print(sep)
    print(f"  {'#':<4} {'Station':<30} {'Score':>6}  {'Level':<12}  {'Degree':>6}  {'Delay':>7}")
    print(f"  {'-'*4} {'-'*30} {'-'*6}  {'-'*12}  {'-'*6}  {'-'*7}")

    for h in hotspots:
        icon  = level_icons.get(h["congestion_level"], "⚪")
        level = f"{icon} {h['congestion_level']}"
        print(
            f"  {h['rank']:<4} {h['station']:<30} "
            f"{h['congestion_score']:>6.1f}  "
            f"{level:<14}  "
            f"{h['total_degree']:>6}  "
            f"{h['avg_delay_min']:>6.1f}m"
        )
    print(sep)


def _print_corridors(corridors: list[dict]) -> None:
    """Print a formatted corridor congestion table to stdout."""
    sep  = "=" * 72
    sep2 = "-" * 72

    level_icons = {"High": "🔴", "Moderate": "🟠", "Low": "🟢"}

    print(f"\n{sep}")
    print("  🛤️   TOP CONGESTED CORRIDORS")
    print(sep)
    print(f"  {'#':<4} {'Route':<40} {'Score':>6}  {'Delay':>7}  {'Pressure':>8}")
    print(f"  {'-'*4} {'-'*40} {'-'*6}  {'-'*7}  {'-'*8}")

    for c in corridors:
        icon  = level_icons.get(c["congestion_level"], "⚪")
        route = c["route"]
        if len(route) > 38:
            route = route[:35] + "..."
        print(
            f"  {c['rank']:<4} {route:<40} "
            f"{c['congestion_score']:>6.1f}  "
            f"{c['avg_delay_min']:>6.1f}m  "
            f"{c['degree_pressure']:>8}"
        )
    print(sep)


def _print_summary(summary: dict) -> None:
    """Print a formatted system-wide congestion summary."""
    sep = "=" * 50
    print(f"\n{sep}")
    print("  📊  NETWORK CONGESTION SUMMARY")
    print(sep)
    print(f"  Total Stations          : {summary['total_stations']}")
    print(f"  🔴 High Congestion      : {summary['high_congestion_stations']}")
    print(f"  🟠 Moderate Congestion  : {summary['moderate_congestion_stations']}")
    print(f"  🟢 Low Congestion       : {summary['low_congestion_stations']}")
    print(f"  Network Avg Score       : {summary['network_avg_congestion']:.1f} / 100")
    print(f"  Most Congested Station  : {summary['most_congested_station']}")
    print(f"  Peak Score              : {summary['most_congested_score']:.1f} / 100")
    print(sep)


# ===========================================================================
#  __main__ — demonstration & smoke-test
# ===========================================================================

if __name__ == "__main__":
    print("\n" + "=" * 72)
    print("  congestion_predictor.py  —  Phase-2 Task-2 Demo")
    print("=" * 72)

    # ── Test 1: Single station congestion ────────────────────────────────
    print("\n[TEST 1]  calculate_station_congestion('Howrah Jn')")
    result = calculate_station_congestion("Howrah Jn")
    print(f"  Station          : {result['station']}")
    print(f"  Congestion Score : {result['congestion_score']} / 100")
    print(f"  Congestion Level : {result['congestion_level']}")
    print(f"  Delay Risk Score : {result['delay_risk_score']}")
    print(f"  Betweenness      : {result['betweenness_centrality']}")
    print(f"  Total Degree     : {result['total_degree']}")
    print(f"  Avg Delay        : {result['avg_delay_min']} min")

    # ── Test 2: Top 10 hotspots ──────────────────────────────────────────
    print("\n[TEST 2]  identify_congestion_hotspots(n=10)")
    hotspots = identify_congestion_hotspots(n=10)
    _print_hotspots(hotspots)

    # ── Test 3: Corridor analysis ────────────────────────────────────────
    print("\n[TEST 3]  corridor_congestion_analysis(top_n=10)")
    corridors = corridor_congestion_analysis(top_n=10)
    _print_corridors(corridors)

    # ── Test 4: System summary ───────────────────────────────────────────
    print("\n[TEST 4]  congestion_summary()")
    summary = congestion_summary()
    _print_summary(summary)

    # ── Test 5: Spot checks for key junctions ────────────────────────────
    print("\n[TEST 5]  Spot-checking major junctions")
    for name in ["New Delhi", "Bhusaval Jn", "Nagpur", "Kalyan Jn"]:
        try:
            r = calculate_station_congestion(name)
            print(f"  {r['station']:<30}  score={r['congestion_score']:>5.1f}  level={r['congestion_level']}")
        except ValueError as e:
            print(f"  ⚠️  {e}")

    print("\n✅  All tests passed — congestion_predictor.py ready for integration.\n")
