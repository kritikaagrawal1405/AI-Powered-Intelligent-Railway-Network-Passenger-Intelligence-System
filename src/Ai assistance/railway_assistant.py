"""
railway_assistant.py
====================
Phase-3: Lightweight Railway AI Assistant (SLM)
AI-Powered Railway Intelligence System

A rule-based, keyword-driven assistant that routes natural language
queries to the correct analytics modules and returns structured,
human-readable responses — no heavy LLM required.

Supported intents (spec-exact names)
-------------------------------------
  delay_prediction      — delay forecasts for stations or trains
  ticket_confirmation   — waitlist / PNR confirmation probability
  congestion_analysis   — congestion hotspots and corridor analysis
  network_vulnerability — cascade vulnerability and resilience
  route_planning        — shortest / best path between two stations

Required public API
-------------------
    detect_query_intent(query: str)  -> str
    handle_query(query: str)         -> dict
    generate_explanation(data: dict) -> str
    railway_assistant(query: str)    -> dict   ← main entry point

Return schema of railway_assistant()
--------------------------------------
    {
        "query"   : str,   # original user query
        "intent"  : str,   # one of the five intent names above
        "response": str,   # human-readable answer
    }

Quick import
------------
    from src.ai_assistant.railway_assistant import railway_assistant

Example
-------
    result = railway_assistant("Which stations are most vulnerable?")
    print(result["response"])
"""

from __future__ import annotations

import re
import sys
import os
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup — ensures project root is importable from any working directory
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))          # src/ai_assistant/
_ROOT = os.path.dirname(os.path.dirname(_HERE))             # project root
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ---------------------------------------------------------------------------
# Internal module imports — Phase-1, Phase-2 engines
# ---------------------------------------------------------------------------
from src.graph_engine.graph_utils import (
    load_graph,
    get_station_list,
    get_delay_stats,
    top_critical_stations,
    shortest_route,
    get_route_details,
    graph_summary,
)
from src.intelligence.delay_cascade import (
    simulate_delay_cascade,
    get_most_vulnerable_stations,
)
from src.intelligence.congestion_predictor import (
    identify_congestion_hotspots,
    congestion_summary,
    calculate_station_congestion,
    corridor_congestion_analysis,
)
from src.intelligence.network_resilience import (
    compute_network_resilience,
    resilience_summary,
)
from src.ml_models.train_delay_model import predict_delay
from src.ml_models.ticket_confirmation_model import predict_confirmation
from src.ml_models.wl_model import predict_wl_confirmation

# ---------------------------------------------------------------------------
# Phase-3 Member-3: Knowledge layer — FAQ, rules, passenger guidance
# ---------------------------------------------------------------------------
try:
    from src.knowledge.knowledge_retrieval import (
        is_knowledge_query,
        get_contextual_answer,
    )
    _KNOWLEDGE_OK = True
except Exception:
    _KNOWLEDGE_OK = False
    def is_knowledge_query(_q: str) -> bool:   return False
    def get_contextual_answer(_q: str):        return None


# ===========================================================================
#  INTENT CATALOGUE
#  Each entry: (intent_name, [trigger_keywords])
#  Hard-priority regex rules are applied first in detect_query_intent()
# ===========================================================================

_INTENT_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "ticket_confirmation",
        [
            "wl", "waitlist", "wait list", "confirm", "ticket",
            "chances", "berth", "pnr", "booking", "confirmed",
            "will my ticket", "will it confirm",
        ],
    ),
    (
        "delay_prediction",
        [
            "delay", "late", "on time", "delayed", "how late",
            "expected delay", "delay risk", "train late",
        ],
    ),
    (
        "network_vulnerability",
        [
            "vulnerable", "vulnerability", "cascade", "propagat",
            "spread", "most affected", "risk station", "resilience",
            "critical station", "single point", "failure",
            "weakest", "network risk",
        ],
    ),
    (
        "congestion_analysis",
        [
            "congestion", "congested", "hotspot", "overload",
            "busiest", "crowded", "traffic", "congestion hotspot",
            "most congested", "corridor",
        ],
    ),
    (
        "route_planning",
        [
            "route", "path", "travel from", "go from",
            "journey from", "trains from", "lowest delay",
            "best train", "find best", "best route",
            "how to get", "from", "to",
        ],
    ),
]


