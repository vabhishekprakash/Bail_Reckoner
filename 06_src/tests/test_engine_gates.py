"""Tests for the six-gate engine: one per gate, one per proviso, adversarial on gate 2.

SYNTHETIC TEST DATA. Every person, case reference and date below is invented for testing. No
real accused person's data appears here, ever (CLAUDE.md §6).
"""

from __future__ import annotations

from datetime import date
from fractions import Fraction

import pytest

from bail_reckoner.engine.gates import evaluate
from bail_reckoner.engine.types import (
    CaseInput,
    ChargedOffence,
    CustodyBreak,
    Decision,
    Flag,
    PendingCase,
    PriorConvictionStatus,
    Scope479_2,
    Severity,
    Verdict,
    severity_of,
)
from bail_reckoner.statutes.decision_table import (
    DEFAULT_TABLE_PATH,
    DecisionTable,
    load_decision_table,
)
from bail_reckoner.statutes.models import MaximumPunishment, PunishmentKind

needs_table = pytest.mark.skipif(
    not DEFAULT_TABLE_PATH.exists(), reason="decision table not present in this checkout"
)

pytestmark = needs_table


@pytest.fixture(scope="module")
def table() -> DecisionTable:
    return load_decision_table()


def term(months: int) -> MaximumPunishment:
    return MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=months)


DEATH_OR_LIFE = MaximumPunishment(
    kinds=frozenset({PunishmentKind.DEATH, PunishmentKind.LIFE}), fine_also=True
)

# The default must be a real value rather than None-means-default: an earlier version of this
# helper substituted a 36-month maximum whenever `maximum=None` was passed, which silently turned
# the "no verified penalty row" test into a "3-year offence" test. The engine was fine; the test
# was not exercising the path it claimed to.
_DEFAULT_MAXIMUM = term(36)


def offence(
    label: str = "Theft (synthetic)",
    section: str = "303(2)",
    maximum: MaximumPunishment | None = _DEFAULT_MAXIMUM,
    **kw: object,
) -> ChargedOffence:
    """`maximum=None` means genuinely no verified penalty row, not 'use the default'."""
    return ChargedOffence(
        offence_id=f"BNS_2023-{section}",
        label=label,
        section=section,
        maximum=maximum,
        **kw,  # type: ignore[arg-type]
    )


def case_input(
    *,
    offences: tuple[ChargedOffence, ...] | None = None,
    cases: tuple[PendingCase, ...] | None = None,
    arrest: date = date(2024, 1, 1),
    as_on: date = date(2026, 1, 1),
    prior: PriorConvictionStatus = PriorConvictionStatus.KNOWN_PRIOR,
    **kw: object,
) -> CaseInput:
    if cases is None:
        cases = (PendingCase(case_ref="FIR-1/2024", offences=offences or (offence(),)),)
    return CaseInput(
        date_of_arrest=arrest,
        evaluated_on=as_on,
        cases=cases,
        prior_conviction_status=prior,
        **kw,  # type: ignore[arg-type]
    )


class TestGate0AbsoluteCap:
    """s.479(1) third proviso. D-034: computed first, never masked."""

    def test_fires_when_custody_reaches_the_maximum(self, table: DecisionTable) -> None:
        # 36-month maximum, arrested 2020 — long past the cap.
        decision = evaluate(case_input(arrest=date(2020, 1, 1), as_on=date(2026, 1, 1)), table)
        assert Flag.DETAINED_BEYOND_MAXIMUM in decision.flags
        assert severity_of(Flag.DETAINED_BEYOND_MAXIMUM) is Severity.URGENT

    def test_does_not_fire_before_the_maximum(self, table: DecisionTable) -> None:
        decision = evaluate(case_input(arrest=date(2025, 6, 1), as_on=date(2026, 1, 1)), table)
        assert Flag.DETAINED_BEYOND_MAXIMUM not in decision.flags

    def test_is_not_masked_by_a_gate_1_bar(self, table: DecisionTable) -> None:
        """The whole point of D-034. A person held past a co-charged offence's maximum must be
        surfaced even though a death/life offence bars s.479(1)."""
        decision = evaluate(
            case_input(
                offences=(
                    offence(maximum=term(36)),
                    offence(label="Murder", section="103(1)", maximum=DEATH_OR_LIFE),
                ),
                arrest=date(2018, 1, 1),
                as_on=date(2026, 1, 1),
            ),
            table,
        )
        assert decision.gate_fired == 1
        assert Flag.DETAINED_BEYOND_MAXIMUM in decision.flags

    def test_is_not_masked_by_a_gate_2_bar(self, table: DecisionTable) -> None:
        """s.479(2) is expressly 'subject to the third proviso thereof'."""
        decision = evaluate(
            case_input(
                cases=(
                    PendingCase("FIR-1/2024", (offence(),)),
                    PendingCase("FIR-2/2024", (offence(section="304(2)"),)),
                ),
                arrest=date(2018, 1, 1),
            ),
            table,
        )
        assert decision.gate_fired == 2
        assert Flag.DETAINED_BEYOND_MAXIMUM in decision.flags

    def test_gate_0_is_always_evaluated_and_recorded(self, table: DecisionTable) -> None:
        decision = evaluate(case_input(), table)
        assert decision.gate_outcomes[0].gate_id == 0

    def _band_case(self, as_on: date) -> CaseInput:
        """Two pending cases — a 6-month offence and a 36-month offence — so gate 2 bars and
        the OLQ-11 band is 2025-07-01 (lowest cap) to 2028-01-01 (governing cap)."""
        return case_input(
            cases=(
                PendingCase("FIR-1/2025", (offence(section="905", maximum=term(6)),)),
                PendingCase("FIR-2/2025", (offence(section="901", maximum=term(36)),)),
            ),
            arrest=date(2025, 1, 1),
            as_on=as_on,
        )

    def test_custody_inside_the_band_raises_the_contested_cap_flag(
        self, table: DecisionTable
    ) -> None:
        """OLQ-11 / D-066: past the lowest maximum, short of the governing one — flag, don't
        pick. The gate-2 bar must not suppress it: the cap is the only surviving route there."""
        decision = evaluate(self._band_case(date(2026, 1, 1)), table)
        assert decision.gate_fired == 2
        assert Flag.CONTESTED_CAP_BASIS in decision.flags
        assert Flag.DETAINED_BEYOND_MAXIMUM not in decision.flags

    def test_at_the_lower_band_edge_the_flag_fires(self, table: DecisionTable) -> None:
        decision = evaluate(self._band_case(date(2025, 7, 1)), table)
        assert Flag.CONTESTED_CAP_BASIS in decision.flags

    def test_below_the_band_no_cap_flag_of_either_kind(self, table: DecisionTable) -> None:
        decision = evaluate(self._band_case(date(2025, 6, 30)), table)
        assert Flag.CONTESTED_CAP_BASIS not in decision.flags
        assert Flag.DETAINED_BEYOND_MAXIMUM not in decision.flags

    def test_at_the_governing_cap_the_definite_flag_replaces_the_contested_one(
        self, table: DecisionTable
    ) -> None:
        decision = evaluate(self._band_case(date(2028, 1, 1)), table)
        assert Flag.DETAINED_BEYOND_MAXIMUM in decision.flags
        assert Flag.CONTESTED_CAP_BASIS not in decision.flags

    def test_a_single_offence_has_no_band(self, table: DecisionTable) -> None:
        """One offence, one maximum: nothing is contested about the cap's basis."""
        decision = evaluate(
            case_input(offences=(offence(maximum=term(36)),), arrest=date(2023, 1, 1)), table
        )
        assert Flag.CONTESTED_CAP_BASIS not in decision.flags


