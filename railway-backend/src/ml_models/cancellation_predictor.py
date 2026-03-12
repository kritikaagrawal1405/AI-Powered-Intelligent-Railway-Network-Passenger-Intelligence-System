"""
cancellation_predictor.py
=========================
Gap G3 Fix — Cancellation Pattern Predictor

Predicts the probability that a ticket/booking will be cancelled,
and models historical cancellation rates per station and route.

Uses the pct_cancelled_unknown feature already present in
station_delay_stats.csv / schedule_features.csv.

Standalone cancellation model trained on:
  - Station-level historical cancellation rates
  - Train type (premium trains have lower cancellations)
  - Day-of-week and seasonal demand
  - Route occupancy levels

Public API
----------
    predict_cancellation_probability(station, train_type, days_before, month) -> float
    get_station_cancellation_stats(station) -> dict
    get_high_cancellation_routes(n) -> list[dict]
    get_cancellation_summary() -> dict
"""

from __future__ import annotations

import os
import sys
import warnings
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix, precision_score, recall_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

warnings.filterwarnings("ignore")

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(os.path.dirname(_HERE))
_PROC   = os.path.join(_ROOT, "data", "processed")
_MODELS = os.path.join(_ROOT, "models")
_PKL    = os.path.join(_MODELS, "cancellation_model.pkl")
os.makedirs(_MODELS, exist_ok=True)

_CACHE: dict = {}


# ══════════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ══════════════════════════════════════════════════════════════════════════

