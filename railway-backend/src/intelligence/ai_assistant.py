"""
ai_assistant.py
===============
Phase-3 Member 3: AI Assistant for Railway Intelligence System

A rule-based AI assistant that routes natural language queries to the
appropriate ML model or analytics engine and returns human-readable answers.

As per task list Phase 3 Member 3:
  "Use simple LLM API or rule system"
  "Assistant uses model outputs to answer"

Handles two user types:
  - Passenger: ticket confirmation, delay risk, best route queries
  - Operator:  cascade vulnerability, congestion hotspots, network status

All answers are generated from LIVE model + graph outputs — nothing is hardcoded.

Quick import
------------
    from src.intelligence.ai_assistant import ask, get_sample_queries

Example
-------
    response = ask("What are the chances my WL 20 ticket will confirm?")
    print(response["answer"])

    response = ask("Which stations are most vulnerable to delay cascades?")
    print(response["answer"])
"""

from __future__ import annotations
import re
from typing import Optional

# ── Internal model imports ────────────────────────────────────────────────
from src.graph_engine.graph_utils import (
    load_graph, get_station_list, get_delay_stats,
    top_critical_stations, shortest_route, get_route_details,
    graph_summary,
)
from src.intelligence.delay_cascade import (
    simulate_delay_cascade, get_most_vulnerable_stations,
)
from src.intelligence.congestion_predictor import (
    identify_congestion_hotspots, congestion_summary,
    calculate_station_congestion,
)
from src.ml_models.train_delay_model import predict_delay
from src.ml_models.wl_model import predict_wl_confirmation


# ── Intent catalogue ──────────────────────────────────────────────────────
_INTENTS = [
    ("ticket_confirm",   ["wl", "waitlist", "wait list", "confirm", "ticket",
                          "chances", "berth", "pnr", "booking"]),
    ("delay_query",      ["delay", "late", "on time", "delayed", "how late",
                          "expected delay"]),
    ("cascade_query",    ["cascade", "vulnerable", "propagat", "spread",
                          "which station", "most affected", "risk station"]),
    ("congestion_query", ["congestion", "congested", "hotspot", "overload",
                          "busiest", "crowded", "traffic"]),
    ("route_query",      ["route", "path", "travel from", "go from",
                          "journey from", "trains from", "lowest delay",
                          "best train", "from", "to"]),
    ("network_summary",  ["network", "summary", "overview", "status",
                          "how many station", "total station"]),
]


# ===========================================================================
#  INTENT DETECTION
# ===========================================================================

def _detect_intent(query: str) -> str:
    """
    Identify the intent of a user query using keyword matching.

    Hard-priority rules handle ambiguous cases (e.g. 'delayed' in a cascade
    query should not route to delay_query).

    Returns the intent name string, or "unknown" if nothing matches.
    """
    q = query.lower().strip()

    # Hard-priority rules first
    if re.search(r'\bcascade', q) or re.search(r'\bpropagate', q):
        return "cascade_query"
    if re.search(r'\bvulnerable\b', q) or "most affected" in q:
        return "cascade_query"
    if re.search(r'\bcongestion\b', q) or re.search(r'\bhotspot\b', q) or re.search(r'\bcrowded\b', q):
        return "congestion_query"
    if re.search(r'\bnetwork\b', q) and re.search(r'status|overview|summary', q):
        return "network_summary"
    if re.search(r'\bwl\b|\bwaitlist\b|\bwait list\b', q):
        return "ticket_confirm"

    # Score remaining intents
    scores = {}
    for intent, keywords in _INTENTS:
        matched = set(kw for kw in keywords if kw in q)
        if matched:
            scores[intent] = len(matched)

    if not scores:
        return "unknown"
    return max(scores, key=scores.get)


def _extract_number(text: str) -> Optional[int]:
    """Extract the first integer found in a string."""
    nums = re.findall(r'\d+', text)
    return int(nums[0]) if nums else None


def _extract_station(text: str, station_list: list) -> Optional[str]:
    """Find a station name mentioned in the text (longest match first)."""
    text_lower = text.lower()
    for station in sorted(station_list, key=len, reverse=True):
        if station.lower() in text_lower:
            return station
    return None


def _extract_two_stations(text: str, station_list: list) -> tuple:
    """Extract source and destination station from text."""
    # Common city aliases → canonical station name
    aliases = {
        "mumbai":   "C Shivaji Term Mumbai",
        "delhi":    "New Delhi",
        "chennai":  "Chennai Central",
        "kolkata":  "Howrah Jn",
        "howrah":   "Howrah Jn",
        "bangalore":"Bangalore City",
        "bengaluru":"Bangalore City",
        "hyderabad":"Secunderabad",
        "pune":     "Pune Jn",
    }
    # Substitute aliases in text
    text_sub = text.lower()
    for alias, canonical in aliases.items():
        text_sub = text_sub.replace(alias, canonical.lower())

    # Now extract from substituted text
    found = []
    for station in sorted(station_list, key=len, reverse=True):
        if station.lower() in text_sub and station not in found:
            found.append(station)
        if len(found) == 2:
            break
    src = found[0] if len(found) > 0 else None
    dst = found[1] if len(found) > 1 else None
    return src, dst