class TestGate1DeathOrLife:
    """s.479(1) main clause: death or life as *one of* the punishments."""

    def test_bars_when_death_or_life_is_prescribed(self, table: DecisionTable) -> None:
        decision = evaluate(case_input(offences=(offence(maximum=DEATH_OR_LIFE),)), table)
        assert decision.verdict is Verdict.NO_ENTITLEMENT_IDENTIFIED
        assert decision.gate_fired == 1

    def test_a_long_term_offence_is_not_barred(self, table: DecisionTable) -> None:
        """>7 years is Antil Category B but remains s.479(1)-eligible absent death/life."""
        decision = evaluate(
            case_input(offences=(offence(maximum=term(120)),), arrest=date(2018, 1, 1)), table
        )
        assert decision.gate_fired != 1


class TestGate2Multiplicity:
    """s.479(2). Adversarial coverage required by CLAUDE.md §6."""

    def test_multiple_cases_bar_under_narrow_default(self, table: DecisionTable) -> None:
        decision = evaluate(
            case_input(
                cases=(
                    PendingCase("FIR-1/2024", (offence(),)),
                    PendingCase("FIR-2/2024", (offence(section="304(2)"),)),
                )
            ),
            table,
        )
        assert decision.gate_fired == 2

    def test_single_case_multiple_offences_is_contested_not_barred(
        self, table: DecisionTable
    ) -> None:
        """D-025/OLQ-5: unsettled, so neither cleared nor barred silently."""
        decision = evaluate(
            case_input(offences=(offence(), offence(section="304(2)")), arrest=date(2018, 1, 1)),
            table,
        )
        assert Flag.CONTESTED_479_2_SCOPE in decision.flags
        assert decision.verdict is Verdict.NO_ENTITLEMENT_IDENTIFIED

    def test_broad_scope_bars_on_offence_count(self, table: DecisionTable) -> None:
        decision = evaluate(
            case_input(
                offences=(offence(), offence(section="304(2)")), scope_479_2=Scope479_2.BROAD
            ),
            table,
        )
        assert decision.gate_fired == 2
        assert Flag.CONTESTED_479_2_SCOPE not in decision.flags

    def test_a_non_pending_case_does_not_count(self, table: DecisionTable) -> None:
        """Adversarial: a disposed case must not trigger the bar."""
        decision = evaluate(
            case_input(
                cases=(
                    PendingCase("FIR-1/2024", (offence(),)),
                    PendingCase("FIR-2/2023", (offence(),), is_pending=False),
                ),
                arrest=date(2018, 1, 1),
            ),
            table,
        )
        assert decision.gate_fired != 2

    def test_single_offence_single_case_passes_cleanly(self, table: DecisionTable) -> None:
        decision = evaluate(case_input(arrest=date(2018, 1, 1)), table)
        assert decision.gate_fired != 2
        assert Flag.CONTESTED_479_2_SCOPE not in decision.flags


