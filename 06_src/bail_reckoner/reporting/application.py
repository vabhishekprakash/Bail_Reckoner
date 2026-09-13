"""The s.479(3) application generator (D-071, executing D-058).

Provision: s.479(3) BNSS 2023 — "The Superintendent of jail ... shall forthwith make an
application in writing to the Court to proceed under sub-section (1) for the release of such
person on bail." The verbatim text is quoted from the verified decision table
(`standing_notes.superintendent_duty`), never from a language file: statutory text in a court
filing carries a `statute_version`; the project's own prose carries the application language
file's hash instead, and the two provenance chains must not mix.

**Four hard refusal conditions, all required before anything is generated:**

1. the verdict is `ENTITLEMENT_ESTABLISHED`;
2. `CASE_LIST_UNVERIFIED` is cleared — the filing asserts the case list's completeness;
3. no `CONTESTED_*` flag is raised — a filing cannot rest on a reading this project has
   declined to choose (checked by name prefix, so any future contested flag blocks
   automatically: over-blocking is the safe direction);
4. where the one-third route is in use, the prior-conviction status is verified — that route
   asserts to a court that the person has never been convicted.

A failed condition produces an `ApplicationRefusal` stating, in reader-facing language, every
condition that failed. There is no silent empty output: that would repeat the
not-found-versus-not-present defect (D-070's failure shape).

**What is filled and what is blank:** the generator fills only what it computed and can cite —
dates, day counts, thresholds, offences, maxima. Court identity, case numbers, the person's
name, the jail, officer name and designation, and the date of signature are blanks for the
officer. Pre-asserting facts on a public officer's behalf is the filled-in-reviewer-field
failure in a more consequential place.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType
from typing import Any

from bail_reckoner.engine.types import CaseInput, Decision, Flag, Verdict
from bail_reckoner.reporting.report import (
    CaseSection,
    CustodySummary,
    OffenceRow,
    Provenance,
    _date_text,
    _fraction_text,
    _max_sentence_text,
    _months_text,
)
from bail_reckoner.statutes.decision_table import DecisionTable

__all__ = [
    "ApplicationLanguage",
    "ApplicationLanguageError",
    "load_application_language",
    "DEFAULT_APPLICATION_LANGUAGE_PATH",
    "Application",
    "ApplicationRefusal",
    "RefusalReason",
    "StatutoryBasis",
    "build_application",
]

DEFAULT_APPLICATION_LANGUAGE_PATH = (
    Path(__file__).resolve().parents[3]
    / "02_data"
    / "report_language"
    / "s479_3_application_language.yaml"
)

_TOP_KEYS = frozenset(
    {
        "language_version",
        "title",
        "draft_notice",
        "opening",
        "body",
        "route",
        "prayer",
        "refusals",
        "blanks",
        "uniformity_note",
        "special_statute_set_note",
        "review_line",
        "footer_caption",
    }
)
_BODY_KEYS = frozenset({"detention", "no_exclusion", "threshold", "cases"})
_ROUTE_KEYS = frozenset({"standard", "first_time"})
_REFUSAL_KEYS = frozenset(
    {"not_established", "case_list_unverified", "contested", "prior_unverified"}
)
_BLANK_KEYS = frozenset(
    {
        "court",
        "case_number",
        "person",
        "jail",
        "place",
        "signature_date",
        "signature",
        "officer_name",
        "designation",
    }
)


class ApplicationLanguageError(ValueError):
    """The application-language file is missing, malformed, or incomplete. Always fatal."""


@dataclass(frozen=True, slots=True)
class ApplicationLanguage:
    """The loaded filing prose. Immutable; the generator fills placeholders, never words."""

    language_version: str
    title: str
    draft_notice: str
    opening: str
    body: Mapping[str, str]
    route: Mapping[str, str]
    prayer: str
    refusals: Mapping[str, str]
    blanks: Mapping[str, str]
    uniformity_note: str
    special_statute_set_note: str
    review_line: str
    footer_caption: str
    content_hash: str


def _nonempty(where: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApplicationLanguageError(f"{where}: expected a non-empty string, got {value!r}")
    return value.strip()


def _str_map(where: str, value: object, required: frozenset[str]) -> Mapping[str, str]:
    if not isinstance(value, dict):
        raise ApplicationLanguageError(f"{where}: must be a mapping")
    keys = {str(k) for k in value}
    if unknown := keys - required:
        raise ApplicationLanguageError(f"{where}: unrecognised key(s) {sorted(unknown)}")
    if missing := required - keys:
        raise ApplicationLanguageError(f"{where}: missing key(s) {sorted(missing)}")
    return MappingProxyType({str(k): _nonempty(f"{where}.{k}", v) for k, v in value.items()})


def load_application_language(path: Path | None = None) -> ApplicationLanguage:
    """Load and validate the application language. Strict, like every loader here: a filing
    with a silently missing paragraph is worse than no filing."""
    import yaml

    language_path = path or DEFAULT_APPLICATION_LANGUAGE_PATH
    try:
        raw_bytes = language_path.read_bytes()
    except OSError as exc:
        raise ApplicationLanguageError(
            f"cannot read application language at {language_path}: {exc}"
        ) from exc
    try:
        data: Any = yaml.safe_load(raw_bytes.decode("utf-8"))
    except yaml.YAMLError as exc:
        raise ApplicationLanguageError(f"{language_path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ApplicationLanguageError(f"{language_path}: top level must be a mapping")
    keys = set(data)
    if unknown := keys - _TOP_KEYS:
        raise ApplicationLanguageError(f"top level: unrecognised key(s) {sorted(unknown)}")
    if missing := _TOP_KEYS - keys:
        raise ApplicationLanguageError(f"top level: missing key(s) {sorted(missing)}")

    body = _str_map("body", data["body"], _BODY_KEYS)
    for key, placeholders in (
        ("detention", ("{arrest_date}", "{evaluated_on}", "{custody_days}")),
        ("threshold", ("{threshold_date}", "{fraction_word}")),
    ):
        for placeholder in placeholders:
            if placeholder not in body[key]:
                raise ApplicationLanguageError(f"body.{key}: must contain {placeholder}")

    return ApplicationLanguage(
        language_version=_nonempty("language_version", data["language_version"]),
        title=_nonempty("title", data["title"]),
        draft_notice=_nonempty("draft_notice", data["draft_notice"]),
        opening=_nonempty("opening", data["opening"]),
        body=body,
        route=_str_map("route", data["route"], _ROUTE_KEYS),
        prayer=_nonempty("prayer", data["prayer"]),
        refusals=_str_map("refusals", data["refusals"], _REFUSAL_KEYS),
        blanks=_str_map("blanks", data["blanks"], _BLANK_KEYS),
        uniformity_note=_nonempty("uniformity_note", data["uniformity_note"]),
        special_statute_set_note=_nonempty(
            "special_statute_set_note", data["special_statute_set_note"]
        ),
        review_line=_nonempty("review_line", data["review_line"]),
        footer_caption=_nonempty("footer_caption", data["footer_caption"]),
        content_hash=hashlib.sha256(raw_bytes).hexdigest(),
    )


@dataclass(frozen=True, slots=True)
class RefusalReason:
    """One failed condition: a machine-readable id and the reader-facing sentence."""

    condition: str
    text: str


@dataclass(frozen=True, slots=True)
class ApplicationRefusal:
    """Why no application was generated. Every failed condition is stated, not just the first.

    This object is the anti-silence guarantee: a caller cannot receive an empty filing, only
    either an `Application` or this, with reasons a reader can act on.
    """

    reasons: tuple[RefusalReason, ...]

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError("a refusal must state at least one reason")


@dataclass(frozen=True, slots=True)
class StatutoryBasis:
    """One provision the filing rests on: citation plus the verbatim table text."""

    cite: str
    quote: str


@dataclass(frozen=True, slots=True)
class Application:
    """The s.479(3) application, structured, in filing order. Renderers lay it out only."""

    title: str
    draft_notice: str
    blanks: Mapping[str, str]
    """Label text for every field left blank for the officer, keyed by field id."""

    opening_text: str
    paragraphs: tuple[str, ...]
    """Numbered body paragraphs, fully resolved: detention, threshold, route, cases intro."""

    case_sections: tuple[CaseSection, ...]
    custody: CustodySummary
    statutory_basis: tuple[StatutoryBasis, ...]
    special_statute_set_note: str
    """The Antil non-exhaustiveness line, officer-facing (the L-002 pattern): a stringent
    bar outside the recorded set cannot be detected, and the applicant confirms none
    applies before filing."""

    uniformity_note: str
    """Officer-facing qualification on the maxima asserted above, rendered inside the
    statutory basis section immediately after the provision quotes — a qualification on a
    substantive assertion belongs where the assertion is, not in the metadata footer
    (L-002 finding 2; Abhishek, 2026-08-19)."""

    prayer_text: str
    review_line: str
    footer_caption: str
    provenance: Provenance


_CONTESTED_PREFIX = "CONTESTED_"
_ONE_THIRD = Fraction(1, 3)


def _refusals(
    case: CaseInput, decision: Decision, language: ApplicationLanguage
) -> tuple[RefusalReason, ...]:
    reasons: list[RefusalReason] = []
    if decision.verdict is not Verdict.ENTITLEMENT_ESTABLISHED:
        reasons.append(RefusalReason("not_established", language.refusals["not_established"]))
    if Flag.CASE_LIST_UNVERIFIED in decision.flags:
        reasons.append(
            RefusalReason("case_list_unverified", language.refusals["case_list_unverified"])
        )
    if any(flag.name.startswith(_CONTESTED_PREFIX) for flag in decision.flags):
        reasons.append(RefusalReason("contested", language.refusals["contested"]))
    if decision.fraction_applied == _ONE_THIRD and not case.prior_conviction_verified:
        reasons.append(RefusalReason("prior_unverified", language.refusals["prior_unverified"]))
    return tuple(reasons)


def build_application(
    case: CaseInput,
    decision: Decision,
    table: DecisionTable,
    language: ApplicationLanguage,
    sources_line: str,
) -> Application | ApplicationRefusal:
    """Generate the s.479(3) application, or refuse with every failed condition named.

    Provision: s.479(3) BNSS 2023; the quoted texts come from the verified decision table.
    """
    refusals = _refusals(case, decision, language)
    if refusals:
        return ApplicationRefusal(reasons=refusals)

    if decision.qualifying_date is None or decision.fraction_applied is None:
        # Unreachable when the verdict is ENTITLEMENT_ESTABLISHED, but stated rather than
        # assumed: an application must never be built around a missing date (D-064's shape).
        return ApplicationRefusal(
            reasons=(RefusalReason("not_established", language.refusals["not_established"]),)
        )

    fraction_word = _fraction_text(decision.fraction_applied)
    route_key = "first_time" if decision.fraction_applied == _ONE_THIRD else "standard"

    paragraphs = (
        language.body["detention"].format(
            arrest_date=_date_text(case.date_of_arrest),
            evaluated_on=_date_text(case.evaluated_on),
            custody_days=decision.custody_days,
            effective_custody_days=decision.effective_custody_days,
        ),
        # The gate-1 finding, stated rather than left for the court to check unaided: the
        # parenthetical exclusion is an operative precondition of sub-section (1), and it is
        # quoted in full below. True by construction here: a death/life offence bars the
        # verdict, and no application generates without ENTITLEMENT_ESTABLISHED.
        language.body["no_exclusion"],
        language.route[route_key],
        language.body["threshold"].format(
            threshold_date=_date_text(decision.qualifying_date),
            fraction_word=fraction_word,
        ),
        language.body["cases"],
    )

    by_offence = {id(c.offence): c for c in decision.offence_computations}
    sections: list[CaseSection] = []
    # Pending cases only (D-072 follow-up): the filing invokes s.479(1) for offences under
    # investigation, inquiry or trial, and paragraph 2's death/life statement is scoped to
    # "the case(s) listed" — so the listing must contain exactly the offences the statement
    # and the arithmetic cover. Concluded cases appear in the eligibility report, not here.
    for pending_case in case.pending_cases:
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
                    status_text=(
                        f"completed on {_date_text(comp.qualifying_date)}"
                        if comp.qualifying_date is not None
                        else "not computable"
                    ),
                    note=comp.note,
                    punishment_text=offence.punishment_text,
                    punishment_citation=offence.punishment_citation,
                )
            )
        sections.append(
            CaseSection(
                case_ref=pending_case.case_ref,
                is_pending=pending_case.is_pending,
                offences=tuple(rows),
            )
        )

    superintendent = table.standing_note("superintendent_duty")
    # The FULL sub-section — main clause with its parenthetical exclusion, all three provisos
    # and the Explanation — not the gate-5 operative fragment: a filing must quote the whole
    # provision it invokes, including the exclusion gate 1 checks and the first proviso the
    # one-third route relies on. The text lives in the versioned table (never read from
    # 01_law/ at render time) so statute_version covers the exact words quoted, and a
    # transcription test byte-compares it against the canonical gazette file.
    full_479_1 = table.standing_note("section_479_1_full")
    basis = (
        StatutoryBasis(cite=superintendent.provision, quote=superintendent.text),
        StatutoryBasis(cite=full_479_1.provision, quote=full_479_1.text),
    )

    return Application(
        title=language.title,
        draft_notice=language.draft_notice,
        blanks=language.blanks,
        opening_text=language.opening,
        paragraphs=paragraphs,
        case_sections=tuple(sections),
        custody=CustodySummary(
            date_of_arrest=case.date_of_arrest,
            date_of_first_remand=case.date_of_first_remand,
            evaluated_on=case.evaluated_on,
            custody_days=decision.custody_days,
            break_days=sum(b.days for b in case.custody_breaks),
            excluded_days=case.excluded_days,
            effective_custody_days=decision.effective_custody_days,
        ),
        statutory_basis=basis,
        special_statute_set_note=language.special_statute_set_note,
        uniformity_note=language.uniformity_note,
        prayer_text=language.prayer,
        review_line=language.review_line,
        footer_caption=language.footer_caption,
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
