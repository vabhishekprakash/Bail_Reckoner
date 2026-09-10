"""The six-gate entitlement engine — Layer C (D-034).

Pure: no network, no model, no file or database I/O. Deterministic over `CaseInput`, using only
the standard library (D-050). The statutory *parameters* — fractions and provision texts — arrive
as a loaded `DecisionTable`; the gate *order and semantics* below are code, because they encode
how the system behaves regardless of what the law says (D-055).

Gate order, fixed:

    0  CAP       custody >= maximum prescribed        s.479(1) third proviso
    1  BAR       death or life prescribed             s.479(1) main clause
    2  BAR       multiple offences / multiple cases    s.479(2)
    3  FLAG      special-statute bail bar              Antil Category C
    4  SELECTOR  first-time offender                   s.479(1) first proviso
    5  TEST      custody >= applicable threshold       s.479(1)

Two properties this module exists to guarantee, both tested:

* **Gate 0 is always evaluated and never masked.** It runs before anything else and its flag
  survives every later outcome (D-034). A person held past the maximum sentence is the most
  urgent thing this system can find, and a bar firing at gate 1 or 2 must not hide it.
* **The working is always computed.** Every offence's arithmetic is produced regardless of which
  gate fired (D-035). A bar controls the *verdict*, never whether the reader sees the sums.
"""

from __future__ import annotations

from datetime import date
from fractions import Fraction

from bail_reckoner.engine.custody import CustodyComputation, compute_custody
from bail_reckoner.engine.types import (
    CaseInput,
    ChargedOffence,
    Decision,
    Flag,
    GateOutcome,
    OffenceComputation,
    PriorConvictionStatus,
    Scope479_2,
    Verdict,
)
from bail_reckoner.statutes.decision_table import DecisionTable

__all__ = ["evaluate"]

_WHOLE = Fraction(1)


