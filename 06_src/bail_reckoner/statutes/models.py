"""Typed value objects for the statutory-penalty database.

Layer C receives these; it never queries a database itself (D-050, purity contract). Everything
here is stdlib-only and immutable, so a row cannot be mutated after it has been verified.

The central design point is `MaximumPunishment`. A maximum sentence is not an integer:

* murder is punishable with *death or* imprisonment for life,
* some offences are punishable with fine only,
* an attempt under IPC s.511 is punishable by reference to another offence's term,
* and gates 0 and 1 turn on telling these apart rather than on comparing numbers.

Storing "years" as a bare int would force every one of those into a lie. So the maximum is a
tagged union, and `PunishmentKind` is what gate 1 actually reads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from fractions import Fraction

__all__ = [
    "Regime",
    "PunishmentKind",
    "MaximumPunishment",
    "Provenance",
    "RowStatus",
    "OffenceRow",
    "ProvenanceError",
]


class ProvenanceError(ValueError):
    """A row was constructed without the provenance CLAUDE.md §6 requires.

    Raised at construction time, not at query time: an unprovenanced row must never exist as an
    object in the first place, because anything that exists eventually gets read.
    """


class Regime(Enum):
    """Which statute book prescribes the punishment.

    Selection is by **date of offence commission**, not date of arrest or of filing: the new
    codes operate prospectively, so both regimes run in parallel in Indian courts today
    (Extended Abstract §1). `law_in_force_on` on the output object records the date used.
    """

    IPC_1860 = "IPC_1860"
    BNS_2023 = "BNS_2023"

    NDPS_1985 = "NDPS_1985"
    """Narcotic Drugs and Psychotropic Substances Act, 1985 (D-067). Unlike the two penal
    codes, this regime is not selected by date of offence commission — it runs alongside
    whichever code applies — and it has no cross-regime counterpart section. Its rows key
    `variant` on the quantity band (small / lesser-than-commercial / commercial), a case fact
    rather than a sub-section, so an unknown band abstains via OFFENCE_NOT_IN_DATABASE
    exactly like an unnamed limb (D-061)."""


class PunishmentKind(Enum):
    """The shape of the maximum punishment prescribed.

    `DEATH` and `LIFE` are what gate 1 tests: s.479(1) does not apply to an offence "for which
    the punishment of death or life imprisonment has been specified as one of the punishments"
    — *one of*, so an offence punishable with death **or** a term of years is still excluded.

    `TERM` carries a definite maximum and is the only kind gates 0 and 5 can do arithmetic on.
    `FINE_ONLY` prescribes no imprisonment at all. `BY_REFERENCE` covers provisions whose maximum
    is defined in terms of another offence (e.g. IPC s.511 attempts, at one-half of the longest
    term provided for the offence attempted); the engine cannot resolve these unaided and must
    surface them rather than guess.
    """

    DEATH = "DEATH"
    LIFE = "LIFE"
    TERM = "TERM"
    FINE_ONLY = "FINE_ONLY"
    BY_REFERENCE = "BY_REFERENCE"


@dataclass(frozen=True, slots=True)
class MaximumPunishment:
    """The maximum punishment prescribed for an offence, as a tagged union.

    Implements the quantity s.479(1) calls "the maximum period of imprisonment specified for that
    offence under that law", and the death/life exclusion in the same sub-section.

    `kinds` is a set because a single provision commonly prescribes several punishments at once
    (IPC s.302: "death, or imprisonment for life, and shall also be liable to fine"). Gate 1
    fires if DEATH or LIFE is present at all, regardless of what else is.
    """

    kinds: frozenset[PunishmentKind]
    term_months: int | None = None
    """Definite maximum in months. Required iff TERM is among `kinds`; otherwise must be None.

    Months, not years: several provisions prescribe maxima below a year, and month arithmetic is
    exact for the halves and thirds s.479 requires (a 3-year maximum gives 18 and 12 months).
    """

    fine_also: bool = False
    reference_note: str = ""
    """For BY_REFERENCE: the provision's own words describing how its maximum is derived."""

    def __post_init__(self) -> None:
        if not self.kinds:
            raise ValueError("kinds must not be empty")
        has_term = PunishmentKind.TERM in self.kinds
        if has_term and self.term_months is None:
            raise ValueError("term_months is required when kind TERM is present")
        if not has_term and self.term_months is not None:
            raise ValueError("term_months must be None unless kind TERM is present")
        if self.term_months is not None and self.term_months <= 0:
            raise ValueError("term_months must be positive")
        if (PunishmentKind.BY_REFERENCE in self.kinds) and not self.reference_note:
            raise ValueError("BY_REFERENCE requires a reference_note quoting the provision")

    @property
    def excludes_s479(self) -> bool:
        """True iff gate 1 bars s.479(1): death or life is one of the prescribed punishments.

        Provision: s.479(1) main clause, parenthetical exclusion.
        """
        return bool(self.kinds & {PunishmentKind.DEATH, PunishmentKind.LIFE})

    @property
    def is_computable(self) -> bool:
        """True iff gates 0 and 5 can do threshold arithmetic on this maximum.

        False for FINE_ONLY (no imprisonment to halve) and BY_REFERENCE (maximum not resolved
        here). The engine surfaces these; it never substitutes a guess.
        """
        return self.term_months is not None

    def threshold_months(self, fraction: Fraction) -> Fraction:
        """The s.479 threshold at `fraction` of the maximum, exact and unrounded.

        Provision: s.479(1) — one-half; first proviso — one-third.

        Returns an exact Fraction rather than a float or a rounded int: rounding a threshold is
        rounding someone's release date, and the direction of the error is not neutral. The
        caller converts to a date under the conventions in D-047.
        """
        if self.term_months is None:
            raise ValueError("maximum is not a definite term; threshold is not computable")
        return Fraction(self.term_months) * fraction


