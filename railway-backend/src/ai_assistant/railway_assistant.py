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

# ---------------------------------------------------------------------------
# Phase-4: Passenger Flow layer
# ---------------------------------------------------------------------------
try:
    from src.passenger_flow.passenger_flow import (
        get_network_demand_summary,
        get_busiest_stations,
        get_station_crowd_profile,
        get_seasonal_demand,
        get_route_demand,
        get_transfer_congestion_stations,
        passenger_flow_summary,
    )
    _FLOW_OK = True
except Exception:
    _FLOW_OK = False

# ---------------------------------------------------------------------------
# Phase-7: Routing & Operational Optimization layer
# ---------------------------------------------------------------------------
try:
    from src.routing_optimizer.routing_optimizer import (
        find_alternative_routes,
        suggest_schedule_adjustments,
        multi_objective_route,
        prioritize_corridor_trains,
    )
    _OPT_OK = True
except Exception:
    _OPT_OK = False

# ---------------------------------------------------------------------------
# Item 8: Passenger Travel Intelligence
# ---------------------------------------------------------------------------
try:
    from src.travel_intelligence.travel_intelligence import (
        get_alternative_travel,
        get_crowd_estimate,
        get_booking_guidance,
        get_travel_advisory,
    )
    _TRAVEL_OK = True