def evaluate(case: CaseInput, table: DecisionTable) -> Decision:
    """Run all six gates and return the decision.

    Provision: Section 479, Bharatiya Nagarik Suraksha Sanhita, 2023 (Act 46 of 2023), verbatim
    text in `01_law/Section_479_BNSS_2023.md`.

    Every gate is evaluated and recorded even after a bar fires, so the report can distinguish a
    condition that was checked and passed from one that was never reached.
    """
    custody = compute_custody(
        custody_start=case.date_of_arrest,
        as_on=case.evaluated_on,
        break_days=sum(b.days for b in case.custody_breaks),
        excluded_days=case.excluded_days,
    )
    offences = case.pending_offences
    # D-072: gates 0, 1 and 5 and the person-level arithmetic run over PENDING offences only.
    # s.479(1) ties the period to an offence under investigation, inquiry or trial; a concluded
    # case is under none of those, and letting it raise the governing maximum suppressed the
    # gate-0 cap and pushed qualifying dates out — under-claiming, the dangerous direction
    # (D-010). Non-pending offences still appear in the computations for the record, marked
    # inert (D-035: the working is always shown). Gate 4 is untouched: prior-conviction status
    # is its own input and is never derived from the case list.
    concluded = tuple(o for c in case.cases if not c.is_pending for o in c.offences)
    flags: list[Flag] = []
    outcomes: list[GateOutcome] = []

    if case.date_of_first_remand is not None and case.date_of_first_remand != case.date_of_arrest:
        flags.append(Flag.ARREST_REMAND_DIVERGENCE)

    if not case.case_list_verified:
        # s.479(2) turns on every pending case, disclosed or not. An asserted case list is an
        # input, not a fact; the report must say so rather than let the result read as complete.
        flags.append(Flag.CASE_LIST_UNVERIFIED)

    governing = _governing_maximum_months(offences)
    if any(o.maximum is None for o in offences):
        flags.append(Flag.OFFENCE_NOT_IN_DATABASE)
    if offences and governing is None and Flag.OFFENCE_NOT_IN_DATABASE not in flags:
        flags.append(Flag.MAXIMUM_NOT_COMPUTABLE)

    gate0 = _gate_0_cap(custody, governing, _lowest_maximum_months(offences), table)
    outcomes.append(gate0)
    flags.extend(gate0.flags)

    gate1 = _gate_1_death_or_life(offences, table)
    outcomes.append(gate1)

    gate2 = _gate_2_multiplicity(case, table)
    outcomes.append(gate2)
    flags.extend(gate2.flags)

    gate3 = _gate_3_special_statute(offences, table)
    outcomes.append(gate3)
    flags.extend(gate3.flags)

    gate4 = _gate_4_first_time_offender(case, table)
    outcomes.append(gate4)
    flags.extend(gate4.flags)
    fraction = _fraction_for(case, table)

    computations = _compute_offences(offences, custody, fraction)
    computations.extend(
        OffenceComputation(
            offence=offence,
            max_term_months=None,
            threshold_months=None,
            qualifying_date=None,
            crossed=False,
            fraction_applied=None,
            note=(
                "Case not pending: this offence takes no part in the s.479(1) computation "
                "(D-072). Listed for the record only."
            ),
        )
        for offence in concluded
    )

    gate5 = _gate_5_threshold(custody, governing, fraction, table)
    outcomes.append(gate5)
    flags.extend(gate5.flags)

    qualifying = custody.qualifying_date(Fraction(governing) * fraction) if governing else None

    # D-075 (OLQ-2's band, on the D-066 pattern): if a lower charged offence's own threshold
    # has been crossed while the governing maximum's has not, which aggregation rule
    # s.479(1) requires is unsettled — flag, and carry the per-offence reading's date so the
    # report can show both. Raised regardless of which gate carries the verdict, exactly as
    # the gate-0 band survives a gate-2 bar.
    contested_threshold_date: date | None = None
    if qualifying is not None and _as_on(custody) < qualifying:
        crossed_dates = [
            c.qualifying_date for c in computations if c.crossed and c.qualifying_date is not None
        ]
        if crossed_dates:
            contested_threshold_date = min(crossed_dates)
            flags.append(Flag.CONTESTED_THRESHOLD_BASIS)

    verdict, gate_fired = _decide(gate1, gate2, gate3, gate5, flags)

    if verdict is Verdict.ENTITLEMENT_ESTABLISHED and case.excluded_days == 0:
        # The Explanation may exclude accused-caused delay, which would move this date later.
        # Zero exclusions is the maximum custody the person could claim, so a crossing computed
        # here is the earliest possible one and must be marked as resting on that assumption.
        flags.append(Flag.EXCLUSION_STATUS_UNVERIFIED)

    return Decision(
        verdict=verdict,
        gate_fired=gate_fired,
        flags=tuple(_dedupe(flags)),
        gate_outcomes=tuple(outcomes),
        offence_computations=tuple(computations),
        custody_days=custody.elapsed_days,
        effective_custody_days=custody.effective_days,
        fraction_applied=fraction,
        qualifying_date=qualifying,
        contested_threshold_date=contested_threshold_date,
        statute_version=_statute_version(table),
        law_in_force_on=case.law_in_force_on or case.evaluated_on,
        inputs_hash=case.inputs_hash(),
        timestamp=case.evaluated_on,
        rules_fired=tuple(f"gate{o.gate_id}:{o.provision}" for o in outcomes if o.fired),
        reviewed_by="",
    )


