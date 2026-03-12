"""
passenger_flow.py
=================
Phase-4: Passenger Flow Modeling & Crowd Intelligence
AI-Powered Railway Intelligence System

Analyses passenger demand, crowding, seasonal patterns, and transfer
congestion using the generated demand datasets alongside existing
graph/delay data.

Public API
----------
    get_network_demand_summary()         -> dict
    get_busiest_stations(n)              -> pd.DataFrame
    get_station_crowd_profile(station)   -> dict
    get_peak_hours(station)              -> dict
    get_seasonal_demand()                -> pd.DataFrame
    get_route_demand(src, dst)           -> dict
    get_transfer_congestion_stations(n)  -> pd.DataFrame
    get_overcrowded_routes(month)        -> pd.DataFrame
    passenger_flow_summary()             -> dict   ← dashboard-ready

All functions lazy-load and cache data on first call.
"""

from __future__ import annotations

import os
import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_PROC = os.path.join(_ROOT, "data", "processed")


# ── Data loaders (cached) ─────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _demand() -> pd.DataFrame:
    return pd.read_csv(os.path.join(_PROC, "passenger_demand.csv"))

@lru_cache(maxsize=1)
def _crowd() -> pd.DataFrame:
    return pd.read_csv(os.path.join(_PROC, "station_crowd.csv"))

@lru_cache(maxsize=1)
def _seasonal() -> pd.DataFrame:
    return pd.read_csv(os.path.join(_PROC, "seasonal_patterns.csv"))

@lru_cache(maxsize=1)
def _importance() -> pd.DataFrame:
    return pd.read_csv(os.path.join(_PROC, "station_importance.csv"))


# ===========================================================================
#  FUNCTION 1 — get_network_demand_summary
# ===========================================================================

def get_network_demand_summary() -> dict:
    """
    High-level passenger flow summary across the full network.

    Returns
    -------
    dict
        total_annual_passengers, avg_occupancy, peak_month,
        peak_month_index, low_month, overcrowded_routes_count,
        high_demand_routes_count, network_avg_crowd_score, summary
    """
    df  = _demand()
    sea = _seasonal()

    total       = int(df["estimated_passengers"].sum())
    avg_occ     = round(df["occupancy_rate"].mean(), 3)
    peak_row    = sea.loc[sea["demand_index"].idxmax()]
    low_row     = sea.loc[sea["demand_index"].idxmin()]
    overcrowded = int((df["crowd_level"] == "Overcrowded").sum())
    high        = int((df["crowd_level"] == "High").sum())

    cd = _crowd()
    avg_crowd = round(cd["crowd_score"].mean(), 1)

    return {
        "total_annual_passengers":  total,
        "avg_occupancy_rate":       avg_occ,
        "peak_month":               peak_row["month_name"],
        "peak_month_index":         round(peak_row["demand_index"], 1),
        "low_month":                low_row["month_name"],
        "overcrowded_routes_count": overcrowded,
        "high_demand_routes_count": high,
        "network_avg_crowd_score":  avg_crowd,
        "summary": (
            f"Network carries ~{total:,} estimated annual passengers. "
            f"Average occupancy {avg_occ*100:.0f}%. "
            f"Peak demand in {peak_row['month_name']} "
            f"({peak_row['festival']}). "
            f"{overcrowded} train-month combinations are overcrowded."
        )
    }


# ===========================================================================
#  FUNCTION 2 — get_busiest_stations
# ===========================================================================

