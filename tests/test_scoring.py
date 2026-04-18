"""Unit tests for window_position_score() in scripts/scoring.py.

All wine dicts use year offsets relative to CURRENT_YEAR so the tests remain
valid regardless of which calendar year pytest is run.

Formula reference (from scoring.py):
  Past peak:     min(100, 70 + (CURRENT_YEAR - end) * 5)
  In window:     30 + blended * 35
                   where blended = 0.5 * peak_quality + 0.5 * end_urgency
                         peak_quality = 1 - abs(position - 0.5) * 2
                         end_urgency  = position
                         position     = (CURRENT_YEAR - begin) / window_length
  Before window: max(0, 15 - (begin - CURRENT_YEAR) * 5)
  No data:       35.0
"""

import pytest

from scoring import (
    community_score,
    composite_score,
    ct_score_component,
    diversity_score,
    seasonal_fit_score,
    window_position_score,
)
from wine_utils import CURRENT_YEAR

Y = CURRENT_YEAR  # shorthand used throughout


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def wine(begin=None, end=None):
    """Construct a minimal wine dict with optional BeginConsume / EndConsume."""
    w = {}
    if begin is not None:
        w["BeginConsume"] = begin
    if end is not None:
        w["EndConsume"] = end
    return w


# ---------------------------------------------------------------------------
# TestWindowPositionPastPeak
# ---------------------------------------------------------------------------


class TestWindowPositionPastPeak:
    """End < CURRENT_YEAR: min(100, 70 + years_past * 5)."""

    def test_one_year_past_peak(self):
        # years_past = 1 → 70 + 5 = 75
        assert window_position_score(wine(end=Y - 1)) == pytest.approx(75.0)

    def test_two_years_past_peak(self):
        # years_past = 2 → 70 + 10 = 80
        assert window_position_score(wine(end=Y - 2)) == pytest.approx(80.0)

    def test_five_years_past_peak_not_yet_capped(self):
        # years_past = 5 → 70 + 25 = 95 (still below 100)
        assert window_position_score(wine(end=Y - 5)) == pytest.approx(95.0)

    def test_six_years_past_peak_first_cap_hit(self):
        # years_past = 6 → 70 + 30 = 100 (cap is reached exactly here)
        assert window_position_score(wine(end=Y - 6)) == pytest.approx(100.0)

    def test_ten_years_past_peak_cap_holds(self):
        # years_past = 10 → would be 120 without cap, clamped to 100
        assert window_position_score(wine(end=Y - 10)) == pytest.approx(100.0)

    def test_begin_consume_present_does_not_affect_past_peak(self):
        # BeginConsume is irrelevant once wine is past peak.
        # Both wines share the same EndConsume; only EndConsume drives the score.
        score_without_begin = window_position_score(wine(end=Y - 3))
        score_with_begin = window_position_score(wine(begin=Y - 20, end=Y - 3))
        assert score_without_begin == pytest.approx(score_with_begin)

    def test_begin_consume_far_in_future_ignored_when_past_peak(self):
        # Pathological dict: begin > end but end is already past peak.
        # The past-peak branch fires on end < CURRENT_YEAR regardless of begin.
        # years_past = 2 → 80
        assert window_position_score(wine(begin=Y + 5, end=Y - 2)) == pytest.approx(
            80.0
        )


# ---------------------------------------------------------------------------
# TestWindowPositionInWindow
# ---------------------------------------------------------------------------


