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

from scoring import seasonal_fit_score, window_position_score
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
