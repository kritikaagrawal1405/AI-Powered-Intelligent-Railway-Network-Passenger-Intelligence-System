"""
knowledge_retrieval.py
======================
Phase-3 Member-3: Railway Knowledge Layer
AI-Powered Railway Intelligence System

Provides contextual, rule-based, and FAQ-driven answers by loading
the railway knowledge base (JSON) and retrieving the best-matching
entry for any natural language query.

This layer fills the gap between data-driven ML answers (delays,
WL probability) and explanatory passenger guidance answers
(booking rules, cancellation policy, concessions, Tatkal windows).

Public API
----------
    load_knowledge_base()                -> dict
    retrieve_context(query: str)         -> dict | None
    get_contextual_answer(query: str)    -> str | None
    is_knowledge_query(query: str)       -> bool

Integration with railway_assistant.py
--------------------------------------
    The assistant calls is_knowledge_query(query) first.
    If True, get_contextual_answer(query) returns a full text response
    and the assistant returns it directly without invoking the ML/graph engines.

Example
-------
    from src.knowledge.knowledge_retrieval import get_contextual_answer, is_knowledge_query

    if is_knowledge_query("How early should I book tickets?"):
        answer = get_contextual_answer("How early should I book tickets?")
        print(answer)
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Optional

# ---------------------------------------------------------------------------
# Path to knowledge base JSON
# ---------------------------------------------------------------------------
_HERE  = os.path.dirname(os.path.abspath(__file__))
_KB_PATH = os.path.join(_HERE, "railway_knowledge_base.json")


# ===========================================================================
#  FUNCTION 1 — load_knowledge_base
# ===========================================================================

@lru_cache(maxsize=1)
def load_knowledge_base() -> dict:
    """
    Load and cache the railway knowledge base from JSON.

    Returns
    -------
    dict
        Parsed knowledge base with keys: 'metadata', 'faqs'.
        Returns empty dict with empty 'faqs' list on any load error.

    Example
    -------
    >>> kb = load_knowledge_base()
    >>> len(kb['faqs'])
    14
    """
    try:
        with open(_KB_PATH, "r", encoding="utf-8") as f:
            kb = json.load(f)
        return kb
    except FileNotFoundError:
        return {"metadata": {}, "faqs": []}
    except json.JSONDecodeError as e:
        print(f"[KnowledgeRetrieval] JSON parse error: {e}")
        return {"metadata": {}, "faqs": []}


# ===========================================================================
#  FUNCTION 2 — retrieve_context
# ===========================================================================

def retrieve_context(query: str, top_n: int = 1) -> Optional[dict]:
    """
    Find the best-matching FAQ entry for a natural language query.

    Scoring strategy (additive):
      +3  for each exact keyword match in query
      +5  if query contains a multi-word keyword phrase exactly
      +2  for each word in the question title that appears in query
      +1  for category-level match

    Parameters
    ----------
    query : str
        The user's natural language question.
    top_n : int
        How many top results to consider (default 1, returns the best).

    Returns
    -------
    dict | None
        The best-matching FAQ entry dict, or None if no reasonable match.
        Dict keys: id, category, keywords, question, answer, tips.

    Example
    -------
    >>> entry = retrieve_context("How early should I book tickets?")
    >>> entry['id']
    'bk_001'
    """
    kb    = load_knowledge_base()
    faqs  = kb.get("faqs", [])
    if not faqs:
        return None

    q_lower = query.lower().strip()
    q_words = set(re.findall(r"\b\w+\b", q_lower))

    scored: list[tuple[float, dict]] = []

    for faq in faqs:
        score = 0.0

        # ── Multi-word keyword phrase match (highest weight) ──────────────
        for kw in faq.get("keywords", []):
            kw_lower = kw.lower()
            if " " in kw_lower:
                if kw_lower in q_lower:
                    score += 5.0
            else:
                if kw_lower in q_words:
                    score += 3.0

        # ── Question title word overlap ────────────────────────────────────
        title_words = set(re.findall(r"\b\w+\b", faq.get("question", "").lower()))
        stop_words  = {"what", "how", "why", "when", "where", "is", "are", "do",
                       "does", "i", "a", "the", "my", "can", "will", "should",
                       "to", "of", "for", "in", "on", "and", "or", "an"}
        meaningful  = title_words - stop_words
        overlap     = meaningful & q_words
        score += len(overlap) * 2.0

        # ── Category match ─────────────────────────────────────────────────
        if faq.get("category", "") in q_lower:
            score += 1.0

        if score > 0:
            scored.append((score, faq))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_faq = scored[0]

    # Minimum threshold — avoid very weak matches
    if best_score < 3.0:
        return None

    return best_faq


# ===========================================================================
#  FUNCTION 3 — get_contextual_answer
# ===========================================================================

def get_contextual_answer(query: str) -> Optional[str]:
    """
    Retrieve a fully formatted natural language answer for a knowledge query.

    Combines the FAQ answer with any practical tips into a single
    human-readable response string ready for display.

    Parameters
    ----------
    query : str
        The user's natural language question.

    Returns
    -------
    str | None
        A formatted answer string, or None if no match found.

    Example
    -------
    >>> ans = get_contextual_answer("How early should I book tickets?")
    >>> "120 days" in ans
    True
    """
    entry = retrieve_context(query)
    if entry is None:
        return None

    answer = entry.get("answer", "")
    tips   = entry.get("tips", [])

    if tips:
        tips_text = "\n".join(f"  • {tip}" for tip in tips)
        return f"{answer}\n\nPractical tips:\n{tips_text}"
    return answer


# ===========================================================================
#  FUNCTION 4 — is_knowledge_query
# ===========================================================================

# Signals that strongly indicate a knowledge/guidance query rather than
# a data/analytics query. Checked before ML models are invoked.
_KNOWLEDGE_SIGNALS: list[str] = [
    # Procedural / how-to
    r"\bhow (to|do i|can i|should i)\b",
    r"\bwhat (is|are|happens|does|affects?|determines?|factors?|influences?)\b",
    r"\bwhen (can|should|do|is)\b",
    r"\bwhere (can|do|is)\b",
    r"\bcan i\b",
    r"\bwhat (are|is) the (rules?|policy|charges?|limit|allowance|steps?|process|procedure)\b",
    # Booking guidance
    r"\bhow early\b",
    r"\badvance booking\b",
    r"\birctc\b",
    r"\btatkal\b",
    r"\bbooking (window|open|time|period)\b",
    r"\b(cancel|refund|cancellation)\b",
    r"\bconcession\b",
    r"\bdiscount\b",
    r"\bsenior citi[sz]en\b",
    r"\bluggage\b",
    r"\bbaggage\b",
    r"\bfood\b",
    r"\bmeal\b",
    r"\bpantry\b",
    r"\bplatform number\b",
    r"\bpnr (status|check|track)\b",
    r"\brac\b",
    r"\b(gnwl|pqwl|rlwl|tqwl)\b",
    r"\bwaitlist (type|quota|kind)\b",
    r"\bclasses? (of train|available|options?)\b",
    r"\b(vande bharat|rajdhani|shatabdi|duronto|tejas)\b",
    r"\bbest train\b",
    r"\bpunctual\b",
    r"\bon.?time\b",
    r"\blost (luggage|item|bag)\b",
    r"\bhelpline\b",
    r"\b139\b",
]

_KNOWLEDGE_SIGNAL_RE = re.compile(
    "|".join(_KNOWLEDGE_SIGNALS), re.IGNORECASE
)

# Keywords that suggest a DATA / ANALYTICS query — these override knowledge signals
_ANALYTICS_OVERRIDES: list[str] = [
    r"\bhow (delayed|late) is\b",
    r"\bdelay (risk|score|stats?|at)\b",
    r"\bcascade\b",
    r"\bresilience\b",
    r"\bcongestion (hotspot|score|level)\b",
    r"\bvulnerable station\b",
    r"\bfind (best )?route\b",
    r"\bshortest (route|path)\b",
    r"\bwl \d+\b",                  # "WL 20" — specific WL number → use ML model
    r"\bwaitlist \d+\b",
    r"\bwl\d+\b",                   # "WL20" no space variant
    r"\bmy (wl|waitlist)\b",        # "my WL ticket" with specific number context
    r"\bwill (it|my ticket) confirm\b",  # specific confirmation prediction request
]

_ANALYTICS_OVERRIDE_RE = re.compile(
    "|".join(_ANALYTICS_OVERRIDES), re.IGNORECASE
)


def is_knowledge_query(query: str) -> bool:
    """
    Determine whether a query should be answered from the knowledge base
    rather than from the ML/graph analytics engines.

    Returns True for guidance, FAQ, and rule-based questions.
    Returns False for data/analytics queries (delay scores, route planning,
    cascade simulation, specific WL number predictions).

    Parameters
    ----------
    query : str

    Returns
    -------
    bool

    Examples
    --------
    >>> is_knowledge_query("How early should I book tickets?")
    True
    >>> is_knowledge_query("Find best route between Surat and Mumbai")
    False
    >>> is_knowledge_query("What affects ticket confirmation?")
    True
    >>> is_knowledge_query("WL 20, 7 days to travel, will it confirm?")
    False
    """
    q = query.strip()

    # Analytics queries take priority — even if they contain FAQ words
    if _ANALYTICS_OVERRIDE_RE.search(q):
        return False

    # Check for knowledge signals
    if _KNOWLEDGE_SIGNAL_RE.search(q):
        # Also check that retrieve_context can find a match (avoids false positives)
        return retrieve_context(q) is not None

    return False


# ===========================================================================
#  FUNCTION 5 — list_categories
# ===========================================================================

def list_categories() -> list[str]:
    """Return all unique FAQ categories in the knowledge base."""
    kb = load_knowledge_base()
    return sorted({f["category"] for f in kb.get("faqs", [])})


# ===========================================================================
#  FUNCTION 6 — get_faqs_by_category
# ===========================================================================

def get_faqs_by_category(category: str) -> list[dict]:
    """
    Return all FAQ entries for a given category.

    Parameters
    ----------
    category : str — one of 'booking', 'waitlist', 'tatkal', 'refund',
                     'concession', 'pnr', 'luggage', 'food', 'platform', 'general'
    """
    kb = load_knowledge_base()
    return [f for f in kb.get("faqs", []) if f["category"] == category.lower()]


# ===========================================================================
#  __main__ — smoke tests
# ===========================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  knowledge_retrieval.py — Phase-3 Knowledge Layer")
    print("=" * 60)

    kb = load_knowledge_base()
    print(f"\n  Loaded {len(kb['faqs'])} FAQ entries across categories: {list_categories()}")

    TEST_QUERIES = [
        ("How early should I book tickets?",         True,  "bk_001"),
        ("What affects ticket confirmation?",        True,  "wl_001"),
        ("What is the IRCTC Tatkal booking window?", True,  "tk_001"),
        ("What are the rules for senior citizens?",  True,  "cc_001"),
        ("WL 20 ticket, 7 days to travel",           False, None),
        ("Find best route between Surat and Mumbai", False, None),
        ("Which stations are most vulnerable?",      False, None),
    ]

    print("\n  Query routing tests:")
    print(f"  {'Query':<50} {'Knowledge?':>10}  {'Entry':>8}  {'Status'}")
    print(f"  {'-'*50} {'-'*10}  {'-'*8}  {'-'*6}")
    all_pass = True
    for q, expected_is_kb, expected_id in TEST_QUERIES:
        is_kb   = is_knowledge_query(q)
        entry   = retrieve_context(q)
        got_id  = entry["id"] if entry else "None"
        correct = (is_kb == expected_is_kb) and (got_id == (expected_id or "None"))
        status  = "✅" if correct else "❌"
        if not correct:
            all_pass = False
        print(f"  {q:<50} {str(is_kb):>10}  {got_id:>8}  {status}")

    print()
    if all_pass:
        print("  ✅  All tests passed — knowledge_retrieval.py ready\n")
    else:
        print("  ⚠️  Some tests failed — check scoring thresholds\n")
