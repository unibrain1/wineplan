"""Tests for build_score() pro score priority chain in generate_plan.py."""

from generate_plan import build_score


class TestBuildScore:
    """build_score() returns best available critic score label."""

    def test_wa_takes_priority(self):
        wine = {"WA": 95, "WS": 93, "CT": 90}
        assert build_score(wine) == "WA95"

    def test_ws_when_no_wa(self):
        wine = {"WS": 93, "BH": 91, "CT": 90}
        assert build_score(wine) == "WS93"

    def test_bh_when_no_wa_ws(self):
        wine = {"BH": 91, "CT": 90}
        assert build_score(wine) == "BH91"

    def test_ag_priority(self):
        wine = {"AG": 92, "JR": 17, "CT": 88}
        assert build_score(wine) == "AG92"

    def test_jr_priority(self):
        wine = {"JR": 17.5, "JS": 94, "CT": 90}
        assert build_score(wine) == "JR17.5"

    def test_js_priority(self):
        wine = {"JS": 94, "JG": 93, "CT": 90}
        assert build_score(wine) == "JS94"

    def test_jg_priority(self):
        wine = {"JG": 93, "CT": 90}
        assert build_score(wine) == "JG93"

    def test_ct_only(self):
        wine = {"CT": 90}
        assert build_score(wine) == "CT90"

    def test_no_scores_returns_none(self):
        wine = {}
        assert build_score(wine) is None

    def test_whole_number_no_decimal(self):
        """Whole number scores should not show '.0'."""
        wine = {"WA": 92.0}
        assert build_score(wine) == "WA92"

    def test_fractional_score_preserved(self):
        """Fractional scores like JR 17.5 should keep the decimal."""
        wine = {"JR": 17.5}
        assert build_score(wine) == "JR17.5"

    def test_none_values_skipped(self):
        """Fields set to None should be skipped in priority chain."""
        wine = {"WA": None, "WS": None, "CT": 88}
        assert build_score(wine) == "CT88"

    def test_zero_score_is_valid(self):
        """A score of 0 should still be returned (not skipped)."""
        wine = {"WA": 0}
        assert build_score(wine) == "WA0"
