"""Tests for enriched pairing matching in pairing.py."""

from pairing import _build_enriched_index, score_enriched_pairing


class TestScoreEnrichedPairing:
    """score_enriched_pairing() scores wine against enriched food features."""

    def test_good_match_bold_red_with_beef(self):
        # Cabernet should match beef + grilled + rich
        enriched = {"protein": "beef", "preparation": "grilled", "richness": "rich"}
        result = score_enriched_pairing("cabernet sauvignon reserve", enriched)
        assert result is not None
        assert result["score"] == "good"

    def test_poor_match_white_with_beef(self):
        # Sauvignon blanc should not match beef
        enriched = {"protein": "beef", "preparation": "grilled", "richness": "rich"}
        result = score_enriched_pairing("sauvignon blanc", enriched)
        assert result is not None
        assert result["score"] in ("poor", "partial")

    def test_good_match_pinot_with_chicken(self):
        enriched = {
            "protein": "chicken",
            "preparation": "roasted",
            "richness": "medium",
        }
        result = score_enriched_pairing("pinot noir laurène", enriched)
        assert result is not None
        assert result["score"] == "good"

    def test_no_signal_returns_none(self):
        # Enriched data with no recognized features
        enriched = {"sides": ["potatoes"]}
        result = score_enriched_pairing("any wine", enriched)
        assert result is None

    def test_empty_enriched_returns_none(self):
        result = score_enriched_pairing("any wine", {})
        assert result is None

    def test_confidence_high_with_many_signals(self):
        enriched = {
            "protein": "pork",
            "preparation": "grilled",
            "richness": "medium",
            "cuisine": "american",
        }
        result = score_enriched_pairing("pinot noir", enriched)
        assert result is not None
        assert result["confidence"] == "high"

    def test_confidence_low_with_one_signal(self):
        enriched = {"protein": "chicken"}
        result = score_enriched_pairing("pinot noir", enriched)
        assert result is not None
        assert result["confidence"] == "low"

    def test_confidence_medium_with_two_signals(self):
        enriched = {"protein": "fish", "richness": "light"}
        result = score_enriched_pairing("sauvignon blanc", enriched)
        assert result is not None
        assert result["confidence"] == "medium"

    def test_partial_match(self):
        # Pinot noir matches chicken but not spice
        enriched = {"protein": "chicken", "spice_heat": "high"}
        result = score_enriched_pairing("pinot noir", enriched)
        assert result is not None
        assert result["score"] == "partial"

    def test_spice_heat_favors_riesling(self):
        # Riesling matches spice_heat=high but not protein=chicken → partial
        enriched = {"protein": "chicken", "spice_heat": "high"}
        result = score_enriched_pairing("riesling", enriched)
        assert result is not None
        assert result["score"] == "partial"

    def test_spice_only_riesling_good(self):
        # With only spice signal, riesling is a good match
        enriched = {"spice_heat": "high"}
        result = score_enriched_pairing("riesling", enriched)
        assert result is not None
        assert result["score"] == "good"

    def test_acidity_matching(self):
        enriched = {"acidity": "high"}
        result = score_enriched_pairing("sangiovese chianti", enriched)
        assert result is not None
        assert result["score"] == "good"

    def test_cuisine_matching_italian(self):
        enriched = {"cuisine": "italian", "richness": "medium"}
        result = score_enriched_pairing("sangiovese chianti classico", enriched)
        assert result is not None
        assert result["score"] == "good"

    def test_suggested_styles_on_mismatch(self):
        enriched = {"protein": "beef", "richness": "rich"}
        result = score_enriched_pairing("riesling", enriched)
        assert result is not None
        assert "suggested_styles" in result
        assert len(result["suggested_styles"]) > 0

    def test_list_valued_protein_does_not_crash(self):
        # The LLM occasionally returns a list for a scalar field when the dish
        # has multiple proteins. Must not raise TypeError on dict membership.
        enriched = {"protein": ["salmon", "shrimp"]}
        result = score_enriched_pairing("pinot noir", enriched)
        assert result is not None
        assert result["score"] == "good"

    def test_list_valued_protein_first_known_wins(self):
        # Unknown leading entries are skipped; first known key drives scoring.
        enriched = {"protein": ["unknownfish", "beef"]}
        result = score_enriched_pairing("cabernet sauvignon", enriched)
        assert result is not None
        assert result["score"] == "good"

    def test_list_valued_cuisine_does_not_crash(self):
        enriched = {"cuisine": ["italian", "american"], "richness": "medium"}
        result = score_enriched_pairing("sangiovese chianti", enriched)
        assert result is not None

    def test_list_with_no_known_keys_skipped(self):
        # A list of unrecognized values should produce no signal, not crash.
        enriched = {"protein": ["unobtanium"]}
        result = score_enriched_pairing("any wine", enriched)
        assert result is None


class TestBuildEnrichedIndex:
    def test_builds_index_from_enriched_list(self):
        enriched = [
            {
                "date": "2026-04-20",
                "meal": "Grilled chicken",
                "enriched": {"protein": "chicken"},
            }
        ]
        index = _build_enriched_index(enriched)
        assert "2026-04-20|Grilled chicken" in index

    def test_skips_entries_without_enriched(self):
        enriched = [{"date": "2026-04-20", "meal": "Leftovers", "enriched": None}]
        index = _build_enriched_index(enriched)
        assert len(index) == 0

    def test_empty_list(self):
        assert _build_enriched_index([]) == {}
