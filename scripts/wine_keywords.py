"""Canonical wine-food pairing keywords and rules.

Single source of truth used by both parse_menu.py (keyword extraction)
and pairing.py (pairing scoring). Adding a keyword here automatically
makes it available for both extraction and pairing.
"""

# Each entry: keyword → { prefer: [varietal/type substrings], category: description }
PAIRING_RULES = {
    # Bold reds for red meat
    "beef": {
        "prefer": [
            "cabernet",
            "syrah",
            "merlot",
            "barolo",
            "bordeaux",
            "malbec",
            "tempranillo",
        ],
        "category": "bold red",
    },
    "steak": {
        "prefer": ["cabernet", "syrah", "merlot", "barolo", "bordeaux", "malbec"],
        "category": "bold red",
    },
    "ribeye": {
        "prefer": ["cabernet", "syrah", "barolo", "bordeaux"],
        "category": "bold red",
    },
    "filet": {
        "prefer": ["cabernet", "merlot", "bordeaux", "pinot noir"],
        "category": "bold red or elegant red",
    },
    "short ribs": {
        "prefer": ["cabernet", "syrah", "merlot", "barolo", "zinfandel"],
        "category": "bold red",
    },
    "ribs": {
        "prefer": ["zinfandel", "syrah", "malbec", "cabernet"],
        "category": "bold red",
    },
    "brisket": {
        "prefer": ["syrah", "zinfandel", "malbec", "cabernet"],
        "category": "bold red",
    },
    "burger": {
        "prefer": ["cabernet", "zinfandel", "malbec", "syrah"],
        "category": "bold red",
    },
    "corned beef": {
        "prefer": ["cabernet", "syrah", "merlot", "malbec", "riesling"],
        "category": "bold red or riesling",
    },
    "lamb": {
        "prefer": ["cabernet", "syrah", "bordeaux", "rhône", "rhone"],
        "category": "bold red",
    },
    "veal": {
        "prefer": ["pinot noir", "chardonnay", "nebbiolo"],
        "category": "medium red or white",
    },
    "venison": {"prefer": ["syrah", "cabernet", "pinot noir"], "category": "bold red"},
    "elk": {"prefer": ["syrah", "cabernet", "pinot noir"], "category": "bold red"},
    "bison": {"prefer": ["syrah", "cabernet", "malbec"], "category": "bold red"},
    # Medium reds for poultry / pork
    "chicken": {
        "prefer": ["pinot noir", "chardonnay", "rosé", "rose"],
        "category": "medium red or white",
    },
    "turkey": {
        "prefer": ["pinot noir", "chardonnay", "gamay"],
        "category": "medium red or white",
    },
    "duck": {"prefer": ["pinot noir", "syrah", "gamay"], "category": "medium red"},
    "quail": {
        "prefer": ["pinot noir", "gamay", "chardonnay"],
        "category": "light to medium red",
    },
    "cornish hen": {
        "prefer": ["pinot noir", "chardonnay", "gamay"],
        "category": "medium red or white",
    },
    "pork": {
        "prefer": ["pinot noir", "rosé", "rose", "riesling", "chardonnay"],
        "category": "medium red or white",
    },
    "chops": {
        "prefer": ["cabernet", "syrah", "pinot noir", "malbec"],
        "category": "medium to bold red",
    },
    "pulled pork": {
        "prefer": ["zinfandel", "syrah", "malbec", "rosé", "rose"],
        "category": "bold red or rosé",
    },
    "carnitas": {
        "prefer": ["malbec", "tempranillo", "zinfandel", "rosé", "rose"],
        "category": "red or rosé",
    },
    "sausage": {
        "prefer": ["syrah", "zinfandel", "barbera", "tempranillo"],
        "category": "medium to bold red",
    },
    "bacon": {
        "prefer": ["syrah", "zinfandel", "pinot noir"],
        "category": "medium to bold red",
    },
    "ham": {
        "prefer": ["riesling", "pinot noir", "rosé", "rose", "chardonnay"],
        "category": "white or light red",
    },
    # Whites / rosé / sparkling for seafood
    "salmon": {
        "prefer": ["pinot noir", "chardonnay", "rosé", "rose"],
        "category": "light red or white",
    },
    "tuna": {
        "prefer": ["pinot noir", "rosé", "rose", "chardonnay"],
        "category": "light red or rosé",
    },
    "halibut": {
        "prefer": ["chardonnay", "sauvignon blanc", "pinot grigio"],
        "category": "white",
    },
    "cod": {
        "prefer": ["chardonnay", "sauvignon blanc", "pinot grigio"],
        "category": "white",
    },
    "trout": {
        "prefer": ["chardonnay", "pinot grigio", "riesling"],
        "category": "white",
    },
    "swordfish": {
        "prefer": ["chardonnay", "rosé", "rose", "pinot noir"],
        "category": "white or light red",
    },
    "mahi": {
        "prefer": ["sauvignon blanc", "chardonnay", "rosé", "rose"],
        "category": "white or rosé",
    },
    "fish": {
        "prefer": ["chardonnay", "sauvignon blanc", "pinot grigio", "rosé", "rose"],
        "category": "white",
    },
    "seafood": {
        "prefer": ["chardonnay", "sauvignon blanc", "sparkling", "rosé", "rose"],
        "category": "white or sparkling",
    },
    "shellfish": {
        "prefer": ["chardonnay", "sauvignon blanc", "sparkling", "muscadet"],
        "category": "white or sparkling",
    },
    "shrimp": {
        "prefer": ["sauvignon blanc", "sparkling", "rosé", "rose", "chardonnay"],
        "category": "white or sparkling",
    },
    "crab": {
        "prefer": ["chardonnay", "sauvignon blanc", "sparkling"],
        "category": "white or sparkling",
    },
    "lobster": {
        "prefer": ["chardonnay", "sparkling"],
        "category": "white or sparkling",
    },
    "scallops": {
        "prefer": ["chardonnay", "sauvignon blanc", "sparkling"],
        "category": "white or sparkling",
    },
    "oysters": {
        "prefer": ["sparkling", "muscadet", "chablis", "sauvignon blanc"],
        "category": "sparkling or crisp white",
    },
    "mussels": {
        "prefer": ["sauvignon blanc", "muscadet", "pinot grigio", "sparkling"],
        "category": "white or sparkling",
    },
    "clams": {
        "prefer": ["sauvignon blanc", "pinot grigio", "sparkling"],
        "category": "white or sparkling",
    },
    # Cuisine-based
    "italian": {
        "prefer": [
            "sangiovese",
            "nebbiolo",
            "barolo",
            "chianti",
            "pinot grigio",
            "barbera",
        ],
        "category": "Italian wine",
    },
    "french": {
        "prefer": ["bordeaux", "burgundy", "pinot noir", "chardonnay", "syrah"],
        "category": "French wine",
    },
    "japanese": {
        "prefer": ["pinot noir", "gamay", "sparkling", "riesling"],
        "category": "light red or white",
    },
    "thai": {
        "prefer": ["riesling", "gewürztraminer", "rosé", "rose"],
        "category": "aromatic white or rosé",
    },
    "mexican": {
        "prefer": ["malbec", "tempranillo", "rosé", "rose"],
        "category": "red or rosé",
    },
    "indian": {
        "prefer": ["riesling", "gewürztraminer", "rosé", "rose"],
        "category": "aromatic white or rosé",
    },
    "korean": {
        "prefer": ["riesling", "gamay", "pinot noir", "rosé", "rose"],
        "category": "light red or aromatic white",
    },
    "chinese": {
        "prefer": ["riesling", "pinot noir", "gamay", "rosé", "rose"],
        "category": "light red or aromatic white",
    },
    "spanish": {
        "prefer": ["tempranillo", "garnacha", "rosé", "rose", "malbec"],
        "category": "Spanish wine",
    },
    "greek": {
        "prefer": ["rosé", "rose", "sauvignon blanc", "pinot noir"],
        "category": "white or rosé",
    },
    "mediterranean": {
        "prefer": ["rosé", "rose", "sangiovese", "tempranillo", "sauvignon blanc"],
        "category": "rosé or Mediterranean red",
    },
    "bbq": {
        "prefer": ["zinfandel", "syrah", "malbec", "cabernet"],
        "category": "bold red",
    },
    "barbecue": {
        "prefer": ["zinfandel", "syrah", "malbec", "cabernet"],
        "category": "bold red",
    },
    "grilled": {
        "prefer": ["cabernet", "syrah", "malbec", "rosé", "rose"],
        "category": "bold red or rosé",
    },
    "braised": {
        "prefer": ["cabernet", "syrah", "barolo", "bordeaux"],
        "category": "bold red",
    },
    "roasted": {
        "prefer": ["pinot noir", "cabernet", "syrah", "chardonnay"],
        "category": "medium to bold red",
    },
    "smoked": {
        "prefer": ["syrah", "zinfandel", "malbec", "cabernet"],
        "category": "bold red",
    },
    # Style-based
    "pasta": {
        "prefer": ["sangiovese", "chianti", "pinot noir", "barbera"],
        "category": "Italian red",
    },
    "lasagna": {
        "prefer": ["sangiovese", "chianti", "barbera", "nebbiolo", "merlot"],
        "category": "Italian red or medium red",
    },
    "risotto": {
        "prefer": ["pinot grigio", "chardonnay", "pinot noir", "nebbiolo"],
        "category": "white or light red",
    },
    "pizza": {
        "prefer": ["sangiovese", "chianti", "barbera", "montepulciano", "pinot noir"],
        "category": "Italian red or light red",
    },
    "noodle": {
        "prefer": ["riesling", "pinot noir", "gamay", "rosé", "rose"],
        "category": "light red or aromatic white",
    },
    "ramen": {
        "prefer": ["riesling", "pinot noir", "gamay"],
        "category": "light red or aromatic white",
    },
    "pho": {
        "prefer": ["riesling", "pinot noir", "gamay"],
        "category": "light red or aromatic white",
    },
    "udon": {
        "prefer": ["riesling", "pinot noir", "gamay"],
        "category": "light red or aromatic white",
    },
    "soba": {
        "prefer": ["riesling", "pinot noir", "gamay"],
        "category": "light red or aromatic white",
    },
    "mac": {
        "prefer": ["chardonnay", "pinot noir", "rosé", "rose"],
        "category": "white or light red",
    },
    "shepherd": {
        "prefer": ["cabernet", "syrah", "merlot", "malbec", "pinot noir"],
        "category": "medium to bold red",
    },
    "salad": {
        "prefer": ["sauvignon blanc", "rosé", "rose", "sparkling"],
        "category": "white or rosé",
    },
    "soup": {
        "prefer": ["chardonnay", "pinot noir", "riesling"],
        "category": "white or light red",
    },
    "taco": {
        "prefer": ["malbec", "tempranillo", "rosé", "rose"],
        "category": "red or rosé",
    },
    "tacos": {
        "prefer": ["malbec", "tempranillo", "rosé", "rose"],
        "category": "red or rosé",
    },
    "burrito": {
        "prefer": ["malbec", "tempranillo", "zinfandel"],
        "category": "medium to bold red",
    },
    "enchilada": {
        "prefer": ["malbec", "tempranillo", "zinfandel"],
        "category": "medium to bold red",
    },
    "quesadilla": {
        "prefer": ["malbec", "tempranillo", "rosé", "rose"],
        "category": "red or rosé",
    },
    "curry": {
        "prefer": ["riesling", "gewürztraminer", "rosé", "rose"],
        "category": "aromatic white or rosé",
    },
    "stew": {
        "prefer": ["cabernet", "syrah", "merlot", "zinfandel"],
        "category": "bold red",
    },
    "chili": {
        "prefer": ["zinfandel", "malbec", "syrah", "tempranillo"],
        "category": "bold red",
    },
    "casserole": {
        "prefer": ["pinot noir", "merlot", "chardonnay"],
        "category": "medium red or white",
    },
    "sandwich": {
        "prefer": ["pinot noir", "rosé", "rose", "zinfandel"],
        "category": "light red or rosé",
    },
    "beans": {
        "prefer": ["tempranillo", "malbec", "zinfandel", "rosé", "rose", "pinot noir"],
        "category": "medium red or rosé",
    },
    "lentil": {
        "prefer": ["pinot noir", "syrah", "rosé", "rose"],
        "category": "medium red",
    },
    "tofu": {
        "prefer": ["pinot noir", "riesling", "sauvignon blanc", "rosé", "rose"],
        "category": "light red or white",
    },
    "tempeh": {
        "prefer": ["pinot noir", "riesling", "sauvignon blanc"],
        "category": "light red or white",
    },
    "vegetarian": {
        "prefer": ["pinot noir", "sauvignon blanc", "rosé", "rose"],
        "category": "light red or white",
    },
    "vegan": {
        "prefer": ["pinot noir", "sauvignon blanc", "rosé", "rose"],
        "category": "light red or white",
    },
}