def _gate_0_cap(
    custody: CustodyComputation,
    governing_months: int | None,
    lowest_months: int | None,
    table: DecisionTable,
) -> GateOutcome:
    """Gate 0 — custody has reached the maximum sentence prescribed.

    Provision: s.479(1), third proviso — "no such person shall in any case be detained during the
    period of investigation, inquiry or trial for more than the maximum period of imprisonment
    provided for the said offence under that law."

    Runs first and unconditionally (D-034). s.479(2) is expressly "subject to the third proviso
    thereof", so the multiple-case bar cannot suppress this; nor may any other gate.

    Note the open questions this does *not* resolve: whether the cap reaches an offence excluded
    from s.479(1) by the death/life carve-out (OLQ-9a), and which maximum the cap measures
    against when several offences are charged (OLQ-11). The flag posture is over-inclusive in
    both, because flagging over-inclusively costs a human review while flagging under-inclusively
    costs someone their liberty.

    OLQ-11 handling (D-066, the D-025 flag-not-pick pattern): the cap is computed against the
    governing (highest) maximum AND the lowest per-offence maximum. Custody at or past the
    highest → DETAINED_BEYOND_MAXIMUM, unchanged. Custody in the band — at or past the lowest,
    below the highest — → CONTESTED_CAP_BASIS, routed to a human, because in a gate-2-barred
    multi-offence case (s.479(2) being expressly subject to the third proviso) the cap is the
    only surviving route to relief, and measuring it solely against the highest maximum would
    make that sole route fire as late as it possibly could.
    """
    spec = table.gate(0)
    if governing_months is None:
        return GateOutcome(
            gate_id=0,
            name=spec.name,
            provision=spec.provision,
            fired=False,
            detail="No computable maximum, so the cap cannot be tested.",
        )
    cap_date = custody.qualifying_date(_WHOLE * governing_months)
    reached = custody.custody_start <= cap_date and _as_on(custody) >= cap_date
    if reached:
        return GateOutcome(
            gate_id=0,
            name=spec.name,
            provision=spec.provision,
            fired=True,
            detail=(
                f"Custody reached the maximum prescribed ({governing_months} months) on "
                f"{cap_date.isoformat()}."
            ),
            flags=(Flag.DETAINED_BEYOND_MAXIMUM,),
        )
    if lowest_months is not None and lowest_months != governing_months:
        cap_low = custody.qualifying_date(_WHOLE * lowest_months)
        if _as_on(custody) >= cap_low:
            return GateOutcome(
                gate_id=0,
                name=spec.name,
                provision=spec.provision,
                fired=False,
                detail=(
                    f"Custody passed the lowest charged offence's maximum ({lowest_months} "
                    f"months, on {cap_low.isoformat()}) but not the governing maximum "
                    f"({governing_months} months, {cap_date.isoformat()}). Which maximum the "
                    f"third proviso measures against is unsettled (OLQ-11); routed to human "
                    f"review."
                ),
                flags=(Flag.CONTESTED_CAP_BASIS,),
            )
    return GateOutcome(
        gate_id=0,
        name=spec.name,
        provision=spec.provision,
        fired=False,
        detail=f"Maximum prescribed ({governing_months} months) would be reached on {cap_date}.",
    )


def _gate_1_death_or_life(
    offences: tuple[ChargedOffence, ...], table: DecisionTable
) -> GateOutcome:
    """Gate 1 — death or life imprisonment is prescribed. BAR.

    Provision: s.479(1) main clause — the sub-section does not apply to "an offence for which the
    punishment of death or life imprisonment has been specified as **one of** the punishments".

    "One of" is the load-bearing phrase: an offence punishable with death *or* a term of years is
    still excluded, so this cannot be implemented as "is the maximum a number?".
    """
    spec = table.gate(1)
    excluded = [o for o in offences if o.maximum is not None and o.maximum.excludes_s479]
    if excluded:
        listed = ", ".join(f"{o.label} ({o.section})" for o in excluded)
        return GateOutcome(
            gate_id=1,
            name=spec.name,
            provision=spec.provision,
            fired=True,
            detail=f"Death or life imprisonment is among the punishments for: {listed}.",
        )
    return GateOutcome(
        gate_id=1,
        name=spec.name,
        provision=spec.provision,
        fired=False,
        detail="No charged offence carries death or life imprisonment.",
    )


def _gate_2_multiplicity(case: CaseInput, table: DecisionTable) -> GateOutcome:
    """Gate 2 — more than one offence, or multiple cases, pending. BAR.

    Provision: s.479(2) — "Notwithstanding anything in sub-section (1), and subject to the third
    proviso thereof, where an investigation, inquiry or trial in more than one offence or in
    multiple cases are pending against a person, he shall not be released on bail by the Court."

    Scope is configurable and defaults to NARROW (D-025): the bar fires on multiple *cases*. A
    single case charging several sections is flagged CONTESTED and routed to a human, never
    silently cleared and never silently barred — whether that situation triggers s.479(2) is
    genuinely unsettled (OLQ-5), and multi-section FIRs are the norm rather than the exception.
    """
    spec = table.gate(2)
    pending = case.pending_cases
    offence_count = sum(len(c.offences) for c in pending)

    if len(pending) > 1:
        return GateOutcome(
            gate_id=2,
            name=spec.name,
            provision=spec.provision,
            fired=True,
            detail=f"{len(pending)} cases pending: {', '.join(c.case_ref for c in pending)}.",
        )

    if case.scope_479_2 is Scope479_2.BROAD and offence_count > 1:
        return GateOutcome(
            gate_id=2,
            name=spec.name,
            provision=spec.provision,
            fired=True,
            detail=f"BROAD scope: {offence_count} offences pending in a single case.",
        )

    if offence_count > 1:
        return GateOutcome(
            gate_id=2,
            name=spec.name,
            provision=spec.provision,
            fired=False,
            detail=(
                f"One case charging {offence_count} offences. Whether s.479(2) applies to a "
                f"single case with multiple offences is unsettled; routed to human review."
            ),
            flags=(Flag.CONTESTED_479_2_SCOPE,),
        )

    return GateOutcome(
        gate_id=2,
        name=spec.name,
        provision=spec.provision,
        fired=False,
        detail="A single offence in a single case is pending.",
    )


