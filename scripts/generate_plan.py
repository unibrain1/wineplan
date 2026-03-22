#!/usr/bin/env python3
"""Deterministic wine plan generator.

Reads inventory.json and produces site/plan.json with allWeeks (104 entries),
quarterInfo, and changelog.  A backup of the previous plan is saved to
data/plan_previous.json before overwriting.

Usage:
    python3 scripts/generate_plan.py data/inventory.json site/plan.json
"""

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CURRENT_YEAR = date.today().year

TOTAL_WEEKS = 52

# TYPE_TO_BADGE — matches validate_plan.py exactly so generated badges are
# always valid without a subsequent validation pass.
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

# Wines that must hold ≥ 2 bottles back (schedule at most qty - 2, min 1).
# Keys are lowercased fragments matched against the wine name.
HOLD_BACK_NAMES: list[str] = [
    "adamant cellars cabernet sauvignon don't be a dull boy 2021",
    "adamant cellars don't be a dull boy 2021",
    "don't be a dull boy 2021",
]

# Long-ager hold list — do not schedule unless EndConsume is within the
# planning horizon (current year + 2).  Each entry is (name_fragment, vintage).
LONG_AGER_HOLD: list[tuple[str, str]] = [
    ("roserock", "2022"),
    ("roserock", "2024"),
    ("laurène", "2021"),
    ("laurène", "2022"),
    ("laurène", "2023"),
    ("louise", "2021"),
    ("louise", "2022"),
    ("louise", "2023"),
    ("domaine drouhin oregon pinot noir", "2019"),
    ("domaine drouhin oregon pinot noir", "2022"),
    ("domaine drouhin oregon pinot noir", "2024"),
    ("caymus cabernet sauvignon", "2023"),
    ("arthur chardonnay", "2023"),
    ("arthur chardonnay", "2024"),
    ("dion vineyard pinot noir old vines", "2020"),
    ("dion vineyard pinot noir old vines", "2021"),
    ("origine 36", ""),
    ("origine 37", ""),
]

# Holiday anchors: (name, approximate month, approximate day)
HOLIDAYS: list[tuple[str, int, int]] = [
    ("Thanksgiving", 11, 26),  # late November
    ("Christmas", 12, 18),  # mid December
    ("New Year's Eve", 12, 28),  # late December
    ("Valentine's Day", 2, 14),  # mid February
    ("4th of July", 7, 4),  # early July
    ("Anniversary", 5, 28),  # May 28
]

# Evolution tracking definitions.
# Each entry: (label, name_fragment, preferred_month_range, preferred_month)
EVOLUTION_TRACKS: list[dict] = [
    {
        "label": "Laurène",
        "name_fragment": "laurène",
        "season_months": (10, 11),  # October–November
        "preferred_month": 11,  # Thanksgiving month
        "occasion_template": "{occasion} — Laurène evolution",
    },
    {
        "label": "Louise",
        "name_fragment": "louise",
        "season_months": (12, 12),  # December
        "preferred_month": 12,
        "occasion_template": "{occasion} — Louise evolution",
    },
    {
        "label": "Roserock",
        "name_fragment": "roserock",
        "season_months": (2, 2),  # February
        "preferred_month": 2,
        "occasion_template": "{occasion} — Roserock evolution",
    },
]

# Seasonal badge preferences (applied as tie-breakers / candidates filter)
# Maps season name → preferred badge list in priority order
SEASON_PREFER: dict[str, list[str]] = {
    "spring": ["sparkling", "rose", "white", "red"],
    "summer": ["sparkling", "rose", "white", "red"],
    "fall": ["red", "white", "sparkling", "rose"],
    "winter": ["red", "white", "sparkling", "rose"],
}

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


# ---------------------------------------------------------------------------
# Urgency scoring (mirrors pairing.py — reimplemented to stay standalone)
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def monday_of_week(d: date) -> date:
    """Return the Monday on or before *d*."""
    return d - timedelta(days=d.weekday())


def season_for_date(d: date) -> str:
    """Return the season name for a calendar date."""
    m = d.month
    if m in (3, 4):
        return "spring"
    if m == 5:
        # May 1–24 spring, May 25+ summer (Memorial Day shoulder)
        return "spring" if d.day < 25 else "summer"
    if m in (6, 7, 8):
        return "summer"
    if m in (9, 10, 11):
        return "fall"
    return "winter"  # 12, 1, 2