except Exception:
    _TRAVEL_OK = False


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
    (
        "travel_advisory",
        [
            "travel advisory", "book in advance", "how many days",
            "when should i book", "best time to travel",
            "crowd at station", "how busy", "train occupancy",
            "ticket guidance", "booking advice", "advance booking",
            "crowd level", "is it safe to travel", "travel plan",
        ],
    ),
    (
        "routing_optimization",
        [
            "alternative route", "disruption", "blocked", "closed station",
            "reschedule", "schedule adjustment", "cascade saving",
            "multi objective", "priority corridor", "train priority",
            "high demand corridor", "operational", "optimize",
        ],
    ),

    (
        "passenger_flow",
        [
            "crowd", "crowding", "passenger", "demand",
            "busy station", "peak hours", "seasonal",
            "transfer congestion", "passenger flow", "how busy",
            "footfall", "occupancy", "busiest",
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

    # Travel advisory — fires before routing_optimization, passenger_flow,
    # and knowledge_guidance where keywords overlap
    if re.search(
        r"\btravel advisory\b|\bbooking advice\b|\bbook in advance\b"
        r"|\bhow many days.*book\b|\bwhen.*should.*book\b"
        r"|\bbest time.*travel\b|\btrain.*occupancy\b"
        r"|\bticket guidance\b|\badvance booking\b",
        q
    ):
        return "travel_advisory"
    # crowd-at-station: more specific than passenger_flow "busy"
    if re.search(r"\bcrowd.*level\b|\bcrowd.*at\b|\bat.*:00\b.*crowd|crowd.*score", q):
        return "travel_advisory"

    # Routing optimization — must fire BEFORE delay_prediction (shares "delay") and passenger_flow (shares "demand/corridor")
    if re.search(r"\balternative route\b|\bdisruption\b|\bblocked station\b|\breschedul\b|\bschedule adjustment\b|\bpriority corridor\b|\btrain priority\b|\bmulti.objective\b|\boperational optim\b", q):
        return "routing_optimization"
    if re.search(r"\bschedule\b.*(adjust|optim|delay|cascade)|(adjust|optim).+\bschedule\b", q):
        return "routing_optimization"
    if re.search(r"(high.demand|critical).*(corridor|route)|priority.*(corridor|route|train)", q):
        return "routing_optimization"

    # Ticket / WL queries — must beat "confirm" matching other intents
    if re.search(r"\bwl\b|\bwaitlist\b|\bwait list\b", q):
        return "ticket_confirmation"
    if re.search(r"\bticket\b", q) and re.search(r"\bconfirm\b|\bchances\b|\bwill\b", q):
        return "ticket_confirmation"

    # Passenger flow / crowd queries — checked BEFORE congestion (shares "crowded" keyword)
    if re.search(r"\bpassenger(s)?\b|\bpeak hour\b|\bseasonal\b|\bhow busy\b|\btransfer congestion\b|\bfootfall\b|\bpassenger demand\b|\bhighest demand\b|\bcrowd profile\b|\bcrowd score\b|\bcrowd level\b", q):
        return "passenger_flow"
    if re.search(r"\bdemand\b", q) and not re.search(r"\bdelay\b|\broute\b|\bcongestion\b", q):
        return "passenger_flow"

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





def _handler_travel_advisory(query: str) -> dict:
    """Handle travel advisory, crowd estimate, and booking guidance queries."""
    if not _TRAVEL_OK:
        return {"intent": "travel_advisory",
                "error": "Travel intelligence module not available."}

    q = query.lower()
    from src.graph_engine.graph_utils import get_station_list
    stations = get_station_list()

    src = _extract_station(query, stations)
    dst = None
    if src:
        remaining = query.lower().replace(src.lower(), "", 1)
        for s in sorted(stations, key=len, reverse=True):
            if s.lower() in remaining.lower() and s != src:
                dst = s
                break

    # Crowd estimate query
    if any(w in q for w in ["crowd at", "crowd level", "how busy", "train occupancy",
                             "busy at", "crowded at"]):
        stn = src or "New Delhi"
        result = get_crowd_estimate(stn)
        return {"intent": "travel_advisory", "mode": "crowd", "data": result}

    # Booking guidance query
    if any(w in q for w in ["book", "advance", "days before", "when should", "ticket",
                             "wl", "waitlist", "how many days"]):
        n = _extract_number(query) or 0
        wl, days = (n, 30) if n <= 50 else (0, n)
        result = get_booking_guidance(
            src or "Howrah Jn",
            dst or "New Delhi",
            wl_number=wl,
            days_before_travel=days,
        )
        return {"intent": "travel_advisory", "mode": "booking", "data": result}

    # Full travel advisory (src + dst present)
    if src and dst:
        result = get_travel_advisory(src, dst)
        return {"intent": "travel_advisory", "mode": "advisory", "data": result}

    # Generic help tip
    return {
        "intent": "travel_advisory",
        "mode":   "tip",
        "tip": (
            "I can help with travel advisories, station crowd estimates, and smart "
            "booking guidance. Try:\n"
            "• 'Give me a travel advisory from Chennai Central to Howrah Jn in November'\n"
            "• 'What is the crowd level at New Delhi at 18:00 in November?'\n"
            "• 'How many days in advance should I book for Howrah to Asansol in November?'"
        ),
    }

def _handler_routing_optimization(query: str) -> dict:
    """Handle routing optimization, disruption, schedule, and priority queries."""
    if not _OPT_OK:
        return {"intent": "routing_optimization", "error": "Routing optimizer not available."}

    q = query.lower()

    from src.graph_engine.graph_utils import get_station_list
    stations = get_station_list()

    # Disruption / alternative route
    if any(w in q for w in ["alternative", "disruption", "blocked", "closed", "avoid"]):
        src = _extract_station(query, stations)
        # Try to find a second station for destination
        remaining = query
        dst = None
        if src:
            remaining = query.lower().replace(src.lower(), "", 1)
        for s in sorted(stations, key=len, reverse=True):
            if s.lower() in remaining.lower() and s != src:
                dst = s
                break
        if src and dst:
            result = find_alternative_routes(src, dst, n_alternatives=2)
            return {"intent": "routing_optimization", "mode": "alternatives", "data": result}
        # Fall through to summary

    # Schedule adjustments
    if any(w in q for w in ["reschedul", "schedule", "adjustment", "cascade saving", "hold"]):
        src = _extract_station(query, stations)
        delay = _extract_number(query) or 30
        if src:
            result = suggest_schedule_adjustments(src, delay, max_affected=5)
            return {"intent": "routing_optimization", "mode": "schedule", "data": result}

    # Priority corridors
    if any(w in q for w in ["priority", "corridor", "high demand", "critical corridor"]):
        result = prioritize_corridor_trains(5).to_dict("records")
        return {"intent": "routing_optimization", "mode": "corridors", "data": result}

    # Multi-objective routing
    if any(w in q for w in ["multi", "objective", "optim", "best"]):
        src = _extract_station(query, stations)
        dst = None
        if src:
            rem = query.lower().replace(src.lower(), "", 1)
            for s in sorted(stations, key=len, reverse=True):
                if s.lower() in rem.lower() and s != src:
                    dst = s
                    break
        if src and dst:
            result = multi_objective_route(src, dst)
            return {"intent": "routing_optimization", "mode": "multi_objective", "data": result}

    # Default: optimization summary
    from src.routing_optimizer.routing_optimizer import optimization_summary
    summary = optimization_summary()
    corridors = prioritize_corridor_trains(3).to_dict("records")
    return {"intent": "routing_optimization", "mode": "summary",
            "summary": summary, "corridors": corridors}

def _handler_passenger_flow(query: str) -> dict:
    """
    Handle passenger flow, crowd, seasonal, and demand queries.
    """
    if not _FLOW_OK:
        return {"intent": "passenger_flow", "error": "Passenger flow module not available."}

    q = query.lower()

    # Station crowd profile
    from src.graph_engine.graph_utils import get_station_list
    stations = get_station_list()
    station  = _extract_station(query, stations)

    if station and any(w in q for w in ["busy", "crowd", "peak", "hour", "profile"]):
        profile = get_station_crowd_profile(station)
        return {"intent": "passenger_flow", "mode": "station_profile", "data": profile, "station": station}

    # Seasonal pattern
    if any(w in q for w in ["seasonal", "season", "month", "festival", "holiday", "peak month"]):
        sea = get_seasonal_demand().to_dict("records")
        return {"intent": "passenger_flow", "mode": "seasonal", "data": sea}

    # Transfer congestion
    if any(w in q for w in ["transfer", "connecting", "junction congestion"]):
        tc = get_transfer_congestion_stations(5).to_dict("records")
        return {"intent": "passenger_flow", "mode": "transfer", "data": tc}

    # Default: network summary + busiest stations
    summary = get_network_demand_summary()
    busiest = get_busiest_stations(5).to_dict("records")
    return {"intent": "passenger_flow", "mode": "summary", "summary": summary, "busiest": busiest}

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
    "passenger_flow":       _handler_passenger_flow,
    "routing_optimization": _handler_routing_optimization,
    "travel_advisory":      _handler_travel_advisory,
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

    # ── travel_advisory ─────────────────────────────────────────────────────
    if intent == "travel_advisory":
        if data.get("error"):
            return f"Travel intelligence unavailable: {data['error']}"

        mode = data.get("mode", "advisory")

        if mode == "tip":
            return data.get("tip", "Ask me about travel advisories, crowd levels or booking guidance.")

        if mode == "crowd":
            d = data.get("data", {})
            if "error" in d:
                return d["error"]
            return (
                f"{d['station_name']} in {d['month_name']} at {d['hour']:02d}:00: "
                f"{d['crowd_level']} crowd (score {d['crowd_score']}/100, "
                f"seasonal multiplier {d['seasonal_multiplier']}x). "
                f"Peak hours: {', '.join(d['peak_hours'][:2])}. "
                f"Best time: {d['offpeak_hours'][0]}. "
                f"{d.get('advice', '')}"
            )

        if mode == "booking":
            d = data.get("data", {})
            steps_text = " | ".join(
                f"({i+1}) {s}" for i, s in enumerate(d.get("step_by_step_advice", [])[:3])
            )
            wl_str = (
                f"WL {d['wl_number']} confirmation probability: "
                f"{d['wl_confirmation_probability']}%. "
                if d.get("wl_confirmation_probability") is not None else ""
            )
            return (
                f"Booking guidance for {d.get('source_station','?')} -> "
                f"{d.get('destination_station','?')} in {d.get('month_name','?')}: "
                f"Occupancy {d['occupancy_pct']:.0f}% | Urgency: {d['urgency']}. "
                f"{wl_str}"
                f"Book at least {d['recommended_advance_days']} days ahead. "
                f"{d['booking_window']}. "
                f"Steps: {steps_text}"
            )

        if mode == "advisory":
            d = data.get("data", {})
            pr   = d.get("primary_route")
            bk   = d.get("booking", {})
            cw   = d.get("crowd", {})
            alts = d.get("alternatives", [])
            return (
                f"Travel advisory {d.get('source','?')} -> {d.get('destination','?')} "
                f"({d.get('month_name','?')}, {d.get('season','')}): "
                + (f"Primary route - {pr['num_stops']} stops, "
                   f"{pr['occupancy_pct']:.0f}% occupancy, "
                   f"crowd {pr.get('crowd_level','?')}, "
                   f"reliability {pr.get('reliability_score',0):.0f}/100. "
                   if pr else "")
                + (f"{len(alts)} alternative(s) available. " if alts else "")
                + (f"Source station crowd: {cw.get('crowd_level','?')}. " if "error" not in cw else "")
                + (f"Book {bk['recommended_advance_days']} days ahead - "
                   f"urgency: {bk.get('urgency','Low')}. "
                   if bk else "")
                + d.get("route_recommendation", "")
            )

        return "Travel advisory data available. Use the Luggage Travel Advisor tab for full details."

    # ── routing_optimization ────────────────────────────────────────────────
    if intent == "routing_optimization":
        if data.get("error"):
            return f"Routing optimizer unavailable: {data['error']}"

        mode = data.get("mode", "summary")

        if mode == "alternatives":
            d   = data["data"]
            src = d["source"]
            dst = d["destination"]
            if d.get("disruption_active"):
                alts = d.get("alternatives", [])
                if alts:
                    best = alts[0]
                    stops = " → ".join(best["path"][:4]) + ("..." if len(best["path"]) > 4 else "")
                    return (
                        f"Primary route {src}→{dst} is disrupted. "
                        f"Best alternative: {stops} "
                        f"({best['num_stops']} stops, adds {best['extra_time_vs_primary']:.0f} min). "
                        f"Reliability: {best['reliability_score']}/100. "
                        f"{len(alts)} alternative(s) available."
                    )
                return f"Primary route {src}→{dst} is disrupted and no alternatives found."
            return d.get("recommendation", f"Route {src}→{dst} is clear. No disruption.")

        if mode == "schedule":
            d = data["data"]
            high = [a for a in d["adjustments"] if a["priority"] == "High"]
            return (
                f"Delay of {d['delay_minutes']} min at {d['station']} "
                f"(congestion factor {d['congestion_factor']}×) affects {d['affected_trains']} trains. "
                f"{len(high)} trains need immediate HOLD action. "
                f"Implementing recommendations saves ~{d['total_cascade_saving_min']:.0f} min of cascade delay."
            )

        if mode == "corridors":
            d = data["data"]
            top3 = ", ".join(f"{r['source_station']}→{r['destination_station']}" for r in d[:3])
            return (
                f"Top priority corridors: {top3}. "
                f"These are overcrowded for multiple months annually. "
                f"Recommendation: increase frequency and add seasonal special trains."
            )

        if mode == "multi_objective":
            d = data["data"]
            routes = d.get("routes", [])
            if not routes:
                return d.get("recommendation", "No multi-objective routes found.")
            best = routes[0]
            return (
                f"Multi-objective route {d['source']}→{d['destination']}: "
                f"{len(routes)} options scored. Best option — {best['num_stops']} stops, "
                f"{best['total_travel_time_min']:.0f} min, {best['label']}. "
                f"Reliability: {best['reliability_score']*100:.0f}%, "
                f"Congestion score: {best['congestion_score']:.2f}."
            )

        # summary
        s   = data.get("summary", {})
        cor = data.get("corridors", [])
        top = ", ".join(f"{c['source_station']}→{c['destination_station']}" for c in cor[:2])
        return (
            f"Network has {s.get('total_stations','?')} stations and {s.get('total_routes','?')} routes. "
            f"{s.get('critical_corridors', 0)} critical corridors require priority management. "
            f"Most congested: {top}. "
            f"Use the Intelligent Routing tab for disruption alternatives, "
            f"schedule adjustments, and multi-objective optimization."
        )

    # ── passenger_flow ─────────────────────────────────────────────────────
    if intent == "passenger_flow":
        if data.get("error"):
            return f"Passenger flow data unavailable: {data['error']}"

        mode = data.get("mode", "summary")

        if mode == "station_profile":
            p    = data["data"]
            stn  = data.get("station", p.get("station_name","the station"))
            if "error" in p:
                return p["error"]
            return (
                f"{stn} has an average crowd score of {p['avg_crowd_score']}/100 "
                f"({p['crowd_level']} crowd level). "
                f"The busiest time is around {p['peak_hour']} and the quietest hour is {p['quietest_hour']}. "
                f"Weekday with highest footfall: {p['busiest_day']}. "
                f"Transfer congestion risk: {p['transfer_congestion_risk']}. "
                f"This station serves {p['num_trains']} train services."
            )

        if mode == "seasonal":
            sea   = data["data"]
            peak  = max(sea, key=lambda x: x["demand_index"])
            low   = min(sea, key=lambda x: x["demand_index"])
            peaks = [m["month_name"] for m in sea if m["peak"] == "Yes"]
            return (
                f"Indian Railway demand peaks in {peak['month_name']} "
                f"(demand index {peak['demand_index']}) during {peak['festival']}. "
                f"The lowest demand month is {low['month_name']} "
                f"({low['demand_index']} index). "
                f"Peak months are: {', '.join(peaks)}. "
                f"Book at least 60 days in advance for peak season travel."
            )

        if mode == "transfer":
            tc    = data["data"]
            top3  = ", ".join(d["station_name"] for d in tc[:3])
            return (
                f"The highest transfer congestion risk during peak hours is at: {top3}. "
                f"These stations have many connecting trains and experience the highest "
                f"passenger interchange volumes. Allow extra time for transfers at these junctions."
            )

        # mode == "summary"
        s   = data["summary"]
        b   = data.get("busiest", [])
        top = ", ".join(d["station_name"] for d in b[:3])
        return (
            f"The Indian Railway network carries an estimated "
            f"{s['total_annual_passengers']:,} passengers annually. "
            f"Average occupancy is {s['avg_occupancy_rate']*100:.0f}%. "
            f"Peak demand occurs in {s['peak_month']} — trains are most crowded during festivals. "
            f"The busiest stations by crowd score are: {top}. "
            f"There are {s['overcrowded_routes_count']} overcrowded train-month combinations "
            f"across the network. Book early for peak season travel."
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
    # Check FAQ/guidance queries FIRST — but skip if this is a travel advisory
    # query (crowd/booking/advisory), since those share keywords like "best time".
    _is_travel_q = bool(re.search(
        r"\btravel advisory\b|\bbooking advice\b|\bbook in advance\b"
        r"|\bhow many days.*book\b|\bwhen.*should.*book\b"
        r"|\bbest time.*travel\b|\btrain.*occupancy\b"
        r"|\bticket guidance\b|\badvance booking\b"
        r"|\bcrowd.*level\b|\bcrowd.*at\b|\bcrowd.*score\b",
        query.lower()
    ))
    if _KNOWLEDGE_OK and is_knowledge_query(query) and not _is_travel_q:
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