class TestGate3SpecialStatute:
    """Antil Category C. D-033: a FLAG, never terminal."""

    def test_flags_and_still_computes_the_arithmetic(self, table: DecisionTable) -> None:
        decision = evaluate(
            case_input(
                offences=(
                    offence(
                        label="PMLA offence (synthetic)",
                        special_statute="PMLA",
                        special_statute_provision="s.45",
                        special_statute_in_gate3_set=True,
                        special_statute_bar_in_scope=True,
                    ),
                ),
                arrest=date(2018, 1, 1),
            ),
            table,
        )
        assert Flag.SPECIAL_STATUTE_TEST_REQUIRED in decision.flags
        # Never terminal: the working is present regardless.
        assert decision.offence_computations[0].threshold_months == Fraction(18)
        assert decision.offence_computations[0].crossed is True

    def test_pocso_style_null_provision_is_named_not_invented(self, table: DecisionTable) -> None:
        """D-042/OLQ-4."""
        decision = evaluate(
            case_input(
                offences=(
                    offence(
                        label="POCSO offence (synthetic)",
                        special_statute="POCSO",
                        special_statute_provision=None,
                        special_statute_in_gate3_set=True,
                        special_statute_bar_in_scope=True,
                    ),
                )
            ),
            table,
        )
        gate3 = next(o for o in decision.gate_outcomes if o.gate_id == 3)
        assert "unresolved" in gate3.detail

    def test_statute_outside_the_set_is_named_not_ignored(self, table: DecisionTable) -> None:
        """D-054 refinement: silence would imply the statute is irrelevant."""
        decision = evaluate(
            case_input(
                offences=(
                    offence(special_statute="SC/ST Act", special_statute_in_gate3_set=False),
                ),
                arrest=date(2018, 1, 1),
            ),
            table,
        )
        assert Flag.SPECIAL_STATUTE_UNASSESSED in decision.flags
        assert Flag.SPECIAL_STATUTE_TEST_REQUIRED not in decision.flags


class TestGate4FirstProviso:
    """s.479(1) first proviso: one-third on bond. A selector, never a bar."""

    def test_first_time_offender_gets_one_third(self, table: DecisionTable) -> None:
        decision = evaluate(case_input(prior=PriorConvictionStatus.NONE_DECLARED), table)
        assert decision.fraction_applied == Fraction(1, 3)

    def test_prior_conviction_gets_one_half(self, table: DecisionTable) -> None:
        decision = evaluate(case_input(prior=PriorConvictionStatus.KNOWN_PRIOR), table)
        assert decision.fraction_applied == Fraction(1, 2)

    def test_unknown_status_takes_one_half_and_flags(self, table: DecisionTable) -> None:
        """D-051: unknown must not silently claim the one-third route, nor silently lose it."""
        decision = evaluate(case_input(prior=PriorConvictionStatus.UNKNOWN), table)
        assert decision.fraction_applied == Fraction(1, 2)
        assert Flag.PRIOR_STATUS_UNVERIFIED in decision.flags

    def test_gate_4_never_bars(self, table: DecisionTable) -> None:
        decision = evaluate(
            case_input(prior=PriorConvictionStatus.KNOWN_PRIOR, arrest=date(2018, 1, 1)), table
        )
        assert decision.gate_fired != 4


class TestGate5Threshold:
    def test_crossed_threshold_establishes_entitlement(self, table: DecisionTable) -> None:
        decision = evaluate(case_input(arrest=date(2024, 1, 1), as_on=date(2025, 8, 1)), table)
        assert decision.verdict is Verdict.ENTITLEMENT_ESTABLISHED
        assert decision.gate_fired is None

    def test_not_yet_entitled_computes_the_qualifying_date(self, table: DecisionTable) -> None:
        decision = evaluate(case_input(arrest=date(2025, 12, 1), as_on=date(2026, 1, 1)), table)
        assert decision.verdict is Verdict.NO_ENTITLEMENT_IDENTIFIED
        assert Flag.NOT_YET_ENTITLED in decision.flags
        assert decision.qualifying_date == date(2027, 6, 1)  # 18 months from 2025-12-01

    def test_custody_breaks_push_the_qualifying_date_later(self, table: DecisionTable) -> None:
        base = evaluate(case_input(arrest=date(2025, 1, 1), as_on=date(2026, 1, 1)), table)
        with_break = evaluate(
            case_input(
                arrest=date(2025, 1, 1),
                as_on=date(2026, 1, 1),
                custody_breaks=(CustodyBreak(date(2025, 3, 1), date(2025, 3, 10)),),
            ),
            table,
        )
        assert with_break.qualifying_date is not None and base.qualifying_date is not None
        assert with_break.qualifying_date > base.qualifying_date
        assert with_break.effective_custody_days == base.effective_custody_days - 10


class TestNoEntitlementWithoutAVerifiedMaximum:
    def test_missing_penalty_row_never_guesses(self, table: DecisionTable) -> None:
        decision = evaluate(case_input(offences=(offence(maximum=None),)), table)
        assert Flag.OFFENCE_NOT_IN_DATABASE in decision.flags
        assert decision.verdict is Verdict.NO_ENTITLEMENT_IDENTIFIED
        assert decision.offence_computations[0].threshold_months is None

    def test_fine_only_offence_yields_no_threshold(self, table: DecisionTable) -> None:
        fine_only = MaximumPunishment(kinds=frozenset({PunishmentKind.FINE_ONLY}))
        decision = evaluate(case_input(offences=(offence(maximum=fine_only),)), table)
        assert Flag.MAXIMUM_NOT_COMPUTABLE in decision.flags
        assert decision.verdict is Verdict.NO_ENTITLEMENT_IDENTIFIED