def format_date(d: date) -> str:
    """Format date as 'Mon D, YYYY' — matches existing plan.json."""
    return d.strftime("%b %-d, %Y")


def build_appellation(wine: dict) -> str:
    """Construct 'Country · Region · Appellation' string from inventory fields."""
    parts = []
    country = (wine.get("Country") or "").strip()
    region = (wine.get("Region") or "").strip()
    sub_region = (wine.get("SubRegion") or "").strip()
    appellation = (wine.get("Appellation") or "").strip()

    if country:
        parts.append(country)
    if region:
        parts.append(region)
    # Prefer the most specific geographic unit available
    if appellation and appellation.lower() not in ("unknown", ""):
        parts.append(appellation)
    elif sub_region and sub_region.lower() not in ("unknown", ""):
        parts.append(sub_region)

    return " · ".join(parts)


def build_window(wine: dict) -> str | None:
    """Return 'Begin–End' window string, or None if data is absent."""
    begin = wine.get("BeginConsume")
    end = wine.get("EndConsume")
    if begin is None and end is None:
        return None
    b = str(begin) if begin is not None else "?"
    e = str(end) if end is not None else "?"
    return f"{b}–{e}"


def build_score(wine: dict) -> str | None:
    """Return 'CT##' score string, or None if absent."""
    ct = wine.get("CT")
    if ct is None:
        return None
    # Format: CT90 for whole numbers, CT90.5 for fractional
    return f"CT{ct:g}"


def normalize(name: str) -> str:
    """Lowercase, strip accents-insensitive normalization for fragment matching."""
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def is_long_ager_hold(wine: dict) -> bool:
    """Return True if this wine is on the long-ager hold list.

    Hold-list items are blocked unless EndConsume falls within the 2-year
    planning horizon (caller checks that separately).
    """
    name_norm = normalize(wine.get("Wine", ""))
    vintage_str = str(wine.get("Vintage", ""))
    for frag, vint in LONG_AGER_HOLD:
        if normalize(frag) in name_norm:
            if vint == "" or vint == vintage_str:
                return True
    return False


def requires_hold_back(wine: dict) -> bool:
    """Return True if the hold-back rule applies (schedule at most qty-2)."""
    name_lower = wine.get("Wine", "").lower()
    vintage_str = str(wine.get("Vintage", ""))
    for entry in HOLD_BACK_NAMES:
        parts = entry.rsplit(" ", 1)
        frag = parts[0]
        vint = parts[1] if len(parts) > 1 else ""
        if frag in name_lower and (vint == "" or vint == vintage_str):
            return True
    return False


def max_schedulable(wine: dict) -> int:
    """Maximum bottles of this wine that may appear in the plan.

    General hold-back rule: if 3+ bottles of the same wine, hold at least
    2 back for future drinking (schedule at most qty - 2, minimum 1).
    Named hold-back entries follow the same rule regardless of quantity.
    """
    qty = wine.get("Quantity", 1)
    if qty <= 0:
        return 0
    if qty >= 3:
        return max(1, qty - 2)
    return qty


def is_bold_red(wine: dict) -> bool:
    searchable = " ".join(
        [
            wine.get("Wine", ""),
            wine.get("Varietal", ""),
            wine.get("MasterVarietal", ""),
        ]
    ).lower()
    return any(kw in searchable for kw in BOLD_RED_KEYWORDS)


def is_light_red(wine: dict) -> bool:
    searchable = " ".join(
        [
            wine.get("Wine", ""),
            wine.get("Varietal", ""),
            wine.get("MasterVarietal", ""),
        ]
    ).lower()
    return any(kw in searchable for kw in LIGHT_RED_KEYWORDS)


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


# ---------------------------------------------------------------------------
# Week schedule generation
# ---------------------------------------------------------------------------


def generate_week_dates(start: date) -> list[date]:
    """Generate 104 Monday dates starting from *start*."""
    return [start + timedelta(weeks=i) for i in range(TOTAL_WEEKS)]


