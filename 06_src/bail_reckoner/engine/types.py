"""Typed inputs and outputs for the six-gate engine (Layer C).

Stdlib only, all frozen (D-050). Nothing here reads a file, calls a model or touches a clock:
even `evaluated_at` is an *input*, because an engine that calls `datetime.now()` is not a
deterministic function of its inputs and cannot be replayed against a stored report.

The output shape is where D-010 is enforced structurally rather than by convention. `Verdict` has
exactly two members and there is no way to express a third; everything else a reader might call
an outcome -- not-yet-entitled, contested scope, offence unknown -- is a `Flag`. A future
contributor cannot add an "ineligible" state without deleting a member of an enum, which is a
conspicuous act rather than an easy one.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from fractions import Fraction

from bail_reckoner.statutes.models import MaximumPunishment

__all__ = [
    "PriorConvictionStatus",
    "Verdict",
    "Flag",
    "Severity",
    "ChargedOffence",
    "PendingCase",
    "CustodyBreak",
    "Scope479_2",
    "CaseInput",
    "GateOutcome",
    "OffenceComputation",
    "Decision",
]


class PriorConvictionStatus(Enum):
    """Whether the person has been convicted before (s.479(1), first proviso).

    Three-valued by design (D-051). Two values would force `UNKNOWN` to masquerade as one of the
    others: treating unknown as first-time overstates entitlement, and treating it as a prior
    conviction silently withholds the one-third route from someone who may qualify. Neither is
    acceptable, so unknown is represented and surfaced.
    """

    NONE_DECLARED = "NONE_DECLARED"
    """Self-declared as never convicted. Engages the one-third route with a caveat printed."""

    KNOWN_PRIOR = "KNOWN_PRIOR"
    UNKNOWN = "UNKNOWN"
    """Takes the conservative one-half threshold AND raises PRIOR_STATUS_UNVERIFIED."""


class Verdict(Enum):
    """The only two verdicts the system can reach (D-010).

    There is deliberately no third member. A false "eligible" is caught by the court; a false
    "ineligible" silently keeps a person in custody and nobody appeals a machine's silence.
    """

    ENTITLEMENT_ESTABLISHED = "ENTITLEMENT_ESTABLISHED"
    NO_ENTITLEMENT_IDENTIFIED = "NO_ENTITLEMENT_IDENTIFIED — HUMAN REVIEW REQUIRED"


class Severity(Enum):
    """How prominently a flag must be surfaced. Ordered."""

    INFO = 1
    NOTABLE = 2
    URGENT = 3


class Flag(Enum):
    """Typed conditions accompanying a verdict (D-048).

    Flags carry the nuance that D-010 forbids putting in the verdict. Every flag is displayed;
    none is a verdict.
    """

    DETAINED_BEYOND_MAXIMUM = "DETAINED_BEYOND_MAXIMUM"
    """s.479(1) third proviso. Gate 0. The most urgent condition this system can detect: the
    person has been in custody at least as long as the maximum sentence the offence carries.
    Computed first and never masked by a later gate (D-034)."""

    SPECIAL_STATUTE_TEST_REQUIRED = "SPECIAL_STATUTE_TEST_REQUIRED"
    """Gate 3 (D-033). Never terminal -- the arithmetic is still computed and displayed."""

    SPECIAL_STATUTE_UNASSESSED = "SPECIAL_STATUTE_UNASSESSED"
    """A special statute is present but is not in the gate-3 set, so this project has not
    verified whether it bars bail (D-054 refinement). Named rather than passed over in silence,
    which would let a reader infer the statute is irrelevant."""

    CONTESTED_479_2_SCOPE = "CONTESTED_479_2_SCOPE"
    """A single case charging several offences. Whether s.479(2) fires is genuinely unsettled
    (D-025, OLQ-5), so the case is routed to a human rather than cleared or barred silently."""

    PRIOR_STATUS_UNVERIFIED = "PRIOR_STATUS_UNVERIFIED"
    """Prior-conviction status unknown, so the one-half threshold was applied. The one-third
    route may apply on verification (D-051)."""

    EXCLUSION_STATUS_UNVERIFIED = "EXCLUSION_STATUS_UNVERIFIED"
    """A threshold was crossed with `excluded_days = 0`. The s.479(1) Explanation may exclude
    accused-caused delay, which would push the qualifying date later (D-047, OLQ-7)."""

    OFFENCE_NOT_IN_DATABASE = "OFFENCE_NOT_IN_DATABASE"
    """At least one charged offence has no verified penalty row. The engine never guesses a
    maximum sentence."""

    MAXIMUM_NOT_COMPUTABLE = "MAXIMUM_NOT_COMPUTABLE"
    """An offence's maximum is fine-only or defined by reference to another offence, so no
    threshold arithmetic is possible for it."""

    NOT_YET_ENTITLED = "NOT_YET_ENTITLED"
    """Gate 5 negative. Not a finding against the person: the qualifying date is computed and
    recomputation should be scheduled."""

    CONTESTED_CAP_BASIS = "CONTESTED_CAP_BASIS"
    """Custody has passed the LOWEST charged offence's maximum but not the governing (highest)
    one, and which maximum the third-proviso cap measures against is unsettled (OLQ-11).

    Flag-not-pick, on the D-025 pattern: where readings diverge materially and the law is
    unsettled, the engine routes the divergence to a human rather than choosing. This matters
    most in multi-offence cases barred by gate 2 — s.479(2) is expressly subject to the third
    proviso, so the cap is the ONLY surviving route to relief there, and measuring it solely
    against the highest maximum would make that sole route fire as late as it possibly could.
    Raised only inside the band; outside it behaviour is unchanged and definite crossings still
    raise DETAINED_BEYOND_MAXIMUM."""

    CONTESTED_THRESHOLD_BASIS = "CONTESTED_THRESHOLD_BASIS"
    """A lower charged offence's own threshold has been crossed while the governing (highest)
    maximum's has not, and which aggregation rule s.479(1) requires is unsettled (OLQ-2;
    D-075, the D-066 band at the person level — the same conservatism inversion at a third
    level after the cap and limb attachment).

    Not flag-only, on Abhishek's direction: the qualifying date is the instruction a jail
    officer acts on, and a bare flag leaves them acting on the later date anyway. The report
    shows BOTH dates — governing-maximum and lowest-crossed — naming which aggregation rule
    yields which, and that the question is unsettled. `Decision.contested_threshold_date`
    carries the earlier date."""

    CASE_LIST_UNVERIFIED = "CASE_LIST_UNVERIFIED"
    """The pending-case list was supplied with the inputs and has not been verified against
    court records.

    s.479(2) turns on facts OUTSIDE the case in hand — every pending case, disclosed or not — so
    this flag sits upstream of the worst error available to the system: an undisclosed pending
    case silently changes the multiple-case result. Raised by default; cleared only when the
    caller affirms the list was verified against court records, never assumed.
    """

    CONTESTED_SPECIAL_STATUTE_SCOPE = "CONTESTED_SPECIAL_STATUTE_SCOPE"
    """A charged offence sits under a gate-3 statute whose bar attaches to enumerated
    offences, and whether this charge falls within those scope words is undetermined (D-074).

    Flag-not-pick, the D-025 pattern: firing the special-statute test on statute-membership
    alone would over-fire (an NDPS small-quantity charge does not engage s.37 at all), and
    silently clearing would under-protect. The scope question is surfaced and the case routed
    to a human. The CONTESTED_ prefix also blocks the s.479(3) application automatically."""

    STATE_AMENDMENT_UNASSESSED = "STATE_AMENDMENT_UNASSESSED"
    """The charged section carries a State amendment that this project has not evaluated (L-002).

    Named rather than passed over, because silence would imply the maximum is uniform across
    India — and it may not be. IPC s.304A carries two years, while the Himachal Pradesh amendment
    printed beneath it carries life.

    Unusually, the error here runs in BOTH directions: a higher true maximum understates the
    gate-5 threshold and over-claims, while a lower one overstates it AND suppresses gate 0. So
    there is no safe default to lean on, which is why this is surfaced rather than absorbed.
    """

    ARREST_REMAND_DIVERGENCE = "ARREST_REMAND_DIVERGENCE"
    """Date of arrest and date of first remand differ, and which governs is unsettled
    (D-028, OLQ-6). Both are shown."""


_SEVERITY: dict[Flag, Severity] = {
    Flag.DETAINED_BEYOND_MAXIMUM: Severity.URGENT,
    Flag.OFFENCE_NOT_IN_DATABASE: Severity.NOTABLE,
    Flag.SPECIAL_STATUTE_TEST_REQUIRED: Severity.NOTABLE,
    Flag.CONTESTED_479_2_SCOPE: Severity.NOTABLE,
    Flag.SPECIAL_STATUTE_UNASSESSED: Severity.NOTABLE,
    Flag.MAXIMUM_NOT_COMPUTABLE: Severity.NOTABLE,
    Flag.STATE_AMENDMENT_UNASSESSED: Severity.NOTABLE,
    Flag.CONTESTED_CAP_BASIS: Severity.NOTABLE,
    Flag.CONTESTED_SPECIAL_STATUTE_SCOPE: Severity.NOTABLE,
    Flag.CONTESTED_THRESHOLD_BASIS: Severity.NOTABLE,
    Flag.CASE_LIST_UNVERIFIED: Severity.NOTABLE,
    Flag.PRIOR_STATUS_UNVERIFIED: Severity.INFO,
    Flag.EXCLUSION_STATUS_UNVERIFIED: Severity.INFO,
    Flag.NOT_YET_ENTITLED: Severity.INFO,
    Flag.ARREST_REMAND_DIVERGENCE: Severity.INFO,
}


def severity_of(flag: Flag) -> Severity:
    """Severity for report ordering. Every flag has one, checked by test."""
    return _SEVERITY[flag]


class Scope479_2(Enum):
    """Which reading of s.479(2) the engine applies (D-025). Default NARROW."""

    NARROW = "NARROW"
    """The bar fires on multiple *cases*. A single case charging several offences is flagged
    CONTESTED rather than barred."""

    BROAD = "BROAD"
    """The bar fires on more than one offence, however many cases."""


@dataclass(frozen=True, slots=True)
class ChargedOffence:
    """One offence charged, with its maximum already resolved from a verified penalty row.

    The engine receives the maximum; it never looks one up. If no verified row exists the caller
    passes `maximum=None`, which raises OFFENCE_NOT_IN_DATABASE -- the engine never guesses.
    """

    offence_id: str
    label: str
    section: str
    maximum: MaximumPunishment | None
    special_statute: str | None = None
    special_statute_provision: str | None = None
    special_statute_in_gate3_set: bool = False
    """True only for statutes in the *Antil* Category C set (D-054)."""

    special_statute_bar_in_scope: bool | None = None
    """Whether the charged offence falls within the bar's own SCOPE WORDS (D-074).

    These bars attach to enumerated offences, not whole Acts: NDPS s.37(1)(b) reaches
    ss.19/24/27A and commercial-quantity offences only; Companies Act s.212(6) reaches s.447
    only (post-2015); UAPA s.43-D(5) reaches Chapters IV and VI. Scope can turn on a case
    fact (the quantity band), so this is CALLER-DETERMINED against the decision table's
    quoted scope words — the engine never construes scope itself.

    Three-valued on the D-051 pattern: True → the statutory test applies
    (SPECIAL_STATUTE_TEST_REQUIRED); False → determined outside the scope words, recorded in
    the gate outcome, no flag; None (default) → undetermined, raising
    CONTESTED_SPECIAL_STATUTE_SCOPE and routing to a human — a scope question, never a
    default to firing (D-069: a flag firing when nothing is wrong trains people to clear
    flags, and gate 3's flag is the one that routes to a human)."""

    punishment_text: str | None = None
    """The punishment provision verbatim, from the verified row's quoted_text. The maximum is
    the number every other figure derives from; without this it reaches the filing as a bare
    assertion — the same gap that justified quoting s.479(1) in full. None means the caller
    did not supply it, and the filing says so rather than passing over it."""

    punishment_citation: str | None = None
    """Page-level citation for the punishment text, from the verified row's provenance
    (`verified_against`). The floor where the full text is unwieldy."""


@dataclass(frozen=True, slots=True)
class PendingCase:
    """A case pending against the person, for gate 2 (D-052)."""

    case_ref: str
    offences: tuple[ChargedOffence, ...]
    is_pending: bool = True


@dataclass(frozen=True, slots=True)
class CustodyBreak:
    """A period not spent in custody (interim bail, parole). Inclusive of both dates."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"custody break ends before it starts: {self.start}..{self.end}")

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


@dataclass(frozen=True, slots=True)
class CaseInput:
    """Everything the engine needs. Deterministic function of these values and nothing else."""

    date_of_arrest: date
    evaluated_on: date
    """The 'as on' date. An input, not `date.today()`, so a report can be replayed exactly."""

    cases: tuple[PendingCase, ...]
    prior_conviction_status: PriorConvictionStatus = PriorConvictionStatus.UNKNOWN
    date_of_first_remand: date | None = None
    custody_breaks: tuple[CustodyBreak, ...] = ()
    excluded_days: int = 0
    """s.479(1) Explanation. Court-determined only; the engine never computes it (D-047, OLQ-7)."""

    scope_479_2: Scope479_2 = Scope479_2.NARROW
    case_list_verified: bool = False
    """True only when the pending-case list has been verified against court records. Defaults to
    False: an asserted list is an input, not a fact, and s.479(2) turns on its completeness."""

    prior_conviction_verified: bool = False
    """True only when the prior-conviction status has been verified against records, not merely
    declared. Defaults to False on the case-list pattern: a self-declaration (NONE_DECLARED) is
    an input, not a fact. The s.479(3) application generator refuses the one-third route on an
    unverified declaration, because that route asserts to a court that the person has never
    been convicted. Contradictory with UNKNOWN status — you cannot have verified a status you
    do not know — and refused in __post_init__."""

    law_in_force_on: date | None = None
    """Which regime governs, by date of offence commission. Defaults to `evaluated_on`."""

    def __post_init__(self) -> None:
        if self.evaluated_on < self.date_of_arrest:
            raise ValueError("evaluated_on precedes date_of_arrest")
        if self.excluded_days < 0:
            raise ValueError("excluded_days cannot be negative")
        if not self.cases:
            raise ValueError("at least one case is required")
        if self.prior_conviction_verified and (
            self.prior_conviction_status is PriorConvictionStatus.UNKNOWN
        ):
            raise ValueError(
                "prior_conviction_verified=True contradicts UNKNOWN status: a status cannot "
                "be verified and unknown at once"
            )

    @property
    def all_offences(self) -> tuple[ChargedOffence, ...]:
        return tuple(o for case in self.cases for o in case.offences)

    @property
    def pending_cases(self) -> tuple[PendingCase, ...]:
        return tuple(c for c in self.cases if c.is_pending)

    @property
    def pending_offences(self) -> tuple[ChargedOffence, ...]:
        """Offences in pending cases only — what gates 0, 1 and 5 compute over (D-072).

        s.479(1) ties the period to an offence under "investigation, inquiry or trial"; a
        concluded case is under none of those. Before D-072 a concluded 20-year case could
        push a pending 7-year offence's qualifying date years out and, sharpest of all,
        suppress the gate-0 cap: a person detained past their pending offence's maximum went
        unflagged because a case that had ENDED raised the cap — the third proviso's absolute
        protection defeated by a larger number that looks conservative (OLQ-11's inversion,
        second mechanism). Under-claiming is the dangerous direction here (D-010).

        Prior-conviction status is deliberately NOT derived from this: gate 4 reads the
        standalone `prior_conviction_status` input, so a concluded conviction still defeats
        first-time status through that input, never through this property.
        """
        return tuple(o for c in self.pending_cases for o in c.offences)

    def inputs_hash(self) -> str:
        """SHA-256 over a canonical rendering of the inputs.

        Built field by field with sorted, explicit ordering rather than hashing `repr`: a
        `frozenset`'s repr order is not stable across runs, so a repr-based hash would change
        for identical inputs and silently break report reproducibility.
        """
        parts: list[str] = [
            f"arrest={self.date_of_arrest.isoformat()}",
            f"evaluated={self.evaluated_on.isoformat()}",
            f"remand={self.date_of_first_remand.isoformat() if self.date_of_first_remand else ''}",
            f"prior={self.prior_conviction_status.value}",
            f"excluded={self.excluded_days}",
            f"scope={self.scope_479_2.value}",
            f"case_list_verified={self.case_list_verified}",
            f"prior_verified={self.prior_conviction_verified}",
            f"law_on={self.law_in_force_on.isoformat() if self.law_in_force_on else ''}",
            "breaks=" + ";".join(sorted(f"{b.start}:{b.end}" for b in self.custody_breaks)),
        ]
        for case in sorted(self.cases, key=lambda c: c.case_ref):
            offences = ";".join(
                sorted(
                    "|".join(
                        (
                            o.offence_id,
                            o.section,
                            _maximum_key(o.maximum),
                            o.special_statute or "",
                            ""
                            if o.special_statute_bar_in_scope is None
                            else str(o.special_statute_bar_in_scope),
                            o.punishment_citation or "",
                        )
                    )
                    for o in case.offences
                )
            )
            parts.append(f"case={case.case_ref}|pending={case.is_pending}|{offences}")
        return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _maximum_key(maximum: MaximumPunishment | None) -> str:
    if maximum is None:
        return "NONE"
    kinds = ",".join(sorted(k.value for k in maximum.kinds))
    return f"{kinds}@{maximum.term_months}"


@dataclass(frozen=True, slots=True)
class GateOutcome:
    """What one gate concluded, and why. Every gate produces one, fired or not.

    Gates that did not fire are recorded too: a report that shows only the gate that stopped the
    case leaves a reader unable to tell a checked condition from an unchecked one.
    """

    gate_id: int
    name: str
    provision: str
    fired: bool
    detail: str
    flags: tuple[Flag, ...] = ()


@dataclass(frozen=True, slots=True)
class OffenceComputation:
    """Per-offence arithmetic, always displayed -- including when a bar fired (D-035)."""

    offence: ChargedOffence
    max_term_months: int | None
    threshold_months: Fraction | None
    qualifying_date: date | None
    crossed: bool
    fraction_applied: Fraction | None
    note: str = ""


@dataclass(frozen=True, slots=True)
class Decision:
    """The engine's output. Carries every field CLAUDE.md §6 requires."""

    verdict: Verdict
    gate_fired: int | None
    flags: tuple[Flag, ...]
    gate_outcomes: tuple[GateOutcome, ...]
    offence_computations: tuple[OffenceComputation, ...]
    custody_days: int
    effective_custody_days: int
    fraction_applied: Fraction | None
    qualifying_date: date | None
    contested_threshold_date: date | None
    """The earliest date on which a charged offence's OWN threshold was crossed, set only
    when CONTESTED_THRESHOLD_BASIS is raised (D-075): the qualifying date the per-offence
    aggregation reading of s.479(1) would give, shown beside the governing-maximum date."""

    statute_version: str
    law_in_force_on: date
    inputs_hash: str
    timestamp: date
    rules_fired: tuple[str, ...]
    reviewed_by: str = field(default="")
    """Empty until a human signs. Never populated by the engine."""

    @property
    def urgent_flags(self) -> tuple[Flag, ...]:
        return tuple(f for f in self.flags if severity_of(f) is Severity.URGENT)

    @property
    def is_entitlement_established(self) -> bool:
        return self.verdict is Verdict.ENTITLEMENT_ESTABLISHED
