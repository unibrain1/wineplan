#!/usr/bin/env python3
"""Composite scoring functions for wine scheduling.

Symbols exported:
  window_position_score — drinking-window position score (0–100, higher = schedule sooner)
  seasonal_score        — seasonal fit penalty (0=perfect, 1=acceptable, 2=poor)
  seasonal_fit_score    — seasonal fit as a 0–100 float (higher = better fit)
  ct_score_component    — CellarTracker quality score normalized to 0–100
  community_score       — community signals score from RSS notes (0–100)
  diversity_score       — diversity penalty based on proximity to similar placed wines (0–100)
  diversity_penalty     — linear decay helper for diversity scoring
  composite_score       — weighted combination of all components (lower = schedule sooner)
"""

import re
from datetime import datetime, timedelta

from wine_utils import CURRENT_YEAR, TYPE_TO_BADGE

# ---------------------------------------------------------------------------
# Window position scoring
# ---------------------------------------------------------------------------


def window_position_score(wine: dict) -> float:
    """Score a wine's drinking-window position on a 0–100 scale.

    Higher scores indicate the wine is more desirable to schedule now.
    The wine dict is never mutated; begin/end inference uses local variables.

    Args:
        wine: Wine dict with optional integer keys BeginConsume and EndConsume.

    Returns:
        Float in [0.0, 100.0].
    """
    begin = wine.get("BeginConsume")
    end = wine.get("EndConsume")

    # --- Missing data handling ---
    if begin is None and end is None:
        return 35.0
    if begin is None and end is not None:
        begin = end - 5
    if end is None and begin is not None:
        end = begin + 10

    assert begin is not None and end is not None  # guaranteed by inference above

    # --- Past peak ---
    if end < CURRENT_YEAR:
        years_past = CURRENT_YEAR - end
        return min(100.0, 70.0 + years_past * 5.0)

    # --- Before window ---
    if begin > CURRENT_YEAR:
        years_before = begin - CURRENT_YEAR
        return max(0.0, 15.0 - years_before * 5.0)

    # --- In window ---
    window_length = end - begin
    if window_length <= 0:
        window_length = 1
    position = (CURRENT_YEAR - begin) / window_length
    peak_quality = 1.0 - abs(position - 0.5) * 2
    end_urgency = position
    blended = 0.5 * peak_quality + 0.5 * end_urgency
    return 30.0 + blended * 35.0


# ---------------------------------------------------------------------------
# Seasonal scoring
# ---------------------------------------------------------------------------

# Red varietals that are "light" and acceptable in spring/summer
LIGHT_RED_KEYWORDS = ["pinot noir", "bardolino", "barbera", "dolcetto", "gamay"]

# Bold red keywords that strongly prefer fall/winter
BOLD_RED_KEYWORDS = [
    "cabernet",
    "syrah",
    "merlot",
    "barolo",
    "bordeaux",
    "rhône",
    "rhone",
    "sangiovese",
    "nebbiolo",
    "tempranillo",
]


def _wine_searchable(wine: dict) -> str:
    """Lowercase concatenation of Wine, Varietal, and MasterVarietal fields."""
    return " ".join(
        [
            wine.get("Wine", ""),
            wine.get("Varietal", ""),
            wine.get("MasterVarietal", ""),
        ]
    ).lower()


def is_bold_red(wine: dict) -> bool:
    return any(kw in _wine_searchable(wine) for kw in BOLD_RED_KEYWORDS)


def is_light_red(wine: dict) -> bool:
    return any(kw in _wine_searchable(wine) for kw in LIGHT_RED_KEYWORDS)


