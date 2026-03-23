"""Plan configuration — holidays, evolution tracks, and hold list.

Edit this file to customize The Sommelier's plan generation rules.
"""

# Holiday anchors: (name, approximate month, approximate day)
# The plan generator finds the nearest week to each date and assigns a special bottle.
HOLIDAYS: list[tuple[str, int, int]] = [
    ("Thanksgiving", 11, 26),  # late November
    ("Christmas", 12, 18),  # mid December
    ("New Year's Eve", 12, 28),  # late December
    ("Valentine's Day", 2, 14),  # mid February
    ("4th of July", 7, 4),  # early July
    ("Anniversary", 5, 28),  # May 28
    ("Nadya's Birthday", 11, 19),  # November 19
    ("Jim's Birthday", 10, 10),  # October 10
]

# Evolution tracking: open one bottle per year from each label to monitor development.
# The generator picks the most urgent vintage within the drinking window.
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