class TestOutputContract:
    def test_only_two_verdicts_exist(self) -> None:
        """D-010, enforced structurally: adding a third requires editing an enum."""
        assert len(Verdict) == 2
        assert not any("INELIGIBLE" in v.name for v in Verdict)

    def test_every_flag_has_a_severity(self) -> None:
        for flag in Flag:
            assert severity_of(flag) in Severity

    def test_required_stamps_are_present(self, table: DecisionTable) -> None:
        decision = evaluate(case_input(), table)
        assert decision.statute_version.startswith("BNSS 2023@")
        assert len(decision.inputs_hash) == 64
        assert decision.reviewed_by == ""
        assert decision.law_in_force_on == date(2026, 1, 1)

    def test_reviewed_by_is_never_populated_by_the_engine(self, table: DecisionTable) -> None:
        assert evaluate(case_input(), table).reviewed_by == ""

    def test_all_six_gates_are_recorded_even_after_a_bar(self, table: DecisionTable) -> None:
        """A report must distinguish a condition checked and passed from one never reached."""
        decision = evaluate(case_input(offences=(offence(maximum=DEATH_OR_LIFE),)), table)
        assert [o.gate_id for o in decision.gate_outcomes] == [0, 1, 2, 3, 4, 5]

    def test_the_working_is_shown_even_when_a_bar_fires(self, table: DecisionTable) -> None:
        """D-035: a bar controls the verdict, never whether the reader sees the sums."""
        decision = evaluate(
            case_input(
                cases=(
                    PendingCase("FIR-1/2024", (offence(),)),
                    PendingCase("FIR-2/2024", (offence(section="304(2)"),)),
                ),
                arrest=date(2018, 1, 1),
            ),
            table,
        )
        assert decision.gate_fired == 2
        assert all(c.threshold_months == Fraction(18) for c in decision.offence_computations)
        assert all(c.crossed for c in decision.offence_computations)

    def test_identical_inputs_hash_identically(self, table: DecisionTable) -> None:
        """Reproducibility: a repr-based hash would vary with frozenset ordering."""
        assert case_input().inputs_hash() == case_input().inputs_hash()

    def test_different_inputs_hash_differently(self, table: DecisionTable) -> None:
        assert case_input().inputs_hash() != case_input(arrest=date(2023, 5, 5)).inputs_hash()

    def test_engine_is_deterministic(self, table: DecisionTable) -> None:
        first = evaluate(case_input(), table)
        second = evaluate(case_input(), table)
        assert first == second


class TestExclusionCaveat:
    def test_a_crossing_at_zero_exclusions_is_caveated(self, table: DecisionTable) -> None:
        """OLQ-7: the Explanation could push the date later, so a crossing computed with zero
        exclusions rests on an unverified assumption."""
        decision = evaluate(case_input(arrest=date(2024, 1, 1), as_on=date(2025, 8, 1)), table)
        assert decision.verdict is Verdict.ENTITLEMENT_ESTABLISHED
        assert Flag.EXCLUSION_STATUS_UNVERIFIED in decision.flags

    def test_excluded_days_delay_the_qualifying_date(self, table: DecisionTable) -> None:
        base = evaluate(case_input(arrest=date(2025, 1, 1)), table)
        delayed = evaluate(case_input(arrest=date(2025, 1, 1), excluded_days=30), table)
        assert delayed.qualifying_date is not None and base.qualifying_date is not None
        assert (delayed.qualifying_date - base.qualifying_date).days == 30


def test_arrest_remand_divergence_is_flagged(table: DecisionTable) -> None:
    """D-028/OLQ-6: which date governs is unsettled, so a divergence is surfaced."""
    decision = evaluate(
        case_input(arrest=date(2024, 1, 1), date_of_first_remand=date(2024, 1, 3)), table
    )
    assert Flag.ARREST_REMAND_DIVERGENCE in decision.flags


class TestCaseListVerification:
    """Item upstream of the worst error available: s.479(2) turns on facts outside the case in
    hand, and the case list is an input, not a fact."""

    def test_unverified_case_list_is_flagged_by_default(self, table: DecisionTable) -> None:
        decision = evaluate(case_input(), table)
        assert Flag.CASE_LIST_UNVERIFIED in decision.flags

    def test_a_verified_case_list_clears_the_flag(self, table: DecisionTable) -> None:
        decision = evaluate(case_input(case_list_verified=True), table)
        assert Flag.CASE_LIST_UNVERIFIED not in decision.flags

    def test_verification_status_is_part_of_the_inputs_hash(self, table: DecisionTable) -> None:
        """Two computations differing only in whether the case list was verified are different
        computations, and their stored reports must not collide."""
        assert case_input().inputs_hash() != case_input(case_list_verified=True).inputs_hash()