def find_nearest_week_index(
    dates: list[date], target_month: int, target_day: int, year_offset: int = 0
) -> int:
    """Find the index in *dates* whose date is nearest to the given month/day.

    *year_offset* 0 searches within year 1 of the plan; 1 searches year 2.
    """
    base_year = dates[0].year + year_offset
    try:
        target = date(base_year, target_month, target_day)
    except ValueError:
        # Clamp invalid dates (e.g., Feb 30)
        import calendar

        last_day = calendar.monthrange(base_year, target_month)[1]
        target = date(base_year, target_month, min(target_day, last_day))

    best_idx = 0
    best_delta = abs((dates[0] - target).days)
    for i, d in enumerate(dates):
        delta = abs((d - target).days)
        if delta < best_delta:
            best_delta = delta
            best_idx = i
    return best_idx


# ---------------------------------------------------------------------------
# Candidate building
# ---------------------------------------------------------------------------


def build_candidates(inventory: list[dict]) -> list[dict]:
    """Filter and sort inventory wines into a schedulable candidate list.

    Wines that are long-agers AND whose EndConsume is beyond the 2-year
    planning horizon are excluded entirely.

    Sort order:
      1. urgency_score ascending (most urgent first)
      2. CT score descending (higher rated first within same urgency tier)
      3. EndConsume ascending (tightest window first)
      4. Wine name ascending (deterministic tie-break)
    """
    candidates = []
    for wine in inventory:
        score = urgency_score(wine)
        # Exclude wines not yet in their window and beyond current year + 2
        if score == 5:
            end = wine.get("EndConsume")
            begin = wine.get("BeginConsume")
            # Allow if EndConsume is within the planning horizon
            if end is not None and end <= CURRENT_YEAR + 2:
                pass  # borderline long-ager — allow
            elif begin is not None and begin <= CURRENT_YEAR + 2:
                pass  # just entering — allow
            else:
                continue  # true long-ager — skip

        # Skip hold-list wines if their EndConsume is beyond horizon
        if is_long_ager_hold(wine):
            end = wine.get("EndConsume")
            if end is None or end > CURRENT_YEAR + 2:
                continue

        if max_schedulable(wine) <= 0:
            continue

        candidates.append(wine)

    candidates.sort(
        key=lambda w: (
            urgency_score(w),
            -(w.get("CT") or 0),
            w.get("EndConsume") or 9999,
            w.get("Wine", ""),
        )
    )
    return candidates


# ---------------------------------------------------------------------------
# Evolution track scheduling
# ---------------------------------------------------------------------------


def find_evolution_vintage(
    track: dict,
    candidates: list[dict],
    scheduled_counts: dict[str, int],
    year_index: int,  # 0-based plan year (0 or 1)
) -> dict | None:
    """Pick the most urgent schedulable bottle for an evolution track.

    Prefer vintages within their drinking window, most urgent first.
    """
    frag = normalize(track["name_fragment"])
    matches = []
    for wine in candidates:
        if frag not in normalize(wine.get("Wine", "")):
            continue
        key = f"{wine.get('Vintage', '')}|{wine.get('Wine', '')}"
        already = scheduled_counts.get(key, 0)
        if already >= max_schedulable(wine):
            continue
        score = urgency_score(wine)
        if score == 5:
            continue  # don't use true long-agers for evolution
        matches.append(wine)

    if not matches:
        return None

    # Sort by urgency, then EndConsume ascending, then vintage descending
    # (newer vintages are more interesting for evolution tracking)
    matches.sort(
        key=lambda w: (
            urgency_score(w),
            w.get("EndConsume") or 9999,
            -(w.get("Vintage") or 0),
        )
    )
    return matches[0]


# ---------------------------------------------------------------------------
# Holiday anchor scheduling
# ---------------------------------------------------------------------------