class TestWindowPositionInWindow:
    """begin <= CURRENT_YEAR <= end: 30 + blended * 35.

    Constructing specific positions:
      position=0.0  → begin=Y,    end=Y+10  (window_length=10, pos=0/10=0.0)
      position=0.5  → begin=Y-5,  end=Y+5   (window_length=10, pos=5/10=0.5)
      position=1.0  → begin=Y-10, end=Y     (window_length=10, pos=10/10=1.0)
      position=0.6  → begin=Y-6,  end=Y+4   (window_length=10, pos=6/10=0.6)
    """

    # --- Exact score assertions ---

    def test_position_zero_just_entered_window(self):
        # position=0.0: peak_quality=0.0, end_urgency=0.0, blended=0.0 → 30.0
        w = wine(begin=Y, end=Y + 10)
        assert window_position_score(w) == pytest.approx(30.0)

    def test_position_midpoint(self):
        # position=0.5: peak_quality=1.0, end_urgency=0.5, blended=0.75 → 56.25
        w = wine(begin=Y - 5, end=Y + 5)
        assert window_position_score(w) == pytest.approx(56.25)

    def test_position_one_end_of_window(self):
        # position=1.0: peak_quality=0.0, end_urgency=1.0, blended=0.5 → 47.5
        w = wine(begin=Y - 10, end=Y)
        assert window_position_score(w) == pytest.approx(47.5)

    # --- Ordering assertions ---

    def test_midpoint_beats_start(self):
        # Midpoint (0.5) should outscore the very start (0.0).
        score_start = window_position_score(wine(begin=Y, end=Y + 10))
        score_mid = window_position_score(wine(begin=Y - 5, end=Y + 5))
        assert score_mid > score_start

    def test_midpoint_beats_end(self):
        # Midpoint (0.5) should outscore the very end (1.0).
        score_mid = window_position_score(wine(begin=Y - 5, end=Y + 5))
        score_end = window_position_score(wine(begin=Y - 10, end=Y))
        assert score_mid > score_end

    def test_midpoint_beats_position_0_6(self):
        # 0.5 is the actual peak of the blended formula, so 0.6 must score lower.
        # position=0.6: begin=Y-6, end=Y+4, window_length=10
        score_mid = window_position_score(wine(begin=Y - 5, end=Y + 5))
        score_0_6 = window_position_score(wine(begin=Y - 6, end=Y + 4))
        assert score_mid > score_0_6

    def test_all_in_window_scores_in_valid_range(self):
        # Every in-window score must lie in [30.0, 56.25].
        # Max is 30 + 0.75*35 = 56.25 at position=0.5 (midpoint).
        positions_windows = [
            wine(begin=Y, end=Y + 10),  # position=0.0
            wine(begin=Y - 5, end=Y + 5),  # position=0.5
            wine(begin=Y - 10, end=Y),  # position=1.0
            wine(begin=Y - 6, end=Y + 4),  # position=0.6
            wine(begin=Y - 1, end=Y + 9),  # position=0.1
            wine(begin=Y - 9, end=Y + 1),  # position=0.9
        ]
        for w in positions_windows:
            score = window_position_score(w)
            assert 30.0 <= score <= 56.25, (
                f"Score {score} out of [30, 56.25] range for wine {w}"
            )


# ---------------------------------------------------------------------------
# TestWindowPositionBeforeWindow
# ---------------------------------------------------------------------------


class TestWindowPositionBeforeWindow:
    """begin > CURRENT_YEAR: max(0, 15 - years_before * 5)."""

    def test_one_year_before_window(self):
        # years_before=1 → 15 - 5 = 10
        assert window_position_score(wine(begin=Y + 1, end=Y + 11)) == pytest.approx(
            10.0
        )

    def test_two_years_before_window(self):
        # years_before=2 → 15 - 10 = 5
        assert window_position_score(wine(begin=Y + 2, end=Y + 12)) == pytest.approx(
            5.0
        )

    def test_three_years_before_window_first_zero(self):
        # years_before=3 → 15 - 15 = 0 (floor first reached here)
        assert window_position_score(wine(begin=Y + 3, end=Y + 13)) == pytest.approx(
            0.0
        )

    def test_four_years_before_window_floor_holds(self):
        # years_before=4 → would be -5 without floor; clamped to 0
        assert window_position_score(wine(begin=Y + 4, end=Y + 14)) == pytest.approx(
            0.0
        )

    def test_ten_years_before_window_floor_holds(self):
        # years_before=10 → -35 without floor; clamped to 0
        assert window_position_score(wine(begin=Y + 10, end=Y + 20)) == pytest.approx(
            0.0
        )


# ---------------------------------------------------------------------------
# TestWindowPositionMissingData
# ---------------------------------------------------------------------------