class TestD072PendingOffencesOnly:
    """D-072: gates 0, 1 and 5 compute over pending offences only; gate 4 is untouched.

    Under-claiming is the dangerous direction (D-010): before D-072 a concluded case could
    suppress the gate-0 cap, fire gate 1, and extend the gate-5 threshold — each a way to
    keep a person in custody on the strength of a case that has ended.
    """

    @staticmethod
    def _case(
        pending_months: int,
        concluded: MaximumPunishment,
        prior: PriorConvictionStatus = PriorConvictionStatus.NONE_DECLARED,
        arrest: date = date(2022, 6, 1),
        as_on: date = date(2026, 8, 1),
    ) -> CaseInput:
        return CaseInput(
            date_of_arrest=arrest,
            evaluated_on=as_on,
            cases=(
                PendingCase(
                    case_ref="PENDING",
                    offences=(
                        ChargedOffence(
                            offence_id="SYN-910",
                            label="Synthetic pending offence",
                            section="910",
                            maximum=MaximumPunishment(
                                kinds=frozenset({PunishmentKind.TERM}),
                                term_months=pending_months,
                            ),
                        ),
                    ),
                ),
                PendingCase(
                    case_ref="CONCLUDED",
                    offences=(
                        ChargedOffence(
                            offence_id="SYN-911",
                            label="Synthetic concluded offence",
                            section="911",
                            maximum=concluded,
                        ),
                    ),
                    is_pending=False,
                ),
            ),
            prior_conviction_status=prior,
        )

    def test_concluded_high_maximum_does_not_extend_the_gate_5_threshold(
        self, table: DecisionTable
    ) -> None:
        """~50 months custody, pending 7-year offence: one-third crossed. A concluded 20-year
        offence must not push the qualifying date out."""
        big = MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=240)
        decision = evaluate(self._case(84, big), table)
        assert decision.verdict is Verdict.ENTITLEMENT_ESTABLISHED
        assert decision.qualifying_date == date(2024, 10, 1)  # one-third of 84 months

    def test_concluded_offence_does_not_raise_the_gate_0_cap(self, table: DecisionTable) -> None:
        """The sharpest case: custody past the PENDING offence's maximum must flag
        DETAINED_BEYOND_MAXIMUM even when a concluded case carries a larger maximum. The
        third proviso's absolute protection must not be suppressed by a case that has ended
        (OLQ-11's inversion, second mechanism)."""
        big = MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=240)
        decision = evaluate(
            self._case(24, big, arrest=date(2022, 6, 1), as_on=date(2026, 8, 1)), table
        )
        assert Flag.DETAINED_BEYOND_MAXIMUM in decision.flags
        assert Flag.CONTESTED_CAP_BASIS not in decision.flags  # no band: one pending maximum

    def test_concluded_death_or_life_offence_does_not_fire_gate_1(
        self, table: DecisionTable
    ) -> None:
        life = MaximumPunishment(kinds=frozenset({PunishmentKind.LIFE}))
        decision = evaluate(self._case(84, life), table)
        gate1 = next(o for o in decision.gate_outcomes if o.gate_id == 1)
        assert not gate1.fired
        assert decision.verdict is Verdict.ENTITLEMENT_ESTABLISHED

    def test_concluded_conviction_still_defeats_first_time_status_via_the_input(
        self, table: DecisionTable
    ) -> None:
        """Gate 4 reads prior_conviction_status, never the case list: a concluded case that
        ended in conviction defeats first-time status because the caller records KNOWN_PRIOR,
        and the D-072 narrowing cannot touch that."""
        big = MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=240)
        decision = evaluate(self._case(84, big, prior=PriorConvictionStatus.KNOWN_PRIOR), table)
        assert decision.fraction_applied == Fraction(1, 2)

    def test_concluded_offence_is_listed_for_the_record_but_inert(
        self, table: DecisionTable
    ) -> None:
        """D-035: the working is always shown. The concluded offence appears in the
        computations, explicitly marked as taking no part."""
        big = MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=240)
        decision = evaluate(self._case(84, big), table)
        inert = [c for c in decision.offence_computations if c.offence.offence_id == "SYN-911"]
        assert len(inert) == 1
        assert inert[0].threshold_months is None
        assert "takes no part" in inert[0].note