# All recognized keywords — used by parse_menu.py for extraction
ALL_KEYWORDS = set(PAIRING_RULES.keys())

# ---------------------------------------------------------------------------
# Enriched feature → wine preference mappings (used by pairing.py)
# ---------------------------------------------------------------------------

# Protein → preferred wine styles (same format as PAIRING_RULES["prefer"])
ENRICHED_PROTEIN_RULES: dict[str, list[str]] = {
    "beef": ["cabernet", "syrah", "merlot", "barolo", "bordeaux", "malbec"],
    "lamb": ["cabernet", "syrah", "bordeaux", "rhône", "rhone"],
    "pork": ["pinot noir", "rosé", "rose", "riesling", "chardonnay"],
    "chicken": ["pinot noir", "chardonnay", "rosé", "rose"],
    "turkey": ["pinot noir", "chardonnay", "gamay"],
    "duck": ["pinot noir", "syrah", "gamay"],
    "salmon": ["pinot noir", "chardonnay", "rosé", "rose"],
    "tuna": ["pinot noir", "rosé", "rose"],
    "fish": ["chardonnay", "sauvignon blanc", "pinot grigio"],
    "shellfish": ["chardonnay", "sauvignon blanc", "sparkling"],
    "shrimp": ["sauvignon blanc", "sparkling", "rosé", "rose"],
    "tofu": ["pinot noir", "riesling", "sauvignon blanc"],
    "vegetable": ["sauvignon blanc", "rosé", "rose", "pinot noir"],
}