class TestWindowPositionMissingData:
    """Missing BeginConsume / EndConsume values trigger inference or default."""

    def test_both_none_returns_default(self):
        # No window data at all → neutral default score.
        assert window_position_score(wine()) == pytest.approx(35.0)

    def test_empty_dict_returns_default(self):
        # No keys present at all — identical to both being None.
        assert window_position_score({}) == pytest.approx(35.0)

    def test_end_consume_only_infers_begin(self):
        # Only EndConsume present.
        # Inference: begin = end - 5
        # With end=Y: inferred begin=Y-5, window_length=5
        # position = (Y - (Y-5)) / 5 = 5/5 = 1.0
        # peak_quality=0.0, end_urgency=1.0, blended=0.5 → score=47.5
        assert window_position_score(wine(end=Y)) == pytest.approx(47.5)

    def test_begin_consume_only_infers_end(self):
        # Only BeginConsume present.
        # Inference: end = begin + 10
        # With begin=Y: inferred end=Y+10, window_length=10
        # position = (Y - Y) / 10 = 0.0
        # peak_quality=0.0, end_urgency=0.0, blended=0.0 → score=30.0
        assert window_position_score(wine(begin=Y)) == pytest.approx(30.0)

    def test_end_consume_only_past_peak_uses_inferred_begin(self):
        # Inferred begin does not affect past-peak branch (end drives it).
        # years_past=2 → 80.0; begin is inferred but irrelevant.
        assert window_position_score(wine(end=Y - 2)) == pytest.approx(80.0)

    def test_end_consume_only_before_window(self):
        # end=Y+6 → inferred begin=Y+1 → before-window: years_before=1 → 10.0
        assert window_position_score(wine(end=Y + 6)) == pytest.approx(10.0)

    def test_begin_consume_only_past_peak(self):
        # begin=Y-15 → inferred end=Y-5 → past-peak: years_past=5 → 95.0
        assert window_position_score(wine(begin=Y - 15)) == pytest.approx(95.0)


# ---------------------------------------------------------------------------
# TestWindowPositionEdgeCases
# ---------------------------------------------------------------------------


class TestWindowPositionEdgeCases:
    """Boundary and degenerate inputs."""

    def test_past_peak_always_exceeds_in_window(self):
        # Worst past-peak (1yr, 75.0) must always beat best in-window (midpoint, 56.25).
        worst_past_peak = window_position_score(wine(end=Y - 1))
        best_in_window = window_position_score(wine(begin=Y - 5, end=Y + 5))
        assert worst_past_peak > best_in_window

    def test_zero_length_window_in_current_year(self):
        # begin == end == CURRENT_YEAR: window_length forced to 1.
        # begin > CURRENT_YEAR? No (begin==Y). past peak? No (end==Y, not < Y).
        # In-window branch: window_length=0 → forced to 1, position=0/1=0.0
        # score = 30.0
        assert window_position_score(wine(begin=Y, end=Y)) == pytest.approx(30.0)

    def test_zero_length_window_past_peak(self):
        # begin == end == CURRENT_YEAR - 1: end < CURRENT_YEAR, so past-peak fires.
        # years_past=1 → 75.0
        # The in-window branch (with its window_length guard) is never reached.
        assert window_position_score(wine(begin=Y - 1, end=Y - 1)) == pytest.approx(
            75.0
        )

    def test_very_old_wine_no_overflow(self):
        # EndConsume = CURRENT_YEAR - 50: years_past=50, raw=70+250=320, capped at 100.
        assert window_position_score(wine(end=Y - 50)) == pytest.approx(100.0)

    def test_return_type_is_float(self):
        # The function must always return a float, not an int.
        result = window_position_score(wine(begin=Y - 3, end=Y + 3))
        assert isinstance(result, float)

    def test_score_never_exceeds_100(self):
        # Exhaustive check for a range of past-peak depths.
        for years_past in range(1, 101):
            score = window_position_score(wine(end=Y - years_past))
            assert score <= 100.0, (
                f"Score {score} exceeded 100 at years_past={years_past}"
            )

    def test_score_never_below_zero(self):
        # Exhaustive check for a range of before-window distances.
        for years_before in range(1, 101):
            score = window_position_score(
                wine(begin=Y + years_before, end=Y + years_before + 5)
            )
            assert score >= 0.0, (
                f"Score {score} went below 0 at years_before={years_before}"
            )


# ---------------------------------------------------------------------------
# TestSeasonalFitMapping
# ---------------------------------------------------------------------------