def assign_holiday_anchors(
    week_dates: list[date],
    candidates: list[dict],
    reserved: dict[int, dict],  # week_index → wine
    scheduled_counts: dict[str, int],
) -> None:
    """For each holiday, find the nearest unoccupied week and reserve a bottle.

    Holidays whose target date falls before the plan start are scheduled in
    the second plan year instead.  Modifies *reserved* and *scheduled_counts*
    in place.
    """
    plan_start = week_dates[0]
    plan_year1 = plan_start.year

    # Collect occasions already covered by evolution track reservations
    evolution_occasions: set[str] = set()
    for slot in reserved.values():
        occ = slot.get("occasion", "") or ""
        for holiday_name, _, _ in HOLIDAYS:
            if holiday_name.lower() in occ.lower():
                evolution_occasions.add(holiday_name)

    for holiday_name, month, day in HOLIDAYS:
        # Skip if an evolution track already anchored this holiday
        if holiday_name in evolution_occasions:
            continue
        # Try both plan years; prefer year 1 if the date hasn't passed
        for year_offset in (0, 1):
            calendar_year = plan_year1 + year_offset
            try:
                target = date(calendar_year, month, day)
            except ValueError:
                import calendar as cal_mod

                last_day = cal_mod.monthrange(calendar_year, month)[1]
                target = date(calendar_year, month, min(day, last_day))

            # Skip if the holiday has already passed for this year
            if target < plan_start:
                continue

            idx = find_nearest_week_index(week_dates, month, day, year_offset)

            # Verify the found week is within ±3 weeks of the actual target
            if abs((week_dates[idx] - target).days) > 21:
                continue

            if idx in reserved:
                # Try adjacent weeks (up to ±3)
                found_slot = False
                for delta in (1, -1, 2, -2, 3, -3):
                    alt = idx + delta
                    if 0 <= alt < TOTAL_WEEKS and alt not in reserved:
                        idx = alt
                        found_slot = True
                        break
                if not found_slot:
                    continue

            season = season_for_date(week_dates[idx])
            # Pick the best seasonal bottle that isn't already fully scheduled
            best = _pick_best_for_slot(
                candidates,
                scheduled_counts,
                season,
                prefer_special=True,
                exclude_keys=set(reserved_keys(reserved)),
            )
            if best is None:
                continue

            key = wine_key(best)
            scheduled_counts[key] = scheduled_counts.get(key, 0) + 1
            reserved[idx] = {"wine": best, "special": True, "occasion": holiday_name}
            break


def reserved_keys(reserved: dict[int, dict]) -> set[str]:
    """Return the set of wine keys already reserved."""
    keys = set()
    for slot in reserved.values():
        w = slot.get("wine")
        if w:
            keys.add(wine_key(w))
    return keys


def wine_key(wine: dict) -> str:
    return f"{wine.get('Vintage', '')}|{wine.get('Wine', '')}"


def _pick_best_for_slot(
    candidates: list[dict],
    scheduled_counts: dict[str, int],
    season: str,
    prefer_special: bool = False,
    exclude_keys: set[str] | None = None,
    required_fragment: str | None = None,
) -> dict | None:
    """Pick the best available bottle for a given season slot.

    Candidates are already sorted by urgency.  Apply seasonal preference as a
    secondary sort only, to avoid bumping urgent bottles too far back.
    """
    exclude_keys = exclude_keys or set()
    pool = []
    for wine in candidates:
        key = wine_key(wine)
        if key in exclude_keys:
            continue
        if scheduled_counts.get(key, 0) >= max_schedulable(wine):
            continue
        if required_fragment and required_fragment not in normalize(
            wine.get("Wine", "")
        ):
            continue
        pool.append(wine)

    if not pool:
        return None

    # Sort pool: urgent bottles first, seasonal fit as tie-breaker
    pool.sort(
        key=lambda w: (
            urgency_score(w),
            seasonal_score(w, season),
            -(w.get("CT") or 0),
            w.get("EndConsume") or 9999,
            w.get("Wine", ""),
        )
    )
    return pool[0]


# ---------------------------------------------------------------------------
# Quarter info generation
# ---------------------------------------------------------------------------

_SEASON_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "spring": {
        "y1": "Urgent opens · lighter whites & rosés warming up",
        "y2": "Expiring bottles cleared · lighter reds & whites",
    },
    "summer": {
        "y1": "Rosés, whites & celebratory bottles",
        "y2": "Sparkling, whites & lighter Pinots",
    },
    "fall": {
        "y1": "Transition to reds — Oregon, Washington, Italian",
        "y2": "Bold reds · evolution tracks continue",
    },
    "winter": {
        "y1": "Big reds, Barolo, Bordeaux & evolution tracks",
        "y2": "Louise & Roserock evolution · Adamant Cabs",
    },
}

_SEASON_MONTHS: dict[str, str] = {
    "spring": "March – May",
    "summer": "June – August",
    "fall": "September – November",
    "winter": "December – March",
}


