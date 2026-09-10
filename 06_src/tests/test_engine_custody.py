"""Tests for custody and threshold-date arithmetic, including property tests on the calendar.

SYNTHETIC TEST DATA. All dates are invented. No real accused person's data appears here.

The properties matter more than the examples: month-end clamping and leap years are where
hand-picked cases miss, and a one-day error in a qualifying date is a day of someone's liberty.
"""

from __future__ import annotations

from datetime import date, timedelta
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from bail_reckoner.engine.custody import (
    add_calendar_months,
    add_months_fraction,
    compute_custody,
)

_DATES = st.dates(min_value=date(1990, 1, 1), max_value=date(2100, 12, 31))


class TestAddCalendarMonths:
    def test_zero_months_is_identity(self) -> None:
        assert add_calendar_months(date(2024, 3, 15), 0) == date(2024, 3, 15)

    def test_simple_addition(self) -> None:
        assert add_calendar_months(date(2024, 1, 15), 18) == date(2025, 7, 15)

    @pytest.mark.parametrize(
        ("start", "months", "expected"),
        [
            (date(2024, 1, 31), 1, date(2024, 2, 29)),  # leap February clamps to 29
            (date(2023, 1, 31), 1, date(2023, 2, 28)),  # non-leap clamps to 28
            (date(2024, 3, 31), 1, date(2024, 4, 30)),  # 30-day month
            (date(2024, 8, 31), 6, date(2025, 2, 28)),
        ],
    )
    def test_month_end_clamps_down(self, start: date, months: int, expected: date) -> None:
        """31 February does not exist. Clamping down keeps the qualifying date no later than a
        reader expects, which is this module's safe direction."""
        assert add_calendar_months(start, months) == expected

    def test_leap_day_start(self) -> None:
        assert add_calendar_months(date(2024, 2, 29), 12) == date(2025, 2, 28)

    def test_negative_months_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            add_calendar_months(date(2024, 1, 1), -1)

    @given(start=_DATES, months=st.integers(min_value=0, max_value=600))
    def test_result_is_never_earlier_than_the_start(self, start: date, months: int) -> None:
        assert add_calendar_months(start, months) >= start

    @given(start=_DATES, a=st.integers(min_value=0, max_value=300), b=st.integers(0, 300))
    def test_monotonic_in_months(self, start: date, a: int, b: int) -> None:
        lo, hi = min(a, b), max(a, b)
        assert add_calendar_months(start, lo) <= add_calendar_months(start, hi)

    @given(start=_DATES, months=st.integers(min_value=0, max_value=240))
    def test_month_arithmetic_lands_in_the_expected_month(self, start: date, months: int) -> None:
        result = add_calendar_months(start, months)
        expected_total = (start.year * 12 + start.month - 1) + months
        assert result.year * 12 + result.month - 1 == expected_total


class TestAddMonthsFraction:
    def test_whole_fraction_matches_calendar_months(self) -> None:
        start = date(2024, 1, 15)
        assert add_months_fraction(start, Fraction(18)) == add_calendar_months(start, 18)

    def test_half_of_three_years_is_eighteen_months(self) -> None:
        assert add_months_fraction(date(2024, 1, 1), Fraction(36, 2)) == date(2025, 7, 1)

    def test_one_third_of_three_years_is_twelve_months(self) -> None:
        assert add_months_fraction(date(2024, 1, 1), Fraction(36, 3)) == date(2025, 1, 1)

    def test_fractional_remainder_uses_days_of_the_month_it_falls_in(self) -> None:
        """10/3 months from 1 Jan: 3 whole months to 1 April, then 1/3 of April's 30 days = 10."""
        assert add_months_fraction(date(2024, 1, 1), Fraction(10, 3)) == date(2024, 4, 11)

    def test_remainder_floors_rather_than_rounds(self) -> None:
        """Flooring yields the earlier qualifying date. Over-claiming is testable in court;
        under-claiming keeps someone in custody with nobody to appeal to (D-010)."""
        # 2/3 of a 31-day month is 20.67 days -> 20, not 21.
        assert add_months_fraction(date(2024, 1, 1), Fraction(2, 3)) == date(2024, 1, 21)

    @given(start=_DATES, num=st.integers(0, 600), den=st.integers(1, 12))
    def test_never_earlier_than_start(self, start: date, num: int, den: int) -> None:
        assert add_months_fraction(start, Fraction(num, den)) >= start

    @given(start=_DATES, a=st.integers(0, 200), b=st.integers(0, 200))
    def test_monotonic_in_the_fraction(self, start: date, a: int, b: int) -> None:
        lo, hi = Fraction(min(a, b), 3), Fraction(max(a, b), 3)
        assert add_months_fraction(start, lo) <= add_months_fraction(start, hi)

    @given(start=_DATES, months=st.integers(0, 240))
    def test_fractional_result_lies_between_its_whole_month_neighbours(
        self, start: date, months: int
    ) -> None:
        """A threshold of n + 1/2 months must fall between n and n+1 months."""
        half = add_months_fraction(start, Fraction(2 * months + 1, 2))
        assert add_calendar_months(start, months) <= half
        assert half <= add_calendar_months(start, months + 1)