def _gate_3_special_statute(
    offences: tuple[ChargedOffence, ...], table: DecisionTable
) -> GateOutcome:
    """Gate 3 — a special-statute bail bar may apply. FLAG, never a bar.

    Provision: *Satender Kumar Antil v. CBI* (11 July 2022), Category C.

    Never terminal (D-033). *Badshah Majid Malik v. Directorate of Enforcement* (SC,
    Crl. A. No. 4258/2024, 27 December 2024) holds s.479(1) applies to PMLA prosecutions, so a
    Category-C statute cannot extinguish the computation. The arithmetic is produced in full, the
    provision is named, and the verdict is routed to a human.

    The NDPS s.37 position is **not** assumed to follow the PMLA position (OLQ-1).

    A statute present but outside the gate-3 set raises SPECIAL_STATUTE_UNASSESSED rather than
    nothing (D-054): silence would let a reader infer the statute is irrelevant to the case.

    **Pending offences only (Abhishek, 2026-08-19).** A special-statute bar attaches to the
    offence for which release is sought; a flag derived from a concluded case is a false alarm
    by construction, and per D-069 a signal that fires when nothing is wrong trains people to
    clear signals. (This narrowing first landed as an unflagged side effect of D-072's shared
    `offences` variable — recorded as such, then made deliberate here.) Counter-argument,
    recorded: a prior special-statute conviction may bear on merits-based bail — but
    merits-based bail is outside s.479 and belongs to counsel, not to this system (D-009's
    boundary).
    """
    spec = table.gate(3)
    in_set = [o for o in offences if o.special_statute and o.special_statute_in_gate3_set]
    outside = [o for o in offences if o.special_statute and not o.special_statute_in_gate3_set]

    flags: list[Flag] = []
    details: list[str] = []
    # D-074: the bar attaches to the offences its own scope words enumerate, never to the
    # whole Act. In-scope → the test applies. Determined out of scope → recorded, no flag
    # (an NDPS small-quantity charge does not engage s.37 at all, and a flag firing when
    # nothing is wrong trains people to clear flags — D-069). Undetermined → a scope
    # question, surfaced and routed, never a default to firing.
    in_scope = [o for o in in_set if o.special_statute_bar_in_scope is True]
    out_of_scope = [o for o in in_set if o.special_statute_bar_in_scope is False]
    scope_unknown = [o for o in in_set if o.special_statute_bar_in_scope is None]
    if in_scope:
        flags.append(Flag.SPECIAL_STATUTE_TEST_REQUIRED)
        for offence in in_scope:
            provision = offence.special_statute_provision
            named = provision if provision else "barring provision unresolved by this project"
            details.append(f"{offence.special_statute} ({named}) applies to {offence.label}")
    if out_of_scope:
        for offence in out_of_scope:
            details.append(
                f"{offence.special_statute}: {offence.label} determined to fall outside the "
                f"bar's own scope words; the statutory test is not engaged"
            )
    if scope_unknown:
        flags.append(Flag.CONTESTED_SPECIAL_STATUTE_SCOPE)
        for offence in scope_unknown:
            details.append(
                f"{offence.special_statute}: whether {offence.label} falls within the bar's "
                f"scope words is undetermined; routed as a scope question"
            )
    if outside:
        flags.append(Flag.SPECIAL_STATUTE_UNASSESSED)
        listed = ", ".join(sorted({str(o.special_statute) for o in outside}))
        details.append(
            f"{listed}: present, but no bail bar for it has been verified by this project"
        )

    if not flags and not details:
        return GateOutcome(
            gate_id=3,
            name=spec.name,
            provision=spec.provision,
            fired=False,
            detail="No special statute identified among the charged offences.",
        )
    return GateOutcome(
        gate_id=3,
        name=spec.name,
        provision=spec.provision,
        fired=bool(in_scope),
        detail="; ".join(details) + ".",
        flags=tuple(flags),
    )