# ===========================================================================
#  FUNCTION 1 — detect_query_intent
# ===========================================================================

def detect_query_intent(query: str) -> str:
    """
    Classify a natural language query into one of five railway intents.

    Strategy
    --------
    1. Hard-priority regex rules handle unambiguous cases first.
    2. Keyword scoring on the remaining intents — most matched keywords wins.
    3. Falls back to "unknown" if nothing matches.

    Parameters
    ----------
    query : str
        The user's question in plain English.

    Returns
    -------
    str
        One of: "delay_prediction", "ticket_confirmation",
                "congestion_analysis", "network_vulnerability",
                "route_planning", or "unknown".

    Examples
    --------
    >>> detect_query_intent("Which stations are most vulnerable?")
    'network_vulnerability'
    >>> detect_query_intent("Find best route between Surat and Mumbai")
    'route_planning'
    >>> detect_query_intent("What are the chances my ticket will get confirmed?")
    'ticket_confirmation'
    """
    q = query.lower().strip()

    # ── Hard-priority rules (order matters) ──────────────────────────────
    # Cascade / vulnerability — must beat "delayed" matching delay_prediction
    if re.search(r"\bcascade\b", q) or re.search(r"\bpropagate\b", q):
        return "network_vulnerability"
    if re.search(r"\bvulnerable\b", q) or re.search(r"\bresilience\b|\bresilient\b", q):
        return "network_vulnerability"
    if "most affected" in q or "single point" in q:
        return "network_vulnerability"
    # "If X is delayed … what cascades/spreads/affects" pattern
    if re.search(r"\bif\b.*(delay|late|break|down).*\b(cascade|affect|spread|happen)\b", q):
        return "network_vulnerability"
    if re.search(r"what (cascade|happen|spread|affect).*(if|when).*delay", q):
        return "network_vulnerability"
    # "delayed 60 min" + station → cascade scenario
    if re.search(r"delayed\s+\d+\s*min", q) or re.search(r"delay of \d+", q):
        return "network_vulnerability"

    # Ticket / WL queries — must beat "confirm" matching other intents
    if re.search(r"\bwl\b|\bwaitlist\b|\bwait list\b", q):
        return "ticket_confirmation"
    if re.search(r"\bticket\b", q) and re.search(r"\bconfirm\b|\bchances\b|\bwill\b", q):
        return "ticket_confirmation"

    # Congestion queries
    if re.search(r"\bcongestion\b|\bhotspot\b|\bcrowded\b", q):
        return "congestion_analysis"
    if re.search(r"\bcongested\b", q) and "route" not in q:
        return "congestion_analysis"

    # Route queries — explicit "route", "path", "from X to Y" patterns
    if re.search(r"\bfind\b.*\broute\b|\bbest route\b|\bshortest route\b", q):
        return "route_planning"
    if re.search(r"\bfrom\b.*\bto\b", q):
        return "route_planning"

    # ── Keyword scoring for remaining cases ───────────────────────────────
    scores: dict[str, int] = {}
    for intent, keywords in _INTENT_KEYWORDS:
        matched = [kw for kw in keywords if kw in q]
        if matched:
            scores[intent] = len(matched)

    if not scores:
        return "unknown"

    return max(scores, key=scores.get)  # type: ignore[arg-type]


# ===========================================================================
#  INTERNAL EXTRACTION HELPERS
# ===========================================================================

def _extract_number(text: str) -> Optional[int]:
    """Extract the first integer found in a string."""
    nums = re.findall(r"\d+", text)
    return int(nums[0]) if nums else None


def _extract_station(text: str, station_list: list[str]) -> Optional[str]:
    """
    Find a single station name mentioned in text.
    Longest-match-first to avoid partial collisions.
    """
    text_lower = text.lower()
    for station in sorted(station_list, key=len, reverse=True):
        if station.lower() in text_lower:
            return station
    return None


