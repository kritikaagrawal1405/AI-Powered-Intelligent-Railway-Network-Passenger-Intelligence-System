"""
generate_passenger_data.py
==========================
Generates a realistic synthetic passenger demand dataset by combining:
  - station_importance.csv  (degree/centrality → capacity proxy)
  - station_delay_stats.csv (num_trains → route frequency proxy)
  - routes.csv              (edges → route pairs)
  - schedule_features.csv   (train types → coach/capacity)
  - Known Indian Railway seasonal patterns (holidays, festivals)

Run once to produce:
  data/processed/passenger_demand.csv
  data/processed/station_crowd.csv

Usage:
    cd railway-intelligence-system-v3
    python src/passenger_flow/generate_passenger_data.py
"""

import os, sys
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)

PROC = os.path.join(_ROOT, "data", "processed")
RAW  = os.path.join(_ROOT, "data", "raw")
np.random.seed(42)

# ── Train-type capacity map (seats per rake, approximate) ─────────────────
TRAIN_TYPE_CAPACITY = {
    "rajdhani":  1200,
    "shatabdi":   850,
    "vande bharat": 1128,
    "duronto":   1100,
    "superfast":  1500,
    "express":    1800,
    "passenger":  1200,
    "local":      3000,
    "memu":       1400,
    "demu":       1000,
    "default":    1500,
}

# ── Seasonal demand multipliers (month → factor) ──────────────────────────
# Based on Indian holiday calendar: Diwali(Oct/Nov), Summer(May), Holi(Mar)
SEASONAL = {
    1: 1.05,  # Jan — winter travel
    2: 0.90,  # Feb — low season
    3: 1.25,  # Mar — Holi peak
    4: 1.10,  # Apr — school trips
    5: 1.40,  # May — summer vacation peak
    6: 0.85,  # Jun — monsoon low
    7: 0.80,  # Jul — monsoon low
    8: 0.90,  # Aug — Independence Day bump
    9: 1.00,  # Sep — baseline
    10: 1.30, # Oct — Navratri/Dussehra
    11: 1.45, # Nov — Diwali peak (highest)
    12: 1.20, # Dec — Christmas/New Year
}

# ── Day-of-week multipliers ────────────────────────────────────────────────
DOW = {0: 1.10, 1: 0.90, 2: 0.85, 3: 0.88, 4: 1.05, 5: 1.30, 6: 1.35}
# Mon Tue Wed Thu Fri Sat Sun

# ── Hour-of-day demand curve (departure hour → load factor) ───────────────
HOUR_DEMAND = {
    0:0.55, 1:0.50, 2:0.48, 3:0.50, 4:0.55, 5:0.70,
    6:0.85, 7:0.95, 8:0.90, 9:0.80, 10:0.75, 11:0.78,
    12:0.82, 13:0.80, 14:0.78, 15:0.82, 16:0.88, 17:0.95,
    18:1.00, 19:1.00, 20:0.98, 21:0.92, 22:0.80, 23:0.65,
}


def _train_capacity(train_name: str, coaches: int = 18) -> int:
    name = str(train_name).lower()
    for key, cap in TRAIN_TYPE_CAPACITY.items():
        if key in name:
            return int(cap * coaches / 18)
    return int(TRAIN_TYPE_CAPACITY["default"] * coaches / 18)


def _crowd_level(occupancy: float) -> str:
    if occupancy >= 1.05:  return "Overcrowded"
    if occupancy >= 0.90:  return "High"
    if occupancy >= 0.70:  return "Moderate"
    return "Low"


def build_passenger_demand() -> pd.DataFrame:
    """
    Build route-level passenger demand dataset.
    One row = one train × one month, with demand, capacity, occupancy.
    """
    routes   = pd.read_csv(os.path.join(PROC, "routes.csv"))
    sched    = pd.read_csv(os.path.join(PROC, "schedule_features.csv"))
    imp      = pd.read_csv(os.path.join(PROC, "station_importance.csv"))

    # Map station importance score (betweenness → popularity multiplier)
    imp["pop_score"] = (imp["betweenness_centrality"] * 5 +
                        imp["total_degree"] / imp["total_degree"].max() * 3 +
                        (1 - imp["delay_risk_score"] / 100) * 2)
    imp["pop_score"] = imp["pop_score"].clip(1, 10)
    pop_map = dict(zip(imp["station_name"], imp["pop_score"]))

    # Unique trains
    trains = routes[["train_number","train_name","source_station","destination_station"]].drop_duplicates("train_number")

    # Train type from schedule_features
    type_map = {}
    for _, row in sched[["train_number","train_name"]].drop_duplicates("train_number").iterrows():
        type_map[row["train_number"]] = row["train_name"]

    records = []
    for _, t in trains.iterrows():
        tnum  = t["train_number"]
        tname = str(t["train_name"])
        src   = t["source_station"]
        dst   = t["destination_station"]
        cap   = _train_capacity(tname)

        src_pop = pop_map.get(src, 3.0)
        dst_pop = pop_map.get(dst, 3.0)
        base_load = min(0.95, 0.45 + (src_pop + dst_pop) / 20)

        for month in range(1, 13):
            season_mult = SEASONAL[month]
            # Add a small per-train random effect (fixed by seed for reproducibility)
            rng_seed = int(tnum) % 1000 + month
            rng = np.random.RandomState(rng_seed)
            noise = rng.uniform(0.92, 1.08)

            occupancy = base_load * season_mult * noise
            occupancy = round(np.clip(occupancy, 0.20, 1.35), 3)
            passengers = int(cap * occupancy)
            waitlist   = max(0, int((occupancy - 1.0) * cap * 0.6)) if occupancy > 1.0 else 0

            records.append({
                "train_number":     tnum,
                "train_name":       tname,
                "source_station":   src,
                "destination_station": dst,
                "capacity":         cap,
                "month":            month,
                "season":           _month_to_season(month),
                "demand_multiplier": round(season_mult, 2),
                "estimated_passengers": passengers,
                "occupancy_rate":   occupancy,
                "waitlist_count":   waitlist,
                "crowd_level":      _crowd_level(occupancy),
            })

    df = pd.DataFrame(records)
    out = os.path.join(PROC, "passenger_demand.csv")
    df.to_csv(out, index=False)
    print(f"  ✅ passenger_demand.csv  →  {len(df):,} rows")
    return df