def get_busiest_stations(n: int = 10) -> pd.DataFrame:
    """
    Return the N busiest stations ranked by average crowd score.

    Returns
    -------
    pd.DataFrame  [rank, station_name, avg_crowd_score, crowd_level,
                   peak_hour, num_trains, transfer_congestion_risk]
    """
    cd  = _crowd()
    imp = _importance()

    agg = (
        cd.groupby("station_name")
          .agg(
              avg_crowd_score=("crowd_score", "mean"),
              max_crowd_score=("crowd_score", "max"),
              num_trains     =("num_trains",  "first"),
          )
          .reset_index()
    )

    # Peak hour per station
    peak_h = (
        cd.groupby(["station_name","hour_of_day"])["crowd_score"]
          .mean().reset_index()
          .sort_values("crowd_score", ascending=False)
          .drop_duplicates("station_name")[["station_name","hour_of_day"]]
          .rename(columns={"hour_of_day":"peak_hour"})
    )
    agg = agg.merge(peak_h, on="station_name", how="left")

    # Transfer congestion mode
    tc = (
        cd.groupby("station_name")["transfer_congestion_risk"]
          .agg(lambda x: x.value_counts().index[0])
          .reset_index()
    )
    agg = agg.merge(tc, on="station_name", how="left")

    agg = agg.merge(imp[["station_name","betweenness_centrality"]], on="station_name", how="left")
    agg = agg.sort_values("avg_crowd_score", ascending=False).head(n).reset_index(drop=True)
    agg.insert(0, "rank", range(1, len(agg)+1))

    def _cl(s): return "Overcrowded" if s>=75 else "High" if s>=55 else "Moderate" if s>=35 else "Low"
    agg["crowd_level"] = agg["avg_crowd_score"].apply(_cl)
    agg["avg_crowd_score"] = agg["avg_crowd_score"].round(1)
    agg["peak_hour"] = agg["peak_hour"].apply(lambda h: f"{int(h):02d}:00")

    return agg[["rank","station_name","avg_crowd_score","crowd_level",
                "peak_hour","num_trains","transfer_congestion_risk"]]


# ===========================================================================
#  FUNCTION 3 — get_station_crowd_profile
# ===========================================================================

def get_station_crowd_profile(station: str) -> dict:
    """
    Full crowd profile for a single station: hourly curves + weekday patterns.

    Parameters
    ----------
    station : str  — exact or partial station name (case-insensitive)

    Returns
    -------
    dict  with keys:
        station_name, num_trains, avg_crowd_score, peak_hour,
        hourly_profile (list of 24 scores),
        weekday_profile (dict: Mon–Sun → avg score),
        crowd_level, transfer_congestion_risk,
        busiest_day, quietest_slot
    """
    cd = _crowd()

    # Fuzzy match
    matches = cd[cd["station_name"].str.lower().str.contains(station.lower(), regex=False)]
    if matches.empty:
        return {"error": f"Station '{station}' not found in crowd data."}

    stn_name  = matches["station_name"].iloc[0]
    stn_data  = cd[cd["station_name"] == stn_name]

    hourly = (
        stn_data.groupby("hour_of_day")["crowd_score"].mean()
        .reindex(range(24), fill_value=0).round(1).tolist()
    )
    weekday = (
        stn_data.groupby("day_name")["crowd_score"].mean()
        .round(1).to_dict()
    )

    peak_h   = int(stn_data.groupby("hour_of_day")["crowd_score"].mean().idxmax())
    avg_cs   = round(stn_data["crowd_score"].mean(), 1)
    ntrain   = int(stn_data["num_trains"].iloc[0])
    tc_risk  = stn_data["transfer_congestion_risk"].mode()[0]
    quiet_h  = int(stn_data.groupby("hour_of_day")["crowd_score"].mean().idxmin())
    busy_day = stn_data.groupby("day_name")["crowd_score"].mean().idxmax()

    def _cl(s): return "Overcrowded" if s>=75 else "High" if s>=55 else "Moderate" if s>=35 else "Low"

    return {
        "station_name":            stn_name,
        "num_trains":              ntrain,
        "avg_crowd_score":         avg_cs,
        "crowd_level":             _cl(avg_cs),
        "peak_hour":               f"{peak_h:02d}:00",
        "quietest_hour":           f"{quiet_h:02d}:00",
        "busiest_day":             busy_day,
        "hourly_profile":          hourly,
        "weekday_profile":         weekday,
        "transfer_congestion_risk": tc_risk,
    }


# ===========================================================================
#  FUNCTION 4 — get_peak_hours
# ===========================================================================