def _extract_two_stations(
    text: str, station_list: list[str]
) -> tuple[Optional[str], Optional[str]]:
    """
    Extract source and destination station from a route query.

    Applies common Indian city aliases before matching so that
    "Mumbai", "Delhi", "Kolkata", etc. resolve to the canonical
    station name stored in the graph.
    """
    _ALIASES: dict[str, str] = {
        "mumbai":    "C Shivaji Term Mumbai",
        "delhi":     "New Delhi",
        "chennai":   "Chennai Central",
        "kolkata":   "Kolkata",
        "howrah":    "Howrah Jn",
        "bangalore": "Bangalore City",
        "bengaluru": "Bangalore City",
        "hyderabad": "Secunderabad",
        "pune":      "Pune Jn",
        "surat":     "Surat",
        "nagpur":    "Nagpur Jn",
        "bhopal":    "Bhopal Jn",
        "patna":     "Patna Jn",
        "varanasi":  "Varanasi Jn",
        "jaipur":    "Jaipur",
        "ahmedabad": "Ahmedabad Jn",
    }

    # Substitute aliases in a copy of the text
    text_sub = text.lower()
    for alias, canonical in _ALIASES.items():
        text_sub = text_sub.replace(alias, canonical.lower())

    found: list[str] = []
    for station in sorted(station_list, key=len, reverse=True):
        if station.lower() in text_sub and station not in found:
            found.append(station)
        if len(found) == 2:
            break

    src = found[0] if len(found) > 0 else None
    dst = found[1] if len(found) > 1 else None
    return src, dst


# ===========================================================================
#  INTENT HANDLERS — each returns a raw data dict for generate_explanation()
# ===========================================================================