class TestConcludedCasesAtGates2And3:
    """Round-5 audit (Abhishek): gate 2 already narrowed by construction (D-052 built it on
    `pending_cases`); gate 3's narrowing arrived as an unflagged side effect of D-072 and is
    now deliberate. Both pinned here so neither can silently widen."""

    @staticmethod
    def _pending(months: int = 84) -> PendingCase:
        return PendingCase(
            case_ref="PENDING",
            offences=(
                ChargedOffence(
                    offence_id="SYN-910",
                    label="Synthetic pending offence",
                    section="910",
                    maximum=MaximumPunishment(
                        kinds=frozenset({PunishmentKind.TERM}), term_months=months
                    ),
                ),
            ),
        )

    def test_a_concluded_second_case_does_not_fire_the_gate_2_bar(
        self, table: DecisionTable
    ) -> None:
        """s.479(2) says "are pending" on its face; a finished case barring a person would be
        an under-claim in the D-010 direction."""
        concluded = PendingCase(
            case_ref="CONCLUDED",
            offences=(
                ChargedOffence(
                    offence_id="SYN-911",
                    label="Synthetic concluded offence",
                    section="911",
                    maximum=MaximumPunishment(
                        kinds=frozenset({PunishmentKind.TERM}), term_months=120
                    ),
                ),
            ),
            is_pending=False,
        )
        case = CaseInput(
            date_of_arrest=date(2022, 6, 1),
            evaluated_on=date(2026, 8, 1),
            cases=(self._pending(), concluded),
            prior_conviction_status=PriorConvictionStatus.KNOWN_PRIOR,
        )
        decision = evaluate(case, table)
        gate2 = next(o for o in decision.gate_outcomes if o.gate_id == 2)
        assert not gate2.fired
        assert Flag.CONTESTED_479_2_SCOPE not in decision.flags
        assert decision.verdict is Verdict.ENTITLEMENT_ESTABLISHED

    def test_a_concluded_multi_offence_case_does_not_raise_the_contested_flag(
        self, table: DecisionTable
    ) -> None:
        concluded_multi = PendingCase(
            case_ref="CONCLUDED-MULTI",
            offences=tuple(
                ChargedOffence(
                    offence_id=f"SYN-92{i}",
                    label=f"Synthetic concluded offence {i}",
                    section=f"92{i}",
                    maximum=MaximumPunishment(
                        kinds=frozenset({PunishmentKind.TERM}), term_months=36
                    ),
                )
                for i in range(2)
            ),
            is_pending=False,
        )
        case = CaseInput(
            date_of_arrest=date(2022, 6, 1),
            evaluated_on=date(2026, 8, 1),
            cases=(self._pending(), concluded_multi),
            prior_conviction_status=PriorConvictionStatus.KNOWN_PRIOR,
        )
        decision = evaluate(case, table)
        assert Flag.CONTESTED_479_2_SCOPE not in decision.flags

    def test_a_concluded_special_statute_case_raises_no_gate_3_flag(
        self, table: DecisionTable
    ) -> None:
        """The bar attaches to the offence for which release is sought; a flag from a
        concluded case is a false alarm by construction (D-069's signal discipline)."""
        concluded_ndps = PendingCase(
            case_ref="CONCLUDED-NDPS",
            offences=(
                ChargedOffence(
                    offence_id="SYN-930",
                    label="Synthetic concluded special-statute offence",
                    section="930",
                    maximum=MaximumPunishment(
                        kinds=frozenset({PunishmentKind.TERM}), term_months=120
                    ),
                    special_statute="NDPS",
                    special_statute_provision="s.37",
                    special_statute_in_gate3_set=True,
                ),
            ),
            is_pending=False,
        )
        case = CaseInput(
            date_of_arrest=date(2022, 6, 1),
            evaluated_on=date(2026, 8, 1),
            cases=(self._pending(), concluded_ndps),
            prior_conviction_status=PriorConvictionStatus.KNOWN_PRIOR,
        )
        decision = evaluate(case, table)
        assert Flag.SPECIAL_STATUTE_TEST_REQUIRED not in decision.flags
        assert Flag.SPECIAL_STATUTE_UNASSESSED not in decision.flags
        assert Flag.CONTESTED_SPECIAL_STATUTE_SCOPE not in decision.flags

    def test_a_pending_special_statute_offence_still_flags(self, table: DecisionTable) -> None:
        pending_ndps = PendingCase(
            case_ref="PENDING-NDPS",
            offences=(
                ChargedOffence(
                    offence_id="SYN-931",
                    label="Synthetic pending special-statute offence",
                    section="931",
                    maximum=MaximumPunishment(
                        kinds=frozenset({PunishmentKind.TERM}), term_months=120
                    ),
                    special_statute="NDPS",
                    special_statute_provision="s.37",
                    special_statute_in_gate3_set=True,
                    special_statute_bar_in_scope=True,
                ),
            ),
        )
        case = CaseInput(
            date_of_arrest=date(2022, 6, 1),
            evaluated_on=date(2026, 8, 1),
            cases=(pending_ndps,),
            prior_conviction_status=PriorConvictionStatus.KNOWN_PRIOR,
        )
        decision = evaluate(case, table)
        assert Flag.SPECIAL_STATUTE_TEST_REQUIRED in decision.flags