# Preparation → wine style adjustments
ENRICHED_PREPARATION_RULES: dict[str, list[str]] = {
    "grilled": ["cabernet", "syrah", "malbec", "zinfandel"],
    "braised": ["cabernet", "syrah", "barolo", "bordeaux"],
    "roasted": ["pinot noir", "cabernet", "chardonnay"],
    "smoked": ["syrah", "zinfandel", "malbec"],
    "fried": ["sparkling", "rosé", "rose", "sauvignon blanc"],
    "raw": ["sparkling", "sauvignon blanc", "pinot grigio"],
    "poached": ["chardonnay", "pinot grigio", "riesling"],
    "sautéed": ["pinot noir", "chardonnay", "sauvignon blanc"],
    "steamed": ["riesling", "sauvignon blanc", "pinot grigio"],
}

# Richness → wine body preference
ENRICHED_RICHNESS_RULES: dict[str, list[str]] = {
    "light": ["sauvignon blanc", "pinot grigio", "rosé", "rose", "gamay", "riesling"],
    "medium": ["pinot noir", "chardonnay", "merlot", "sangiovese", "barbera"],
    "rich": ["cabernet", "syrah", "barolo", "bordeaux", "malbec", "zinfandel"],
}

# Spice heat → wine affinity
ENRICHED_SPICE_RULES: dict[str, list[str]] = {
    "medium": ["riesling", "rosé", "rose", "pinot noir"],
    "high": ["riesling", "gewürztraminer", "rosé", "rose"],
}