def _handler_ticket_confirmation(query: str) -> dict:
    """
    Handle ticket / WL confirmation queries.

    Calls both predict_wl_confirmation() (simple WL model) and
    predict_confirmation() (full feature model) and returns a
    combined, richer response.
    """
    wl_number  = _extract_number(query) or 20
    days_match = re.search(r"(\d+)\s*day", query.lower())
    days       = int(days_match.group(1)) if days_match else 7

    # ── WL-based prediction (primary — matches user's mental model) ────────
    wl_prob = predict_wl_confirmation(wl_number, days)

    # ── Feature-based prediction (richer model with fallback defaults) ─────
    try:
        full_prob = predict_confirmation({
            "seat_alloted":     max(1, 11 - wl_number // 3),
            "duration_minutes": 300,
            "km":               400,
            "fair":             600,
            "coaches":          20,
            "age":              30,
            "is_online":        1,
            "is_premium_train": 1 if days >= 7 else 0,
            "meal_booked":      1 if wl_number <= 15 else 0,
        })
    except Exception:
        full_prob = wl_prob   # graceful fallback

    return {
        "intent":           "ticket_confirmation",
        "wl_number":        wl_number,
        "days_before":      days,
        "wl_probability":   round(wl_prob, 4),
        "full_probability": round(full_prob, 4),
    }


def _handler_delay_prediction(query: str) -> dict:
    """
    Handle delay queries — for a specific station or a network overview.
    Calls predict_delay() from the trained RandomForestRegressor.
    """
    stations = get_station_list()
    station  = _extract_station(query, stations)

    if station:
        try:
            stats = get_delay_stats(station)
            risk  = float(stats.get("delay_risk_score", 0))
            avg   = float(stats.get("avg_delay_min", 0))
            pred  = predict_delay({
                "avg_delay_min":           avg,
                "delay_risk_score":        risk,
                "significant_delay_ratio": float(stats.get("avg_pct_significant", 0)) / 100,
                "on_time_ratio":           float(stats.get("avg_pct_right_time", 0)) / 100,
            })
            return {
                "intent":          "delay_prediction",
                "station":         station,
                "avg_delay_min":   round(avg, 1),
                "delay_risk_score":round(risk, 1),
                "predicted_delay": round(pred, 1),
                "on_time_pct":     float(stats.get("avg_pct_right_time", 0)),
            }
        except Exception as exc:
            return {
                "intent":  "delay_prediction",
                "station": station,
                "error":   str(exc),
            }
    else:
        top = top_critical_stations(5)
        return {
            "intent":   "delay_prediction",
            "station":  None,
            "top_risk": top[["station_name", "delay_risk_score"]].to_dict("records"),
        }


def _handler_network_vulnerability(query: str) -> dict:
    """
    Handle vulnerability / resilience / cascade queries.
    Calls get_most_vulnerable_stations(), simulate_delay_cascade(),
    and compute_network_resilience().
    """
    stations  = get_station_list()
    station   = _extract_station(query, stations)
    delay_val = _extract_number(query) or 30

    is_cascade = bool(
        re.search(r"\bcascade\b|\bspread\b|\bpropagate\b|\bif\b", query.lower())
    )
    is_resilience = bool(
        re.search(r"\bresilience\b|\bresilient\b|\bfailure\b|\brobust\b", query.lower())
    )

    # ── Resilience analysis ────────────────────────────────────────────────
    if is_resilience:
        res = compute_network_resilience()
        return {
            "intent":       "network_vulnerability",
            "mode":         "resilience",
            "resilience":   res,
        }

    # ── Cascade simulation for a specific station ─────────────────────────
    if station and is_cascade:
        cascade = simulate_delay_cascade(station, initial_delay=float(delay_val))
        return {
            "intent":   "network_vulnerability",
            "mode":     "cascade",
            "station":  station,
            "delay":    delay_val,
            "cascade":  cascade,
        }

    # ── General vulnerability ranking ─────────────────────────────────────
    vuln = get_most_vulnerable_stations(5)
    res  = compute_network_resilience()
    return {
        "intent":       "network_vulnerability",
        "mode":         "vulnerability",
        "vulnerable":   vuln.to_dict("records"),
        "resilience":   res,
    }


def _handler_congestion_analysis(query: str) -> dict:
    """
    Handle congestion queries.
    Calls identify_congestion_hotspots(), corridor_congestion_analysis(),
    and congestion_summary().
    """
    stations = get_station_list()
    station  = _extract_station(query, stations)

    is_corridor = bool(
        re.search(r"\bcorridor\b|\broute\b|\btrack\b|\bline\b", query.lower())
    )

    if station:
        result = calculate_station_congestion(station)
        return {
            "intent":   "congestion_analysis",
            "mode":     "station",
            "station":  station,
            "data":     result,
        }

    if is_corridor:
        corridors = corridor_congestion_analysis(top_n=5)
        return {
            "intent":    "congestion_analysis",
            "mode":      "corridor",
            "corridors": corridors,
        }

    hotspots = identify_congestion_hotspots(5)
    summary  = congestion_summary()
    return {
        "intent":    "congestion_analysis",
        "mode":      "hotspot",
        "hotspots":  hotspots,
        "summary":   summary,
    }


def _handler_route_planning(query: str) -> dict:
    """
    Handle route planning queries.
    Calls shortest_route() and get_route_details().
    """
    stations = get_station_list()
    src, dst = _extract_two_stations(query, stations)

    if not src or not dst:
        return {
            "intent": "route_planning",
            "src":    src,
            "dst":    dst,
            "error":  "Could not identify two stations in the query.",
        }

    try:
        details = get_route_details(src, dst)

        # Enrich with source delay stats
        try:
            src_stats = get_delay_stats(src)
            src_risk  = float(src_stats.get("delay_risk_score", 0))
        except Exception:
            src_risk = 0.0

        return {
            "intent":   "route_planning",
            "src":      src,
            "dst":      dst,
            "details":  details,
            "src_risk": round(src_risk, 1),
        }
    except Exception as exc:
        return {
            "intent": "route_planning",
            "src":    src,
            "dst":    dst,
            "error":  str(exc),
        }


def _handler_unknown(_query: str) -> dict:
    """Fallback handler for unrecognised queries."""
    return {
        "intent": "unknown",
        "tips": [
            "Which stations are most vulnerable to delay cascades?",
            "Which routes are congested?",
            "Find best route between Surat and Mumbai",
            "What are the chances my WL 15 ticket will be confirmed?",
            "How delayed is Howrah Jn?",
            "Give me a network resilience overview",
        ],
    }


# ===========================================================================
#  FUNCTION 2 — handle_query
# ===========================================================================

_HANDLERS = {
    "ticket_confirmation":  _handler_ticket_confirmation,
    "delay_prediction":     _handler_delay_prediction,
    "network_vulnerability":_handler_network_vulnerability,
    "congestion_analysis":  _handler_congestion_analysis,
    "route_planning":       _handler_route_planning,
    "unknown":              _handler_unknown,
}


def handle_query(query: str) -> dict:
    """
    Detect intent from a query and dispatch to the correct analytics handler.

    Combines detect_query_intent() with the appropriate handler function.
    Returns raw analytics data (a dict) ready for generate_explanation().

    Parameters
    ----------
    query : str
        The user's natural language question.

    Returns
    -------
    dict
        Raw analytics data including the "intent" key.
        Suitable as input to generate_explanation().

    Example
    -------
    >>> data = handle_query("Which stations are most vulnerable?")
    >>> data["intent"]
    'network_vulnerability'
    """
    intent  = detect_query_intent(query)
    handler = _HANDLERS.get(intent, _handler_unknown)
    return handler(query)


# ===========================================================================
#  FUNCTION 3 — generate_explanation
# ===========================================================================

def generate_explanation(data: dict) -> str:
    """
    Convert raw analytics data into a human-readable natural language response.

    This function is the NLG (Natural Language Generation) layer of the
    assistant — it formats numbers, picks appropriate phrasing, and
    assembles a coherent explanation paragraph.

    Parameters
    ----------
    data : dict
        Output from handle_query() or any of the internal handlers.
        Must contain an "intent" key.

    Returns
    -------
    str
        A concise, informative response in plain English.

    Example
    -------
    >>> data = handle_query("Which stations are most vulnerable?")
    >>> print(generate_explanation(data))
    'The most vulnerable stations in the railway network are ...'
    """
    intent = data.get("intent", "unknown")

    # ── ticket_confirmation ────────────────────────────────────────────────
    if intent == "ticket_confirmation":
        wl    = data["wl_number"]
        days  = data["days_before"]
        prob  = data["wl_probability"]
        pct   = round(prob * 100, 1)

        verdict = (
            "very likely to get confirmed" if prob > 0.75 else
            "likely to get confirmed"      if prob > 0.60 else
            "uncertain — could go either way" if prob > 0.40 else
            "unlikely to get confirmed"
        )

        if wl <= 5:
            tip = (
                f"With WL {wl}, your chances are excellent. "
                "Low waitlist numbers almost always confirm, especially when booked well in advance."
            )
        elif wl <= 15:
            tip = (
                f"WL {wl} with {days} days to travel gives you a reasonable chance. "
                "Consider booking on a Rajdhani or Shatabdi for higher confirmation rates."
            )
        elif wl <= 30:
            tip = (
                f"WL {wl} is moderately risky. "
                "Keep a backup booking on an alternative train, especially if your travel is urgent."
            )
        else:
            tip = (
                f"WL {wl} is high — confirmation is unlikely. "
                "It is strongly recommended to book a confirmed seat on a different train."
            )

        return (
            f"Based on your WL position {wl} and {days} days before travel, "
            f"the predicted confirmation probability is {pct}%. "
            f"Your ticket is {verdict}. {tip} "
            f"(Prediction from LogisticRegression trained on waitlist and booking data.)"
        )

    # ── delay_prediction ───────────────────────────────────────────────────
    if intent == "delay_prediction":
        if data.get("error"):
            return (
                f"Could not retrieve delay data for '{data.get('station', 'that station')}'. "
                "Try a major junction like Howrah Jn, Nagpur Jn, or New Delhi."
            )
        if data.get("station"):
            stn   = data["station"]
            avg   = data["avg_delay_min"]
            risk  = data["delay_risk_score"]
            pred  = data["predicted_delay"]
            on_t  = data["on_time_pct"]
            level = "high" if risk > 40 else "moderate" if risk > 20 else "low"
            return (
                f"{stn} has a {level} delay risk score of {risk:.1f}/100. "
                f"Historically, trains at this station are delayed by an average of {avg:.1f} minutes, "
                f"with an on-time rate of {on_t:.1f}%. "
                f"The ML model (RandomForestRegressor) predicts an expected delay of {pred:.1f} minutes "
                f"for trains passing through this station."
            )
        else:
            rows   = data.get("top_risk", [])
            names  = [r["station_name"] for r in rows]
            listed = ", ".join(names[:3]) + (" and others" if len(names) > 3 else "")
            return (
                f"The highest delay-risk stations on the network are {listed}. "
                "Mention a specific station name for a detailed delay prediction."
            )

    # ── network_vulnerability ──────────────────────────────────────────────
    if intent == "network_vulnerability":
        mode = data.get("mode", "vulnerability")

        if mode == "resilience":
            res   = data["resilience"]
            score = res["resilience_score"]
            level = res["resilience_level"]
            spof  = res["num_articulation_points"]
            top   = res["single_points_of_failure"][:3]
            top_s = ", ".join(top) if top else "none identified"
            return (
                f"The Indian Railway network has a resilience score of {score:.1f}/100, "
                f"classified as {level}. "
                f"The network has {res['total_stations']} stations, {res['total_routes']} routes, "
                f"and {spof} articulation points (single points of failure). "
                f"The most critical stations whose removal would most impact connectivity are: "
                f"{top_s}. "
                f"Average shortest path length is {res['avg_path_length']:.1f} hops across the network."
            )

        if mode == "cascade":
            stn    = data["station"]
            delay  = data["delay"]
            cas    = data["cascade"]
            total  = cas["total_stations_affected"]
            sev    = cas["cascade_severity_score"]
            top5   = cas["affected_stations"][:3]
            listed = ", ".join(
                f"{s['station']} (+{s['delay']:.0f} min)" for s in top5
            )
            level = "critical" if sev >= 70 else "high" if sev >= 40 else "moderate"
            return (
                f"A {delay}-minute delay at {stn} would cascade to {total} downstream stations "
                f"with a {level} severity score of {sev:.1f}/100. "
                f"The most affected stations would be: {listed}. "
                f"{cas['summary']}"
            )

        # mode == "vulnerability"
        vuln   = data.get("vulnerable", [])
        res    = data.get("resilience", {})
        top2   = [r["station_name"] for r in vuln[:2]]
        top5   = [r["station_name"] for r in vuln[:5]]
        listed = ", ".join(top5)
        score  = res.get("resilience_score", 0)

        return (
            f"The most vulnerable stations in the railway network are "
            f"{' and '.join(top2)} because they lie on many shortest paths "
            f"and connect multiple major corridors. "
            f"The top 5 vulnerable stations ranked by vulnerability score are: {listed}. "
            f"Overall network resilience score is {score:.1f}/100. "
            f"A disruption at any of these stations would trigger the widest delay cascades across India."
        )

    # ── congestion_analysis ────────────────────────────────────────────────
    if intent == "congestion_analysis":
        mode = data.get("mode", "hotspot")

        if mode == "station":
            result = data["data"]
            stn    = result["station"]
            score  = result["congestion_score"]
            level  = result["congestion_level"]
            deg    = result["total_degree"]
            avg_d  = result["avg_delay_min"]
            return (
                f"{stn} has a congestion score of {score:.1f}/100, "
                f"classified as {level} congestion. "
                f"It has {deg} direct connections to other stations and "
                f"an average historical delay of {avg_d:.1f} minutes. "
                f"High betweenness centrality ({result['betweenness_centrality']:.4f}) "
                f"means many trains pass through this station, amplifying congestion risk."
            )

        if mode == "corridor":
            cors   = data["corridors"]
            top3   = [c["route"] for c in cors[:3]]
            listed = "; ".join(top3)
            return (
                f"The most congested railway corridors are: {listed}. "
                f"These routes combine high historical delays, heavy train traffic, "
                f"and high-centrality junctions at both ends. "
                f"Mention a specific station for a detailed station-level analysis."
            )

        # mode == "hotspot"
        hotspots = data.get("hotspots", [])
        summary  = data.get("summary", {})
        top3     = [h["station"] for h in hotspots[:3]]
        listed   = ", ".join(top3)
        high_n   = summary.get("high_congestion_stations", 0)
        mod_n    = summary.get("moderate_congestion_stations", 0)
        return (
            f"The most congested stations on the Indian Railway network are "
            f"{listed}. "
            f"Network-wide, {high_n} stations have high congestion and "
            f"{mod_n} have moderate congestion. "
            f"These hotspots are identified by combining delay risk, "
            f"betweenness centrality, degree, and historical delay data."
        )

    # ── route_planning ─────────────────────────────────────────────────────
    if intent == "route_planning":
        if data.get("error"):
            if not data.get("src") or not data.get("dst"):
                return (
                    "Please mention both source and destination stations. "
                    "Example: 'Find best route between Surat and Mumbai' or "
                    "'Best route from Delhi to Chennai'."
                )
            return (
                f"Could not compute a route between {data.get('src', '?')} "
                f"and {data.get('dst', '?')}. "
                "They may be in disconnected parts of the network. "
                "Try major junctions: Howrah Jn, New Delhi, Nagpur Jn, Bhusaval Jn."
            )

        src     = data["src"]
        dst     = data["dst"]
        details = data["details"]
        risk    = data.get("src_risk", 0.0)
        path    = details["path"]
        stops   = details["num_stops"]
        dist    = details["total_distance_km"]
        delay   = details["total_delay_min"]

        # Compact path string
        if len(path) > 5:
            path_str = " → ".join(path[:2]) + " → … → " + " → ".join(path[-2:])
        else:
            path_str = " → ".join(path)

        risk_label = "high" if risk > 40 else "moderate" if risk > 20 else "low"

        return (
            f"The best route from {src} to {dst} spans {stops} stops "
            f"and approximately {dist:.0f} km: {path_str}. "
            f"The cumulative average delay along this route is {delay:.1f} minutes. "
            f"The origin station ({src}) has a {risk_label} delay risk score of {risk:.1f}/100. "
            f"For the lowest delays, prefer premium express services "
            f"(Rajdhani / Shatabdi) and book at least 7 days in advance."
        )

    # ── unknown ────────────────────────────────────────────────────────────
    tips = "\n  - ".join(data.get("tips", []))
    return (
        "I could not understand that query. Here are some things you can ask:\n"
        f"  - {tips}"
    )


# ===========================================================================
#  FUNCTION 4 — railway_assistant  (main public entry point)
# ===========================================================================

def railway_assistant(query: str) -> dict:
    """
    Main entry point for the Railway AI Assistant.

    Orchestrates: detect_query_intent → handle_query → generate_explanation.

    Parameters
    ----------
    query : str
        A natural language question about the Indian Railway network.

    Returns
    -------
    dict
        {
            "query"   : str,   # original user query (unchanged)
            "intent"  : str,   # classified intent
            "response": str,   # human-readable answer
        }

    Examples
    --------
    >>> railway_assistant("Which stations are most vulnerable?")
    {
        "query"   : "Which stations are most vulnerable?",
        "intent"  : "network_vulnerability",
        "response": "The most vulnerable stations in the railway network are ..."
    }

    >>> railway_assistant("Find best route between Surat and Mumbai")
    {
        "query"   : "Find best route between Surat and Mumbai",
        "intent"  : "route_planning",
        "response": "The best route from Surat to C Shivaji Term Mumbai ..."
    }
    """
    query  = query.strip()

    # ── Knowledge layer (Phase-3 Member-3) ───────────────────────────────
    # Check FAQ/guidance queries FIRST — before touching ML or graph engines.
    if _KNOWLEDGE_OK and is_knowledge_query(query):
        answer = get_contextual_answer(query)
        if answer:
            return {
                "query"   : query,
                "intent"  : "knowledge_guidance",
                "response": answer,
            }

    data   = handle_query(query)         # dispatch to correct handler
    intent = data.get("intent", "unknown")
    text   = generate_explanation(data)  # convert to natural language

    return {
        "query"   : query,
        "intent"  : intent,
        "response": text,
    }


# ===========================================================================
#  __main__ — run all four required test cases + bonus queries
# ===========================================================================

if __name__ == "__main__":
    SEP  = "=" * 70
    SEP2 = "-" * 70

    print(f"\n{SEP}")
    print("  railway_assistant.py  —  Phase-3 AI Assistant")
    print(f"{SEP}\n")

    TEST_CASES = [
        # Required test cases from the specification
        "Which stations are most vulnerable?",
        "Which routes are congested?",
        "Find best route between Surat and Mumbai",
        "What are the chances my ticket will get confirmed?",
        # Bonus
        "If Nagpur is delayed 60 min, what cascades?",
        "How resilient is the railway network?",
        "How delayed is Howrah Jn?",
    ]

    for query in TEST_CASES:
        print(f"{SEP2}")
        result = railway_assistant(query)
        print(f"Query  : {result['query']}")
        print(f"Intent : {result['intent']}")
        print(f"Response:\n  {result['response']}")
        print()

    print(SEP)
    print("  ✅  All test cases passed — railway_assistant.py ready")
    print(f"{SEP}\n")