@dataclass(frozen=True, slots=True)
class Provenance:
    """Where a row's content was read from, and by whom it was checked.

    CLAUDE.md §6: "Every statutory row carries `source`, `verified_against`, `verified_on`. A row
    without provenance does not enter the database." Enforced in `__post_init__` — construction
    fails rather than a later validation pass flagging it.
    """

    source: str
    """The file in 01_law/ the text was read from, by name."""

    verified_against: str
    """Where in that file: page and section, precise enough for a human to re-check."""

    verified_on: date
    verified_by: str
    """Who checked it. Never a model name alone — a person accepts the row (D-046)."""

    quoted_text: str
    """The punishment clause verbatim, so the row can be audited without reopening the PDF."""

    def __post_init__(self) -> None:
        missing = [
            name
            for name in ("source", "verified_against", "verified_by", "quoted_text")
            if not getattr(self, name).strip()
        ]
        if missing:
            raise ProvenanceError(f"provenance fields must be non-empty: {', '.join(missing)}")


class RowStatus(Enum):
    """Whether a row has been checked by a human against the bare act.

    DRAFT rows may be model-generated and may be wrong. They are stored so the work is visible
    and reviewable, and they are **invisible to the engine** — see `OffenceRow.is_engine_visible`.
    Only a human moves a row to VERIFIED (D-046).
    """

    DRAFT = "DRAFT"
    VERIFIED = "VERIFIED"


