#!/usr/bin/env python3
"""Shared utilities for wine plan scripts.

Symbols exported:
  CURRENT_YEAR  — current calendar year
  TYPE_TO_BADGE — CellarTracker Type → plan badge mapping
  normalize     — canonical name normalizer (accent-aware)
  urgency_score — bottle urgency priority (0 = most urgent)
"""

import re
from datetime import date

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CURRENT_YEAR: int = date.today().year

# Map CellarTracker Type field to plan badge.
TYPE_TO_BADGE: dict[str, str] = {
    "Red": "red",
    "White": "white",
    "Rosé": "rose",
    "Sparkling": "sparkling",
    "Sparkling - White": "sparkling",
    "White - Sparkling": "sparkling",
    "Sparkling - Rosé": "sparkling",
    "White - Sweet/Dessert": "white",
    "Red - Sweet/Dessert": "red",
}

# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------


def normalize(name: str) -> str:
    """Lowercase, strip accented characters and punctuation, collapse whitespace.

    Uses the most thorough variant: handles curly quotes, common accented
    characters (é, è, ñ), then strips remaining non-alphanumeric characters.
    """
    s = name.lower()
    s = re.sub(r"[''`]", "", s)  # curly/straight apostrophes
    s = s.replace("è", "e").replace("é", "e").replace("ñ", "n")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# Urgency scoring
# ---------------------------------------------------------------------------


def urgency_score(wine: dict) -> int:
    """Priority score — lower is more urgent.

    0  past peak      (EndConsume < current year)
    1  expiring now   (EndConsume == current year)
    2  expiring soon  (EndConsume == current year + 1)
    3  peak window    (BeginConsume <= current year <= EndConsume)
    4  entering window(BeginConsume == current year or current year + 1)
    5  long-ager / unknown
    """
    end = wine.get("EndConsume")
    begin = wine.get("BeginConsume")
    if end is not None and end < CURRENT_YEAR:
        return 0
    if end is not None and end == CURRENT_YEAR:
        return 1
    if end is not None and end == CURRENT_YEAR + 1:
        return 2
    if begin is not None and end is not None and begin <= CURRENT_YEAR <= end:
        return 3
    if begin is not None and begin in (CURRENT_YEAR, CURRENT_YEAR + 1):
        return 4
    return 5