class TestSeasonalFitMapping:
    """seasonal_fit_score() maps seasonal_score() penalty (0/1/2) to 100/50/0.

    SEASONAL_FIT_MAP = {0: 100.0, 1: 50.0, 2: 0.0}

    Badge resolution: TYPE_TO_BADGE.get(wine["Type"], "red")
    Red subtype resolution: is_bold_red() and is_light_red() search
      wine["Wine"], wine["Varietal"], and wine["MasterVarietal"].
    """

    def test_perfect_fit_returns_100(self):
        # Sparkling in summer → seasonal_score=0 (perfect) → 100.0
        w = {"Type": "Sparkling"}
        assert seasonal_fit_score(w, "summer") == pytest.approx(100.0)

    def test_acceptable_fit_returns_50(self):
        # Sparkling in winter → seasonal_score=1 (acceptable) → 50.0
        w = {"Type": "Sparkling"}
        assert seasonal_fit_score(w, "winter") == pytest.approx(50.0)

    def test_poor_fit_returns_0(self):
        # Bold red (Cabernet Sauvignon) in summer → seasonal_score=2 (poor) → 0.0
        # is_bold_red() matches "cabernet" in Varietal.
        w = {"Type": "Red", "Varietal": "Cabernet Sauvignon"}
        assert seasonal_fit_score(w, "summer") == pytest.approx(0.0)

    def test_red_in_winter_perfect(self):
        # Any red badge in fall/winter → seasonal_score=0 (perfect) → 100.0
        # A generic "Red" with no bold/light keywords still returns 0 in winter.
        w = {"Type": "Red", "Varietal": "Grenache"}
        assert seasonal_fit_score(w, "winter") == pytest.approx(100.0)

    def test_rose_in_winter_poor(self):
        # Rosé in winter → seasonal_score=2 (poor) → 0.0
        # CellarTracker Type for rosé is "Rosé" (with accent).
        w = {"Type": "Rosé"}
        assert seasonal_fit_score(w, "winter") == pytest.approx(0.0)

    def test_light_red_in_summer_perfect(self):
        # Light red (Pinot Noir) in summer → seasonal_score=0 (perfect) → 100.0
        # is_light_red() matches "pinot noir" in Varietal.
        w = {"Type": "Red", "Varietal": "Pinot Noir"}
        assert seasonal_fit_score(w, "summer") == pytest.approx(100.0)

    def test_white_in_summer_perfect(self):
        # White in summer → seasonal_score=0 (perfect) → 100.0
        w = {"Type": "White"}
        assert seasonal_fit_score(w, "summer") == pytest.approx(100.0)

    def test_white_in_winter_acceptable(self):
        # White in winter → seasonal_score=1 (acceptable) → 50.0
        w = {"Type": "White"}
        assert seasonal_fit_score(w, "winter") == pytest.approx(50.0)

    def test_bold_red_keyword_matched_via_wine_name(self):
        # "barolo" matched in Wine field (not Varietal) → is_bold_red=True
        # Bold red in summer → seasonal_score=2 (poor) → 0.0
        w = {"Type": "Red", "Wine": "Barolo Riserva 2018"}
        assert seasonal_fit_score(w, "summer") == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# TestCtScoreComponent
# ---------------------------------------------------------------------------


class TestCtScoreComponent:
    """ct_score_component() normalizes CT ratings to 0–100 via (ct - 80) * 5."""

    def test_ct_80_returns_0(self):
        assert ct_score_component({"CT": 80}) == pytest.approx(0.0)

    def test_ct_85_returns_25(self):
        assert ct_score_component({"CT": 85}) == pytest.approx(25.0)

    def test_ct_88_returns_40(self):
        # 88 is AVG_CT — the default for missing scores
        assert ct_score_component({"CT": 88}) == pytest.approx(40.0)

    def test_ct_90_returns_50(self):
        assert ct_score_component({"CT": 90}) == pytest.approx(50.0)

    def test_ct_95_returns_75(self):
        assert ct_score_component({"CT": 95}) == pytest.approx(75.0)

    def test_ct_100_returns_100(self):
        assert ct_score_component({"CT": 100}) == pytest.approx(100.0)

    def test_ct_below_80_clamped_to_0(self):
        assert ct_score_component({"CT": 75}) == pytest.approx(0.0)
        assert ct_score_component({"CT": 60}) == pytest.approx(0.0)

    def test_ct_above_100_clamped_to_100(self):
        assert ct_score_component({"CT": 105}) == pytest.approx(100.0)

    def test_ct_none_uses_avg(self):
        # CT=None → uses AVG_CT=88 → (88-80)*5 = 40.0
        assert ct_score_component({"CT": None}) == pytest.approx(40.0)

    def test_ct_missing_key_uses_avg(self):
        # No CT key → .get returns None → uses AVG_CT
        assert ct_score_component({}) == pytest.approx(40.0)

    def test_return_type_is_float(self):
        assert isinstance(ct_score_component({"CT": 90}), float)