def build_quarter_info(week_dates: list[date]) -> dict:
    """Build the quarterInfo object from actual week dates."""
    # Identify the calendar year for each plan year
    y1_year = week_dates[0].year
    y2_year = week_dates[52].year if len(week_dates) > 52 else y1_year + 1

    quarter_info: dict[str, dict] = {}
    for season in ("spring", "summer", "fall", "winter"):
        sub = _SEASON_MONTHS[season]
        desc = _SEASON_DESCRIPTIONS[season]

        # Determine calendar year labels for winter (spans two years)
        if season == "winter":
            y1_title = f"Winter {y1_year}–{y1_year + 1}"
            y2_title = f"Winter {y2_year}–{y2_year + 1}"
        else:
            y1_title = f"{season.capitalize()} {y1_year}"
            y2_title = f"{season.capitalize()} {y2_year}"

        quarter_info[season] = {
            "y1": {"title": y1_title, "sub": sub, "note": desc["y1"]},
            "y2": {"title": y2_title, "sub": sub, "note": desc["y2"]},
        }
    return quarter_info


# ---------------------------------------------------------------------------
# Changelog diffing
# ---------------------------------------------------------------------------


def diff_plans(old_weeks: list[dict], new_weeks: list[dict]) -> list[dict]:
    """Compare two allWeeks lists and return changelog entries."""

    def plan_key(w: dict) -> str:
        return f"{w.get('vintage', '')}|{w.get('name', '')}"

    old_by_key: dict[str, list[int]] = {}
    for w in old_weeks:
        k = plan_key(w)
        old_by_key.setdefault(k, []).append(w.get("week", 0))

    new_by_key: dict[str, list[int]] = {}
    for w in new_weeks:
        k = plan_key(w)
        new_by_key.setdefault(k, []).append(w.get("week", 0))

    changes: list[dict] = []

    all_keys = set(old_by_key) | set(new_by_key)
    for key in sorted(all_keys):
        old_weeks_list = old_by_key.get(key, [])
        new_weeks_list = new_by_key.get(key, [])
        vintage, name = key.split("|", 1)
        label = f"{vintage} {name}"

        if not old_weeks_list and new_weeks_list:
            for wk in new_weeks_list:
                changes.append(
                    {"type": "added", "week": wk, "description": f"{label} added"}
                )
        elif old_weeks_list and not new_weeks_list:
            for wk in old_weeks_list:
                changes.append(
                    {"type": "removed", "week": wk, "description": f"{label} removed"}
                )
        else:
            old_sorted = sorted(old_weeks_list)
            new_sorted = sorted(new_weeks_list)
            if old_sorted != new_sorted:
                changes.append(
                    {
                        "type": "adjusted",
                        "description": (
                            f"{label} moved from week(s) {old_sorted} to {new_sorted}"
                        ),
                    }
                )

    return changes


# ---------------------------------------------------------------------------
# Plan entry builder
# ---------------------------------------------------------------------------


def make_entry(
    week_num: int,
    plan_year: int,
    week_date: date,
    wine: dict,
    special: bool = False,
    evolution: bool = False,
    occasion: str | None = None,
) -> dict:
    """Assemble a single plan entry dict from an inventory wine."""
    end = wine.get("EndConsume")
    urgent = end is not None and end <= CURRENT_YEAR + 1

    badge = TYPE_TO_BADGE.get(wine.get("Type", ""), "red")

    return {
        "week": week_num,
        "year": plan_year,
        "date": format_date(week_date),
        "season": season_for_date(week_date),
        "badge": badge,
        "vintage": str(wine.get("Vintage", "")),
        "name": wine.get("Wine", ""),
        "appellation": build_appellation(wine),
        "window": build_window(wine),
        "score": build_score(wine),
        "urgent": urgent,
        "special": special,
        "evolution": evolution,
        "occasion": occasion,
        "note": "",
    }


# ---------------------------------------------------------------------------
# Main scheduling logic
# ---------------------------------------------------------------------------


def _evolution_target_date(preferred_month: int, year: int) -> date:
    """Return the target anchor date for an evolution slot in a given year."""
    try:
        return date(year, preferred_month, 15)
    except ValueError:
        return date(year, preferred_month, 28)