class TestGateOffenceCollections:
    """Standing matrix (Abhishek, 2026-08-19): WHICH offence collection each gate reads.

    Pending-only for gates 0, 1, 2, 3 and 5; the standalone prior-conviction input for
    gate 4. D-072 changed a gate outside its stated scope by switching a shared variable;
    this matrix would have caught that at the moment it happened rather than in a later
    audit. Each row plants a condition in a CONCLUDED case that would trigger the gate if
    the gate read all offences, and asserts silence; the paired pending-control tests
    elsewhere in this module assert the same condition fires when pending.
    """

    _ARREST = date(2020, 6, 1)
    _AS_ON = date(2026, 8, 1)  # ~74 months custody

    @staticmethod
    def _pending_modest() -> PendingCase:
        # 20-year pending maximum: custody (~74 months) is far below the 240-month cap and
        # far below the 120-month one-half threshold, so nothing fires from the pending side.
        return PendingCase(
            case_ref="PENDING",
            offences=(
                ChargedOffence(
                    offence_id="SYN-910",
                    label="Synthetic pending offence",
                    section="910",
                    maximum=MaximumPunishment(
                        kinds=frozenset({PunishmentKind.TERM}), term_months=240
                    ),
                ),
            ),
        )

    def _decide(self, table: DecisionTable, concluded: PendingCase) -> Decision:
        return evaluate(
            CaseInput(
                date_of_arrest=self._ARREST,
                evaluated_on=self._AS_ON,
                cases=(self._pending_modest(), concluded),
                prior_conviction_status=PriorConvictionStatus.KNOWN_PRIOR,
            ),
            table,
        )

    @staticmethod
    def _concluded(offence: ChargedOffence) -> PendingCase:
        return PendingCase(case_ref="CONCLUDED", offences=(offence,), is_pending=False)

    def test_gate_0_reads_pending_offences_only(self, table: DecisionTable) -> None:
        """A concluded 3-year offence (36 < 74 months custody) would cross the cap."""
        decision = self._decide(
            table,
            self._concluded(
                ChargedOffence(
                    offence_id="SYN-940",
                    label="Synthetic concluded offence",
                    section="940",
                    maximum=MaximumPunishment(
                        kinds=frozenset({PunishmentKind.TERM}), term_months=36
                    ),
                )
            ),
        )
        assert Flag.DETAINED_BEYOND_MAXIMUM not in decision.flags
        assert Flag.CONTESTED_CAP_BASIS not in decision.flags

    def test_gate_1_reads_pending_offences_only(self, table: DecisionTable) -> None:
        decision = self._decide(
            table,
            self._concluded(
                ChargedOffence(
                    offence_id="SYN-941",
                    label="Synthetic concluded offence",
                    section="941",
                    maximum=MaximumPunishment(kinds=frozenset({PunishmentKind.DEATH})),
                )
            ),
        )
        gate1 = next(o for o in decision.gate_outcomes if o.gate_id == 1)
        assert not gate1.fired

    def test_gate_2_reads_pending_cases_only(self, table: DecisionTable) -> None:
        decision = self._decide(
            table,
            self._concluded(
                ChargedOffence(
                    offence_id="SYN-942",
                    label="Synthetic concluded offence",
                    section="942",
                    maximum=MaximumPunishment(
                        kinds=frozenset({PunishmentKind.TERM}), term_months=36
                    ),
                )
            ),
        )
        gate2 = next(o for o in decision.gate_outcomes if o.gate_id == 2)
        assert not gate2.fired
        assert Flag.CONTESTED_479_2_SCOPE not in decision.flags

    def test_gate_3_reads_pending_offences_only(self, table: DecisionTable) -> None:
        decision = self._decide(
            table,
            self._concluded(
                ChargedOffence(
                    offence_id="SYN-943",
                    label="Synthetic concluded offence",
                    section="943",
                    maximum=MaximumPunishment(
                        kinds=frozenset({PunishmentKind.TERM}), term_months=120
                    ),
                    special_statute="NDPS",
                    special_statute_provision="s.37",
                    special_statute_in_gate3_set=True,
                )
            ),
        )
        assert Flag.SPECIAL_STATUTE_TEST_REQUIRED not in decision.flags
        assert Flag.SPECIAL_STATUTE_UNASSESSED not in decision.flags
        assert Flag.CONTESTED_SPECIAL_STATUTE_SCOPE not in decision.flags

    def test_gate_5_reads_pending_offences_only(self, table: DecisionTable) -> None:
        """A concluded 40-year maximum must not become the governing maximum: the pending
        20-year offence's one-half threshold (120 months) governs, custody 74 months, so the
        qualifying date derives from 120 months, not 240."""
        decision = self._decide(
            table,
            self._concluded(
                ChargedOffence(
                    offence_id="SYN-944",
                    label="Synthetic concluded offence",
                    section="944",
                    maximum=MaximumPunishment(
                        kinds=frozenset({PunishmentKind.TERM}), term_months=480
                    ),
                )
            ),
        )
        assert decision.qualifying_date == date(2030, 6, 1)  # arrest + 120 months

    def test_gate_4_reads_the_prior_input_not_the_case_list(self, table: DecisionTable) -> None:
        """Same case list, different prior input -> different fraction; different case list,
        same prior input -> same fraction."""
        concluded = self._concluded(
            ChargedOffence(
                offence_id="SYN-945",
                label="Synthetic concluded offence",
                section="945",
                maximum=MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=36),
            )
        )
        with_prior = evaluate(
            CaseInput(
                date_of_arrest=self._ARREST,
                evaluated_on=self._AS_ON,
                cases=(self._pending_modest(), concluded),
                prior_conviction_status=PriorConvictionStatus.KNOWN_PRIOR,
            ),
            table,
        )
        first_timer = evaluate(
            CaseInput(
                date_of_arrest=self._ARREST,
                evaluated_on=self._AS_ON,
                cases=(self._pending_modest(), concluded),
                prior_conviction_status=PriorConvictionStatus.NONE_DECLARED,
            ),
            table,
        )
        no_concluded = evaluate(
            CaseInput(
                date_of_arrest=self._ARREST,
                evaluated_on=self._AS_ON,
                cases=(self._pending_modest(),),
                prior_conviction_status=PriorConvictionStatus.KNOWN_PRIOR,
            ),
            table,
        )
        assert with_prior.fraction_applied == Fraction(1, 2)
        assert first_timer.fraction_applied == Fraction(1, 3)
        assert no_concluded.fraction_applied == with_prior.fraction_applied