def get_peak_hours(station: str) -> dict:
    """
    Return the top-3 peak and off-peak hour windows for a station.
    """
    cd = _crowd()
    matches = cd[cd["station_name"].str.lower().str.contains(station.lower(), regex=False)]
    if matches.empty:
        return {"error": f"Station '{station}' not found."}

    stn_name = matches["station_name"].iloc[0]
    hourly   = (
        cd[cd["station_name"] == stn_name]
        .groupby("hour_of_day")["crowd_score"].mean()
        .sort_values(ascending=False)
    )

    peak_hours    = [f"{h:02d}:00" for h in hourly.head(4).index.tolist()]
    offpeak_hours = [f"{h:02d}:00" for h in hourly.tail(4).index.tolist()]

    return {
        "station_name": stn_name,
        "peak_hours":   peak_hours,
        "offpeak_hours": offpeak_hours,
        "peak_score":   round(hourly.max(), 1),
        "offpeak_score": round(hourly.min(), 1),
        "advice": (
            f"Best time to travel through {stn_name}: {offpeak_hours[0]}–{offpeak_hours[-1]}. "
            f"Avoid {peak_hours[0]}–{peak_hours[-1]} for minimum crowding."
        )
    }


# ===========================================================================
#  FUNCTION 5 — get_seasonal_demand
# ===========================================================================

def get_seasonal_demand() -> pd.DataFrame:
    """
    Return the 12-month seasonal demand index for the full network.

    Returns
    -------
    pd.DataFrame  [month, month_name, demand_index, season, peak, festival]
    """
    return _seasonal().copy()


# ===========================================================================
#  FUNCTION 6 — get_route_demand
# ===========================================================================