def seasonal_score(wine: dict, season: str) -> int:
    """Penalty for scheduling a wine in the wrong season (higher = worse fit).

    0  perfect fit
    1  acceptable
    2  poor fit
    """
    badge = TYPE_TO_BADGE.get(wine.get("Type", ""), "red")
    if season in ("spring", "summer"):
        if badge in ("sparkling", "rose", "white"):
            return 0
        if badge == "red" and is_light_red(wine):
            return 0
        if badge == "red":
            return 2 if is_bold_red(wine) else 1
    else:  # fall, winter
        if badge == "red":
            return 0
        if badge in ("sparkling", "white"):
            return 1
        if badge == "rose":
            return 2
    return 1


SEASONAL_FIT_MAP: dict[int, float] = {0: 100.0, 1: 50.0, 2: 0.0}


def seasonal_fit_score(wine: dict, season: str) -> float:
    """Return seasonal fit as a 0–100 float (higher = better fit)."""
    return SEASONAL_FIT_MAP[seasonal_score(wine, season)]


# ---------------------------------------------------------------------------
# CT quality scoring
# ---------------------------------------------------------------------------

AVG_CT = 88.0  # default for wines with no CellarTracker score


def ct_score_component(wine: dict) -> float:
    """Normalize CellarTracker score to 0–100 (higher = better quality).

    Anchors at CT=80 (floor). Wines below 80 score 0; above 100 score 100.
    Missing CT defaults to AVG_CT (88.0).
    """
    ct = wine.get("CT")
    if ct is None:
        ct = AVG_CT
    return max(0.0, min(100.0, float((ct - 80) * 5)))


# ---------------------------------------------------------------------------
# Community signals scoring
# ---------------------------------------------------------------------------

# Regex patterns for window drift detection in community note bodies
_DRIFT_DRINK_NOW = re.compile(
    r"past\s+prime|fading|tired|over\s+the\s+hill|declining|drink\s+(it\s+)?now|"
    r"peaked|losing|falling\s+apart|drying\s+out",
    re.IGNORECASE,
)
_DRIFT_HOLD = re.compile(
    r"needs?\s+time|closed|young|tight|tannic|too\s+young|years?\s+away|"
    r"cellaring|not\s+ready",
    re.IGNORECASE,
)


def community_score(
    wine: dict, community_notes: dict[str, list[dict]] | None = None
) -> float:
    """Score based on community tasting note signals (0–100, higher = schedule sooner).

    Combines three sub-signals:
    - recent_score_mean: if recent scores diverge from CT avg, nudge accordingly
    - note_velocity: many recent notes = people are drinking it now
    - window_drift: text signals about readiness

    Returns 50.0 (neutral) when no community data is available.
    """
    if not community_notes:
        return 50.0

    iwine = str(wine.get("iWine", ""))
    notes = community_notes.get(iwine, [])
    if not notes:
        return 50.0

    score = 50.0  # neutral baseline

    # Sub-signal 1: recent score mean vs CT average
    recent_scores = [n["score"] for n in notes[:10] if n.get("score") is not None]
    if recent_scores:
        ct = wine.get("CT") or AVG_CT
        mean_recent = sum(recent_scores) / len(recent_scores)
        diff = mean_recent - ct
        # A 4+ point drop → bump urgency (might be disappointing)
        # A 4+ point rise → quality is better than expected
        if diff <= -4:
            score += 10.0  # disappointing → drink sooner to clear
        elif diff >= 4:
            score += 5.0  # better than expected → slight bump

    # Sub-signal 2: note velocity (notes in last 30 days)
    cutoff = datetime.now().date() - timedelta(days=30)
    recent_count = 0
    for n in notes:
        td_str = n.get("tasting_date")
        if td_str:
            try:
                td = datetime.strptime(td_str, "%m/%d/%Y").date()
                if td >= cutoff:
                    recent_count += 1
            except ValueError:
                pass
    if recent_count >= 5:
        score += 10.0  # high velocity → people are drinking these now
    elif recent_count >= 2:
        score += 5.0

    # Sub-signal 3: window drift from note text
    drink_now_hits = 0
    hold_hits = 0
    for n in notes[:10]:
        body = n.get("body") or ""
        if _DRIFT_DRINK_NOW.search(body):
            drink_now_hits += 1
        if _DRIFT_HOLD.search(body):
            hold_hits += 1

    if drink_now_hits > hold_hits:
        score += 10.0  # community says drink now
    elif hold_hits > drink_now_hits:
        score -= 10.0  # community says hold

    return max(0.0, min(100.0, score))