# ---------------------------------------------------------------------------
# TestDiversityScore
# ---------------------------------------------------------------------------


class TestDiversityScore:
    """diversity_score() penalizes proximity to similar wines in placed[]."""

    def _make_wine(
        self,
        name: str = "Wine A",
        vintage: str = "2020",
        producer: str = "Producer A",
        varietal: str = "Cabernet Sauvignon",
    ) -> dict:
        return {
            "Wine": name,
            "Vintage": vintage,
            "Producer": producer,
            "Varietal": varietal,
        }

    def test_no_placed_wines_returns_100(self):
        # Empty placed list → no penalty → 100.0
        w = self._make_wine()
        assert diversity_score(w, 0, []) == pytest.approx(100.0)

    def test_all_none_slots_returns_100(self):
        placed: list[dict | None] = [None] * 10
        w = self._make_wine()
        assert diversity_score(w, 5, placed) == pytest.approx(100.0)

    def test_same_wine_adjacent(self):
        # Same wine 1 week ago: penalty = 60 * (1 - 1/5) = 48
        # Score = 100 - 48 = 52
        w = self._make_wine()
        placed: list[dict | None] = [None] * 10
        placed[4] = self._make_wine()  # same wine at index 4
        assert diversity_score(w, 5, placed) == pytest.approx(52.0)

    def test_same_wine_at_decay_boundary(self):
        # Same wine exactly 5 weeks ago: distance == DIV_DECAY_WEEKS → 0 penalty
        w = self._make_wine()
        placed: list[dict | None] = [None] * 10
        placed[0] = self._make_wine()
        assert diversity_score(w, 5, placed) == pytest.approx(100.0)

    def test_same_wine_at_4_weeks(self):
        # Same wine 4 weeks ago: penalty = 60 * (1 - 4/5) = 12
        # Score = 100 - 12 = 88
        w = self._make_wine()
        placed: list[dict | None] = [None] * 10
        placed[1] = self._make_wine()
        assert diversity_score(w, 5, placed) == pytest.approx(88.0)

    def test_same_producer_adjacent(self):
        # Same producer, different wine, 1 week ago: penalty = 35 * (1 - 1/5) = 28
        # Score = 100 - 28 = 72
        w = self._make_wine(name="Wine B")
        placed: list[dict | None] = [None] * 10
        placed[4] = self._make_wine(name="Wine A")  # same producer
        assert diversity_score(w, 5, placed) == pytest.approx(72.0)

    def test_same_varietal_adjacent(self):
        # Same varietal, different wine+producer, 1 week ago: penalty = 20 * (1 - 1/5) = 16
        # Score = 100 - 16 = 84
        w = self._make_wine(name="Wine B", vintage="2021", producer="Producer B")
        placed: list[dict | None] = [None] * 10
        placed[4] = self._make_wine(
            name="Wine A", vintage="2020", producer="Producer A"
        )
        assert diversity_score(w, 5, placed) == pytest.approx(84.0)

    def test_tier_priority_same_wine_beats_producer(self):
        # Same wine match should fire same-wine penalty (60), NOT producer (35)
        w = self._make_wine()
        placed: list[dict | None] = [None] * 10
        placed[4] = self._make_wine()  # same wine AND same producer
        score = diversity_score(w, 5, placed)
        # If same-wine fires: 100 - 60*(1-1/5) = 52
        # If producer fired instead: 100 - 35*(1-1/5) = 72
        assert score == pytest.approx(52.0)

    def test_tier_priority_producer_beats_varietal(self):
        # Same producer match should fire producer penalty (35), NOT varietal (20)
        w = self._make_wine(name="Wine B")
        placed: list[dict | None] = [None] * 10
        placed[4] = self._make_wine(name="Wine A")  # diff wine, same producer+varietal
        score = diversity_score(w, 5, placed)
        assert score == pytest.approx(72.0)  # producer penalty, not varietal

    def test_penalties_accumulate_across_slots(self):
        # Two same-varietal wines at distances 1 and 3
        # Penalty1 = 20 * (1 - 1/5) = 16, Penalty2 = 20 * (1 - 3/5) = 8
        # Total = 24, score = 76
        w = self._make_wine(name="Wine C", producer="Producer C")
        placed: list[dict | None] = [None] * 10
        placed[4] = self._make_wine(name="Wine A", producer="Producer A")  # 1 week ago
        placed[2] = self._make_wine(name="Wine B", producer="Producer B")  # 3 weeks ago
        assert diversity_score(w, 5, placed) == pytest.approx(76.0)

    def test_missing_producer_skips_producer_penalty(self):
        # Wine with no Producer: should not match on producer tier
        w = self._make_wine(name="Wine B", vintage="2021", producer="")
        placed: list[dict | None] = [None] * 10
        placed[4] = self._make_wine(
            name="Wine A", vintage="2020", producer="Producer A"
        )
        # No same-wine, no producer match (empty), check varietal match
        # Same varietal → penalty = 20 * (1 - 1/5) = 16, score = 84
        assert diversity_score(w, 5, placed) == pytest.approx(84.0)

    def test_missing_varietal_skips_varietal_penalty(self):
        # Wine with no Varietal or MasterVarietal: should not match on varietal
        w = {"Wine": "Wine B", "Vintage": "2020", "Producer": "Producer B"}
        placed: list[dict | None] = [None] * 10
        placed[4] = self._make_wine()
        # Different wine, different producer, no varietal to match → no penalty
        assert diversity_score(w, 5, placed) == pytest.approx(100.0)

    def test_master_varietal_fallback(self):
        # MasterVarietal takes priority over Varietal for matching
        w = {
            "Wine": "Wine B",
            "Vintage": "2021",
            "Producer": "Producer B",
            "MasterVarietal": "Cab Blend",
            "Varietal": "Cabernet Sauvignon",
        }
        placed: list[dict | None] = [None] * 10
        placed[4] = {
            "Wine": "Wine A",
            "Vintage": "2020",
            "Producer": "Producer A",
            "MasterVarietal": "Cab Blend",
            "Varietal": "Merlot",
        }
        # MasterVarietal matches ("Cab Blend"), Varietal differs
        # penalty = 20 * (1 - 1/5) = 16, score = 84
        assert diversity_score(w, 5, placed) == pytest.approx(84.0)

    def test_score_never_negative(self):
        # Many same-wine placements should floor at 0, not go negative
        w = self._make_wine()
        placed: list[dict | None] = [self._make_wine() for _ in range(5)]
        score = diversity_score(w, 5, placed)
        assert score >= 0.0

    def test_week_index_0_no_lookback(self):
        # At week 0, there's nothing to look back at
        w = self._make_wine()
        placed: list[dict | None] = [None] * 52
        assert diversity_score(w, 0, placed) == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# TestCompositeScore