# Acidity → wine acidity matching
ENRICHED_ACIDITY_RULES: dict[str, list[str]] = {
    "medium-high": ["sauvignon blanc", "sangiovese", "barbera", "riesling"],
    "high": ["sauvignon blanc", "sangiovese", "barbera", "riesling", "sparkling"],
}

# Cuisine → wine region affinity
ENRICHED_CUISINE_RULES: dict[str, list[str]] = {
    "italian": ["sangiovese", "nebbiolo", "barbera", "pinot grigio", "chianti"],
    "french": ["bordeaux", "burgundy", "pinot noir", "chardonnay", "syrah"],
    "japanese": ["pinot noir", "gamay", "sparkling", "riesling"],
    "thai": ["riesling", "gewürztraminer", "rosé", "rose"],
    "mexican": ["malbec", "tempranillo", "rosé", "rose"],
    "indian": ["riesling", "gewürztraminer", "rosé", "rose"],
    "korean": ["riesling", "gamay", "pinot noir"],
    "chinese": ["riesling", "pinot noir", "gamay"],
    "spanish": ["tempranillo", "garnacha", "rosé", "rose"],
    "greek": ["rosé", "rose", "sauvignon blanc"],
    "mediterranean": ["rosé", "rose", "sangiovese", "tempranillo"],
    "american": ["cabernet", "zinfandel", "chardonnay", "pinot noir"],
}