# ---------------------------------------------------------------------------
# Diversity scoring
# ---------------------------------------------------------------------------

DIV_SAME_WINE = 60
DIV_SAME_PRODUCER = 35
DIV_SAME_VARIETAL = 20
DIV_DECAY_WEEKS = 5


def diversity_penalty(distance_weeks: int, max_penalty: float) -> float:
    """Linear decay: full penalty at distance 0, zero at DIV_DECAY_WEEKS."""
    if distance_weeks >= DIV_DECAY_WEEKS:
        return 0.0
    return max_penalty * (1.0 - distance_weeks / DIV_DECAY_WEEKS)


def diversity_score(wine: dict, week_index: int, placed: list[dict | None]) -> float:
    """Return 0–100, where 100 = maximum diversity (no penalty).

    Looks back up to DIV_DECAY_WEEKS slots in placed[]. For each nearby
    placed wine, applies the strongest matching penalty tier (same wine >
    same producer > same varietal). Penalties accumulate across multiple
    nearby wines but only the strongest tier fires per comparison.
    """
    total_penalty = 0.0
    wine_key = f"{wine.get('Vintage', '')}|{wine.get('Wine', '')}"
    wine_producer = wine.get("Producer", "")
    wine_varietal = wine.get("MasterVarietal") or wine.get("Varietal", "")

    for prev_idx in range(max(0, week_index - DIV_DECAY_WEEKS), week_index):
        prev = placed[prev_idx]
        if prev is None:
            continue
        distance = week_index - prev_idx
        prev_key = f"{prev.get('Vintage', '')}|{prev.get('Wine', '')}"
        prev_producer = prev.get("Producer", "")
        prev_varietal = prev.get("MasterVarietal") or prev.get("Varietal", "")

        # Only the strongest matching penalty per comparison
        if wine_key == prev_key:
            total_penalty += diversity_penalty(distance, DIV_SAME_WINE)
        elif wine_producer and wine_producer == prev_producer:
            total_penalty += diversity_penalty(distance, DIV_SAME_PRODUCER)
        elif wine_varietal and wine_varietal == prev_varietal:
            total_penalty += diversity_penalty(distance, DIV_SAME_VARIETAL)

    return max(0.0, 100.0 - total_penalty)


# ---------------------------------------------------------------------------
# Composite score
# ---------------------------------------------------------------------------

W_WINDOW = 0.50
W_SEASON = 0.25
W_DIVERSITY = 0.10
W_CT = 0.10
W_COMMUNITY = 0.05
# Weights must sum to 1.0: 0.50 + 0.25 + 0.10 + 0.10 + 0.05 = 1.00


def composite_score(
    wine: dict,
    season: str,
    week_index: int,
    placed: list[dict | None],
    community_notes: dict[str, list[dict]] | None = None,
) -> float:
    """Weighted composite of all scoring components. Lower = schedule sooner.

    Inverts the 0–100 desirability scores so that the most desirable wines
    (past-peak, perfect season, high diversity, high CT) get the lowest
    composite score, consistent with urgency_score() convention.
    """
    window = window_position_score(wine)
    seasonal = seasonal_fit_score(wine, season)
    diversity = diversity_score(wine, week_index, placed)
    ct = ct_score_component(wine)
    comm = community_score(wine, community_notes)

    desirability = (
        W_WINDOW * window
        + W_SEASON * seasonal
        + W_DIVERSITY * diversity
        + W_CT * ct
        + W_COMMUNITY * comm
    )
    return 100.0 - desirability