def _load_station_stats() -> pd.DataFrame:
    path = os.path.join(_PROC, "station_delay_stats.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        # Normalise: support both column name variants
        if "avg_pct_cancelled" in df.columns and "pct_cancelled_unknown" not in df.columns:
            df["pct_cancelled_unknown"] = df["avg_pct_cancelled"]
        for col in ["avg_delay_min", "pct_cancelled_unknown", "num_trains"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        return df
    return pd.DataFrame()


def _load_schedule_features() -> pd.DataFrame:
    path = os.path.join(_PROC, "schedule_features.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        for col in ["pct_cancelled_unknown", "average_delay_minutes"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        return df
    return pd.DataFrame()


def _load_importance() -> pd.DataFrame:
    path = os.path.join(_PROC, "station_importance.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════
#  SYNTHETIC TRAINING DATA GENERATION
# ══════════════════════════════════════════════════════════════════════════

def _build_cancellation_dataset() -> pd.DataFrame:
    """
    Build a training dataset for the cancellation model.
    Synthesises domain-faithful rows using real pct_cancelled_unknown
    from station data as the ground truth signal.
    """
    stats   = _load_station_stats()
    sched   = _load_schedule_features()
    imp     = _load_importance()

    np.random.seed(42)
    N = 4000

    # Base cancellation rate distribution from real data
    if "pct_cancelled_unknown" in stats.columns and len(stats) > 0:
        real_cancel_rates = stats["pct_cancelled_unknown"].dropna().values
        cancel_base = np.random.choice(real_cancel_rates, N) / 100.0
    else:
        cancel_base = np.random.beta(2, 18, N)  # ~10% mean cancellation rate

    # Feature synthesis — domain-faithful correlations
    days_before    = np.random.randint(1, 120, N).astype(float)
    wl_number      = np.random.randint(0, 60, N).astype(float)  # 0 = confirmed
    is_premium     = np.random.binomial(1, 0.3, N).astype(float)
    month          = np.random.randint(1, 13, N).astype(float)
    is_peak_season = ((month >= 5) & (month <= 7) | (month == 10) | (month == 11)).astype(float)
    occupancy_pct  = np.clip(np.random.normal(70, 20, N), 10, 100)

    # Cancel probability: logic
    # - WL tickets cancel more; confirmed cancel less
    # - Premium trains: lower cancellation (people don't give up Rajdhani)
    # - Peak season: lower cancellation (hard to get tickets)
    # - Long days_before: higher cancellation (plans change)
    # - High WL: higher cancellation (gave up waiting)
    logit = (
        -2.0                          # base
        + 0.015 * days_before         # farther from travel → more cancellations
        + 0.025 * wl_number           # higher WL → more give up
        - 1.2  * is_premium           # premium → less cancellation
        - 0.6  * is_peak_season       # peak → less cancellation
        + 0.01 * (100 - occupancy_pct)# low demand → more cancellation
        + 2.5  * cancel_base          # station's base cancel rate
    )
    from scipy.special import expit
    prob_cancel = expit(logit)
    cancelled   = (np.random.rand(N) < prob_cancel).astype(int)

    return pd.DataFrame({
        "cancel_base":     cancel_base,
        "days_before":     days_before,
        "wl_number":       wl_number,
        "is_premium":      is_premium,
        "is_peak_season":  is_peak_season,
        "occupancy_pct":   occupancy_pct,
        "cancelled":       cancelled,
    })


# ══════════════════════════════════════════════════════════════════════════
#  MODEL TRAINING
# ══════════════════════════════════════════════════════════════════════════

FEATURES = [
    "cancel_base", "days_before", "wl_number",
    "is_premium", "is_peak_season", "occupancy_pct",
]

def train_cancellation_model(save: bool = True) -> dict:
    df = _build_cancellation_dataset()
    X  = df[FEATURES]
    y  = df["cancelled"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model",   GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            random_state=42,
        )),
    ])
    pipeline.fit(X_train, y_train)

    y_pred  = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    acc     = accuracy_score(y_test, y_pred)
    prec    = precision_score(y_test, y_pred, zero_division=0)
    rec     = recall_score(y_test, y_pred, zero_division=0)
    f1      = f1_score(y_test, y_pred, zero_division=0)
    auc     = roc_auc_score(y_test, y_proba)
    cm      = confusion_matrix(y_test, y_pred)
    train_acc = accuracy_score(y_train, pipeline.predict(X_train))

    if save:
        payload = {
            "pipeline": pipeline,
            "features": FEATURES,
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "auc":      auc,
            "train_accuracy": train_acc,
            "confusion_matrix": cm.tolist(),
            "feature_medians": dict(X.median()),
        }
        with open(_PKL, "wb") as f:
            pickle.dump(payload, f)

    return {
        "pipeline": pipeline, 
        "accuracy": acc, 
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "train_accuracy": train_acc,
        "auc": auc
    }


def _load_model() -> dict:
    if _CACHE:
        return _CACHE
    if not os.path.exists(_PKL):
        result = train_cancellation_model(save=True)
        _CACHE.update(result)
        _CACHE["feature_medians"] = {}
        return _CACHE
    with open(_PKL, "rb") as f:
        payload = pickle.load(f)
    _CACHE.update(payload)
    return _CACHE


# ══════════════════════════════════════════════════════════════════════════
#  PUBLIC PREDICTION API
# ══════════════════════════════════════════════════════════════════════════

def predict_cancellation_probability(
    station: str = "",
    train_type: str = "express",     # "premium", "express", "passenger"
    days_before: int = 30,
    month: int = 6,
    wl_number: int = 0,
    occupancy_pct: float = 70.0,
) -> float:
    """
    Predict the probability that a booking for this station/train will be cancelled.

    Parameters
    ----------
    station      : station name (used to look up historical cancel rate)
    train_type   : "premium" (Rajdhani/Shatabdi), "express", "passenger"
    days_before  : days until travel
    month        : 1–12
    wl_number    : 0 = confirmed booking; > 0 = waitlisted
    occupancy_pct: expected route occupancy

    Returns
    -------
    float — cancellation probability 0.0–1.0
    """
    cache = _load_model()
    pipeline = cache["pipeline"]
    medians  = cache.get("feature_medians", {})

    # Look up station base cancel rate
    stats = _load_station_stats()
    cancel_base = 0.10  # default 10%
    if len(stats) > 0 and "pct_cancelled_unknown" in stats.columns:
        row = stats[stats["station_name"].str.lower() == station.lower()]
        if len(row) > 0:
            cancel_base = float(row["pct_cancelled_unknown"].values[0]) / 100.0

    is_peak    = 1 if month in (5, 6, 7, 10, 11, 12) else 0
    is_premium = 1 if train_type == "premium" else 0

    X = pd.DataFrame([{
        "cancel_base":    cancel_base,
        "days_before":    float(days_before),
        "wl_number":      float(wl_number),
        "is_premium":     float(is_premium),
        "is_peak_season": float(is_peak),
        "occupancy_pct":  float(occupancy_pct),
    }])
    prob = float(pipeline.predict_proba(X[FEATURES])[0][1])
    return round(prob, 4)


def get_station_cancellation_stats(station: str) -> dict:
    """
    Historical cancellation statistics for a specific station.

    Returns
    -------
    dict: station, cancel_rate_pct, cancel_level, avg_delay_min,
          num_trains, interpretation
    """
    stats = _load_station_stats()
    if len(stats) == 0:
        return {"error": "Station stats unavailable"}

    row = stats[stats["station_name"].str.lower() == station.lower()]
    if len(row) == 0:
        # Try partial match
        mask = stats["station_name"].str.lower().str.contains(station.lower(), na=False)
        row  = stats[mask]

    if len(row) == 0:
        return {"error": f"Station '{station}' not found"}

    row = row.iloc[0]
    rate = float(row.get("pct_cancelled_unknown", 0))
    level = "High" if rate > 15 else "Medium" if rate > 7 else "Low"

    return {
        "station":         row.get("station_name", station),
        "cancel_rate_pct": round(rate, 2),
        "cancel_level":    level,
        "avg_delay_min":   round(float(row.get("avg_delay_min", 0)), 1),
        "num_trains":      int(row.get("num_trains", 0)),
        "interpretation": (
            f"{level} cancellation risk at {station}. "
            f"Approximately {rate:.1f}% of trains at this station have "
            f"cancellation/unknown status historically."
        ),
    }


def get_high_cancellation_routes(n: int = 10) -> list[dict]:
    """
    Return the top-N routes/stations with highest historical cancellation rates.

    Returns
    -------
    list of dicts: rank, station, cancel_rate_pct, avg_delay_min, num_trains
    """
    stats = _load_station_stats()
    if len(stats) == 0 or "pct_cancelled_unknown" not in stats.columns:
        return []

    df = stats.dropna(subset=["pct_cancelled_unknown"]).copy()
    df = df.sort_values("pct_cancelled_unknown", ascending=False).head(n).reset_index(drop=True)

    return [
        {
            "rank":            i + 1,
            "station":         row.get("station_name", ""),
            "cancel_rate_pct": round(float(row["pct_cancelled_unknown"]), 2),
            "cancel_level":    "High" if row["pct_cancelled_unknown"] > 15 else "Medium",
            "avg_delay_min":   round(float(row.get("avg_delay_min", 0)), 1),
            "num_trains":      int(row.get("num_trains", 0)),
        }
        for i, row in df.iterrows()
    ]


def get_cancellation_summary() -> dict:
    """
    Network-wide cancellation summary statistics.
    """
    stats = _load_station_stats()
    if len(stats) == 0 or "pct_cancelled_unknown" not in stats.columns:
        return {"error": "Data unavailable"}

    col = stats["pct_cancelled_unknown"].dropna()
    high   = int((col > 15).sum())
    medium = int(((col > 7) & (col <= 15)).sum())
    low    = int((col <= 7).sum())

    return {
        "network_avg_cancel_rate_pct": round(float(col.mean()), 2),
        "high_cancel_stations":        high,
        "medium_cancel_stations":      medium,
        "low_cancel_stations":         low,
        "total_stations_tracked":      len(col),
        "worst_station":               stats.loc[col.idxmax(), "station_name"] if len(col) > 0 else "",
        "best_station":                stats.loc[col.idxmin(), "station_name"] if len(col) > 0 else "",
    }