# ===========================================================================
#  INTENT HANDLERS
# ===========================================================================

def _handle_ticket_confirm(query: str) -> dict:
    """
    Answer waitlist / ticket confirmation queries.
    Calls predict_wl_confirmation() from LogisticRegression (Phase 2 Member 2).
    Inputs: waitlist_no + days_before_travel — exactly as per task spec.
    """
    wl_number   = _extract_number(query) or 20
    days_match  = re.search(r'(\d+)\s*day', query.lower())
    days_before = int(days_match.group(1)) if days_match else 7

    # Direct call to LogisticRegression WL model — auto-trains if pkl missing
    prob = predict_wl_confirmation(wl_number, days_before)

    pct     = round(prob * 100, 1)
    verdict = "✅ Likely to confirm" if prob > 0.65 else \
              "⚠️ Uncertain — could go either way" if prob > 0.35 else \
              "❌ Unlikely to confirm"

    if wl_number <= 10:
        tip = "Low WL number — excellent confirmation chances, especially 7+ days before travel."
    elif wl_number <= 20:
        tip = f"WL {wl_number} is reasonable. Booking {max(10, days_before + 3)} days ahead improves chances."
    elif wl_number <= 35:
        tip = "WL above 20 is uncertain. Consider booking on a different train as backup."
    else:
        tip = "WL above 35 rarely confirms. Book a confirmed ticket on an alternative train."

    answer = (
        f"**WL {wl_number} — Confirmation Probability: {pct}%**\n\n"
        f"Verdict: {verdict}\n\n"
        f"💡 Tip: {tip}\n\n"
        f"_Prediction from LogisticRegression trained on waitlist + days-before-travel data._"
    )
    return {"intent": "ticket_confirm", "answer": answer,
            "probability": prob, "wl_number": wl_number, "days_before": days_before}


def _handle_delay_query(query: str) -> dict:
    """Answer delay queries. Calls predict_delay() from trained RandomForestRegressor."""
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
            level = "🔴 High" if risk > 40 else "🟠 Moderate" if risk > 20 else "🟢 Low"
            answer = (
                f"**Delay Analysis for {station}**\n\n"
                f"- Historical avg delay: **{avg:.1f} min**\n"
                f"- Delay risk score: **{risk:.1f}/100** ({level})\n"
                f"- ML predicted delay: **{pred:.1f} min**\n"
                f"- On-time rate: **{float(stats.get('avg_pct_right_time', 0)):.1f}%**\n\n"
                f"_Prediction from RandomForestRegressor trained on 1,900 real records._"
            )
        except Exception:
            answer = f"Delay data not found for '{station}'. Try a major junction like Howrah Jn or New Delhi."
    else:
        top   = top_critical_stations(5)
        lines = [f"- **{r['station_name']}**: risk {r.get('delay_risk_score', 0):.1f}/100"
                 for _, r in top.iterrows()]
        answer = (
            "**Top 5 High-Risk Stations (Network Overview)**\n\n"
            + "\n".join(lines)
            + "\n\n_Mention a specific station for detailed delay prediction._"
        )
    return {"intent": "delay_query", "answer": answer, "station": station}


def _handle_cascade_query(query: str) -> dict:
    """Answer cascade and vulnerability queries using simulate_delay_cascade()."""
    stations = get_station_list()
    station  = _extract_station(query, stations)
    delay    = _extract_number(query) or 30

    if station and any(w in query.lower() for w in ["cascade", "spread", "propagat", "delayed", "if"]):
        result = simulate_delay_cascade(station, initial_delay=float(delay))
        top5   = result["affected_stations"][:5]
        lines  = [f"- **{s['station']}**: +{s['delay']:.0f} min (hop {s['depth']})" for s in top5]
        score  = result["cascade_severity_score"]
        level  = "🔴 Critical" if score >= 70 else "🟠 High" if score >= 40 else "🟡 Moderate"
        answer = (
            f"**Cascade Simulation: {station} delayed {delay} min**\n\n"
            f"Severity: **{score:.1f}/100** ({level})\n"
            f"Stations affected: **{result['total_stations_affected']}**\n\n"
            f"**Top affected stations:**\n" + "\n".join(lines) +
            f"\n\n_{result['summary']}_"
        )
    else:
        vuln  = get_most_vulnerable_stations(5)
        lines = [f"- **{r['station_name']}**: vulnerability {r['vulnerability_score']:.1f}/100"
                 for _, r in vuln.iterrows()]
        answer = (
            "**Most Vulnerable Stations to Delay Cascades**\n\n"
            + "\n".join(lines)
            + "\n\n💡 These stations sit on many shortest paths — a delay here "
            "spreads to the most downstream stations.\n\n"
            "_Try: 'If Howrah Jn is delayed 45 min, what cascades?'_"
        )
    return {"intent": "cascade_query", "answer": answer}