def get_route_demand(src: str, dst: str) -> dict:
    """
    Demand profile for a source→destination pair across all months.

    Strategy
    --------
    1. Try exact direct-route match in passenger_demand.csv
    2. If no direct route, estimate from the two stations' individual
       crowd profiles + network seasonal index (works for ANY station pair)

    Parameters
    ----------
    src, dst : str  — station names (partial match OK)

    Returns
    -------
    dict  with monthly_demand, peak_month, avg_occupancy, crowd_level, advice
    """
    df  = _demand()
    cd  = _crowd()
    imp = _importance()
    sea = _seasonal()

    # ── resolve station names via fuzzy match ─────────────────────────────
    def _resolve_station_demand(name: str, col: str):
        """Return rows from demand df matching name in given column."""
        return df[df[col].str.lower().str.contains(name.lower(), regex=False)]

    def _resolve_station_crowd(name: str):
        """Return crowd rows for a station."""
        return cd[cd["station_name"].str.lower().str.contains(name.lower(), regex=False)]

    def _resolve_station_imp(name: str):
        return imp[imp["station_name"].str.lower().str.contains(name.lower(), regex=False)]

    src_direct = _resolve_station_demand(src, "source_station")
    if src_direct.empty:
        # Try crowd data to at least verify the station exists
        src_crowd = _resolve_station_crowd(src)
        if src_crowd.empty:
            return {"error": f"Station '{src}' not found in network data."}

    dst_direct = _resolve_station_demand(dst, "destination_station")

    # ── Path 1: direct route exists ───────────────────────────────────────
    if not src_direct.empty:
        route = src_direct[
            src_direct["destination_station"].str.lower()
            .str.contains(dst.lower(), regex=False)
        ]
        if not route.empty:
            trains  = route[["train_number","train_name"]].drop_duplicates().to_dict("records")
            monthly = route.groupby("month").agg(
                avg_occupancy    =("occupancy_rate","mean"),
                total_passengers =("estimated_passengers","sum"),
                avg_waitlist     =("waitlist_count","mean"),
            ).round(3).reset_index()
            peak_row = monthly.loc[monthly["avg_occupancy"].idxmax()]
            avg_occ  = round(route["occupancy_rate"].mean(), 3)
            src_name = src_direct["source_station"].iloc[0]
            dst_name = route["destination_station"].iloc[0]

            return {
                "source_station":      src_name,
                "destination_station": dst_name,
                "estimation_method":   "direct",
                "trains":              trains,
                "monthly_demand":      monthly.to_dict("records"),
                "peak_month":          int(peak_row["month"]),
                "peak_occupancy":      round(peak_row["avg_occupancy"], 3),
                "avg_occupancy":       avg_occ,
                "crowd_level":  "High" if avg_occ > 0.85 else "Moderate" if avg_occ > 0.65 else "Low",
                "advice": (
                    f"Book early for {src_name}→{dst_name}. "
                    f"Peak demand in month {int(peak_row['month'])} — "
                    f"book at least 60 days ahead."
                    if avg_occ > 0.85 else
                    f"{src_name}→{dst_name} has moderate demand. "
                    f"15–30 days advance booking is usually sufficient."
                ),
            }

    # ── Path 2: no direct route — estimate from station crowd profiles ────
    # Resolve display names
    src_cd = _resolve_station_crowd(src)
    dst_cd = _resolve_station_crowd(dst)

    src_name = src_cd["station_name"].iloc[0] if not src_cd.empty else src.title()
    dst_name = dst_cd["station_name"].iloc[0] if not dst_cd.empty else dst.title()

    # Base occupancy = average of the two stations' crowd scores (normalised to 0–1)
    src_score = src_cd["crowd_score"].mean() / 100 if not src_cd.empty else 0.55
    dst_score = dst_cd["crowd_score"].mean() / 100 if not dst_cd.empty else 0.55
    base_occ  = round((src_score + dst_score) / 2, 3)

    # Build monthly demand by applying the network seasonal index
    MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    sea_idx = {r["month"]: r["demand_index"] / 100 for _, r in sea.iterrows()}

    # Estimate capacity from importance (higher degree → more trains → more capacity)
    src_imp_row = _resolve_station_imp(src)
    dst_imp_row = _resolve_station_imp(dst)
    avg_degree  = 0
    if not src_imp_row.empty: avg_degree += src_imp_row["total_degree"].iloc[0]
    if not dst_imp_row.empty: avg_degree += dst_imp_row["total_degree"].iloc[0]
    avg_degree  = max(1, avg_degree / 2)
    est_capacity = int(800 + avg_degree * 50)   # rough seats estimate

    monthly = []
    for m in range(1, 13):
        occ  = round(min(1.35, base_occ * sea_idx.get(m, 1.0)), 3)
        pax  = int(est_capacity * occ)
        wl   = max(0, int((occ - 1.0) * est_capacity * 0.6)) if occ > 1.0 else 0
        monthly.append({
            "month": m,
            "month_name": MONTH_NAMES[m],
            "avg_occupancy": occ,
            "total_passengers": pax,
            "avg_waitlist": wl,
        })

    monthly_df  = sorted(monthly, key=lambda x: x["avg_occupancy"], reverse=True)
    peak_row    = monthly_df[0]
    avg_occ     = round(sum(r["avg_occupancy"] for r in monthly) / 12, 3)

    def _cl(o): return "High" if o > 0.85 else "Moderate" if o > 0.65 else "Low"

    return {
        "source_station":      src_name,
        "destination_station": dst_name,
        "estimation_method":   "estimated",   # tells the UI to show a note
        "trains":              [],
        "monthly_demand":      monthly,
        "peak_month":          peak_row["month"],
        "peak_occupancy":      peak_row["avg_occupancy"],
        "avg_occupancy":       avg_occ,
        "crowd_level":         _cl(avg_occ),
        "advice": (
            f"No direct train data found for {src_name}→{dst_name}. "
            f"Demand is estimated from station crowd profiles and seasonal patterns. "
            f"Peak travel expected in {peak_row['month_name']} — book well in advance."
        ),
    }


# ===========================================================================
#  FUNCTION 7 — get_transfer_congestion_stations
# ===========================================================================

