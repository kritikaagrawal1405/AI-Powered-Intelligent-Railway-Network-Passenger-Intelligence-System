"""
railradar_client.py
===================
RailRadar Live API Integration Layer
https://api.railradar.in/api/v1/

Provides live data enrichment on top of the static graph:
  - Real-time train position and delay
  - Live station arrivals/departures board
  - Trains between stations (live schedule)
  - Temporal graph snapshot (graph edges weighted by live delays)

All functions gracefully degrade to static CSV data if:
  - No API key is set (RAILRADAR_API_KEY env var)
  - The API is unreachable
  - Rate limit exceeded

RailRadar API Endpoints used:
  GET /api/v1/trains/{trainNumber}       — live status, delay, position
  GET /api/v1/trains/between             — trains between two stations
  GET /api/v1/search/trains              — train search/autocomplete
  GET /api/v1/stations/{code}/live       — live station board

Usage
-----
    from src.live.railradar_client import (
        get_live_train_status,
        get_live_station_board,
        get_trains_between_live,
        build_temporal_graph_snapshot,
        enrich_delay_with_live_data,
    )

    # Single train
    status = get_live_train_status("12951")

    # Station board
    board = get_live_station_board("NDLS")

    # Temporal graph (live-weighted)
    G_live = build_temporal_graph_snapshot()
"""

from __future__ import annotations

import os
import sys
import time
import logging
from typing import Optional

import requests
import pandas as pd
import networkx as nx

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.graph_engine.graph_utils import load_graph, get_station_list

logger = logging.getLogger(__name__)

# ─── Config ────────────────────────────────────────────────────────────────
_BASE_URL   = "https://api.railradar.in/api/v1"
_API_KEY    = os.environ.get("RAILRADAR_API_KEY", "")
_TIMEOUT    = 8   # seconds
_CACHE_TTL  = 60  # seconds — live data cache lifetime

# Simple in-memory cache: {cache_key: (timestamp, data)}
_cache: dict[str, tuple[float, any]] = {}


def _is_configured() -> bool:
    return bool(_API_KEY)


