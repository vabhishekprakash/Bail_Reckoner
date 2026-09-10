"""Build the structured report object (D-068, executing D-058).

One generator, many renderers. Everything a reader will see is resolved *here* — verdict prose,
legal reason, provision quotes, per-offence status lines — from exactly three sources: the
engine's `Decision`, the statutory `DecisionTable`, and the versioned `ReportLanguage`. A
renderer receives finished strings and structure; it chooses layout and nothing else, so no
renderer can introduce words of its own.

Language rules enforced by construction:

* **No internal gate vocabulary.** Nothing in this object exposes "gate 2" or an enum name as
  display text. Machine-readable identifiers are kept (a flag's enum, the provenance hashes)
  but every `*_text` / prose field is reader-facing.
* **Status first, then the legal reason with its provision, then the working** — the field
  order of `Report` is the reading order.
* Every barred report carries the mandated notice verbatim (`ReportLanguage` refuses to load
  without it).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from fractions import Fraction

from bail_reckoner.engine.types import (
    CaseInput,
    Decision,
    Flag,
    OffenceComputation,
    Severity,
    Verdict,
    severity_of,
)
from bail_reckoner.reporting.language import ReportLanguage
from bail_reckoner.statutes.decision_table import DecisionTable, GateKind

__all__ = [
    "Report",
    "UrgentNotice",
    "LegalBasis",
    "CustodySummary",
    "OffenceRow",
    "CaseSection",
    "CasesConsidered",
    "Finding",
    "Provenance",
    "build_report",
]


@dataclass(frozen=True, slots=True)
class UrgentNotice:
    """The boxed block a renderer must place above everything else, emphasised by position
    and wording — never by colour (D-068)."""

    heading: str
    body: str


@dataclass(frozen=True, slots=True)
class LegalBasis:
    """Why the status is what it is: prose first, then the provision it rests on."""

    reason_text: str
    provision_cite: str
    provision_quote: str | None
    """The provision verbatim, from the decision table (gazette-verified). None where the
    basis is judicial gloss (gate 3) or a data gap — nothing is quoted that is not statute."""


@dataclass(frozen=True, slots=True)
class CustodySummary:
    date_of_arrest: date
    date_of_first_remand: date | None
    evaluated_on: date
    custody_days: int
    break_days: int
    excluded_days: int
    effective_custody_days: int


@dataclass(frozen=True, slots=True)
class OffenceRow:
    """One offence's arithmetic, in the fixed report shape (CLAUDE.md §6):
    offence → section → max sentence → custody → fraction served → threshold → status."""

    label: str
    section: str
    max_sentence_text: str
    fraction_text: str | None
    threshold_text: str | None
    qualifying_date: date | None
    status_text: str
    note: str
    punishment_text: str | None = None
    """The punishment provision verbatim, from the inputs (ultimately the verified row's
    quoted_text). Filled by the application builder; the report leaves it None — the report
    renderer does not print it and its goldens are unaffected."""

    punishment_citation: str | None = None


@dataclass(frozen=True, slots=True)
class CaseSection:
    case_ref: str
    is_pending: bool
    offences: tuple[OffenceRow, ...]


@dataclass(frozen=True, slots=True)
class CasesConsidered:
    """Which cases the multiple-case assessment was computed over — stated in the body, with
    the caveat that an undisclosed pending case would change the result (D-068)."""

    intro: str
    case_refs: tuple[str, ...]
    caveat: str


@dataclass(frozen=True, slots=True)
class Finding:
    """One flag, resolved to prose. The enum stays for machine use; a renderer prints prose."""

    flag: Flag
    severity: Severity
    text: str


@dataclass(frozen=True, slots=True)
class Provenance:
    statute_version: str
    language_version: str
    language_hash: str
    law_in_force_on: date
    inputs_hash: str
    computed_on: date
    reviewed_by: str
    sources_line: str
    """One line stating what statutory source material is on record (statutes/sources.py).
    Required, not defaulted: a report that cannot say what its system holds is how material
    already on disk gets re-directed for acquisition."""


@dataclass(frozen=True, slots=True)
class Report:
    """The report, in reading order. Field order is the display order."""

    title: str
    facilitator_line: str
    urgent_notice: UrgentNotice | None
    status_text: str
    barred_notice: str | None
    """The mandated sentence; present on every report whose status is negative, absent
    otherwise."""

    legal_basis: LegalBasis | None
    contested_threshold_text: str | None
    """Both qualifying dates with the aggregation rule that yields each, present only when
    CONTESTED_THRESHOLD_BASIS was raised (D-075): the qualifying date is the instruction a
    jail officer acts on, and a bare flag would leave them acting on the later date anyway."""

    custody: CustodySummary
    case_sections: tuple[CaseSection, ...]
    cases_considered: CasesConsidered
    findings: tuple[Finding, ...]
    footer_review_line: str
    footer_caption: str
    special_statute_set_note: str
    """Standing on every report (Antil acquisition finding, 2026-08-19): the judgment's own
    Category C list is non-exhaustive, so the recorded five-statute set is not a closed
    enumeration and a stringent bar outside it produces no flag. Named rather than implied
    complete — the L-002 pattern; with no advocate available, final behaviour."""

    uniformity_note: str
    """Standing on every report (L-002, second audit finding): the maxima assume national
    uniformity, and a State amendment absent from the stored consolidation cannot be
    detected. Per D-054's refinement — name the gap rather than let silence imply an answer;
    silence here implies uniformity, which nothing establishes."""

    provenance: Provenance

    @property
    def is_entitlement_established(self) -> bool:
        return self.barred_notice is None


_FRACTION_WORDS = {Fraction(1, 2): "one-half", Fraction(1, 3): "one-third"}


def _fraction_text(fraction: Fraction) -> str:
    return _FRACTION_WORDS.get(fraction, str(fraction))


def _term_text(months: int) -> str:
    years, rem = divmod(months, 12)
    parts: list[str] = []
    if years:
        parts.append(f"{years} year" + ("s" if years != 1 else ""))
    if rem:
        parts.append(f"{rem} month" + ("s" if rem != 1 else ""))
    return " ".join(parts) if parts else "0 months"


def _months_text(months: Fraction) -> str:
    if months.denominator == 1:
        return f"{months.numerator} months"
    whole, part = divmod(months.numerator, months.denominator)
    return f"{whole} {part}/{months.denominator} months"


def _date_text(value: date) -> str:
    # %-d / %#d are platform-dependent; strip the leading zero portably so the byte-comparable
    # golden files do not change between Windows and POSIX.
    return f"{value.day} {value.strftime('%B %Y')}"


def _max_sentence_text(comp: OffenceComputation) -> str:
    maximum = comp.offence.maximum
    if maximum is None:
        return "no verified record — not assumed"
    if maximum.excludes_s479:
        kinds = sorted(k.value for k in maximum.kinds)
        base = "death or imprisonment for life" if "DEATH" in kinds else "imprisonment for life"
        if comp.max_term_months is not None:
            return f"{base}, or {_term_text(comp.max_term_months)}"
        return base
    if comp.max_term_months is not None:
        return _term_text(comp.max_term_months)
    return "no definite term prescribed"


def _offence_status_text(
    comp: OffenceComputation,
    verdict: Verdict,
    gate_fired: int | None,
    language: ReportLanguage,
) -> str:
    if comp.qualifying_date is None:
        why = comp.note or "no verified maximum sentence is available for this offence"
        return language.offence_status["not_computable"].format(why=why)
    date_text = _date_text(comp.qualifying_date)
    if not comp.crossed:
        return language.offence_status["not_crossed"].format(date=date_text)
    if verdict is Verdict.ENTITLEMENT_ESTABLISHED:
        return language.offence_status["crossed_entitled"].format(date=date_text)
    return language.offence_status["crossed_not_entitled"].format(
        date=date_text, reason_short=language.reason_short_for(gate_fired)
    )


def _legal_basis(
    decision: Decision, table: DecisionTable, language: ReportLanguage
) -> LegalBasis | None:
    if decision.verdict is Verdict.ENTITLEMENT_ESTABLISHED:
        return None
    reason_text = language.reason_for(decision.gate_fired)
    if decision.gate_fired is None:
        # Data gap, not a statutory bar: there is no provision to cite for missing data.
        return LegalBasis(reason_text=reason_text, provision_cite="", provision_quote=None)
    spec = table.gate(decision.gate_fired)
    quote = spec.text if spec.kind is not GateKind.FLAG else None
    return LegalBasis(reason_text=reason_text, provision_cite=spec.provision, provision_quote=quote)


def build_report(
    case: CaseInput,
    decision: Decision,
    table: DecisionTable,
    language: ReportLanguage,
    sources_line: str,
) -> Report:
    """Resolve a `Decision` into the reader-facing report object.

    Provision: s.479 BNSS 2023 throughout; every quote comes from the decision table, which is
    keyed to the gazette-verified text (D-045), never from this module.
    """
    by_offence = {id(c.offence): c for c in decision.offence_computations}

    sections: list[CaseSection] = []
    for pending_case in case.cases:
        rows: list[OffenceRow] = []
        for offence in pending_case.offences:
            comp = by_offence[id(offence)]
            rows.append(
                OffenceRow(
                    label=offence.label,
                    section=offence.section,
                    max_sentence_text=_max_sentence_text(comp),
                    fraction_text=(
                        _fraction_text(comp.fraction_applied)
                        if comp.fraction_applied is not None
                        else None
                    ),
                    threshold_text=(
                        _months_text(comp.threshold_months)
                        if comp.threshold_months is not None
                        else None
                    ),
                    qualifying_date=comp.qualifying_date,
                    status_text=_offence_status_text(
                        comp, decision.verdict, decision.gate_fired, language
                    ),
                    note=comp.note,
                )
            )
        sections.append(
            CaseSection(
                case_ref=pending_case.case_ref,
                is_pending=pending_case.is_pending,
                offences=tuple(rows),
            )
        )

    findings = tuple(
        Finding(flag=flag, severity=severity_of(flag), text=language.flags[flag])
        for flag in sorted(decision.flags, key=lambda f: (-severity_of(f).value, f.name))
    )

    urgent = (
        UrgentNotice(heading=language.urgent_block_heading, body=language.urgent_block_body)
        if Flag.DETAINED_BEYOND_MAXIMUM in decision.flags
        else None
    )

    barred = (
        language.barred_report_notice
        if decision.verdict is not Verdict.ENTITLEMENT_ESTABLISHED
        else None
    )

    contested_threshold_text = None
    if (
        Flag.CONTESTED_THRESHOLD_BASIS in decision.flags
        and decision.qualifying_date is not None
        and decision.contested_threshold_date is not None
    ):
        contested_threshold_text = language.contested_threshold_line.format(
            governing_date=_date_text(decision.qualifying_date),
            lowest_crossed_date=_date_text(decision.contested_threshold_date),
        )

    return Report(
        title="SECTION 479 BNSS 2023 — ENTITLEMENT COMPUTATION REPORT",
        facilitator_line=language.facilitator_line,
        urgent_notice=urgent,
        status_text=language.verdicts[decision.verdict],
        barred_notice=barred,
        legal_basis=_legal_basis(decision, table, language),
        contested_threshold_text=contested_threshold_text,
        custody=CustodySummary(
            date_of_arrest=case.date_of_arrest,
            date_of_first_remand=case.date_of_first_remand,
            evaluated_on=case.evaluated_on,
            custody_days=decision.custody_days,
            break_days=sum(b.days for b in case.custody_breaks),
            excluded_days=case.excluded_days,
            effective_custody_days=decision.effective_custody_days,
        ),
        case_sections=tuple(sections),
        cases_considered=CasesConsidered(
            intro=language.cases_considered_intro,
            case_refs=tuple(c.case_ref for c in case.pending_cases),
            caveat=language.cases_considered_caveat,
        ),
        findings=findings,
        footer_review_line=language.footer_review_line,
        footer_caption=language.footer_caption,
        special_statute_set_note=language.special_statute_set_note,
        uniformity_note=language.uniformity_note,
        provenance=Provenance(
            statute_version=decision.statute_version,
            language_version=language.language_version,
            language_hash=language.content_hash,
            law_in_force_on=decision.law_in_force_on,
            inputs_hash=decision.inputs_hash,
            computed_on=decision.timestamp,
            reviewed_by=decision.reviewed_by,
            sources_line=sources_line,
        ),
    )