def get_transfer_congestion_stations(n: int = 10) -> pd.DataFrame:
    """
    Stations with the highest transfer congestion risk during peak hours.

    Returns
    -------
    pd.DataFrame  [rank, station_name, transfer_congestion_risk,
                   peak_crowd_score, num_trains, betweenness_centrality]
    """
    cd  = _crowd()
    imp = _importance()

    # Only peak hours (7–10, 17–21)
    peak = cd[cd["peak_slot"] == "Yes"]
    agg  = (
        peak.groupby("station_name")
            .agg(
                peak_crowd_score=("crowd_score","mean"),
                transfer_congestion_risk=("transfer_congestion_risk",
                                          lambda x: x.value_counts().index[0]),
                num_trains=("num_trains","first"),
            ).reset_index()
    )
    agg = agg.merge(imp[["station_name","betweenness_centrality"]], on="station_name", how="left")
    high = agg[agg["transfer_congestion_risk"] == "High"].copy()
    high = high.sort_values("peak_crowd_score", ascending=False).head(n).reset_index(drop=True)
    high.insert(0, "rank", range(1, len(high)+1))
    high["peak_crowd_score"] = high["peak_crowd_score"].round(1)
    high["betweenness_centrality"] = high["betweenness_centrality"].round(4)
    return high[["rank","station_name","transfer_congestion_risk",
                 "peak_crowd_score","num_trains","betweenness_centrality"]]


# ===========================================================================
#  FUNCTION 8 — get_overcrowded_routes
# ===========================================================================

def get_overcrowded_routes(month: int = 11) -> pd.DataFrame:
    """
    Return routes that are overcrowded in a given month.

    Parameters
    ----------
    month : int  (1–12, default 11 = November/Diwali)

    Returns
    -------
    pd.DataFrame  sorted by occupancy descending
    """
    df = _demand()
    month_df = df[df["month"] == month].copy()
    oc = month_df[month_df["crowd_level"].isin(["Overcrowded","High"])].copy()
    oc = oc.sort_values("occupancy_rate", ascending=False).reset_index(drop=True)
    oc.insert(0, "rank", range(1, len(oc)+1))
    oc["occupancy_pct"] = (oc["occupancy_rate"] * 100).round(1).astype(str) + "%"
    return oc[["rank","train_name","source_station","destination_station",
               "occupancy_pct","estimated_passengers","waitlist_count","crowd_level"]]


# ===========================================================================
#  FUNCTION 9 — passenger_flow_summary  (dashboard-ready)
# ===========================================================================

def passenger_flow_summary() -> dict:
    """
    Compact summary dict for the dashboard overview cards.

    Returns
    -------
    dict with all KPIs needed for the dashboard header metrics.
    """
    summary   = get_network_demand_summary()
    busiest   = get_busiest_stations(5)
    transfer  = get_transfer_congestion_stations(5)
    seasonal  = get_seasonal_demand()

    peak_season = seasonal[seasonal["peak"] == "Yes"]["season"].mode()[0]

    return {
        "total_annual_passengers":   summary["total_annual_passengers"],
        "avg_occupancy_pct":         round(summary["avg_occupancy_rate"] * 100, 1),
        "peak_month":                summary["peak_month"],
        "low_month":                 summary["low_month"],
        "overcrowded_routes":        summary["overcrowded_routes_count"],
        "peak_season":               peak_season,
        "busiest_stations":          busiest["station_name"].tolist(),
        "top_transfer_hotspot":      transfer["station_name"].iloc[0] if len(transfer) else "N/A",
        "high_transfer_risk_count":  len(transfer),
        "network_avg_crowd_score":   summary["network_avg_crowd_score"],
    }


# ===========================================================================
#  __main__ — smoke tests
# ===========================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  passenger_flow.py — Crowd Intelligence Engine")
    print("="*60)

    s = passenger_flow_summary()
    print(f"\n  Total passengers  : {s['total_annual_passengers']:,}")
    print(f"  Avg occupancy     : {s['avg_occupancy_pct']}%")
    print(f"  Peak month        : {s['peak_month']}")
    print(f"  Overcrowded routes: {s['overcrowded_routes']}")
    print(f"  Top transfer spot : {s['top_transfer_hotspot']}")

    print("\n  Top 5 busiest stations:")
    print(get_busiest_stations(5)[["rank","station_name","avg_crowd_score","crowd_level"]].to_string(index=False))

    print("\n  Station crowd profile (New Delhi):")
    p = get_station_crowd_profile("New Delhi")
    print(f"    Peak hour: {p['peak_hour']} | Crowd level: {p['crowd_level']} | Transfer risk: {p['transfer_congestion_risk']}")

    print("\n  ✅  passenger_flow.py ready\n")