def schedule_evolution_tracks(
    week_dates: list[date],
    candidates: list[dict],
    reserved: dict[int, dict],
    scheduled_counts: dict[str, int],
) -> None:
    """Reserve one week per year per evolution track.

    If the preferred month for year-1 has already passed (i.e. the target date
    falls before the plan start), that track is only scheduled in year 2.

    Modifies *reserved* and *scheduled_counts* in place.
    """
    plan_start = week_dates[0]
    plan_year1_calendar = plan_start.year  # e.g. 2026

    for year_offset in (0, 1):
        calendar_year = plan_year1_calendar + year_offset
        for track in EVOLUTION_TRACKS:
            preferred_month = track["preferred_month"]
            target = _evolution_target_date(preferred_month, calendar_year)

            # If the target date is before the plan start, this track cannot
            # be scheduled in year 1 — skip it (will be handled in year 2).
            if target < plan_start:
                continue

            wine = find_evolution_vintage(
                track, candidates, scheduled_counts, year_offset
            )
            if wine is None:
                continue

            # Find the week index nearest to the target date
            idx = find_nearest_week_index(week_dates, preferred_month, 15, year_offset)

            # Verify the found week is actually in the correct calendar year
            # (find_nearest_week_index may overshoot into the adjacent year)
            if week_dates[idx].year != calendar_year:
                # Accept it if it's within the plan and within ±6 weeks of
                # the month boundary (e.g. late-Jan / early-Mar for February)
                if abs((week_dates[idx] - target).days) > 42:
                    continue

            # Adjust if slot is already taken — search within the season window
            if idx in reserved:
                season_months = track["season_months"]
                placed = False
                for delta in range(1, 10):
                    for sign in (1, -1):
                        alt = idx + sign * delta
                        if 0 <= alt < TOTAL_WEEKS and alt not in reserved:
                            alt_date = week_dates[alt]
                            if alt_date.month in range(
                                season_months[0], season_months[1] + 1
                            ):
                                idx = alt
                                placed = True
                                break
                    if placed:
                        break

            if idx in reserved:
                continue  # couldn't find a free slot

            # Determine occasion label — check if a holiday anchor is nearby
            nearby_holiday = None
            for holiday_name, month, day in HOLIDAYS:
                try:
                    h_target = date(week_dates[idx].year, month, day)
                except ValueError:
                    continue
                if abs((week_dates[idx] - h_target).days) <= 7:
                    nearby_holiday = holiday_name
                    break

            occasion = (
                f"{nearby_holiday} — {track['label']} evolution"
                if nearby_holiday
                else f"{track['label']} evolution Year {year_offset + 1}"
            )

            key = wine_key(wine)
            scheduled_counts[key] = scheduled_counts.get(key, 0) + 1
            reserved[idx] = {
                "wine": wine,
                "special": True,
                "evolution": True,
                "occasion": occasion,
            }


def generate_plan(inventory: list[dict]) -> dict:
    """Generate the full 104-week plan from inventory data."""
    today = date.today()
    start = monday_of_week(today)
    week_dates = generate_week_dates(start)

    candidates = build_candidates(inventory)

    # Track how many bottles of each wine we've already scheduled
    scheduled_counts: dict[str, int] = {}

    # reserved[week_index] = {"wine": ..., "special": ..., "evolution": ..., "occasion": ...}
    reserved: dict[int, dict] = {}

    # --- Phase 1: Reserve evolution tracks ---
    schedule_evolution_tracks(week_dates, candidates, reserved, scheduled_counts)

    # --- Phase 2: Reserve holiday anchors ---
    assign_holiday_anchors(week_dates, candidates, reserved, scheduled_counts)

    # --- Phase 3: Fill remaining weeks ---
    # For weeks 0-7 (first 8): strongly prefer urgent/past-peak regardless of season
    # For weeks 8-15 (next 8): prefer expiring-this-year
    # After that: seasonal preference applies

    all_weeks: list[dict] = []

    for i, week_date in enumerate(week_dates):
        week_num = i + 1
        plan_year = 1 if i < 52 else 2
        season = season_for_date(week_date)

        if i in reserved:
            slot = reserved[i]
            wine = slot["wine"]
            entry = make_entry(
                week_num,
                plan_year,
                week_date,
                wine,
                special=slot.get("special", False),
                evolution=slot.get("evolution", False),
                occasion=slot.get("occasion"),
            )
            all_weeks.append(entry)
            continue

        # Determine which wine to place here
        if i < 8:
            # Phase A: past-peak and urgent bottles first
            wine = _pick_for_urgent_phase(
                candidates, scheduled_counts, season, max_urgency=1
            )
        elif i < 16:
            # Phase B: expiring this/next year
            wine = _pick_for_urgent_phase(
                candidates, scheduled_counts, season, max_urgency=2
            )
        else:
            # Phase C: seasonal selection
            wine = _pick_best_for_slot(candidates, scheduled_counts, season)

        if wine is None:
            # Fallback: any available bottle
            wine = _pick_best_for_slot(candidates, scheduled_counts, season)

        if wine is None:
            # Nothing left — this should not happen if inventory is sufficient
            raise RuntimeError(
                f"Ran out of schedulable bottles at week {week_num}. "
                f"Check inventory.json."
            )

        key = wine_key(wine)
        scheduled_counts[key] = scheduled_counts.get(key, 0) + 1
        entry = make_entry(week_num, plan_year, week_date, wine)
        all_weeks.append(entry)

    quarter_info = build_quarter_info(week_dates)

    return {
        "allWeeks": all_weeks,
        "quarterInfo": quarter_info,
    }