def _handle_congestion_query(query: str) -> dict:
    """Answer congestion queries using identify_congestion_hotspots()."""
    stations = get_station_list()
    station  = _extract_station(query, stations)

    if station:
        result = calculate_station_congestion(station)
        score  = result["congestion_score"]
        level  = result["congestion_level"]
        icon   = "🔴" if level == "High" else "🟠" if level == "Moderate" else "🟢"
        answer = (
            f"**Congestion Analysis: {station}**\n\n"
            f"- Congestion score: **{score:.1f}/100** {icon} {level}\n"
            f"- Avg delay: **{result['avg_delay_min']:.1f} min**\n"
            f"- Network connections: **{result['total_degree']}** routes\n"
            f"- Betweenness centrality: **{result['betweenness_centrality']:.4f}**\n\n"
            f"_Higher betweenness = more trains pass through = higher congestion risk._"
        )
    else:
        hotspots = identify_congestion_hotspots(5)
        summary  = congestion_summary()
        lines    = [
            f"- **{h['station']}**: {h['congestion_score']:.1f}/100 "
            f"({'🔴' if h['congestion_level']=='High' else '🟠'} {h['congestion_level']})"
            for h in hotspots
        ]
        answer = (
            f"**Network Congestion Summary**\n\n"
            f"🔴 High: {summary['high_congestion_stations']} stations  |  "
            f"🟠 Moderate: {summary['moderate_congestion_stations']} stations  |  "
            f"🟢 Low: {summary['low_congestion_stations']} stations\n\n"
            f"**Top 5 Congestion Hotspots:**\n" + "\n".join(lines) +
            f"\n\n_Mention a station name for a detailed breakdown._"
        )
    return {"intent": "congestion_query", "answer": answer}


def _handle_route_query(query: str) -> dict:
    """Answer route queries using shortest_route() and get_route_details()."""
    stations = get_station_list()
    src, dst = _extract_two_stations(query, stations)

    if not src or not dst:
        return {
            "intent": "route_query",
            "answer": (
                "Please mention both **source** and **destination** stations.\n\n"
                "Example: _'Best route from Mumbai to Delhi'_ or "
                "_'Which trains from Nagpur to Howrah have lowest delay?'_"
            ),
        }

    try:
        details  = get_route_details(src, dst)
        path     = details["path"]
        stops    = details["num_stops"]
        dist     = details["total_distance_km"]
        time_min = details["total_travel_time_min"]
        delay    = details["total_delay_min"]

        try:
            src_stats = get_delay_stats(src)
            src_risk  = float(src_stats.get("delay_risk_score", 0))
        except Exception:
            src_risk = 0.0

        path_str = (" → ".join(path[:3]) + " → … → " + " → ".join(path[-2:])
                    if len(path) > 6 else " → ".join(path))
        risk_label = "🔴 High" if src_risk > 40 else "🟠 Moderate" if src_risk > 20 else "🟢 Low"

        answer = (
            f"**Best Route: {src} → {dst}**\n\n"
            f"📍 Path: {path_str}\n\n"
            f"- Stops: **{stops}**\n"
            f"- Distance: **{dist:.0f} km**\n"
            + (f"- Est. travel time: **{time_min:.0f} min**\n" if time_min > 0 else "") +
            f"- Cumulative avg delay: **{delay:.1f} min**\n"
            f"- Origin delay risk: **{src_risk:.1f}/100** ({risk_label})\n\n"
            f"💡 _For lowest delay, choose premium trains (Rajdhani/Shatabdi) "
            f"and book at least 7 days in advance._"
        )
    except Exception:
        answer = (
            f"Could not compute route between **{src}** and **{dst}**.\n"
            f"They may be in disconnected network segments. "
            f"Try major junctions: Howrah Jn, New Delhi, Nagpur, Bhusaval Jn."
        )
    return {"intent": "route_query", "answer": answer, "source": src, "destination": dst}