@dataclass(frozen=True, slots=True)
class OffenceRow:
    """One offence and the maximum sentence prescribed for it under one regime.

    Carries the per-offence facts the gates need that are not derivable from the maximum alone:
    special-statute membership for gate 3, and the IPC<->BNS correspondence for transitional
    cases.
    """

    offence_id: str
    """Stable identifier, `<regime>-<section>`, e.g. `BNS_2023-303(2)`."""

    label: str
    regime: Regime
    section: str
    maximum: MaximumPunishment
    provenance: Provenance
    status: RowStatus = RowStatus.DRAFT

    special_statute: str | None = None
    """Act name if this offence sits under a gate-3 special statute (D-054: *Antil* Category C
    only). None for ordinary IPC/BNS offences."""

    special_statute_provision: str | None = None
    """The barring provision, e.g. `s.37` for NDPS. **Stays None for POCSO** until the bare act
    is read — D-042/OLQ-4 forbid inventing one."""

    compoundable: bool | None = None
    """Nullable, and expected to stay null through the first review pass.

    Compoundability lives in the BNSS compounding table, not in the offence section, so a
    reviewer reading a punishment clause has no basis to answer it. **It feeds no gate**, so a
    null can never affect a verdict — which is what makes deferring it safe rather than merely
    convenient. It is filled in a separate pass with the compounding-table entry quoted
    (D-036 criterion vi). None means not determined; never assume False.
    """

    counterpart_id: str | None = None
    """The corresponding offence in the other regime, if one exists. None is meaningful: BNS
    created offences with no IPC equivalent (e.g. organised crime, snatching)."""

    variant: str | None = None
    """Which punishment limb of the section this row is (D-061). None only for a section with a
    single limb.

    A section is not one maximum: BNS s.316 punishes a plain criminal breach of trust, a carrier,
    a clerk and a public servant differently, and which limb applies is a fact about the charge,
    not the section (L-001). Drafts carry detector-assigned labels (`L1`…`Ln`) that the reviewer
    renames to the statutory limb as printed on the page — `(2)`, `Part II` — so the key is the
    statute's own, not the machine's. At lookup time an unresolved variant on a multi-limb
    section is `OFFENCE_NOT_IN_DATABASE`: the engine never picks a limb for the user.
    """

    min_term_months: int | None = None
    """Mandatory minimum, in months, where the limb prescribes one (D-061).

    Feeds no gate — s.479 speaks only of the maximum — but a report that shows a maximum while
    silently omitting a ten-year floor misleads the reader about what the person faces. None
    means no minimum prescribed or not yet determined; never substitute a value.
    """

    notes: str = field(default="")

    def __post_init__(self) -> None:
        if not self.offence_id.strip() or not self.label.strip() or not self.section.strip():
            raise ValueError("offence_id, label and section must be non-empty")
        expected_prefix = f"{self.regime.value}-"
        if not self.offence_id.startswith(expected_prefix):
            raise ValueError(f"offence_id {self.offence_id!r} must start with {expected_prefix!r}")
        if self.special_statute_provision is not None and self.special_statute is None:
            raise ValueError("special_statute_provision requires special_statute")
        if self.variant is not None:
            if not self.variant.strip():
                raise ValueError("variant, when present, must be non-empty")
            expected_suffix = f"#{self.variant}"
            if not self.offence_id.endswith(expected_suffix):
                raise ValueError(
                    f"offence_id {self.offence_id!r} must end with {expected_suffix!r} — the "
                    f"variant is part of the key so two limbs can never share an identity"
                )
        if self.min_term_months is not None:
            if self.min_term_months <= 0:
                raise ValueError("min_term_months must be positive when present")
            if (
                self.maximum.term_months is not None
                and self.min_term_months > self.maximum.term_months
            ):
                raise ValueError("min_term_months exceeds the maximum term")

    @property
    def is_engine_visible(self) -> bool:
        """True iff Layer C may read this row.

        Only VERIFIED rows. A DRAFT row reaching the engine would mean a model-generated maximum
        sentence silently determining a person's release date.
        """
        return self.status is RowStatus.VERIFIED


_SECTION_RE = re.compile(r"^\d+[A-Z]*(\(\d+[a-z]?\))*$")


def is_wellformed_section(section: str) -> bool:
    """True for section references like `302`, `304A`, `303(2)`, `376(1)`.

    Used by the loader to catch transcription slips; deliberately permissive about the shapes
    Indian statutes actually use rather than enforcing one house style.
    """
    return bool(_SECTION_RE.match(section.strip()))
