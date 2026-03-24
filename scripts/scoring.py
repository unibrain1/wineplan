#!/usr/bin/env python3
"""Composite scoring functions for wine scheduling.

Symbols exported:
  window_position_score — drinking-window position score (0–100, higher = schedule sooner)
  seasonal_score        — seasonal fit penalty (0=perfect, 1=acceptable, 2=poor)
  seasonal_fit_score    — seasonal fit as a 0–100 float (higher = better fit)
"""

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
