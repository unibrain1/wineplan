#!/usr/bin/env python3
"""Wine-food pairing engine.

Takes menu.json, plan.json, and inventory.json. For each menu item:
- Scores the planned wine against the food
- Suggests a specific bottle from inventory that would pair better
- Uses priority rules: past peak > expiring this year > expiring next year > peak window

Outputs pairing_suggestions.json.
"""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from wine_keywords import PAIRING_RULES
from wine_utils import CURRENT_YEAR, urgency_score


def _parse_plan_date(raw: str) -> date:
    """Parse a plan date string in either ISO or display format."""
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return datetime.strptime(raw, "%b %d, %Y").date()


def build_week_index(plan: list[dict]) -> dict[date, dict]:
    """Pre-index plan weeks by their start date for O(1) lookup."""
    return {_parse_plan_date(w["date"]): w for w in plan}


def find_week_for_date(week_index: dict[date, dict], target_date: str) -> dict | None:
    """Find the plan week that contains the given date (0-6 days after week start)."""
    td = date.fromisoformat(target_date)
    for offset in range(7):
        candidate = td - timedelta(days=offset)
        if candidate in week_index:
            return week_index[candidate]
    return None


def precompute_searchable(inventory: list[dict]) -> None:
    """Add a pre-lowered searchable string to each inventory wine."""
    for wine in inventory:
        wine["_searchable"] = " ".join(
            [
                wine.get("Wine", ""),
                wine.get("Varietal", ""),
                wine.get("MasterVarietal", ""),
                wine.get("Type", ""),
                wine.get("Region", ""),
                wine.get("SubRegion", ""),
            ]
        ).lower()


def wine_matches_styles(wine: dict, prefer_list: list[str]) -> bool:
    """Check if an inventory wine matches any of the preferred style keywords."""
    searchable = wine.get("_searchable", "")
    return any(style in searchable for style in prefer_list)


def find_best_bottle(
    keywords: list[str],
    inventory: list[dict],
    planned_wines: dict[str, str] | None = None,
    exclude: set[str] | None = None,
) -> dict | None:
    """Find the best bottle from inventory matching food keywords, using priority rules.

    planned_wines maps "vintage wine" keys to the week they're planned for.
    Planned bottles are still valid candidates — they can be moved forward.
    """
    # Collect all preferred styles from matched keywords
    all_preferred = []
    for kw in keywords:
        rule = PAIRING_RULES.get(kw)
        if rule:
            all_preferred.extend(rule["prefer"])
    if not all_preferred:
        return None

    planned_wines = planned_wines or {}
    exclude = exclude or set()

    # Find matching bottles — only consider wines in their drinking window
    candidates = []
    for wine in inventory:
        if not wine_matches_styles(wine, all_preferred):
            continue
        # Skip bottles already suggested for another meal
        wine_key = f"{wine.get('Vintage', '')} {wine.get('Wine', '')}"
        if wine_key in exclude:
            continue
        begin = wine.get("BeginConsume")
        end = wine.get("EndConsume")
        # Skip wines not yet in their window (long-agers)
        if begin is not None and begin > CURRENT_YEAR + 1:
            continue
        # Skip wines with no window data
        if begin is None and end is None:
            continue
        candidates.append(wine)

    if not candidates:
        return None

    # Sort by urgency (most urgent first), then by CT score descending
    candidates.sort(
        key=lambda w: (
            urgency_score(w),
            -(w.get("CT") or 0),
        )
    )

    best = candidates[0]
    u = urgency_score(best)
    urgency_label = {
        0: "past peak — drink now",
        1: "expiring this year",
        2: "expiring next year",
        3: "in peak window",
        4: "just entering window",
        5: "cellar candidate",
    }.get(u, "")

    wine_key = f"{best.get('Vintage', '')} {best.get('Wine', '')}"
    planned_week = planned_wines.get(wine_key)

    result = {
        "vintage": best.get("Vintage"),
        "wine": best.get("Wine"),
        "varietal": best.get("Varietal"),
        "type": best.get("Type"),
        "window": f"{best.get('BeginConsume', '?')}–{best.get('EndConsume', '?')}",
        "score": best.get("CT"),
        "quantity": best.get("Quantity", 1),
        "urgency": urgency_label,
    }
    if planned_week:
        result["move_from_week"] = planned_week

    return result