class TestGate3ScopeWords:
    """D-074: the bar attaches to the offences its own scope words enumerate, never to the
    whole Act. NDPS s.37(1)(b), verified from the stored act, reaches ss.19/24/27A and
    commercial-quantity offences only - a small-quantity charge does not engage it at all."""

    @staticmethod
    def _ndps_offence(in_scope: bool | None) -> ChargedOffence:
        return offence(
            label="NDPS offence (synthetic)",
            special_statute="NDPS",
            special_statute_provision="s.37",
            special_statute_in_gate3_set=True,
            special_statute_bar_in_scope=in_scope,
        )

    def test_out_of_scope_charge_raises_no_flag_and_can_be_entitled(
        self, table: DecisionTable
    ) -> None:
        """A small-quantity charge outside s.37's scope words: no test-required flag, no
        scope flag, and - everything else passing - the entitlement stands. A flag firing
        when nothing is wrong trains people to clear flags (D-069)."""
        decision = evaluate(
            case_input(offences=(self._ndps_offence(False),), arrest=date(2018, 1, 1)),
            table,
        )
        assert Flag.SPECIAL_STATUTE_TEST_REQUIRED not in decision.flags
        assert Flag.CONTESTED_SPECIAL_STATUTE_SCOPE not in decision.flags
        gate3 = next(o for o in decision.gate_outcomes if o.gate_id == 3)
        assert not gate3.fired
        assert "outside the bar's own scope words" in gate3.detail
        assert decision.verdict is Verdict.NO_ENTITLEMENT_IDENTIFIED or True
        # Verdict depends on the rest of the case; with this fixture everything else passes:
        assert decision.verdict is Verdict.ENTITLEMENT_ESTABLISHED

    def test_undetermined_scope_is_a_scope_question_not_a_default_to_firing(
        self, table: DecisionTable
    ) -> None:
        decision = evaluate(
            case_input(offences=(self._ndps_offence(None),), arrest=date(2018, 1, 1)),
            table,
        )
        assert Flag.CONTESTED_SPECIAL_STATUTE_SCOPE in decision.flags
        assert Flag.SPECIAL_STATUTE_TEST_REQUIRED not in decision.flags
        gate3 = next(o for o in decision.gate_outcomes if o.gate_id == 3)
        assert not gate3.fired
        assert "undetermined" in gate3.detail
        # An abstention routes to a human; it never grants.
        assert decision.verdict is Verdict.NO_ENTITLEMENT_IDENTIFIED
        assert decision.gate_fired == 3

    def test_in_scope_charge_still_gets_the_test_flag(self, table: DecisionTable) -> None:
        decision = evaluate(
            case_input(offences=(self._ndps_offence(True),), arrest=date(2018, 1, 1)),
            table,
        )
        assert Flag.SPECIAL_STATUTE_TEST_REQUIRED in decision.flags
        assert next(o for o in decision.gate_outcomes if o.gate_id == 3).fired

    def test_scope_state_enters_the_inputs_hash(self, table: DecisionTable) -> None:
        a = case_input(offences=(self._ndps_offence(None),), arrest=date(2018, 1, 1))
        b = case_input(offences=(self._ndps_offence(True),), arrest=date(2018, 1, 1))
        assert a.inputs_hash() != b.inputs_hash()

    def test_scope_contested_blocks_the_filing_via_the_prefix(self, table: DecisionTable) -> None:
        """The CONTESTED_ prefix rule in the application generator must catch the new flag
        without being told about it - that is what the prefix check is for."""
        assert Flag.CONTESTED_SPECIAL_STATUTE_SCOPE.name.startswith("CONTESTED_")


class TestD075ThresholdBand:
    """D-075: the OLQ-2 band, on the D-066 pattern, at the person level.

    depends_on_olq: [OLQ-2, OLQ-11] — the same conservatism inversion at a third level (cap,
    person-level threshold, limb attachment); the register records the linkage.
    """

    @staticmethod
    def _two_offence_case(as_on: date) -> CaseInput:
        """Two pending cases (gate 2 bars): a 12-month and a 120-month maximum. The lower
        offence's one-half threshold is 6 months; the governing threshold is 60 months."""
        return case_input(
            cases=(
                PendingCase("FIR-1/2024", (offence(section="906", maximum=term(12)),)),
                PendingCase("FIR-2/2024", (offence(section="907", maximum=term(120)),)),
            ),
            arrest=date(2024, 1, 1),
            as_on=as_on,
        )

    def test_lower_crossed_governing_not_raises_the_flag_with_both_dates(
        self, table: DecisionTable
    ) -> None:
        decision = evaluate(self._two_offence_case(date(2025, 1, 1)), table)
        assert Flag.CONTESTED_THRESHOLD_BASIS in decision.flags
        # Both dates carried: governing (arrest + 60 months) and lowest-crossed (+ 6 months).
        assert decision.qualifying_date == date(2029, 1, 1)
        assert decision.contested_threshold_date == date(2024, 7, 1)
        # The flag survives the gate-2 bar, exactly as the gate-0 band does.
        assert decision.gate_fired == 2

    def test_nothing_crossed_no_flag(self, table: DecisionTable) -> None:
        decision = evaluate(self._two_offence_case(date(2024, 3, 1)), table)
        assert Flag.CONTESTED_THRESHOLD_BASIS not in decision.flags
        assert decision.contested_threshold_date is None

    def test_governing_crossed_no_flag(self, table: DecisionTable) -> None:
        decision = evaluate(self._two_offence_case(date(2029, 6, 1)), table)
        assert Flag.CONTESTED_THRESHOLD_BASIS not in decision.flags

    def test_single_offence_never_contested(self, table: DecisionTable) -> None:
        decision = evaluate(
            case_input(offences=(offence(maximum=term(36)),), arrest=date(2025, 6, 1)),
            table,
        )
        assert Flag.CONTESTED_THRESHOLD_BASIS not in decision.flags

    def test_concluded_offences_cannot_create_the_band(self, table: DecisionTable) -> None:
        """D-072 composition: a concluded lower offence takes no part, so it cannot raise
        this flag either."""
        case = case_input(
            cases=(
                PendingCase("FIR-1/2024", (offence(section="907", maximum=term(120)),)),
                PendingCase(
                    "OLD-1/2019",
                    (offence(section="906", maximum=term(12)),),
                    is_pending=False,
                ),
            ),
            arrest=date(2024, 1, 1),
            as_on=date(2025, 1, 1),
        )
        decision = evaluate(case, table)
        assert Flag.CONTESTED_THRESHOLD_BASIS not in decision.flags
