"""Custody and threshold-date arithmetic (s.479(1) and its third proviso).

Pure stdlib. Every function here is a deterministic function of dates and integers.

Two conventions are chosen deliberately and both are recorded as open legal questions, because
each moves a real person's qualifying date and neither is settled by the bare act:

* **Day counting is inclusive** -- the day of arrest counts as a day undergone (OLQ-9).
* **Fractional months floor to whole days** when converting a threshold to a date (OLQ-10).

Both resolve in the same direction: they produce the *earlier* qualifying date. That follows
D-010's asymmetry. A threshold reached slightly too early yields a claim a court will test; a
threshold reached slightly too late keeps someone in custody with nobody to appeal to.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from fractions import Fraction

__all__ = ["add_calendar_months", "add_months_fraction", "CustodyComputation", "compute_custody"]


def add_calendar_months(start: date, months: int) -> date:
    """Add whole calendar months, clamping to the end of a short month.

    Calendar months rather than a fixed day count because sentences are expressed in years and
    months: "three years" from 15 January is 15 January three years later, not 1095 days later,
    and the difference is a day whenever a leap year intervenes.

    Clamping matters at month ends: 31 January plus one month is 28 (or 29) February, since
    31 February does not exist. Clamping *down* keeps the qualifying date no later than a
    reader would expect, consistent with this module's safe direction.
    """
    if months < 0:
        raise ValueError("months must not be negative")
    total = (start.year * 12 + (start.month - 1)) + months
    year, month = divmod(total, 12)
    month += 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def add_months_fraction(start: date, months: Fraction) -> date:
    """Add a possibly fractional number of calendar months.

    One-third of a term is frequently not a whole number of months -- ten months divided by three
    is 3⅓ -- so the fractional remainder is measured in days of the month it falls in, rather
    than by pretending a month is 30 days.

    The day offset **floors** (OLQ-10). Flooring yields the earlier qualifying date, which is the
    direction D-010 requires: over-claiming is testable in court, under-claiming is invisible.
    """
    if months < 0:
        raise ValueError("months must not be negative")
    whole = int(months)  # Fraction -> int truncates toward zero; months is non-negative here
    base = add_calendar_months(start, whole)
    remainder = months - whole
    if remainder == 0:
        return base
    next_month = add_calendar_months(base, 1)
    days_in_that_month = (next_month - base).days
    extra_days = int(Fraction(days_in_that_month) * remainder)  # floor
    return base + timedelta(days=extra_days)


@dataclass(frozen=True, slots=True)
class CustodyComputation:
    """Custody undergone, and the conventions used to reach it."""

    custody_start: date
    elapsed_days: int
    """Inclusive of the day of arrest (OLQ-9)."""

    break_days: int
    excluded_days: int
    effective_days: int
    """`elapsed - break - excluded`, floored at zero."""

    def qualifying_date(self, threshold_months: Fraction) -> date:
        """The date the threshold is reached, given this custody history.

        Provision: s.479(1) (one-half), first proviso (one-third), third proviso (the whole
        maximum, passed as a fraction of one).

        Breaks and excluded days push the date later by exactly their length, so a person who
        spent 40 days on interim bail reaches the threshold 40 days later than they otherwise
        would. This is why the comparison is date-based rather than a day count: adding calendar
        months to the start date and then shifting by the interruption preserves the calendar
        semantics of "one-half of three years".
        """
        base = add_months_fraction(self.custody_start, threshold_months)
        return base + timedelta(days=self.break_days + self.excluded_days)


def compute_custody(
    *,
    custody_start: date,
    as_on: date,
    break_days: int = 0,
    excluded_days: int = 0,
) -> CustodyComputation:
    """Compute custody undergone as at `as_on`.

    Provision: s.479(1) ("undergone detention for a period extending up to..."), read with the
    Explanation, which excludes detention attributable to delay caused by the accused.

    `excluded_days` is supplied by the caller from a court-determined figure and defaults to
    zero. The engine never derives it: deciding that a delay was caused by the accused is legal
    judgement, and D-009's refusal to compute discretionary matters applies here too (OLQ-7).
    """
    if as_on < custody_start:
        raise ValueError("as_on precedes custody_start")
    if break_days < 0 or excluded_days < 0:
        raise ValueError("break_days and excluded_days must not be negative")

    elapsed = (as_on - custody_start).days + 1  # inclusive of the day of arrest (OLQ-9)
    if break_days + excluded_days > elapsed:
        # SIXTH INSTANCE of the recorded failure shape, found by the 2026-08-29
        # adversarial audit: this used to be `max(0, ...)`, which turned
        # self-contradictory inputs (more break/excluded days than days detained) into a
        # plausible effective custody of zero — and zero custody UNDER-claims, the
        # dangerous direction under D-010's asymmetry. A contradiction is refused, never
        # floored (D-064). Equality is consistent (every day excluded) and stays allowed.
        raise ValueError(
            f"break_days ({break_days}) + excluded_days ({excluded_days}) exceed the "
            f"{elapsed} days elapsed between custody_start and as_on — the inputs "
            "contradict each other; refusing rather than flooring effective custody to 0"
        )
    effective = elapsed - break_days - excluded_days
    return CustodyComputation(
        custody_start=custody_start,
        elapsed_days=elapsed,
        break_days=break_days,
        excluded_days=excluded_days,
        effective_days=effective,
    )