def _pick_for_urgent_phase(
    candidates: list[dict],
    scheduled_counts: dict[str, int],
    season: str,
    max_urgency: int,
) -> dict | None:
    """Pick the most urgent available bottle at or below *max_urgency* tier."""
    for wine in candidates:
        key = wine_key(wine)
        if scheduled_counts.get(key, 0) >= max_schedulable(wine):
            continue
        if urgency_score(wine) <= max_urgency:
            return wine
    return None


# ---------------------------------------------------------------------------
# Changelog helpers
# ---------------------------------------------------------------------------


def build_changelog(old_weeks: list[dict] | None, new_weeks: list[dict]) -> dict:
    today_str = date.today().strftime("%B %-d, %Y")
    if old_weeks is None:
        return {
            "date": today_str,
            "summary": "Initial plan generated from CellarTracker inventory.",
            "changes": [],
        }

    changes = diff_plans(old_weeks, new_weeks)
    if changes:
        summary = (
            f"Synced with CellarTracker inventory. {len(changes)} change(s) detected."
        )
    else:
        summary = "Synced with CellarTracker inventory. No scheduling changes."

    return {
        "date": today_str,
        "summary": summary,
        "changes": changes,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: generate_plan.py <inventory.json> <plan.json>",
            file=sys.stderr,
        )
        sys.exit(1)

    inventory_path = Path(sys.argv[1])
    plan_path = Path(sys.argv[2])
    previous_path = Path("data/plan_previous.json")

    if not inventory_path.exists():
        print(f"Error: inventory file not found: {inventory_path}", file=sys.stderr)
        sys.exit(1)

    inventory: list[dict] = json.loads(inventory_path.read_text(encoding="utf-8"))

    # Load previous plan for changelog diffing
    old_weeks: list[dict] | None = None
    if plan_path.exists():
        try:
            old_data = json.loads(plan_path.read_text(encoding="utf-8"))
            old_weeks = old_data.get("allWeeks")
            # Back up before overwriting
            previous_path.parent.mkdir(parents=True, exist_ok=True)
            previous_path.write_text(
                json.dumps(old_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"Previous plan backed up to {previous_path}")
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: could not read existing plan ({exc})", file=sys.stderr)

    print(f"Generating plan from {len(inventory)} inventory wines…")
    plan_data = generate_plan(inventory)

    changelog = build_changelog(old_weeks, plan_data["allWeeks"])
    plan_data["changelog"] = changelog

    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(plan_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    added = sum(1 for c in changelog["changes"] if c["type"] == "added")
    removed = sum(1 for c in changelog["changes"] if c["type"] == "removed")
    adjusted = sum(1 for c in changelog["changes"] if c["type"] == "adjusted")

    print(f"Plan written to {plan_path}")
    print(f"  {len(plan_data['allWeeks'])} weeks scheduled")
    print(f"  Changelog: +{added} added, -{removed} removed, ~{adjusted} adjusted")


if __name__ == "__main__":
    main()
