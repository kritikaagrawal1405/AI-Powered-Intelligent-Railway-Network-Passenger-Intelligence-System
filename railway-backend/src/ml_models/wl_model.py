"""
wl_model.py
===========
Phase-2 Member 2 — Ticket Confirmation Prediction
(Simple WL version, exactly as per task spec)

Task spec format:
    waitlist_no, days_before_travel → confirmed (0/1)

Algorithm : LogisticRegression  (as required by task)
Features  : waitlist_no + days_before_travel (only 2 — matches task UI)

Calibrated so:
    WL 12,  5 days → ~82%   (task example: WL 12 → 82%)
    WL 40,  3 days → ~25%   (task example: WL 40 → 25%)

Saved to: models/wl_confirmation_model.pkl

Usage
-----
    python src/ml_models/wl_model.py          # train + save
    from src.ml_models.wl_model import predict_wl_confirmation, train_wl_model

    prob = predict_wl_confirmation(wl_number=20, days_before_travel=7)
    # → 0.732
"""

import os
import pickle
import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score, f1_score

warnings.filterwarnings("ignore")

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(os.path.dirname(_HERE))
_MODELS = os.path.join(_ROOT, "models")
_PKL    = os.path.join(_MODELS, "wl_confirmation_model.pkl")


def train_wl_model(save: bool = True) -> dict:
    """
    Train a LogisticRegression model on waitlist + days_before_travel data.

    Generates 3,000 synthetic training rows with the exact pattern from the
    task spec: lower WL and more days before travel = higher confirmation chance.

    Calibrated targets:
        WL 12, 5 days  → ~82%
        WL 40, 3 days  → ~25%

    Returns
    -------
    dict with keys: model, accuracy, pkl_path
    """
    print("=" * 50)
    print("  WL Confirmation Model — LogisticRegression")
    print("=" * 50)

    np.random.seed(42)
    N    = 3000
    wl   = np.random.randint(1, 60, N).astype(float)
    days = np.random.randint(1, 30, N).astype(float)

    # logit calibrated so WL12,5days≈82%  and  WL40,3days≈25%
    from scipy.special import expit
    prob_true = expit(2.4 - 0.095 * wl + 0.05 * days)
    confirmed = (np.random.rand(N) < prob_true).astype(int)

    df = pd.DataFrame({
        "waitlist_no":        wl,
        "days_before_travel": days,
        "confirmed":          confirmed
    })

    print(f"\n  Training samples : {N}")
    print(f"  Confirmed rate   : {confirmed.mean():.1%}")

    X = df[["waitlist_no", "days_before_travel"]]
    y = df["confirmed"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)
    train_acc = accuracy_score(y_train, model.predict(X_train))
    print(f"  Accuracy         : {acc:.3f}")
    print(f"  Confusion Matrix :\n    [[TN={cm[0,0]} FP={cm[0,1]}]\n     [FN={cm[1,0]} TP={cm[1,1]}]]")

    # Print calibration check
    print("\n  Calibration check:")
    for wl_n, d in [(12, 5), (40, 3), (20, 7), (30, 7), (31, 7)]:
        p = float(model.predict_proba(
            pd.DataFrame([[wl_n, d]], columns=["waitlist_no", "days_before_travel"])
        )[0][1])
        print(f"    WL {wl_n:2d}, {d:2d} days → {p:.1%}")

    if save:
        os.makedirs(_MODELS, exist_ok=True)
        with open(_PKL, "wb") as f:
            pickle.dump({
                "model":    model,
                "features": ["waitlist_no", "days_before_travel"],
                "accuracy": acc,
                "precision": prec,
                "recall": rec,
                "f1": f1,
                "train_accuracy": train_acc,
                "confusion_matrix": cm.tolist(),
            }, f)
        print(f"\n  ✅  Saved → {_PKL}")

    return {
        "model": model, 
        "accuracy": acc, 
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "train_accuracy": train_acc,
        "pkl_path": _PKL
    }


def predict_wl_confirmation(wl_number: int, days_before_travel: int = 7) -> float:
    """
    Predict probability that WL ticket will be confirmed.

    Auto-trains the model if pkl doesn't exist.

    Parameters
    ----------
    wl_number          : int  — waitlist position (1 = first on WL)
    days_before_travel : int  — how many days until the journey

    Returns
    -------
    float — probability in [0.0, 1.0]

    Examples
    --------
    >>> predict_wl_confirmation(12, 5)   # → ~0.84  (task: WL12 → 82%)
    >>> predict_wl_confirmation(40, 3)   # → ~0.26  (task: WL40 → 25%)
    >>> predict_wl_confirmation(20, 7)   # → ~0.73
    """
    # Auto-train if pkl missing
    if not os.path.exists(_PKL):
        print("  WL model not found — training now...")
        train_wl_model(save=True)

    with open(_PKL, "rb") as f:
        payload = pickle.load(f)

    model = payload["model"]
    X     = pd.DataFrame(
        [[wl_number, days_before_travel]],
        columns=["waitlist_no", "days_before_travel"]
    )
    return float(model.predict_proba(X)[0][1])


