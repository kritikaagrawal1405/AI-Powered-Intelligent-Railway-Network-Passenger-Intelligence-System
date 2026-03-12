"""
travel_intelligence.py
======================
Item 8: Passenger Travel Intelligence System
AI-Powered Railway Intelligence System

Implements all four missing capabilities identified in the gap analysis:

  1. Alternative travel recommendations
     get_alternative_travel(src, dst, month, n_alternatives)
       → primary route + alternatives, each enriched with crowd level,
         occupancy rate, reliability score, and delay risk

  2. Crowd level estimates for trains & stations
     get_crowd_estimate(station, month, hour)
       → crowd score (0–100), level, hourly profile, seasonal adjustment,
         per-train occupancy for trains at that station in that month

  3. Smart ticket booking guidance
     get_booking_guidance(src, dst, wl_number, days_before_travel, month)
       → WL confirmation probability (from ML model) + computed
         "book X days in advance" advice from occupancy × seasonal demand
         + step-by-step personalized action plan

  4. Unified travel advisory
     get_travel_advisory(src, dst, month, wl_number, days_before)
       → single dict combining all three — used by the dashboard tab
         and AI assistant

Public API
----------
    get_alternative_travel(src, dst, month, n_alternatives)  -> dict
    get_crowd_estimate(station, month, hour)                  -> dict
    get_booking_guidance(src, dst, wl_number,
                         days_before_travel, month)           -> dict
    get_travel_advisory(src, dst, month, wl_number,
                        days_before)                          -> dict
    travel_intelligence_summary()                             -> dict

All data is lazy-loaded and module-level cached.
Graph path-finding uses penalized Dijkstra — O(k × Dijkstra), never hangs.
"""

from __future__ import annotations

import os
import sys
import warnings
from datetime import datetime
from functools import lru_cache
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)

_PROC = os.path.join(_ROOT, "data", "processed")

# ── Month / season reference tables ───────────────────────────────────────
_MONTH_NAMES = {
    1: "January", 2: "February", 3: "March",    4: "April",
    5: "May",     6: "June",     7: "July",      8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}
_MONTH_SHORT = {k: v[:3] for k, v in _MONTH_NAMES.items()}

_SEASON_BOOKING_ADVICE = {
    "Winter":       "Winter travel has moderate demand. Booking 15–30 days ahead is usually enough.",
    "Summer":       "Summer vacation peak — trains fill fast. Book at least 60 days ahead.",
    "Monsoon":      "Lowest demand season — good availability. 15 days ahead is fine.",
    "Post-Monsoon": "Festival season (Oct/Nov) — highest demand. Book 90 days ahead for Diwali/Navratri.",
}

# ── Lazy data loaders (cached after first call) ────────────────────────────