class TestComputeCustody:
    def test_day_of_arrest_counts(self) -> None:
        """Inclusive counting (OLQ-9): arrested and evaluated the same day is one day undergone."""
        custody = compute_custody(custody_start=date(2024, 1, 1), as_on=date(2024, 1, 1))
        assert custody.elapsed_days == 1

    def test_elapsed_days_are_inclusive_of_both_ends(self) -> None:
        custody = compute_custody(custody_start=date(2024, 1, 1), as_on=date(2024, 1, 31))
        assert custody.elapsed_days == 31

    def test_breaks_and_exclusions_reduce_effective_days(self) -> None:
        custody = compute_custody(
            custody_start=date(2024, 1, 1), as_on=date(2024, 1, 31), break_days=5, excluded_days=3
        )
        assert custody.effective_days == 31 - 5 - 3

    def test_effective_days_contradiction_no_longer_floors_at_zero(self) -> None:
        """This test formerly asserted the floor (`effective_days == 0` for 100 break
        days inside a 10-day custody) — pinning the sixth failure-shape instance as
        correct behaviour. The assertion moves with the finding (2026-08-29): the same
        inputs are now a refused contradiction."""
        with pytest.raises(ValueError, match="contradict"):
            compute_custody(
                custody_start=date(2024, 1, 1), as_on=date(2024, 1, 10), break_days=100
            )

    def test_as_on_before_start_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="precedes"):
            compute_custody(custody_start=date(2024, 5, 1), as_on=date(2024, 1, 1))

    def test_negative_adjustments_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            compute_custody(
                custody_start=date(2024, 1, 1), as_on=date(2024, 2, 1), excluded_days=-1
            )

    def test_qualifying_date_shifts_by_breaks_and_exclusions(self) -> None:
        clean = compute_custody(custody_start=date(2024, 1, 1), as_on=date(2024, 6, 1))
        interrupted = compute_custody(
            custody_start=date(2024, 1, 1), as_on=date(2024, 6, 1), break_days=10, excluded_days=5
        )
        assert interrupted.qualifying_date(Fraction(18)) == clean.qualifying_date(
            Fraction(18)
        ) + timedelta(days=15)

    @given(
        start=_DATES,
        span=st.integers(0, 20000),
        breaks=st.integers(0, 500),
        excluded=st.integers(0, 500),
    )
    def test_effective_is_bounded_or_the_contradiction_is_refused(
        self, start: date, span: int, breaks: int, excluded: int
    ) -> None:
        """Rewritten for the sixth-instance fix (2026-08-29): the old property let
        `max(0, ...)` floor contradictory inputs into a plausible zero. The contract is
        now two-sided: consistent inputs stay bounded; contradictory ones (more
        break/excluded days than days elapsed) are REFUSED, never floored — zero
        effective custody UNDER-claims, the dangerous direction under D-010."""
        elapsed = span + 1  # inclusive of the day of arrest (OLQ-9)
        if breaks + excluded > elapsed:
            with pytest.raises(ValueError, match="contradict"):
                compute_custody(
                    custody_start=start,
                    as_on=start + timedelta(days=span),
                    break_days=breaks,
                    excluded_days=excluded,
                )
            return
        custody = compute_custody(
            custody_start=start,
            as_on=start + timedelta(days=span),
            break_days=breaks,
            excluded_days=excluded,
        )
        assert 0 <= custody.effective_days <= custody.elapsed_days

    def test_every_day_excluded_is_consistent_and_yields_zero(self) -> None:
        """Equality is not a contradiction: a custody entirely composed of excluded days
        is a legitimate (if extreme) zero."""
        custody = compute_custody(
            custody_start=date(2026, 1, 1),
            as_on=date(2026, 1, 10),
            excluded_days=10,
        )
        assert custody.effective_days == 0

    def test_contradictory_exclusions_are_refused_not_floored(self) -> None:
        with pytest.raises(ValueError, match="contradict"):
            compute_custody(
                custody_start=date(2026, 1, 1),
                as_on=date(2026, 1, 10),
                excluded_days=11,
            )