def score_pairing(wine_name: str, keywords: list[str]) -> dict:
    """Score how well a wine pairs with menu keywords."""
    wine_lower = wine_name.lower()
    matches = []
    mismatches = []

    for kw in keywords:
        rule = PAIRING_RULES.get(kw)
        if not rule:
            continue
        if any(style in wine_lower for style in rule["prefer"]):
            matches.append({"keyword": kw, "category": rule["category"], "match": True})
        else:
            mismatches.append(
                {"keyword": kw, "category": rule["category"], "match": False}
            )

    if not matches and not mismatches:
        return {"score": "neutral", "details": "no pairing rules matched menu keywords"}

    if mismatches and not matches:
        return {
            "score": "poor",
            "details": f"wine doesn't match: {', '.join(m['category'] for m in mismatches)} would pair better",
            "suggested_styles": list({m["category"] for m in mismatches}),
        }
    if matches and not mismatches:
        return {"score": "good", "details": "wine matches the menu well"}

    return {
        "score": "partial",
        "details": f"matches some ({len(matches)}) but not all ({len(mismatches)}) food elements",
        "suggested_styles": list({m["category"] for m in mismatches}),
    }


def suggest_pairings(
    menu: list[dict], plan: list[dict], inventory: list[dict]
) -> list[dict]:
    """Generate pairing suggestions for weeks with menu entries."""
    # Precompute indexes for O(1) lookups
    week_index = build_week_index(plan)
    precompute_searchable(inventory)

    suggestions = []
    planned_wines = {}
    for w in plan:
        key = f"{w.get('vintage', '')} {w.get('name', '')}"
        planned_wines[key] = w.get("week", "?")

    already_suggested: set[str] = set()

    for entry in menu:
        week = find_week_for_date(week_index, entry["date"])
        if not week:
            suggestions.append(
                {
                    "date": entry["date"],
                    "meal": entry["meal"],
                    "status": "no_plan_week",
                    "note": "no wine plan entry found for this date",
                }
            )
            continue

        if not entry["keywords"]:
            suggestions.append(
                {
                    "date": entry["date"],
                    "meal": entry["meal"],
                    "planned_wine": week.get("name", ""),
                    "planned_vintage": week.get("vintage", ""),
                    "planned_badge": week.get("badge", "red"),
                    "status": "no_keywords",
                    "pairing": {
                        "score": "neutral",
                        "details": "no match — enjoy the planned wine",
                    },
                }
            )
            continue

        # Look up varietal from inventory to improve pairing score accuracy
        inv_varietal = ""
        week_vintage = str(week.get("vintage", ""))
        week_name_lower = week.get("name", "").lower()
        for inv in inventory:
            inv_name_lower = inv.get("Wine", "").lower()
            if str(inv.get("Vintage", "")) == week_vintage and (
                inv_name_lower in week_name_lower or week_name_lower in inv_name_lower
            ):
                inv_varietal = inv.get("Varietal", "")
                break
        wine_name = (
            f"{week.get('name', '')} {week.get('appellation', '')} {inv_varietal}"
        )
        pairing = score_pairing(wine_name, entry["keywords"])

        result = {
            "date": entry["date"],
            "meal": entry["meal"],
            "keywords": entry["keywords"],
            "planned_wine": week.get("name", ""),
            "planned_vintage": week.get("vintage", ""),
            "planned_badge": week.get("badge", "red"),
            "pairing": pairing,
        }

        # If the planned wine doesn't pair well, suggest a better bottle
        if pairing["score"] in ("poor", "partial"):
            suggestion = find_best_bottle(
                entry["keywords"],
                inventory,
                planned_wines,
                already_suggested,
            )
            if suggestion:
                result["suggested_bottle"] = suggestion
                already_suggested.add(f"{suggestion['vintage']} {suggestion['wine']}")

        suggestions.append(result)

    return suggestions


def main():
    if len(sys.argv) < 4:
        print(
            "Usage: pairing.py <menu.json> <plan.json> <inventory.json>",
            file=sys.stderr,
        )
        sys.exit(1)

    menu = json.loads(Path(sys.argv[1]).read_text())
    plan_data = json.loads(Path(sys.argv[2]).read_text())
    plan = (
        plan_data.get("allWeeks", plan_data)
        if isinstance(plan_data, dict)
        else plan_data
    )
    inventory = json.loads(Path(sys.argv[3]).read_text())

    suggestions = suggest_pairings(menu, plan, inventory)

    result = {
        "generated": date.today().isoformat(),
        "total_meals": len(menu),
        "matched_weeks": sum(1 for s in suggestions if s.get("pairing")),
        "sommelier_picks": sum(1 for s in suggestions if s.get("suggested_bottle")),
        "suggestions": suggestions,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