def _gate_4_first_time_offender(case: CaseInput, table: DecisionTable) -> GateOutcome:
    """Gate 4 — first-time offender. SELECTS THE FRACTION. Not a bar.

    Provision: s.479(1), first proviso — a first-time offender "who has never been convicted of
    any offence in the past" is released **on bond** at **one-third** of the maximum period.

    A non-first-time offender is not barred; they proceed to gate 5 on the one-half threshold.
    Unknown status takes one-half and raises PRIOR_STATUS_UNVERIFIED (D-051), so the one-third
    route stays visible as something verification could unlock rather than silently vanishing.
    """
    spec = table.gate(4)
    status = case.prior_conviction_status
    if status is PriorConvictionStatus.NONE_DECLARED:
        return GateOutcome(
            gate_id=4,
            name=spec.name,
            provision=spec.provision,
            fired=True,
            detail="Declared as never previously convicted: one-third threshold, release on bond.",
        )
    if status is PriorConvictionStatus.UNKNOWN:
        return GateOutcome(
            gate_id=4,
            name=spec.name,
            provision=spec.provision,
            fired=False,
            detail=(
                "Prior-conviction status unverified: the one-half threshold is applied. "
                "The one-third route may apply if first-time status is established."
            ),
            flags=(Flag.PRIOR_STATUS_UNVERIFIED,),
        )
    return GateOutcome(
        gate_id=4,
        name=spec.name,
        provision=spec.provision,
        fired=False,
        detail="A previous conviction is recorded: the one-half threshold applies.",
    )


def _gate_5_threshold(
    custody: CustodyComputation,
    governing_months: int | None,
    fraction: Fraction,
    table: DecisionTable,
) -> GateOutcome:
    """Gate 5 — custody has reached the applicable threshold. TEST.

    Provision: s.479(1), read with the first proviso where gate 4 selected one-third.

    A negative result is **not** a finding against the person: the qualifying date is computed
    and NOT_YET_ENTITLED is raised so recomputation can be scheduled.
    """
    spec = table.gate(5)
    if governing_months is None:
        return GateOutcome(
            gate_id=5,
            name=spec.name,
            provision=spec.provision,
            fired=False,
            detail="No computable maximum, so no threshold can be tested.",
        )
    threshold = Fraction(governing_months) * fraction
    qualifying = custody.qualifying_date(threshold)
    if _as_on(custody) >= qualifying:
        return GateOutcome(
            gate_id=5,
            name=spec.name,
            provision=spec.provision,
            fired=True,
            detail=f"Threshold of {threshold} months was reached on {qualifying.isoformat()}.",
        )
    return GateOutcome(
        gate_id=5,
        name=spec.name,
        provision=spec.provision,
        fired=False,
        detail=f"Threshold of {threshold} months is reached on {qualifying.isoformat()}.",
        flags=(Flag.NOT_YET_ENTITLED,),
    )


def _decide(
    gate1: GateOutcome,
    gate2: GateOutcome,
    gate3: GateOutcome,
    gate5: GateOutcome,
    flags: list[Flag],
) -> tuple[Verdict, int | None]:
    """Derive the verdict. Only two are possible (D-010).

    Order of precedence among negatives is the gate order, so the report names the *first*
    reason the case needs a human rather than an arbitrary one.

    Note that gate 3 firing yields NO_ENTITLEMENT_IDENTIFIED even though it is a FLAG: "never
    terminal" (D-033) means it never suppresses the arithmetic, not that it grants entitlement.
    The case still needs the special-statute test applied by a person.
    """
    if gate1.fired:
        return Verdict.NO_ENTITLEMENT_IDENTIFIED, 1
    if gate2.fired:
        return Verdict.NO_ENTITLEMENT_IDENTIFIED, 2
    if not gate5.fired:
        return Verdict.NO_ENTITLEMENT_IDENTIFIED, 5
    if gate3.fired:
        return Verdict.NO_ENTITLEMENT_IDENTIFIED, 3
    if Flag.CONTESTED_479_2_SCOPE in flags:
        return Verdict.NO_ENTITLEMENT_IDENTIFIED, 2
    if Flag.CONTESTED_SPECIAL_STATUTE_SCOPE in flags:
        # An undetermined scope question is an abstention, not a bar: the case routes to a
        # human under the gate-3 reason until scope is determined either way (D-074).
        return Verdict.NO_ENTITLEMENT_IDENTIFIED, 3
    if Flag.OFFENCE_NOT_IN_DATABASE in flags or Flag.MAXIMUM_NOT_COMPUTABLE in flags:
        return Verdict.NO_ENTITLEMENT_IDENTIFIED, None
    return Verdict.ENTITLEMENT_ESTABLISHED, None