if __name__ == "__main__":
    train_wl_model(save=True)

    print("\n" + "=" * 50)
    print("  Prediction Examples")
    print("=" * 50)
    tests = [
        (12, 5,  "Task example: WL12 → should be ~82%"),
        (40, 3,  "Task example: WL40 → should be ~25%"),
        (20, 7,  "WL 20, 7 days"),
        (30, 7,  "WL 30, 7 days"),
        (31, 7,  "WL 31, 7 days  ← should differ from WL30"),
        (5,  10, "WL 5, 10 days"),
        (1,  15, "WL 1, 15 days"),
        (50, 1,  "WL 50, 1 day"),
    ]
    for wl_n, d, label in tests:
        p   = predict_wl_confirmation(wl_n, d)
        bar = "█" * int(p * 25)
        print(f"  WL {wl_n:2d}, {d:2d} days → {p:.1%}  {bar}  ({label})")

    print("\n  ✅  wl_model.py ready\n")


# ===========================================================================
#  GAP G4 FIX — Per-Train WL Confirmation Ranking
# ===========================================================================

def get_trains_by_confirmation_probability(
    source: str,
    destination: str,
    wl_number: int = 20,
    days_before: int = 7,
) -> list[dict]:
    """
    Rank all trains running between two stations by their estimated
    WL ticket confirmation probability.

    This directly addresses the problem statement requirement:
    "identify trains and routes with higher confirmation probability"

    Parameters
    ----------
    source      : origin station name
    destination : destination station name
    wl_number   : your waitlist position
    days_before : days until travel

    Returns
    -------
    list of dicts (sorted by confirmation_probability descending):
      train_name, train_number, estimated_confirmation_pct,
      occupancy_level, recommendation, rank
    """
    import os as _os
    import sys as _sys
    _HERE2 = _os.path.dirname(_os.path.abspath(__file__))
    _ROOT2 = _os.path.dirname(_os.path.dirname(_HERE2))
    if _ROOT2 not in _sys.path:
        _sys.path.insert(0, _ROOT2)

    import pandas as _pd
    import numpy as _np

    _PROC = _os.path.join(_ROOT2, "data", "processed")

    # Load passenger demand data which has per-train occupancy
    results = []
    try:
        demand_path = _os.path.join(_PROC, "passenger_demand.csv")
        routes_path = _os.path.join(_PROC, "routes.csv")

        if _os.path.exists(demand_path):
            demand_df = _pd.read_csv(demand_path)
        else:
            demand_df = _pd.DataFrame()

        if _os.path.exists(routes_path):
            routes_df = _pd.read_csv(routes_path)
        else:
            routes_df = _pd.DataFrame()

        # Find trains that stop at both stations
        if len(routes_df) > 0 and "source_station" in routes_df.columns:
            # Trains passing through source
            src_trains = set(
                routes_df[
                    routes_df["source_station"].str.lower().str.contains(source.lower(), na=False)
                ]["train_name"].dropna().unique()
            )
            # Trains passing through destination
            dst_trains = set(
                routes_df[
                    routes_df["destination_station"].str.lower().str.contains(destination.lower(), na=False)
                ]["train_name"].dropna().unique()
            )
            matching_trains = list(src_trains & dst_trains)
        else:
            matching_trains = []

        # For each matching train, estimate confirmation probability
        # Occupancy-adjusted: high occupancy trains have lower WL confirmation
        for train_name in matching_trains[:15]:  # cap at 15 trains
            # Get occupancy if available
            occ = 70.0  # default
            if len(demand_df) > 0 and "train_name" in demand_df.columns:
                t_rows = demand_df[demand_df["train_name"] == train_name]
                if len(t_rows) > 0 and "occupancy_pct" in t_rows.columns:
                    occ = float(t_rows["occupancy_pct"].mean())

            # Adjust WL based on occupancy:
            # High occupancy → fewer cancellations → harder to confirm
            occupancy_factor = occ / 100.0
            adjusted_wl = wl_number * (0.5 + occupancy_factor)
            adjusted_days = max(1, int(days_before * (1 + (1 - occupancy_factor) * 0.5)))

            prob = predict_wl_confirmation(
                int(adjusted_wl),
                adjusted_days,
            )

            if occ >= 90:
                occ_level = "Overcrowded"
            elif occ >= 75:
                occ_level = "High"
            elif occ >= 55:
                occ_level = "Moderate"
            else:
                occ_level = "Low"

            if prob >= 0.70:
                rec = "Good chance — book this train"
            elif prob >= 0.45:
                rec = "Moderate chance — book early or consider alternatives"
            else:
                rec = "Low chance — consider alternative trains or routes"

            results.append({
                "train_name":                  train_name,
                "estimated_confirmation_pct":  round(prob * 100, 1),
                "occupancy_pct":               round(occ, 1),
                "occupancy_level":             occ_level,
                "recommendation":              rec,
            })

    except Exception:
        pass

    # If no route data found, return a general estimate
    if not results:
        base_prob = predict_wl_confirmation(wl_number, days_before)
        results.append({
            "train_name":                 f"{source} → {destination} (general estimate)",
            "estimated_confirmation_pct": round(base_prob * 100, 1),
            "occupancy_pct":              70.0,
            "occupancy_level":            "Moderate",
            "recommendation":             "General estimate — route-specific data unavailable",
        })

    # Sort by confirmation probability
    results.sort(key=lambda x: x["estimated_confirmation_pct"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return results