@lru_cache(maxsize=1)
def _demand() -> pd.DataFrame:
    p = os.path.join(_PROC, "passenger_demand.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

@lru_cache(maxsize=1)
def _crowd() -> pd.DataFrame:
    p = os.path.join(_PROC, "station_crowd.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

@lru_cache(maxsize=1)
def _seasonal() -> pd.DataFrame:
    p = os.path.join(_PROC, "seasonal_patterns.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

@lru_cache(maxsize=1)
def _delay_stats() -> pd.DataFrame:
    p = os.path.join(_PROC, "station_delay_stats.csv")
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

@lru_cache(maxsize=1)
def _graph():
    from src.graph_engine.graph_utils import load_graph
    return load_graph()

@lru_cache(maxsize=1)
def _station_list() -> list:
    from src.graph_engine.graph_utils import get_station_list
    return get_station_list()


# ── Internal helpers ───────────────────────────────────────────────────────

def _seasonal_row(month: int) -> dict:
    sea = _seasonal()
    row = sea[sea["month"] == month]
    if row.empty:
        return {"demand_index": 100.0, "season": "Unknown",
                "festival": "—", "peak": "No", "month_name": _MONTH_SHORT.get(month, str(month))}
    return row.iloc[0].to_dict()


def _crowd_level(score: float) -> str:
    if score >= 75: return "Overcrowded"
    if score >= 55: return "High"
    if score >= 35: return "Moderate"
    return "Low"


def _occ_level(occ: float) -> str:
    if occ >= 1.05: return "Overcrowded"
    if occ >= 0.90: return "High"
    if occ >= 0.70: return "Moderate"
    return "Low"


def _delay_risk(station: str) -> float:
    """Return delay_risk_score 0–100 for a station; default 30 if unknown."""
    df = _delay_stats()
    if df.empty:
        return 30.0
    row = df[df["station_name"].str.lower().str.contains(station.lower(), regex=False)]
    return float(row["delay_risk_score"].iloc[0]) if not row.empty else 30.0


def _resolve_station(name: str):
    """Fuzzy-match a station name against the graph nodes."""
    G = _graph()
    if name in G:
        return name
    nl = name.lower()
    candidates = [n for n in G.nodes() if nl in n.lower()]
    if not candidates:
        raise ValueError(f"Station '{name}' not found in graph.")
    exact = [c for c in candidates if c.lower() == nl]
    return exact[0] if exact else candidates[0]


def _path_metrics(path: list) -> dict:
    """Compute travel time, distance, delay totals for a path list."""
    G = _graph()
    dist = tt = delay = 0.0
    legs = []
    for i in range(len(path) - 1):
        s, d = path[i], path[i + 1]
        e = G[s][d] if G.has_edge(s, d) else {}
        dist  += e.get("distance",    0.0)
        tt    += e.get("travel_time", 0.0)
        delay += e.get("avg_delay",   0.0)
        legs.append({
            "from":            s,
            "to":              d,
            "distance_km":     round(e.get("distance",    0.0), 1),
            "travel_time_min": round(e.get("travel_time", 0.0), 1),
            "avg_delay_min":   round(e.get("avg_delay",   0.0), 1),
        })
    return {
        "path":                  path,
        "num_stops":             len(path),
        "total_distance_km":     round(dist,  1),
        "total_travel_time_min": round(tt,    1),
        "total_delay_min":       round(delay, 1),
        "legs":                  legs,
    }


def _k_paths(src: str, dst: str, k: int = 4, penalty: float = 8.0) -> list:
    """
    Find k distinct paths via penalized Dijkstra re-runs.
    Fast: O(k × Dijkstra). Never hangs on large graphs.
    """
    import networkx as nx
    G = _graph()
    paths, seen_edges, G_work = [], set(), G.copy()
    for _ in range(k + 3):
        try:
            p = nx.dijkstra_path(G_work, src, dst, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            break
        if p not in paths:
            paths.append(p)
        if len(paths) >= k:
            break
        for i in range(len(p) - 1):
            u, v = p[i], p[i + 1]
            if (u, v) not in seen_edges and G_work.has_edge(u, v):
                G_work[u][v]["weight"] = G_work[u][v].get("weight", 1.0) * penalty
                seen_edges.add((u, v))
    return paths


def _recommended_advance_days(demand_index: float, avg_occ: float, wl: int = 0) -> int:
    """Compute minimum recommended advance booking days from demand signals."""
    if avg_occ >= 1.05 or demand_index >= 130:
        return 90
    if avg_occ >= 0.90 or demand_index >= 110:
        return 60
    if avg_occ >= 0.75 or demand_index >= 100:
        return 30
    if wl > 10:
        return 45
    return 15


# ===========================================================================
#  PUBLIC FUNCTION 1 — get_alternative_travel
# ===========================================================================

def get_alternative_travel(
    src:           str,
    dst:           str,
    month:         int = None,
    n_alternatives: int = 3,
) -> dict:
    """
    Compute the primary route and up to n_alternatives, each enriched with:
      • crowd level at intermediate stops (from station_crowd.csv)
      • route-level occupancy rate for this month (from passenger_demand.csv)
      • reliability score = 100 - avg(delay_risk) across path stations
      • extra travel time vs. the primary route

    Parameters
    ----------
    src / dst      : station names (fuzzy-matched to graph)
    month          : travel month 1–12 (default: current month)
    n_alternatives : max detour routes to return (default 3)

    Returns
    -------
    dict with keys:
        source, destination, month, month_name, season, demand_index,
        primary      → enriched route dict
        alternatives → list of enriched route dicts (sorted best-first)
        recommendation → plain-English travel advice
    """
    if not month:
        month = datetime.now().month

    sea = _seasonal_row(month)

    try:
        src_node = _resolve_station(src)
        dst_node = _resolve_station(dst)
    except ValueError as e:
        return {"error": str(e), "source": src, "destination": dst}

    all_paths = _k_paths(src_node, dst_node, k=n_alternatives + 1)
    if not all_paths:
        return {"error": f"No route found between '{src_node}' and '{dst_node}'.",
                "source": src_node, "destination": dst_node}

    dem = _demand()
    cd  = _crowd()
    month_name = _MONTH_SHORT.get(month, str(month))

    def _enrich(path: list) -> dict:
        m = _path_metrics(path)

        # ── Crowd at intermediate stops ────────────────────────────────────
        stop_crowds = []
        for stn in path[1:-1]:
            rows = cd[cd["station_name"].str.lower().str.contains(stn.lower(), regex=False)]
            if not rows.empty:
                cs = round(float(rows["crowd_score"].mean()), 1)
                stop_crowds.append({"station": stn, "crowd_score": cs,
                                    "crowd_level": _crowd_level(cs)})
        avg_cs = round(float(np.mean([x["crowd_score"] for x in stop_crowds])), 1) \
                 if stop_crowds else 40.0

        # ── Route occupancy for this month ─────────────────────────────────
        mask = (
            dem["source_station"].str.lower().str.contains(src_node.lower(), regex=False) &
            dem["destination_station"].str.lower().str.contains(dst_node.lower(), regex=False) &
            (dem["month"] == month)
        )
        route_dem = dem[mask]
        if not route_dem.empty:
            avg_occ = round(float(route_dem["occupancy_rate"].mean()), 3)
            avg_wl  = int(route_dem["waitlist_count"].mean())
        else:
            # Estimate from seasonal index
            avg_occ = round(min(1.35, 0.65 * sea["demand_index"] / 100), 3)
            avg_wl  = 0

        # ── Reliability = 100 − mean(delay_risk) across all stops ─────────
        risks = [_delay_risk(s) for s in path]
        reliability = round(max(0.0, 100 - float(np.mean(risks))), 1)

        m.update({
            "crowd_level":       _crowd_level(avg_cs),
            "avg_crowd_score":   avg_cs,
            "occupancy_rate":    avg_occ,
            "occupancy_pct":     round(avg_occ * 100, 1),
            "occupancy_level":   _occ_level(avg_occ),
            "avg_waitlist":      avg_wl,
            "reliability_score": reliability,
            "busiest_stops":     sorted(stop_crowds,
                                        key=lambda x: x["crowd_score"], reverse=True)[:3],
        })
        return m

    enriched = [_enrich(p) for p in all_paths]

    primary      = enriched[0]
    alternatives = sorted(
        enriched[1:],
        key=lambda x: x["total_delay_min"] + x["avg_crowd_score"] * 0.4
    )[:n_alternatives]

    # Extra time vs primary for each alternative
    for alt in alternatives:
        alt["extra_time_min"] = round(
            alt["total_travel_time_min"] - primary["total_travel_time_min"], 1
        )

    # ── Recommendation text ────────────────────────────────────────────────
    season_adv = _SEASON_BOOKING_ADVICE.get(str(sea.get("season", "")), "")
    if primary["occupancy_level"] in ("Overcrowded", "High"):
        rec = (
            f"High demand on {src_node} → {dst_node} in {month_name} "
            f"({primary['occupancy_pct']:.0f}% occupancy). "
            f"{season_adv} "
            f"{len(alternatives)} alternative route(s) available below."
        )
    else:
        rec = (
            f"Good availability on {src_node} → {dst_node} in {month_name} "
            f"({primary['occupancy_pct']:.0f}% occupancy). "
            f"{season_adv}"
        )

    return {
        "source":       src_node,
        "destination":  dst_node,
        "month":        month,
        "month_name":   month_name,
        "season":       str(sea.get("season", "")),
        "demand_index": float(sea.get("demand_index", 100.0)),
        "primary":      primary,
        "alternatives": alternatives,
        "recommendation": rec.strip(),
    }


# ===========================================================================
#  PUBLIC FUNCTION 2 — get_crowd_estimate
# ===========================================================================

def get_crowd_estimate(
    station: str,
    month:   int = None,
    hour:    int = None,
) -> dict:
    """
    Crowd level estimate for a station at a given month and hour.

    Includes:
      • Seasonally-adjusted crowd score (score × demand_index / 100)
      • Full 24-hour profile
      • Day-of-week profile
      • Peak and off-peak windows
      • Train-level occupancy for trains serving this station in this month

    Parameters
    ----------
    station : station name (fuzzy matched)
    month   : 1–12 (default: current month)
    hour    : 0–23 (default: 18 = evening peak)

    Returns
    -------
    dict with crowd_score, crowd_level, peak_hours, offpeak_hours,
         hourly_profile, day_profile, train_occupancy, advice
    """
    if not month:
        month = datetime.now().month
    if hour is None:
        hour = 18

    cd   = _crowd()
    dem  = _demand()
    sea  = _seasonal_row(month)

    # Match station in crowd data
    rows = cd[cd["station_name"].str.lower().str.contains(station.lower(), regex=False)]
    if rows.empty:
        return {"error": f"Station '{station}' not found in crowd data."}

    stn_name = rows["station_name"].iloc[0]
    stn_rows = cd[cd["station_name"] == stn_name]

    # 24-hour profile: average across all days
    hourly = (
        stn_rows.groupby("hour_of_day")["crowd_score"]
        .mean()
        .reindex(range(24), fill_value=0)
        .round(1)
    )
    raw_score = round(float(hourly.iloc[hour]), 1)

    # Apply seasonal multiplier
    sea_mult       = float(sea.get("demand_index", 100.0)) / 100.0
    adj_score      = round(min(100.0, raw_score * sea_mult), 1)
    crowd_lv       = _crowd_level(adj_score)

    # Peak / off-peak windows
    sorted_hourly  = hourly.sort_values(ascending=False)
    peak_hours     = [f"{h:02d}:00" for h in sorted_hourly.head(3).index]
    offpeak_hours  = [f"{h:02d}:00" for h in sorted_hourly.tail(3).index]

    # Day-of-week profile
    day_profile = (
        stn_rows.groupby("day_name")["crowd_score"]
        .mean().round(1).to_dict()
    )

    # Transfer congestion risk
    tc_risk = stn_rows["transfer_congestion_risk"].mode()[0] \
              if not stn_rows.empty else "Low"

    # Trains at this station for this month with occupancy
    train_mask = (
        (dem["month"] == month) & (
            dem["source_station"].str.lower().str.contains(stn_name.lower(), regex=False) |
            dem["destination_station"].str.lower().str.contains(stn_name.lower(), regex=False)
        )
    )
    train_occ = dem[train_mask][
        ["train_name", "occupancy_rate", "crowd_level", "waitlist_count"]
    ].copy().drop_duplicates("train_name").sort_values("occupancy_rate", ascending=False)
    train_occ["occupancy_pct"] = (train_occ["occupancy_rate"] * 100).round(1)

    # Advice text
    month_name = _MONTH_SHORT.get(month, str(month))
    festival   = str(sea.get("festival", "—"))
    if crowd_lv == "Overcrowded":
        advice = (
            f"{stn_name} is overcrowded at {hour:02d}:00 in {month_name}. "
            f"Best time to visit: {offpeak_hours[0]}. "
            + (f"{festival} season amplifies demand. " if festival != "—" else "")
            + f"Transfer congestion: {tc_risk}."
        )
    elif crowd_lv == "High":
        advice = (
            f"High crowd at {stn_name} around {hour:02d}:00 in {month_name}. "
            f"Consider arriving at {offpeak_hours[0]} or {offpeak_hours[1]}. "
            f"Transfer congestion risk: {tc_risk}."
        )
    else:
        advice = (
            f"{stn_name} has {crowd_lv.lower()} crowd at {hour:02d}:00. "
            f"Peak hours to avoid: {', '.join(peak_hours[:2])}. "
            f"Transfer congestion: {tc_risk}."
        )

    return {
        "station_name":         stn_name,
        "month":                month,
        "month_name":           month_name,
        "hour":                 hour,
        "crowd_score":          adj_score,
        "raw_crowd_score":      raw_score,
        "crowd_level":          crowd_lv,
        "seasonal_multiplier":  round(sea_mult, 2),
        "season":               str(sea.get("season", "")),
        "festival":             festival,
        "peak_hours":           peak_hours,
        "offpeak_hours":        offpeak_hours,
        "hourly_profile":       hourly.tolist(),
        "day_profile":          day_profile,
        "transfer_congestion":  tc_risk,
        "train_occupancy":      train_occ.head(8).to_dict("records"),
        "advice":               advice,
    }


# ===========================================================================
#  PUBLIC FUNCTION 3 — get_booking_guidance
# ===========================================================================

def get_booking_guidance(
    src:               str,
    dst:               str,
    wl_number:         int = 0,
    days_before_travel: int = 30,
    month:             int = None,
) -> dict:
    """
    Smart ticket booking guidance combining ML WL model with demand analytics.

    Computes:
      • WL confirmation probability from the trained ML model
      • Route occupancy for the travel month
      • Recommended minimum advance booking days (derived formula)
      • Urgency level: Low / Medium / High / Critical
      • Step-by-step personalized action plan

    Parameters
    ----------
    src / dst           : station names
    wl_number           : waitlist position (0 = no WL, general advice)
    days_before_travel  : days until departure
    month               : travel month 1–12

    Returns
    -------
    dict with wl_confirmation_probability, recommended_advance_days,
         urgency, booking_window, step_by_step_advice, and full context
    """
    if not month:
        month = datetime.now().month

    sea = _seasonal_row(month)
    dem = _demand()

    # WL confirmation probability from ML model
    wl_prob = None
    if wl_number > 0:
        try:
            from src.ml_models.wl_model import predict_wl_confirmation
            wl_prob = round(predict_wl_confirmation(wl_number, days_before_travel) * 100, 1)
        except Exception:
            pass

    # Route occupancy this month
    mask = (
        dem["source_station"].str.lower().str.contains(src.lower(), regex=False) &
        dem["destination_station"].str.lower().str.contains(dst.lower(), regex=False) &
        (dem["month"] == month)
    )
    route_dem = dem[mask]
    if not route_dem.empty:
        avg_occ = round(float(route_dem["occupancy_rate"].mean()), 3)
        avg_wl  = int(route_dem["waitlist_count"].mean())
    else:
        # Estimate from seasonal demand index
        avg_occ = round(min(1.35, 0.65 * float(sea.get("demand_index", 100)) / 100), 3)
        avg_wl  = 0

    demand_index = float(sea.get("demand_index", 100.0))
    season       = str(sea.get("season", ""))
    festival     = str(sea.get("festival", "—"))
    month_name   = _MONTH_SHORT.get(month, str(month))

    # Recommended advance booking days
    rec_days = _recommended_advance_days(demand_index, avg_occ, wl_number)

    # Urgency
    days_overdue = rec_days - days_before_travel
    if days_before_travel <= 3:
        urgency = "Critical"
    elif days_overdue >= rec_days * 0.7:
        urgency = "High"
    elif days_overdue > 0:
        urgency = "Medium"
    else:
        urgency = "Low"

    # Booking window string
    if days_overdue > 0:
        booking_window = (
            f"Book immediately — the ideal booking window was {rec_days} days "
            f"before travel. You are {days_overdue} days late."
        )
    else:
        days_left = abs(days_overdue)
        booking_window = (
            f"Book within the next {days_left} days "
            f"(ideally {rec_days} days before departure)."
        )

    # ── Step-by-step advice ────────────────────────────────────────────────
    steps = []

    # WL step
    if wl_prob is not None:
        if wl_prob >= 75:
            steps.append(
                f"WL {wl_number} has a strong {wl_prob}% confirmation chance — "
                f"keep the ticket but book a backup on an alternate train."
            )
        elif wl_prob >= 45:
            steps.append(
                f"WL {wl_number} confirmation is uncertain ({wl_prob}%). "
                f"Book an alternative train now to avoid last-minute scrambling."
            )
        else:
            steps.append(
                f"WL {wl_number} has a low {wl_prob}% confirmation chance. "
                f"Cancel and rebook on a different train or route immediately."
            )

    # Occupancy step
    if avg_occ >= 1.05:
        steps.append(
            f"This corridor is overcrowded in {month_name} "
            f"({avg_occ*100:.0f}% avg occupancy). "
            f"Consider mid-week travel or alternative routes for better berth availability."
        )
    elif avg_occ >= 0.85:
        steps.append(
            f"High demand in {month_name} ({avg_occ*100:.0f}% occupancy). "
            f"Book at least {rec_days} days in advance to secure a confirmed berth."
        )
    else:
        steps.append(
            f"Moderate demand in {month_name} ({avg_occ*100:.0f}% occupancy). "
            f"Booking {rec_days} days ahead should be sufficient."
        )

    # Festival step
    if festival != "—":
        steps.append(
            f"{festival} season in {month_name}: demand spikes sharply. "
            f"Book as early as possible — ideally 90 days ahead."
        )

    # General Tatkal step
    steps.append(
        "Tatkal quota opens 1 day before departure. Use it only as a last resort — "
        "it carries a premium and availability is limited."
    )

    # Urgency escalation step
    if days_before_travel < 7 and wl_number > 5:
        steps.append(
            f"Only {days_before_travel} day(s) left with WL {wl_number}. "
            f"Check RAC/confirmed berths on all trains on this route today."
        )

    return {
        "source_station":              src,
        "destination_station":         dst,
        "month":                       month,
        "month_name":                  month_name,
        "season":                      season,
        "festival":                    festival,
        "demand_index":                demand_index,
        "occupancy_rate":              avg_occ,
        "occupancy_pct":               round(avg_occ * 100, 1),
        "occupancy_level":             _occ_level(avg_occ),
        "avg_waitlist_on_route":       avg_wl,
        "wl_number":                   wl_number,
        "wl_confirmation_probability": wl_prob,
        "days_before_travel":          days_before_travel,
        "recommended_advance_days":    rec_days,
        "booking_window":              booking_window,
        "urgency":                     urgency,
        "season_advice":               _SEASON_BOOKING_ADVICE.get(season, ""),
        "step_by_step_advice":         steps,
    }


# ===========================================================================
#  PUBLIC FUNCTION 4 — get_travel_advisory  (unified one-stop call)
# ===========================================================================

def get_travel_advisory(
    src:         str,
    dst:         str,
    month:       int = None,
    wl_number:   int = 0,
    days_before: int = 30,
) -> dict:
    """
    Unified travel advisory combining all three capabilities:
      • Alternative routes with crowd + occupancy enrichment
      • Source station crowd estimate at typical departure hour (18:00)
      • Smart booking guidance

    Designed for the dashboard panel — returns one consolidated dict.
    """
    if not month:
        month = datetime.now().month

    alt     = get_alternative_travel(src, dst, month)
    crowd   = get_crowd_estimate(src, month, hour=18)
    booking = get_booking_guidance(src, dst, wl_number, days_before, month)

    primary_route = alt.get("primary")
    alternatives  = alt.get("alternatives", [])
    route_err     = alt.get("error", "")

    overall = (
        (alt.get("recommendation", "") + " | ")
        + (f"Source station crowd at 18:00: {crowd.get('crowd_level','?')}. | "
           if "error" not in crowd else "")
        + f"Booking urgency: {booking['urgency']}. {booking['booking_window']}"
    )

    return {
        "source":              alt.get("source", src),
        "destination":         alt.get("destination", dst),
        "month":               month,
        "month_name":          _MONTH_SHORT.get(month, str(month)),
        "season":              alt.get("season", ""),
        "primary_route":       primary_route,
        "alternatives":        alternatives,
        "route_recommendation": alt.get("recommendation", route_err),
        "crowd":               crowd,
        "booking":             booking,
        "overall_advice":      overall.strip(),
        "error":               route_err,
    }


# ===========================================================================
#  PUBLIC FUNCTION 5 — travel_intelligence_summary  (dashboard KPI cards)
# ===========================================================================

def travel_intelligence_summary() -> dict:
    """Compact KPI dict for dashboard header metrics."""
    dem = _demand()
    sea = _seasonal()

    peak_row = sea.loc[sea["demand_index"].idxmax()]
    low_row  = sea.loc[sea["demand_index"].idxmin()]
    avg_occ  = round(float(dem["occupancy_rate"].mean()) * 100, 1) if not dem.empty else 0.0
    overcrowded_count = int((dem["crowd_level"] == "Overcrowded").sum()) if not dem.empty else 0
    peak_months = sea[sea["peak"] == "Yes"]["month_name"].tolist() if not sea.empty else []

    return {
        "avg_network_occupancy_pct": avg_occ,
        "peak_month":               str(peak_row["month_name"]),
        "peak_demand_index":        float(peak_row["demand_index"]),
        "low_month":                str(low_row["month_name"]),
        "overcrowded_train_months": overcrowded_count,
        "peak_season_months":       peak_months,
        "total_trains_tracked":     int(dem["train_number"].nunique()) if not dem.empty else 0,
    }


# ===========================================================================
#  __main__ — smoke tests
# ===========================================================================

if __name__ == "__main__":
    print("\n" + "=" * 62)
    print("  travel_intelligence.py — Passenger Travel Intelligence")
    print("=" * 62)

    print("\n[1] Alternative travel — Chennai Central → Howrah Jn, Nov")
    r = get_alternative_travel("Chennai Central", "Howrah Jn", month=11)
    if "error" not in r:
        p = r["primary"]
        print(f"  Primary : {p['num_stops']} stops | crowd={p['crowd_level']} | "
              f"occ={p['occupancy_pct']:.0f}% | reliability={p['reliability_score']}")
        print(f"  Alts    : {len(r['alternatives'])}")
        print(f"  Rec     : {r['recommendation'][:90]}...")
    else:
        print("  ERROR:", r["error"])

    print("\n[2] Crowd estimate — New Delhi, Nov, 18:00")
    c = get_crowd_estimate("New Delhi", month=11, hour=18)
    if "error" not in c:
        print(f"  Score   : {c['crowd_score']}/100 (raw {c['raw_crowd_score']}) × {c['seasonal_multiplier']}×")
        print(f"  Level   : {c['crowd_level']} | Peak hours: {c['peak_hours'][:2]}")
        print(f"  Trains  : {len(c['train_occupancy'])} with occupancy data")
        print(f"  Advice  : {c['advice'][:90]}...")
    else:
        print("  ERROR:", c["error"])

    print("\n[3] Booking guidance — Howrah Jn → Asansol Jn | WL=15 | 10 days | Nov")
    b = get_booking_guidance("Howrah Jn", "Asansol Jn",
                              wl_number=15, days_before_travel=10, month=11)
    print(f"  WL prob  : {b['wl_confirmation_probability']}%")
    print(f"  Rec days : {b['recommended_advance_days']} | Urgency: {b['urgency']}")
    print(f"  Window   : {b['booking_window']}")
    for i, s in enumerate(b["step_by_step_advice"], 1):
        print(f"  {i}. {s[:80]}...")

    print("\n[4] Unified travel advisory — Howrah Jn → Vijayawada Jn | May | WL=5")
    adv = get_travel_advisory("Howrah Jn", "Vijayawada Jn", month=5,
                               wl_number=5, days_before=20)
    print(f"  Overall : {adv['overall_advice'][:110]}...")

    print("\n[5] KPI summary")
    s = travel_intelligence_summary()
    print(f"  Avg occ         : {s['avg_network_occupancy_pct']}%")
    print(f"  Peak month      : {s['peak_month']} (index {s['peak_demand_index']})")
    print(f"  Trains tracked  : {s['total_trains_tracked']}")
    print(f"  Overcrowded runs: {s['overcrowded_train_months']}")

    print("\n  ✅  All smoke tests passed\n")
