# Menu Plan Guide

How to write Google Calendar menu entries for the best wine pairing suggestions from The Sommelier.

## Setup

Menu data comes from a Google Calendar (managed via Paprika or directly). The pipeline fetches the calendar's secret .ics URL, extracts meals, and matches food keywords to suggest wine pairings.

## Best Format

| Field | Example |
|---|---|
| **Title** | `Grilled Lamb Chops` |
| **Description** (optional) | `Italian style, with risotto` |

The engine scans both title and description, so you can be brief.

## Tips

- **Lead with the protein**: "Salmon with asparagus" works, "Dinner" doesn't
- **Add cuisine when relevant**: "Thai green curry" triggers different pairings than just "curry"
- **Cooking method helps**: "Braised short ribs" and "Grilled steak" both match on both the protein and the method
- **Multiple keywords stack**: "Grilled lamb" matches both "grilled" (bold red or rosé) and "lamb" (bold red) — reinforcing the suggestion

## Output Format

The pipeline produces `data/menu.json` — a JSON array of menu entries sorted by date. Each entry has:

| Field | Type | Description |
|---|---|---|
| `date` | string | ISO date of the meal (e.g., `"2026-03-22"`) |
| `meal` | string | Calendar event title — the recipe name |
| `description` | string | Calendar event description (often just `"Dinner"`) |
| `keywords` | string[] | Auto-extracted food keywords used for wine pairing |

Example:

```json
[
  {
    "date": "2026-03-17",
    "meal": "Slow-Cooker Corned Beef and Cabbage (Irish Boiled Dinner), Apple Pie",
    "description": "Dinner",
    "keywords": ["beef", "corned beef"]
  },
  {
    "date": "2026-03-22",
    "meal": "Mexican Rotisserie Chicken, Feta Lime Coleslaw",
    "description": "Dinner",
    "keywords": ["beans", "chicken", "mexican"]
  },
  {
    "date": "2026-03-25",
    "meal": "Cast Iron Pan Pizza",
    "description": "Dinner",
    "keywords": ["pizza"]
  }
]
```

The more descriptive the meal title, the more keywords get extracted and the better the pairing recommendations.

## How Pairing Works

1. The pipeline extracts food keywords from your calendar events
2. Each keyword maps to preferred wine styles (e.g., "ribs" → bold red)
3. If the planned wine for that week doesn't match, The Sommelier suggests a specific bottle from your cellar
4. Suggestions prioritize bottles that need drinking (past peak, expiring soon)
5. Each meal gets a unique suggestion — no bottle is recommended twice

## What You'll See on the Plan

- **Pairs Well** (green, wine icon) — the planned wine matches your meal
- **Sommelier Pick** (blue, wine icon) — a specific bottle suggestion from your cellar
- **No Match** (muted) — no food keywords matched, enjoy the planned wine

## Recognized Keywords

All keywords are defined in `scripts/wine_keywords.py`. Adding a keyword there automatically makes it available for both extraction and pairing.

### Proteins
beef, steak, ribeye, filet, brisket, burger, short ribs, ribs, corned beef, lamb, veal, venison, elk, bison, pork, sausage, chops, pulled pork, carnitas, bacon, ham, chicken, turkey, duck, quail, cornish hen, salmon, tuna, halibut, cod, trout, swordfish, mahi, shrimp, crab, lobster, scallops, oysters, mussels, clams, fish, seafood, shellfish

### Cuisines
italian, french, japanese, thai, mexican, indian, chinese, korean, mediterranean, greek, spanish, bbq, barbecue, grilled, braised, roasted, smoked

### Dishes / Styles
salad, soup, pasta, risotto, pizza, taco, tacos, burrito, enchilada, quesadilla, curry, stew, chili, casserole, sandwich, lasagna, noodle, ramen, pho, udon, soba, mac, shepherd, beans, lentil, tofu, tempeh, vegetarian, vegan

## Not Yet Supported

Specific sauces, spice levels, side dishes as standalone entries, and desserts are not matched in the current POC. These will come with a richer pairing engine later.