# ---------------------------------------------------------------------------


class TestCompositeScore:
    """composite_score() combines all four components. Lower = schedule sooner."""

    def _past_peak_wine(self) -> dict:
        """A past-peak red wine with high CT — should score very low (urgent)."""
        return {
            "Wine": "Past Peak Red",
            "Vintage": "2015",
            "Type": "Red",
            "Varietal": "Cabernet Sauvignon",
            "BeginConsume": Y - 10,
            "EndConsume": Y - 1,
            "CT": 95,
            "Producer": "Producer A",
        }

    def _in_window_wine(self) -> dict:
        """A mid-window red with average CT — moderate urgency."""
        return {
            "Wine": "Mid Window Red",
            "Vintage": "2020",
            "Type": "Red",
            "Varietal": "Merlot",
            "BeginConsume": Y - 5,
            "EndConsume": Y + 5,
            "CT": 88,
            "Producer": "Producer B",
        }

    def _before_window_wine(self) -> dict:
        """A wine not yet ready — should score high (not urgent)."""
        return {
            "Wine": "Young Wine",
            "Vintage": "2024",
            "Type": "Red",
            "Varietal": "Nebbiolo",
            "BeginConsume": Y + 3,
            "EndConsume": Y + 15,
            "CT": 92,
            "Producer": "Producer C",
        }

    def test_past_peak_ranks_above_in_window(self):
        # Past-peak wine should have LOWER composite (more urgent) than in-window
        placed: list[dict | None] = []
        past = composite_score(self._past_peak_wine(), "fall", 0, placed)
        mid = composite_score(self._in_window_wine(), "fall", 0, placed)
        assert past < mid

    def test_in_window_ranks_above_before_window(self):
        placed: list[dict | None] = []
        mid = composite_score(self._in_window_wine(), "fall", 0, placed)
        young = composite_score(self._before_window_wine(), "fall", 0, placed)
        assert mid < young

    def test_deterministic(self):
        # Same inputs must produce identical output
        w = self._in_window_wine()
        placed: list[dict | None] = [None] * 10
        s1 = composite_score(w, "summer", 5, placed)
        s2 = composite_score(w, "summer", 5, placed)
        assert s1 == s2

    def test_seasonal_penalty_increases_score(self):
        # Bold red in summer should score higher (less urgent) than in winter
        w = self._past_peak_wine()
        placed: list[dict | None] = []
        summer_score = composite_score(w, "summer", 0, placed)
        winter_score = composite_score(w, "winter", 0, placed)
        assert summer_score > winter_score  # summer = worse fit for bold red

    def test_weights_sum_to_one(self):
        from scoring import W_COMMUNITY, W_CT, W_DIVERSITY, W_SEASON, W_WINDOW

        assert W_WINDOW + W_SEASON + W_DIVERSITY + W_CT + W_COMMUNITY == pytest.approx(
            1.0
        )

    def test_empty_placed_list(self):
        # Should work with empty placed list (diversity defaults to 100)
        w = self._in_window_wine()
        score = composite_score(w, "fall", 0, [])
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    def test_lower_is_more_urgent(self):
        # Verify the inversion: high-desirability wine gets LOW composite score
        # Past-peak + perfect season + high CT = very desirable = low score
        w = self._past_peak_wine()
        score = composite_score(w, "winter", 0, [])
        assert score < 50.0  # should be well below midpoint


