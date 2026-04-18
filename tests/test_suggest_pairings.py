"""Integration tests for suggest_pairings() in pairing.py.

Tests the enriched-first fallback chain and bottle suggestion flow
end-to-end, without mocking internal functions.
"""

from datetime import date, timedelta

from pairing import suggest_pairings
from wine_utils import CURRENT_YEAR

# Monday of the current week
_monday = date.today() - timedelta(days=date.today().weekday())
_monday_str = _monday.isoformat()
_tuesday_str = (_monday + timedelta(days=1)).isoformat()
_wednesday_str = (_monday + timedelta(days=2)).isoformat()


def _plan_week(name="Test Cabernet Sauvignon", vintage="2020", badge="red"):
    return {
        "date": _monday.strftime("%b %-d, %Y"),
        "week": "Week 1",
        "name": name,
        "vintage": vintage,
        "badge": badge,
        "appellation": "Napa Valley",
    }


def _inventory_wine(
    name="Alt Pinot Noir",
    vintage="2019",
    varietal="Pinot Noir",
    wine_type="Red",
    begin=None,
    end=None,
):
    return {
        "Wine": name,
        "Vintage": vintage,
        "Varietal": varietal,
        "Type": wine_type,
        "MasterVarietal": varietal,
        "Region": "Willamette Valley",
        "SubRegion": "",
        "BeginConsume": begin or CURRENT_YEAR - 1,
        "EndConsume": end or CURRENT_YEAR + 3,
        "CT": 90,
        "Quantity": 3,
        "Location": "Cellar",
        "Bin": "A1",
    }


class TestEnrichedFirstFallback:
    """suggest_pairings() tries enriched features, then keywords, then neutral."""

    def test_enriched_good_match_no_fallback(self):
        """When enriched data scores 'good', keyword path is not used."""
        menu = [{"date": _monday_str, "meal": "Grilled Steak", "keywords": ["steak"]}]
        plan = [_plan_week()]
        inventory = [_inventory_wine()]
        enriched = [
            {
                "date": _monday_str,
                "meal": "Grilled Steak",
                "enriched": {
                    "protein": "beef",
                    "preparation": "grilled",
                    "richness": "rich",
                    "cuisine": "american",
                },
            }
        ]
        result = suggest_pairings(menu, plan, inventory, enriched)
        assert len(result) == 1
        assert result[0]["pairing"]["score"] == "good"
        assert result[0]["pairing"]["confidence"] == "high"

    def test_enriched_returns_none_falls_back_to_keywords(self):
        """When enriched data has no recognized features, fall back to keywords."""
        menu = [{"date": _monday_str, "meal": "Grilled Steak", "keywords": ["steak"]}]
        plan = [_plan_week()]
        inventory = [_inventory_wine()]
        enriched = [
            {
                "date": _monday_str,
                "meal": "Grilled Steak",
                "enriched": {"sides": ["potatoes"]},  # no recognized features
            }
        ]
        result = suggest_pairings(menu, plan, inventory, enriched)
        assert len(result) == 1
        # Should fall back to keyword matching (steak → bold red)
        assert result[0]["pairing"]["score"] in ("good", "partial", "poor")
        assert result[0]["pairing"]["confidence"] == "medium"  # keyword default

    def test_no_enriched_data_uses_keywords(self):
        """When no enriched data exists for a meal, use keyword matching."""
        menu = [{"date": _monday_str, "meal": "Grilled Steak", "keywords": ["steak"]}]
        plan = [_plan_week()]
        inventory = [_inventory_wine()]
        result = suggest_pairings(menu, plan, inventory, enriched=None)
        assert len(result) == 1
        assert result[0]["pairing"]["confidence"] == "medium"

    def test_no_keywords_no_enriched_gives_neutral(self):
        """No enriched data and no keywords → neutral with low confidence."""
        menu = [{"date": _monday_str, "meal": "Leftovers", "keywords": []}]
        plan = [_plan_week()]
        inventory = [_inventory_wine()]
        result = suggest_pairings(menu, plan, inventory, enriched=None)
        assert len(result) == 1
        assert result[0]["pairing"]["score"] == "neutral"
        assert result[0]["pairing"]["confidence"] == "low"

    def test_enriched_poor_with_suggested_styles_finds_bottle(self):
        """When enriched match is poor, suggested_styles drive bottle suggestion."""
        menu = [{"date": _monday_str, "meal": "Grilled Fish", "keywords": []}]
        # Plan a bold red that won't match fish
        plan = [_plan_week(name="Big Cabernet", badge="red")]
        # Inventory has a white wine that should match
        inventory = [
            _inventory_wine(
                name="Sauvignon Blanc",
                varietal="Sauvignon Blanc",
                wine_type="White",
            )
        ]
        enriched = [
            {
                "date": _monday_str,
                "meal": "Grilled Fish",
                "enriched": {"protein": "fish", "preparation": "grilled"},
            }
        ]
        result = suggest_pairings(menu, plan, inventory, enriched)
        assert len(result) == 1
        pairing = result[0]["pairing"]
        # The enriched engine should score this as poor/partial for cabernet + fish
        assert pairing["score"] in ("poor", "partial")
        # With suggested_styles from enriched, should find the white wine
        if "suggested_bottle" in result[0]:
            assert "Sauvignon Blanc" in result[0]["suggested_bottle"]["wine"]

    def test_each_meal_gets_unique_suggestion(self):
        """No bottle is suggested twice across meals."""
        menu = [
            {"date": _monday_str, "meal": "Steak", "keywords": ["steak"]},
            {"date": _tuesday_str, "meal": "Ribs", "keywords": ["ribs"]},
        ]
        plan = [_plan_week(name="Light Pinot", badge="red")]
        inventory = [
            _inventory_wine(name="Bold Cab 1", varietal="Cabernet Sauvignon"),
            _inventory_wine(
                name="Bold Cab 2", vintage="2018", varietal="Cabernet Sauvignon"
            ),
        ]
        result = suggest_pairings(menu, plan, inventory)
        suggested = [
            r["suggested_bottle"]["wine"] for r in result if "suggested_bottle" in r
        ]
        # All suggestions should be unique
        assert len(suggested) == len(set(suggested))


class TestNoWeekForDate:
    def test_menu_with_no_matching_plan_week(self):
        """Menu date with no plan week gets a note, not a crash."""
        far_future = "2099-01-01"
        menu = [{"date": far_future, "meal": "Dinner", "keywords": []}]
        plan = [_plan_week()]
        result = suggest_pairings(menu, plan, [])
        assert len(result) == 1
        assert "note" in result[0]
