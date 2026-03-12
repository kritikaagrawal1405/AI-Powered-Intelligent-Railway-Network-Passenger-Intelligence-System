"""
train_delay_model.py
====================
Model 1 — Train Delay Prediction

Goal      : Predict expected delay minutes for a train at a given station.
Data      : data/processed/schedule_features.csv   (1,900 real etrain records)
            data/processed/station_importance.csv  (graph centrality)
            data/processed/station_delay_stats.csv (per-station history)
Algorithm : RandomForestRegressor
Saved to  : models/delay_prediction_model.pkl

Integration
-----------
    from src.ml_models.train_delay_model import predict_delay

    minutes = predict_delay({
        "significant_delay_ratio": 0.45,
        "avg_delay_min":           62.0,
        "delay_risk_score":        52.0,
        "stop_number":             8,
    })
"""

import os
import warnings
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────
_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(os.path.dirname(_HERE))
_PROC   = os.path.join(_ROOT, "data", "processed")
_MODELS = os.path.join(_ROOT, "models")
_PKL    = os.path.join(_MODELS, "delay_prediction_model.pkl")
os.makedirs(_MODELS, exist_ok=True)

# ── Feature list (ordered by correlation strength from EDA) ───────────────
FEATURES = [
    "significant_delay_ratio",   # % trains significantly late here  — r=0.77
    "pct_significant_delay",     # same value as raw percentage        — r=0.77
    "avg_delay_min",             # historical avg delay at station     — r=0.63
    "median_delay_min",          # historical median delay             — r=0.59
    "on_time_ratio",             # % trains on time (inverse signal)  — r=-0.54
    "pct_right_time",            # same as raw percentage              — r=-0.54
    "delay_risk_score",          # composite risk score 0-100         — r=0.49
    "stop_number",               # position in journey (delays grow)  — r=0.30
    "pct_cancelled_unknown",     # cancellation rate at station
    "slight_delay_ratio",        # % slightly delayed
    "total_degree",              # station connectivity in network
    "betweenness_centrality",    # station centrality
    "num_trains",                # daily train volume
    "is_junction",               # junction flag
]

TARGET = "average_delay_minutes"


# ══════════════════════════════════════════════════════════════════════════
#  FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════════════

def _build_dataset() -> pd.DataFrame:
    """Merge all three source files and engineer features."""
    df = pd.read_csv(os.path.join(_PROC, "schedule_features.csv"))
    si = pd.read_csv(os.path.join(_PROC, "station_importance.csv"))
    ds = pd.read_csv(os.path.join(_PROC, "station_delay_stats.csv"))

    df = df.merge(
        si[["station_name", "betweenness_centrality", "degree_centrality",
            "total_degree", "delay_risk_score"]],
        on="station_name", how="left"
    )
    df = df.merge(
        ds[["station_name", "avg_delay_min", "median_delay_min", "num_trains"]],
        on="station_name", how="left"
    )

    # Stop position within each train's journey
    df["stop_number"] = df.groupby("train_number").cumcount()

    # Ensure numeric target
    df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")

    # Fill 7 nulls in avg/median delay with column median
    for col in ["avg_delay_min", "median_delay_min"]:
        df[col] = df[col].fillna(df[col].median())

    return df


# ══════════════════════════════════════════════════════════════════════════
#  TRAINING
# ══════════════════════════════════════════════════════════════════════════

def train(save: bool = True) -> dict:
    """
    Train RandomForestRegressor end-to-end.

    Returns dict with keys: model, metrics, feature_names
    """
    print("=" * 62)
    print("  Model 1 — Train Delay Prediction")
    print("  Algorithm : RandomForestRegressor")
    print("=" * 62)

    # ── Data ──────────────────────────────────────────────────────────────
    print("\n[1/4] Loading & engineering features …")
    df = _build_dataset()

    available = [f for f in FEATURES if f in df.columns]
    missing   = [f for f in FEATURES if f not in df.columns]
    if missing:
        print(f"  ⚠  Columns not found (skipped): {missing}")

    X = df[available].copy()
    y = df[TARGET].copy()
    mask = y.notna()
    X, y = X[mask], y[mask]

    print(f"  Samples  : {len(X)}")
    print(f"  Features : {len(available)}")
    print(f"  Target   : mean={y.mean():.1f} min  "
          f"median={y.median():.1f}  max={y.max():.1f}")

    # ── Split ─────────────────────────────────────────────────────────────
    print("\n[2/4] Splitting 80/20 …")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"  Train: {len(X_train)}   Test: {len(X_test)}")

    # ── Model ─────────────────────────────────────────────────────────────
    print("\n[3/4] Training RandomForestRegressor …")
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model",   RandomForestRegressor(
            n_estimators    = 300,
            max_depth       = 15,
            min_samples_leaf= 3,
            max_features    = "sqrt",
            n_jobs          = -1,
            random_state    = 42,
        )),
    ])
    pipeline.fit(X_train, y_train)

    # ── Evaluate ──────────────────────────────────────────────────────────
    print("\n[4/4] Evaluating …")
    y_pred   = pipeline.predict(X_test)
    mae      = mean_absolute_error(y_test, y_pred)
    rmse     = np.sqrt(mean_squared_error(y_test, y_pred))
    baseline = mean_absolute_error(y_test, np.full(len(y_test), y_train.mean()))

    cv      = cross_val_score(pipeline, X, y, cv=5,
                              scoring="neg_mean_absolute_error")
    cv_mae  = -cv.mean()

    rf = pipeline.named_steps["model"]
    importances = (
        pd.Series(rf.feature_importances_, index=available)
        .sort_values(ascending=False)
    )

    metrics = {
        "mae":          round(mae,      2),
        "rmse":         round(rmse,     2),
        "cv_mae":       round(cv_mae,   2),
        "baseline_mae": round(baseline, 2),
        "n_train":      len(X_train),
        "n_test":       len(X_test),
        "features":     available,
    }

    print(f"\n  ┌─────────────────────────────────────┐")
    print(f"  │  MAE           : {mae:6.2f} min           │")
    print(f"  │  RMSE          : {rmse:6.2f} min           │")
    print(f"  │  5-fold CV MAE : {cv_mae:6.2f} min           │")
    print(f"  │  Baseline MAE  : {baseline:6.2f} min  (mean)  │")
    print(f"  └─────────────────────────────────────┘")
    print(f"\n  Top 5 feature importances:")
    for feat, imp in importances.head(5).items():
        bar = "█" * int(imp * 50)
        print(f"    {feat:32s} {imp:.4f}  {bar}")

    # ── Save ──────────────────────────────────────────────────────────────
    if save:
        payload = {
            "pipeline":       pipeline,
            "feature_names":  available,
            "metrics":        metrics,
            "target":         TARGET,
            "feature_medians": dict(X.median()),
        }
        with open(_PKL, "wb") as f:
            pickle.dump(payload, f)
        print(f"\n  ✅  Saved → {_PKL}")

    return {"model": pipeline, "metrics": metrics, "feature_names": available}