# ---------------------------------------------------------------------------
# TestCommunityScore
# ---------------------------------------------------------------------------


class TestCommunityScore:
    """community_score() returns 0–100 based on RSS community note signals."""

    def _wine(self, iwine="123", ct=90):
        return {"iWine": iwine, "CT": ct}

    def _note(self, score=None, body="", tasting_date=None):
        return {
            "iWine": "123",
            "iNote": "1",
            "author": "tester",
            "score": score,
            "body": body,
            "tasting_date": tasting_date,
        }

    def test_no_community_data_returns_neutral(self):
        assert community_score(self._wine(), None) == pytest.approx(50.0)

    def test_empty_community_data_returns_neutral(self):
        assert community_score(self._wine(), {}) == pytest.approx(50.0)

    def test_no_notes_for_wine_returns_neutral(self):
        # Community data exists but not for this wine
        cn = {"999": [self._note(score=90)]}
        assert community_score(self._wine(), cn) == pytest.approx(50.0)

    def test_disappointing_scores_bump_urgency(self):
        # CT=90, recent scores averaging 85 → 5 point drop → bump
        cn = {"123": [self._note(score=85) for _ in range(5)]}
        score = community_score(self._wine(ct=90), cn)
        assert score > 50.0  # bumped up

    def test_better_than_expected_scores(self):
        # CT=85, recent scores averaging 92 → positive surprise
        cn = {"123": [self._note(score=92) for _ in range(5)]}
        score = community_score(self._wine(ct=85), cn)
        assert score > 50.0

    def test_drink_now_text_bumps_score(self):
        cn = {"123": [self._note(body="This wine is past prime, fading fast.")]}
        score = community_score(self._wine(), cn)
        assert score > 50.0

    def test_hold_text_reduces_score(self):
        cn = {"123": [self._note(body="Needs time. Too young and tight.")]}
        score = community_score(self._wine(), cn)
        assert score < 50.0

    def test_score_clamped_to_range(self):
        # Stack all positive signals
        cn = {
            "123": [
                self._note(
                    score=80, body="past prime, fading", tasting_date="12/1/2099"
                )
                for _ in range(10)
            ]
        }
        score = community_score(self._wine(ct=90), cn)
        assert 0.0 <= score <= 100.0

    def test_mixed_drift_signals_cancel_out(self):
        cn = {
            "123": [
                self._note(body="past prime"),
                self._note(body="needs time"),
            ]
        }
        # Equal drink-now and hold hits → no drift adjustment
        score = community_score(self._wine(), cn)
        # Should be close to neutral (only other sub-signals may apply)
        assert 40.0 <= score <= 60.0
