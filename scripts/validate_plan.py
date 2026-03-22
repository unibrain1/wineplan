#!/usr/bin/env python3
"""Validate plan data against CellarTracker inventory.

CellarTracker is the system of record for all wine metadata.
This script checks that badges, varietals, and other attributes
in the plan match the inventory data, and fixes mismatches.

Usage: validate_plan.py <inventory.json> <site/index.html>
"""

import json
import re
import sys
from pathlib import Path


# Map CellarTracker Type field to plan badge
TYPE_TO_BADGE = {
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


def normalize_name(name: str) -> str:
    """Normalize a wine name for fuzzy matching."""
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def build_inventory_index(inventory: list[dict]) -> dict:
    """Index inventory by (vintage, normalized name) for lookup."""
    index = {}
    for wine in inventory:
        vintage = str(wine.get("Vintage", ""))
        norm = normalize_name(wine.get("Wine", ""))
        index[(vintage, norm)] = wine
    return index


def find_inventory_match(vintage: str, name: str, index: dict) -> dict | None:
    """Find the best inventory match for a plan entry."""
    norm = normalize_name(name)
    # Exact match
    if (vintage, norm) in index:
        return index[(vintage, norm)]
    # Substring match
    for (v, n), wine in index.items():
        if v == vintage and (norm in n or n in norm):
            return wine
    return None


def validate_and_fix(inventory_path: str, html_path: str) -> None:
    """Validate plan badges against inventory and fix mismatches."""
    inventory = json.loads(Path(inventory_path).read_text())
    html = Path(html_path).read_text(encoding="utf-8")

    index = build_inventory_index(inventory)

    # Extract allWeeks entries with their badge values
    badge_pattern = re.compile(r'vintage:"(\d+)",\s*name:"([^"]+)".*?badge:"([^"]+)"')

    fixes = []
    for match in badge_pattern.finditer(html):
        vintage = match.group(1)
        name = match.group(2)
        current_badge = match.group(3)

        inv_wine = find_inventory_match(vintage, name, index)
        if not inv_wine:
            continue

        ct_type = inv_wine.get("Type", "")
        expected_badge = TYPE_TO_BADGE.get(ct_type, current_badge)

        if expected_badge != current_badge:
            fixes.append(
                {
                    "wine": f"{vintage} {name}",
                    "ct_type": ct_type,
                    "was": current_badge,
                    "should_be": expected_badge,
                }
            )

    if fixes:
        # Simpler approach: regex replace each fix
        for fix in fixes:
            vintage = fix["wine"].split(" ", 1)[0]
            name = fix["wine"].split(" ", 1)[1]
            pattern = re.compile(
                rf'badge:"{re.escape(fix["was"])}",(\s+)vintage:"{re.escape(vintage)}", name:"{re.escape(name)}"'
            )
            replacement = (
                f'badge:"{fix["should_be"]}",\\1vintage:"{vintage}", name:"{name}"'
            )
            html = pattern.sub(replacement, html)

        Path(html_path).write_text(html, encoding="utf-8")

        print(f"Fixed {len(fixes)} badge mismatch(es):")
        for fix in fixes:
            print(
                f"  {fix['wine']}: {fix['was']} → {fix['should_be']} (CT Type: {fix['ct_type']})"
            )
    else:
        print("All badges match CellarTracker inventory.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: validate_plan.py <inventory.json> <site/index.html>",
            file=sys.stderr,
        )
        sys.exit(1)
    validate_and_fix(sys.argv[1], sys.argv[2])