# ══════════════════════════════════════════════════════════════════════════
#  PREDICTION API
# ══════════════════════════════════════════════════════════════════════════

_CACHE: dict = {}


def _load_model() -> dict:
    if _CACHE:
        return _CACHE
    if not os.path.exists(_PKL):
        print("  Model not found — training now …")
        result = train(save=True)
        _CACHE.update(result)
        _CACHE["feature_medians"] = {}
        return _CACHE
    with open(_PKL, "rb") as f:
        payload = pickle.load(f)
    _CACHE["pipeline"]       = payload["pipeline"]
    _CACHE["feature_names"]  = payload["feature_names"]
    _CACHE["metrics"]        = payload["metrics"]
    _CACHE["feature_medians"]= payload.get("feature_medians", {})
    return _CACHE


def predict_delay(features_dict: dict) -> float:
    """
    Predict expected delay in minutes for a train at a station.

    Parameters
    ----------
    features_dict : dict
        Any subset of the model's features. Missing keys are filled
        with training-set medians automatically.

        Useful keys:
          significant_delay_ratio  — float 0-1  (% significantly delayed)
          avg_delay_min            — float       (historical avg delay)
          delay_risk_score         — float 0-100
          stop_number              — int         (0 = first stop)
          on_time_ratio            — float 0-1
          betweenness_centrality   — float 0-1

    Returns
    -------
    float — predicted delay minutes, clipped to ≥ 0

    Example
    -------
    >>> predict_delay({"avg_delay_min": 62.0, "delay_risk_score": 52.0})
    47.3
    """
    cache    = _load_model()
    pipeline = cache["pipeline"]
    features = cache["feature_names"]
    medians  = cache["feature_medians"]

    row = {f: features_dict.get(f, medians.get(f, np.nan)) for f in features}
    X   = pd.DataFrame([row])[features]
    return float(max(0.0, round(pipeline.predict(X)[0], 1)))


def get_model_info() -> dict:
    """Return model metadata and evaluation metrics."""
    cache = _load_model()
    return {
        "model_type":   "RandomForestRegressor",
        "features":     cache["feature_names"],
        "target":       TARGET,
        "metrics":      cache["metrics"],
        "model_path":   _PKL,
    }


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    train(save=True)

    print("\n" + "=" * 62)
    print("  Prediction Examples")
    print("=" * 62)

    tests = [
        ("High-risk station  (Tatanagar-like)", {
            "significant_delay_ratio": 0.80,
            "pct_significant_delay":   80.0,
            "avg_delay_min":           338.0,
            "median_delay_min":        338.0,
            "on_time_ratio":           0.05,
            "pct_right_time":          5.0,
            "delay_risk_score":        58.7,
            "stop_number":             18,
            "total_degree":            4,
            "betweenness_centrality":  0.05,
            "num_trains":              4,
        }),
        ("Medium-risk station (Howrah-like)", {
            "significant_delay_ratio": 0.25,
            "pct_significant_delay":   25.0,
            "avg_delay_min":           77.7,
            "median_delay_min":        66.0,
            "on_time_ratio":           0.68,
            "pct_right_time":          67.8,
            "delay_risk_score":        17.2,
            "stop_number":             12,
            "total_degree":            19,
            "betweenness_centrality":  0.41,
            "num_trains":              18,
        }),
        ("Low-risk station   (Chennai Central-like)", {
            "significant_delay_ratio": 0.00,
            "pct_significant_delay":   0.0,
            "avg_delay_min":           2.0,
            "median_delay_min":        2.0,
            "on_time_ratio":           0.99,
            "pct_right_time":          98.9,
            "delay_risk_score":        7.0,
            "stop_number":             0,
            "total_degree":            9,
            "betweenness_centrality":  0.03,
            "num_trains":              18,
        }),
        ("Minimal input (only 2 keys)", {
            "avg_delay_min":    45.0,
            "delay_risk_score": 35.0,
        }),
    ]

    for label, feats in tests:
        pred = predict_delay(feats)
        print(f"\n  📍 {label}")
        print(f"     → Predicted delay: {pred:.1f} min")

    info = get_model_info()
    print(f"\n  Model  : {info['model_type']}")
    print(f"  MAE    : {info['metrics']['mae']} min")
    print(f"  RMSE   : {info['metrics']['rmse']} min")
    print(f"  CV MAE : {info['metrics']['cv_mae']} min")
    print("\n  ✅  train_delay_model.py ready for integration\n")