def _handle_network_summary(_query: str) -> dict:
    """Return live network status from graph + congestion analytics."""
    gs      = graph_summary()
    summary = congestion_summary()
    top3    = top_critical_stations(3)
    critical_names = ", ".join(top3["station_name"].tolist())

    answer = (
        f"**Indian Railway Network — Live Status**\n\n"
        f"- 🚉 Stations monitored: **{gs['num_stations']}**\n"
        f"- 🛤️ Routes mapped: **{gs['num_routes']}**\n"
        f"- ⏱️ Network avg delay: **{gs['network_avg_delay_min']} min**\n"
        f"- 🔴 High congestion stations: **{summary['high_congestion_stations']}**\n"
        f"- 🟠 Moderate congestion: **{summary['moderate_congestion_stations']}**\n\n"
        f"**Most Critical Junctions:** {critical_names}\n\n"
        f"_These stations have the highest betweenness centrality — "
        "disruptions here cascade across the entire network._"
    )
    return {"intent": "network_summary", "answer": answer}


def _handle_unknown(_query: str) -> dict:
    """Fallback with helpful suggestions."""
    answer = (
        "I'm not sure how to answer that. Here are some things you can ask:\n\n"
        "**🧳 Passenger queries:**\n"
        "- _What are the chances my WL 15 ticket will confirm?_\n"
        "- _How delayed is Howrah Jn?_\n"
        "- _Best route from Mumbai to Delhi_\n\n"
        "**🛠️ Operator queries:**\n"
        "- _Which stations are most vulnerable to delay cascades?_\n"
        "- _Show congestion hotspots_\n"
        "- _If Nagpur is delayed 60 min, what cascades?_\n"
        "- _Network status overview_"
    )
    return {"intent": "unknown", "answer": answer}


# ===========================================================================
#  PUBLIC API
# ===========================================================================

def ask(query: str, user_type: str = "auto") -> dict:
    """
    Main entry point. Route a natural language query to the right handler.

    Parameters
    ----------
    query     : str — the user's question in plain English
    user_type : str — "passenger", "operator", or "auto" (default)

    Returns
    -------
    dict with keys: query, intent, answer, user_type, (+ intent-specific keys)

    Examples
    --------
    >>> ask("What are the chances my WL 20 ticket will confirm?")
    >>> ask("Which stations are most vulnerable to delay cascades?")
    >>> ask("Which trains from Mumbai to Delhi have lowest delay risk?")
    """
    query  = query.strip()
    intent = _detect_intent(query)

    handlers = {
        "ticket_confirm":   _handle_ticket_confirm,
        "delay_query":      _handle_delay_query,
        "cascade_query":    _handle_cascade_query,
        "congestion_query": _handle_congestion_query,
        "route_query":      _handle_route_query,
        "network_summary":  _handle_network_summary,
        "unknown":          _handle_unknown,
    }

    result              = handlers[intent](query)
    result["query"]     = query
    result["user_type"] = user_type
    return result


def get_sample_queries() -> dict:
    """
    Return sample queries for both user types — used to populate UI buttons.

    Returns
    -------
    dict with keys "passenger" and "operator"
    """
    return {
        "passenger": [
            "What are the chances my WL 20 ticket will confirm?",
            "WL 5, travelling in 3 days — will it confirm?",
            "How delayed is Howrah Jn usually?",
            "Best route from Mumbai to Delhi",
            "Which trains from Nagpur to Bhubaneswar have lowest delay?",
        ],
        "operator": [
            "Which stations are most vulnerable to delay cascades?",
            "Show network congestion hotspots",
            "If Nagpur is delayed 60 min, what stations are affected?",
            "Which routes are most congested?",
            "Give me a network status overview",
        ],
    }


# ===========================================================================
#  __main__ — smoke tests
# ===========================================================================

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  ai_assistant.py  —  Phase-3 Member 3")
    print("=" * 65)

    tests = [
        ("PASSENGER", "What are the chances my WL 20 ticket will confirm?"),
        ("PASSENGER", "WL 5, travelling in 3 days — will it confirm?"),
        ("PASSENGER", "How delayed is Howrah Jn?"),
        ("PASSENGER", "Which trains from Mumbai to Delhi have lowest delay risk?"),
        ("OPERATOR",  "Which stations are most vulnerable to delay cascades?"),
        ("OPERATOR",  "If Nagpur is delayed 60 min, what cascades?"),
        ("OPERATOR",  "Show me congestion hotspots"),
        ("OPERATOR",  "Give me a network status overview"),
    ]

    for user_type, query in tests:
        print(f"\n{'─'*65}")
        print(f"  [{user_type}] {query}")
        print(f"{'─'*65}")
        result = ask(query, user_type=user_type.lower())
        print(f"  Intent: {result['intent']}")
        for line in result["answer"].replace("**", "").replace("_", "").split("\n"):
            if line.strip():
                print(f"  {line}")

    print(f"\n{'='*65}")
    print("  ✅  ai_assistant.py ready for dashboard integration")
    print(f"{'='*65}\n")