def build_station_crowd() -> pd.DataFrame:
    """
    Build station-level crowd profile.
    One row = one station × one hour-of-day × one day-of-week.
    Crowd score derived from: train frequency × time-slot demand × centrality.
    """
    imp   = pd.read_csv(os.path.join(PROC, "station_importance.csv"))
    stats = pd.read_csv(os.path.join(PROC, "station_delay_stats.csv"))

    merged = imp.merge(
        stats[["station_name","num_trains","avg_delay_min","delay_risk_score"]],
        on="station_name", how="left", suffixes=("","_stats")
    )
    merged["num_trains"]  = merged["num_trains"].fillna(2)
    merged["base_crowd"]  = (
        merged["num_trains"] / merged["num_trains"].max() * 50 +
        merged["betweenness_centrality"] / merged["betweenness_centrality"].max() * 30 +
        merged["total_degree"] / merged["total_degree"].max() * 20
    ).clip(5, 100).round(1)

    records = []
    for _, row in merged.iterrows():
        stn    = row["station_name"]
        base   = row["base_crowd"]
        ntrain = int(row["num_trains"])

        for dow in range(7):
            for hour in range(24):
                h_mult  = HOUR_DEMAND[hour]
                d_mult  = DOW[dow]
                crowd   = base * h_mult * d_mult
                crowd   = round(np.clip(crowd, 2, 100), 1)

                # Transfer congestion: stations with high degree get transfer penalty
                transfer_risk = "High" if row["total_degree"] >= 14 and hour in range(7,22) else \
                                "Moderate" if row["total_degree"] >= 8 else "Low"

                records.append({
                    "station_name":    stn,
                    "hour_of_day":     hour,
                    "day_of_week":     dow,
                    "day_name":        ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][dow],
                    "num_trains":      ntrain,
                    "crowd_score":     crowd,
                    "crowd_level":     _crowd_level_raw(crowd),
                    "transfer_congestion_risk": transfer_risk,
                    "peak_slot":       "Yes" if hour in [7,8,9,17,18,19,20] else "No",
                })

    df = pd.DataFrame(records)
    out = os.path.join(PROC, "station_crowd.csv")
    df.to_csv(out, index=False)
    print(f"  ✅ station_crowd.csv      →  {len(df):,} rows")
    return df


def build_seasonal_patterns() -> pd.DataFrame:
    """Monthly demand index across the network for trend visualisation."""
    records = []
    for month, mult in SEASONAL.items():
        records.append({
            "month": month,
            "month_name": ["","Jan","Feb","Mar","Apr","May","Jun",
                           "Jul","Aug","Sep","Oct","Nov","Dec"][month],
            "demand_index": round(mult * 100, 1),
            "season": _month_to_season(month),
            "peak": "Yes" if mult >= 1.25 else "No",
            "festival": _festival(month),
        })
    df = pd.DataFrame(records)
    out = os.path.join(PROC, "seasonal_patterns.csv")
    df.to_csv(out, index=False)
    print(f"  ✅ seasonal_patterns.csv  →  {len(df)} rows")
    return df


def _month_to_season(m: int) -> str:
    if m in [12, 1, 2]: return "Winter"
    if m in [3, 4, 5]:  return "Summer"
    if m in [6, 7, 8]:  return "Monsoon"
    return "Post-Monsoon"

def _festival(m: int) -> str:
    return {3:"Holi",5:"Summer Vacation",8:"Independence Day",
            10:"Navratri/Dussehra",11:"Diwali",12:"Christmas/New Year"}.get(m,"—")

def _crowd_level_raw(score: float) -> str:
    if score >= 75: return "Overcrowded"
    if score >= 55: return "High"
    if score >= 35: return "Moderate"
    return "Low"


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Passenger Flow Data Generator")
    print("="*55 + "\n")
    build_passenger_demand()
    build_station_crowd()
    build_seasonal_patterns()
    print("\n  ✅ All datasets ready in data/processed/\n")