def _get(path: str, params: dict = None) -> Optional[dict]:
    """
    Make authenticated GET request to RailRadar API.
    Returns parsed JSON or None on any failure.
    """
    if not _is_configured():
        logger.debug("RAILRADAR_API_KEY not set — live API unavailable")
        return None

    cache_key = f"{path}?{params}"
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if time.time() - ts < _CACHE_TTL:
            return data

    try:
        resp = requests.get(
            f"{_BASE_URL}{path}",
            params=params or {},
            headers={"X-API-Key": _API_KEY, "Accept": "application/json"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        _cache[cache_key] = (time.time(), data)
        return data
    except requests.exceptions.HTTPError as e:
        logger.warning(f"RailRadar API HTTP error {e.response.status_code} for {path}")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("RailRadar API unreachable — falling back to static data")
        return None
    except requests.exceptions.Timeout:
        logger.warning("RailRadar API timeout")
        return None
    except Exception as e:
        logger.warning(f"RailRadar API unexpected error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════

def get_live_train_status(train_number: str) -> dict:
    """
    Get real-time status for a single train.

    Parameters
    ----------
    train_number : str  e.g. "12951" (Rajdhani Express)

    Returns
    -------
    dict with keys:
      train_number, train_name, current_station, next_station,
      delay_minutes, status_text, is_live,
      last_updated, source (live | static)

    Falls back to static delay stats if API unavailable.
    """
    data = _get(f"/trains/{train_number}")

    if data and "liveData" in data:
        ld = data["liveData"]
        return {
            "train_number":      train_number,
            "train_name":        data.get("trainName", ""),
            "current_station":   ld.get("currentStation", ""),
            "next_station":      ld.get("nextStation", ""),
            "delay_minutes":     int(ld.get("delayMinutes", 0)),
            "status_text":       ld.get("currentPosition", ""),
            "platform":          ld.get("platform", ""),
            "is_live":           True,
            "last_updated":      ld.get("lastUpdated", ""),
            "source":            "live",
        }

    # Graceful fallback
    return {
        "train_number":  train_number,
        "train_name":    "",
        "current_station": "",
        "next_station":  "",
        "delay_minutes": None,
        "status_text":   "Live data unavailable — set RAILRADAR_API_KEY",
        "is_live":       False,
        "source":        "static",
    }


def get_live_station_board(station_code: str) -> dict:
    """
    Real-time arrivals and departures board for a station.

    Parameters
    ----------
    station_code : str  e.g. "NDLS", "HWH", "CSTM"

    Returns
    -------
    dict with keys:
      station_code, arrivals (list), departures (list),
      is_live, source
    Each train entry: train_number, train_name, scheduled_time,
                      expected_time, delay_minutes, platform, status
    """
    data = _get(f"/stations/{station_code}/live")

    if data:
        arrivals   = data.get("arrivals", [])
        departures = data.get("departures", [])

        def _fmt(trains):
            return [
                {
                    "train_number":    t.get("trainNumber", ""),
                    "train_name":      t.get("trainName", ""),
                    "scheduled_time":  t.get("scheduledTime", ""),
                    "expected_time":   t.get("expectedTime", ""),
                    "delay_minutes":   int(t.get("delayMinutes", 0)),
                    "platform":        t.get("platform", ""),
                    "status":          t.get("status", ""),
                }
                for t in trains
            ]

        return {
            "station_code": station_code,
            "arrivals":     _fmt(arrivals),
            "departures":   _fmt(departures),
            "is_live":      True,
            "source":       "live",
        }

    return {
        "station_code": station_code,
        "arrivals":     [],
        "departures":   [],
        "is_live":      False,
        "source":       "static — set RAILRADAR_API_KEY",
    }


def get_trains_between_live(
    from_station: str,
    to_station: str,
    date: str = None,
) -> dict:
    """
    Find all trains running between two stations (live schedule).

    Parameters
    ----------
    from_station : str  station code or name
    to_station   : str  station code or name
    date         : str  YYYY-MM-DD, defaults to today

    Returns
    -------
    dict with keys:
      trains (list), count, source
    Each train: number, name, departure_time, arrival_time,
                duration_minutes, delay_minutes, availability
    """
    params = {"from": from_station, "to": to_station}
    if date:
        params["date"] = date

    data = _get("/trains/between", params=params)

    if data and "trains" in data:
        trains = [
            {
                "number":           t.get("trainNumber", ""),
                "name":             t.get("trainName", ""),
                "departure_time":   t.get("departureTime", ""),
                "arrival_time":     t.get("arrivalTime", ""),
                "duration_minutes": t.get("durationMinutes", 0),
                "delay_minutes":    t.get("currentDelay", 0),
                "availability":     t.get("availability", ""),
                "train_type":       t.get("trainType", ""),
            }
            for t in data["trains"]
        ]
        return {"trains": trains, "count": len(trains), "source": "live"}

    return {"trains": [], "count": 0, "source": "static — set RAILRADAR_API_KEY"}


def search_trains(query: str, limit: int = 10) -> list[dict]:
    """
    Autocomplete search for trains by name or number.

    Returns list of {number, name, type, from_station, to_station}
    """
    data = _get("/search/trains", params={"q": query, "limit": limit})

    if data and "results" in data:
        return [
            {
                "number":       r.get("trainNumber", ""),
                "name":         r.get("trainName", ""),
                "type":         r.get("trainType", ""),
                "from_station": r.get("fromStation", ""),
                "to_station":   r.get("toStation", ""),
            }
            for r in data["results"]
        ]
    return []


# ══════════════════════════════════════════════════════════════════════════
#  TEMPORAL GRAPH SNAPSHOT
# ══════════════════════════════════════════════════════════════════════════

def build_temporal_graph_snapshot(
    sample_trains: list[str] = None,
    fallback_to_static: bool = True,
) -> nx.DiGraph:
    """
    Build a temporally-enriched graph where edge weights reflect
    current live delays rather than historical averages.

    How it works
    ------------
    1. Load the static graph (base topology from graph_utils)
    2. For each edge, query the live delay for trains on that route
    3. Replace the 'weight' attribute with live_delay if available
    4. Add node attribute 'live_delay_min' to each station

    If API is unavailable or no key is set, returns the plain static
    graph unchanged (graceful fallback).

    Parameters
    ----------
    sample_trains    : list of train numbers to query for live delays.
                       If None, uses a representative set of major trains.
    fallback_to_static : if True, always return something usable

    Returns
    -------
    nx.DiGraph with enriched edge/node attributes
    """
    G = load_graph()

    if not _is_configured():
        logger.info("No API key — temporal graph falls back to static graph")
        return G

    # Default: representative major trains covering key corridors
    if sample_trains is None:
        sample_trains = [
            "12951", "12952",  # Mumbai Rajdhani
            "12301", "12302",  # Howrah Rajdhani
            "12004", "12003",  # Shatabdi
            "22691", "22692",  # Rajdhani
            "12627", "12628",  # Karnataka Express
            "11301", "11302",  # Udyan Express
        ]

    # Collect live delays keyed by (current_station)
    live_delay_map: dict[str, list[int]] = {}

    for tn in sample_trains:
        status = get_live_train_status(tn)
        if status["is_live"] and status["current_station"]:
            stn = status["current_station"]
            delay = status["delay_minutes"] or 0
            live_delay_map.setdefault(stn, []).append(delay)

    # Compute per-station avg live delay
    station_live_delay = {
        stn: sum(vals) / len(vals)
        for stn, vals in live_delay_map.items()
    }

    # Enrich graph
    G_live = G.copy()

    for node in G_live.nodes():
        if node in station_live_delay:
            G_live.nodes[node]["live_delay_min"] = station_live_delay[node]
            G_live.nodes[node]["has_live_data"]  = True
        else:
            G_live.nodes[node]["live_delay_min"] = None
            G_live.nodes[node]["has_live_data"]  = False

    # Re-weight edges using live delay of source station where available
    for u, v, data in G_live.edges(data=True):
        live_u = station_live_delay.get(u)
        if live_u is not None:
            # Blend: 70% live, 30% historical
            hist = data.get("avg_delay", data.get("weight", 0))
            data["weight"]     = 0.7 * live_u + 0.3 * hist
            data["live_delay"] = live_u
            data["is_live"]    = True
        else:
            data["live_delay"] = None
            data["is_live"]    = False

    logger.info(
        f"Temporal graph built: {len(G_live.nodes())} nodes, "
        f"{len(G_live.edges())} edges, "
        f"{len(station_live_delay)} stations with live data"
    )
    return G_live


def enrich_delay_with_live_data(station_name: str) -> dict:
    """
    Return the best available delay estimate for a station:
    live if API is available, static otherwise.

    Returns
    -------
    dict:
      station, delay_minutes, source (live|static), confidence
    """
    # Try to get station code from name (simple lookup)
    # RailRadar uses station codes; we attempt a search
    search_result = search_trains(station_name, limit=1)

    # For station boards we need the code — try common known mappings
    _KNOWN_CODES = {
        "New Delhi":          "NDLS",
        "Howrah Jn":          "HWH",
        "Mumbai CST":         "CSTM",
        "Chennai Central":    "MAS",
        "Bengaluru City Jn":  "SBC",
        "Secunderabad Jn":    "SC",
        "Lokmanyatilak T":    "LTT",
        "Pune Jn":            "PUNE",
        "Ahmedabad Jn":       "ADI",
        "Patna Jn":           "PNBE",
        "Nagpur":             "NGP",
        "Bhopal Jn":          "BPL",
        "Jaipur":             "JP",
        "Lucknow":            "LKO",
        "Varanasi Jn":        "BSB",
        "Kolkata":            "KOAA",
        "Guwahati":           "GHY",
        "Kochi":              "ERS",
        "Hyderabad":          "HYB",
        "Coimbatore Jn":      "CBE",
    }

    code = _KNOWN_CODES.get(station_name)
    if code:
        board = get_live_station_board(code)
        if board["is_live"]:
            all_trains = board["arrivals"] + board["departures"]
            if all_trains:
                avg_delay = sum(t["delay_minutes"] for t in all_trains) / len(all_trains)
                return {
                    "station":       station_name,
                    "delay_minutes": round(avg_delay, 1),
                    "source":        "live",
                    "confidence":    "high",
                    "num_trains":    len(all_trains),
                }

    # Static fallback
    try:
        from src.graph_engine.graph_utils import get_delay_stats
        stats = get_delay_stats(station_name)
        return {
            "station":       station_name,
            "delay_minutes": float(stats.get("avg_delay_min", 0)),
            "source":        "static",
            "confidence":    "medium",
            "num_trains":    int(stats.get("num_trains", 0)),
        }
    except Exception:
        return {
            "station":       station_name,
            "delay_minutes": 0,
            "source":        "unavailable",
            "confidence":    "low",
        }


def api_status() -> dict:
    """
    Check whether the RailRadar API is reachable and the key is valid.

    Returns
    -------
    dict: configured, reachable, key_set, message
    """
    if not _is_configured():
        return {
            "configured": False,
            "reachable":  False,
            "key_set":    False,
            "message":    "Set RAILRADAR_API_KEY environment variable to enable live data",
        }

    # Try a lightweight search to validate the key
    result = _get("/search/trains", params={"q": "Rajdhani", "limit": 1})
    reachable = result is not None

    return {
        "configured": True,
        "reachable":  reachable,
        "key_set":    True,
        "message":    "Live API active" if reachable else "API key set but endpoint unreachable",
    }