def _compute_offences(
    offences: tuple[ChargedOffence, ...], custody: CustodyComputation, fraction: Fraction
) -> list[OffenceComputation]:
    """Per-offence arithmetic. Produced for every offence, whatever any gate concluded (D-035)."""
    results: list[OffenceComputation] = []
    for offence in offences:
        maximum = offence.maximum
        if maximum is None:
            results.append(
                OffenceComputation(
                    offence=offence,
                    max_term_months=None,
                    threshold_months=None,
                    qualifying_date=None,
                    crossed=False,
                    fraction_applied=None,
                    note="No verified penalty row: OFFENCE_NOT_IN_DATABASE. No maximum is guessed.",
                )
            )
            continue
        if not maximum.is_computable:
            note = (
                "Maximum is defined by reference to another offence; not resolved here."
                if maximum.reference_note
                else "No term of imprisonment is prescribed, so no threshold arithmetic applies."
            )
            results.append(
                OffenceComputation(
                    offence=offence,
                    max_term_months=None,
                    threshold_months=None,
                    qualifying_date=None,
                    crossed=False,
                    fraction_applied=None,
                    note=note,
                )
            )
            continue
        threshold = maximum.threshold_months(fraction)
        qualifying = custody.qualifying_date(threshold)
        results.append(
            OffenceComputation(
                offence=offence,
                max_term_months=maximum.term_months,
                threshold_months=threshold,
                qualifying_date=qualifying,
                crossed=_as_on(custody) >= qualifying,
                fraction_applied=fraction,
            )
        )
    return results


def _fraction_for(case: CaseInput, table: DecisionTable) -> Fraction:
    """One-third only where first-time status is declared; one-half otherwise (D-051)."""
    if case.prior_conviction_status is PriorConvictionStatus.NONE_DECLARED:
        return table.fraction_first_time_offender
    return table.fraction_standard


def _governing_maximum_months(offences: tuple[ChargedOffence, ...]) -> int | None:
    """The maximum that governs the person-level threshold: the highest among charged offences.

    D-039, marked UNVERIFIED. s.479(1) speaks of "that offence"; with several charged, the
    highest maximum gives the longest threshold, which is the reading that never overstates an
    entitlement. Per-offence arithmetic is displayed separately regardless.
    """
    terms = [
        o.maximum.term_months
        for o in offences
        if o.maximum is not None and o.maximum.term_months is not None
    ]
    return max(terms) if terms else None


def _lowest_maximum_months(offences: tuple[ChargedOffence, ...]) -> int | None:
    """The lowest definite maximum among charged offences — the other bound of the OLQ-11 band.

    The governing (highest) maximum keeps its D-039 role for gate 5; this bound exists only so
    gate 0 can flag the contested band rather than silently adopting one reading of the cap.
    """
    terms = [
        o.maximum.term_months
        for o in offences
        if o.maximum is not None and o.maximum.term_months is not None
    ]
    return min(terms) if terms else None


def _as_on(custody: CustodyComputation) -> date:
    """Reconstruct the evaluation date from the custody computation."""
    from datetime import timedelta

    return custody.custody_start + timedelta(days=custody.elapsed_days - 1)


def _statute_version(table: DecisionTable) -> str:
    """Composite snapshot id (D-049): law snapshot + table version + content hash."""
    return (
        f"{table.statute.short_name}@{table.statute.law_as_on.isoformat()}"
        f"+dt-{table.table_version}+{table.content_hash[:8]}"
    )


def _dedupe(flags: list[Flag]) -> list[Flag]:
    """Preserve first-seen order; `dict.fromkeys` keeps insertion order and drops repeats."""
    return list(dict.fromkeys(flags))
