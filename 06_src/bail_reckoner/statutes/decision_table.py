"""Load the versioned statutory decision table (D-055).

The table in `02_data/decision_table/` is authoritative for **what the law says**: the fractions,
each provision's verbatim text, per-gate metadata, and the gate-3 statute set. Gate *order and
semantics* are not here — they are typed Python in `bail_reckoner.engine`, because they encode
how the system behaves regardless of what the law says (D-055).

This module sits outside Layer C's purity boundary: it reads a file and depends on PyYAML. The
engine receives already-parsed, typed values, so D-050's contract holds by construction.

**Validation is strict on purpose.** D-055's accepted cost is that a malformed table becomes a
runtime failure where code-as-rules would have given a type error. That trade is only acceptable
if the loader refuses anything it does not fully understand — a table that loads with a silently
missing provision would produce reports citing nothing, which is worse than not starting. So:
unknown keys are errors, missing keys are errors, and no field is silently defaulted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Any

__all__ = [
    "GateKind",
    "GateSpec",
    "StandingNote",
    "SpecialStatute",
    "ProvisionStatus",
    "StatuteMeta",
    "DecisionTable",
    "DecisionTableError",
    "load_decision_table",
    "DEFAULT_TABLE_PATH",
]

DEFAULT_TABLE_PATH = (
    Path(__file__).resolve().parents[3] / "02_data" / "decision_table" / "s479_bnss_2023.yaml"
)


class DecisionTableError(ValueError):
    """The decision table is missing, malformed, or contains something unrecognised.

    Always fatal. There is no partial-load path: an engine running on half a decision table
    would cite provisions it does not have.
    """


class GateKind(Enum):
    """How a fired gate affects the verdict.

    Note what is *not* here: there is no kind meaning "ineligible". D-010 permits exactly two
    verdicts, and everything else is a typed flag (D-048).
    """

    CAP = "CAP"
    """Absolute cap, always computed first and never masked by a later gate (D-034)."""

    BAR = "BAR"
    """Bars s.479(1) on these inputs; routes to human review, still showing the working."""

    FLAG = "FLAG"
    """Raises a flag and routes to human review. Never terminal (D-033)."""

    SELECTOR = "SELECTOR"
    """Selects which fraction applies. Not a bar."""

    TEST = "TEST"
    """The threshold comparison itself."""


@dataclass(frozen=True, slots=True)
class GateSpec:
    """Statutory metadata for one gate. The gate's *behaviour* lives in the engine."""

    id: int
    name: str
    kind: GateKind
    provision: str
    text: str | None
    """The provision verbatim. None only for gate 3, which rests on judicial gloss
    (*Satender Kumar Antil* Category C) rather than on a limb of s.479."""

    flag: str | None = None
    scope_default: str | None = None
    contested_flag: str | None = None
    reaches_bond_route: bool | None = None

    def __post_init__(self) -> None:
        if self.text is not None and not self.text.strip():
            raise DecisionTableError(f"gate {self.id}: text present but empty")


@dataclass(frozen=True, slots=True)
class StandingNote:
    """A provision that is not a gate but must appear in every report (D-040, D-045, s.479(3))."""

    id: str
    provision: str
    text: str


class ProvisionStatus(Enum):
    """What this project knows about a special statute's bail provision.

    Three states, because a boolean conflated two very different situations: "we looked and there
    is no such provision" and "we have not looked yet". POCSO is the first; PMLA, UAPA and the
    Companies Act are the second. Reporting both as `provision_verified: false` would let a
    proven negative decay into an unread gap the moment anyone stopped reading the comments.
    """

    VERIFIED_PRESENT = "VERIFIED_PRESENT"
    """The Act was read and it carries a bail bar. The provision may be named and quoted."""

    VERIFIED_ABSENT = "VERIFIED_ABSENT"
    """The Act was read and carries no such provision. A finding, not a gap."""

    NOT_YET_READ = "NOT_YET_READ"
    """The Act is not yet in 01_law/. Nothing may be asserted about it either way."""


@dataclass(frozen=True, slots=True)
class SpecialStatute:
    """A gate-3 statute and the state of this project's knowledge of its bail provision."""

    act: str
    short: str
    provision: str | None
    provision_status: ProvisionStatus
    provision_text: str | None = None
    """The provision verbatim. Required when VERIFIED_PRESENT, forbidden otherwise.

    Stored because the three verified bars are **structurally different** and a report cannot
    convey that by naming a section alone. NDPS s.37 and PMLA s.45 require a positive finding of
    probable innocence before bail may be granted; UAPA s.43-D(5) inverts it, barring bail where
    the court, on perusal of the case diary or the s.173 report, finds the accusation *prima
    facie true*. A reader told only "s.43-D(5) applies" learns nothing about which test they face.
    """

    scope_note: str | None = None
    """The provision's own scope words, quoted: which offences the bar actually attaches to.

    These bars attach to ENUMERATED offences, not to whole Acts (Abhishek, 2026-08-19; the
    Act-21-of-2015 finding on Companies Act s.212(6) generalises). NDPS s.37(1)(b) reaches
    ss.19/24/27A and commercial-quantity offences only — verified from the stored act, so the
    small and intermediate quantity bands do not engage it. Gate 3 therefore fires on
    offence-in-scope, never on statute-membership alone; POCSO already proved membership and
    bar-engagement separable."""

    currency_note: str | None = None
    """A caveat about the currency of the source the provision was verified against — e.g.
    UAPA's PDF prints no "as on" date, so currency to 2019 is inferred from content. Carried
    on the provision record itself, not only in SOURCES.md, so no consumer of the quoted text
    can see the quote without its caveat."""

    def __post_init__(self) -> None:
        if self.provision_status is ProvisionStatus.VERIFIED_PRESENT:
            if not self.provision:
                raise DecisionTableError(
                    f"{self.short}: VERIFIED_PRESENT requires the provision to be named"
                )
            if not (self.provision_text or "").strip():
                raise DecisionTableError(
                    f"{self.short}: VERIFIED_PRESENT requires the provision text verbatim"
                )
        else:
            if self.provision:
                raise DecisionTableError(
                    f"{self.short}: a provision may only be named when VERIFIED_PRESENT"
                )
            if self.provision_text:
                raise DecisionTableError(
                    f"{self.short}: provision text may only be given when VERIFIED_PRESENT"
                )

    @property
    def is_citable(self) -> bool:
        """True iff a report may name and quote this statute's barring provision (C5)."""
        return self.provision_status is ProvisionStatus.VERIFIED_PRESENT

    def report_line(self) -> str:
        """What a report says about this statute. Differs per state, deliberately.

        Note what none of these do: none suppresses the gate-3 flag. Membership of *Antil*
        Category C is what raises `SPECIAL_STATUTE_TEST_REQUIRED` (D-054), and this project's
        reading of an Act's text does not overrule a Supreme Court categorisation. VERIFIED_ABSENT
        changes what the report *says*, never whether the case reaches a human.
        """
        if self.provision_status is ProvisionStatus.VERIFIED_PRESENT:
            line = f"{self.short} {self.provision} applies; the statutory test must be applied."
            if self.currency_note:
                line += f" Currency caveat: {self.currency_note}"
            return line
        if self.provision_status is ProvisionStatus.VERIFIED_ABSENT:
            # Basis restated 2026-08-19 on reading the Antil judgment itself (D-054
            # correction): secondary sources place POCSO in Category C; the judgment's own
            # list does not name it; the Act carries no twin-condition bar on this
            # project's reading; ss.29-30's presumptions may bear on bail in practice.
            return (
                f"{self.short} is placed in Satender Kumar Antil Category C by secondary "
                f"sources; the judgment's own list does not name it, and this project has "
                f"read the Act and found no twin-condition bail bar in it. Its statutory "
                f"presumptions (ss.29-30) may bear on bail in practice. The case still "
                f"requires human review."
            )
        return (
            f"{self.short} is in Satender Kumar Antil Category C. This project has not yet read "
            f"the Act, so no provision is named and nothing is asserted about its effect."
        )


@dataclass(frozen=True, slots=True)
class StatuteMeta:
    """Identity and provenance of the statute the table encodes."""

    short_name: str
    long_name: str
    act_number: str
    assent_date: date
    section: str
    marginal_note: str
    primary_source: str
    primary_source_locator: str
    crosscheck_source: str
    law_as_on: date
    verified_on: date


@dataclass(frozen=True, slots=True)
class DecisionTable:
    """The loaded table. Immutable; the engine reads values off it and never mutates it."""

    table_version: str
    statute: StatuteMeta
    fraction_standard: Fraction
    fraction_first_time_offender: Fraction
    gates: tuple[GateSpec, ...]
    standing_notes: tuple[StandingNote, ...]
    special_statutes: tuple[SpecialStatute, ...]
    content_hash: str
    """SHA-256 of the raw file bytes. Feeds `statute_version` (D-049) so a report can be
    re-derived against exactly this text."""

    def gate(self, gate_id: int) -> GateSpec:
        for spec in self.gates:
            if spec.id == gate_id:
                return spec
        raise DecisionTableError(f"no gate with id {gate_id}")

    def standing_note(self, note_id: str) -> StandingNote:
        for note in self.standing_notes:
            if note.id == note_id:
                return note
        raise DecisionTableError(f"no standing note with id {note_id!r}")


# Every key the loader understands. Anything else in the file is an error rather than ignored:
# a typo'd key that is silently dropped is a provision quietly missing from every report.
_TOP_KEYS = {"table_version", "statute", "fractions", "gates", "standing_notes", "special_statutes"}
_STATUTE_KEYS = {
    "short_name",
    "long_name",
    "act_number",
    "assent_date",
    "section",
    "marginal_note",
    "primary_source",
    "primary_source_locator",
    "crosscheck_source",
    "law_as_on",
    "verified_on",
}
_GATE_KEYS = {
    "id",
    "name",
    "kind",
    "provision",
    "text",
    "flag",
    "scope_default",
    "contested_flag",
    "reaches_bond_route",
}
_GATE_REQUIRED = {"id", "name", "kind", "provision", "text"}
_NOTE_KEYS = {"id", "provision", "text"}
_STATUTE_SET_KEYS = {
    "act",
    "short",
    "provision",
    "provision_status",
    "provision_text",
    "scope_note",
    "currency_note",
}
# provision_text is optional: it is required only for VERIFIED_PRESENT, which SpecialStatute
# enforces after parsing. Requiring it here would force unread statutes to carry an empty field.
_STATUTE_SET_REQUIRED = {"act", "short", "provision", "provision_status"}

_REQUIRED_GATE_IDS = frozenset({0, 1, 2, 3, 4, 5})
_REQUIRED_NOTE_IDS = frozenset(
    {"second_proviso", "explanation", "superintendent_duty", "section_479_1_full"}
)


def _check_keys(where: str, got: dict[str, Any], allowed: set[str], required: set[str]) -> None:
    if unknown := set(got) - allowed:
        raise DecisionTableError(f"{where}: unrecognised key(s) {sorted(unknown)}")
    if missing := required - set(got):
        raise DecisionTableError(f"{where}: missing required key(s) {sorted(missing)}")


def _as_date(where: str, value: object) -> date:
    """Accept either a YAML-native date or an ISO-8601 string.

    YAML types `2023-12-25` as a date but `"2023-12-25"` as a string, so whether a date arrives
    typed depends entirely on whether the author happened to quote it. Depending on quoting style
    would make the table brittle in a way no reviewer would spot in a diff. Both forms are
    accepted; anything else still fails loudly.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError as exc:
            raise DecisionTableError(f"{where}: not an ISO-8601 date: {value!r}") from exc
    raise DecisionTableError(f"{where}: expected a date, got {value!r}")


def _as_fraction(where: str, value: object) -> Fraction:
    """Parse an exact rational like "1/2". Floats are refused deliberately.

    A float fraction would reintroduce the rounding this project takes care to avoid, and it
    would do so invisibly.
    """
    if not isinstance(value, str):
        raise DecisionTableError(f"{where}: fraction must be a string like '1/2', got {value!r}")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise DecisionTableError(f"{where}: not a valid fraction: {value!r}") from exc


def _nonempty_str(where: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DecisionTableError(f"{where}: expected a non-empty string, got {value!r}")
    return value.strip()


def load_decision_table(path: Path | None = None) -> DecisionTable:
    """Load and validate the decision table. Raises `DecisionTableError` on anything unexpected.

    Provision: the table encodes s.479 BNSS 2023 as verified against the gazette
    (`01_law/Section_479_BNSS_2023.md`).
    """
    import hashlib

    import yaml

    table_path = path or DEFAULT_TABLE_PATH
    try:
        raw_bytes = table_path.read_bytes()
    except OSError as exc:
        raise DecisionTableError(f"cannot read decision table at {table_path}: {exc}") from exc

    try:
        data = yaml.safe_load(raw_bytes.decode("utf-8"))
    except yaml.YAMLError as exc:
        raise DecisionTableError(f"{table_path}: invalid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise DecisionTableError(f"{table_path}: top level must be a mapping")
    _check_keys("top level", data, _TOP_KEYS, _TOP_KEYS)

    statute_raw = data["statute"]
    if not isinstance(statute_raw, dict):
        raise DecisionTableError("statute: must be a mapping")
    _check_keys("statute", statute_raw, _STATUTE_KEYS, _STATUTE_KEYS)
    statute = StatuteMeta(
        short_name=_nonempty_str("statute.short_name", statute_raw["short_name"]),
        long_name=_nonempty_str("statute.long_name", statute_raw["long_name"]),
        act_number=_nonempty_str("statute.act_number", statute_raw["act_number"]),
        assent_date=_as_date("statute.assent_date", statute_raw["assent_date"]),
        section=_nonempty_str("statute.section", statute_raw["section"]),
        marginal_note=_nonempty_str("statute.marginal_note", statute_raw["marginal_note"]),
        primary_source=_nonempty_str("statute.primary_source", statute_raw["primary_source"]),
        primary_source_locator=_nonempty_str(
            "statute.primary_source_locator", statute_raw["primary_source_locator"]
        ),
        crosscheck_source=_nonempty_str(
            "statute.crosscheck_source", statute_raw["crosscheck_source"]
        ),
        law_as_on=_as_date("statute.law_as_on", statute_raw["law_as_on"]),
        verified_on=_as_date("statute.verified_on", statute_raw["verified_on"]),
    )

    fractions_raw = data["fractions"]
    if not isinstance(fractions_raw, dict):
        raise DecisionTableError("fractions: must be a mapping")
    _check_keys(
        "fractions",
        fractions_raw,
        {"standard", "first_time_offender"},
        {"standard", "first_time_offender"},
    )

    gates = tuple(_parse_gate(entry, index) for index, entry in enumerate(_as_list(data, "gates")))
    if {gate.id for gate in gates} != _REQUIRED_GATE_IDS:
        raise DecisionTableError(
            f"gates: expected exactly ids {sorted(_REQUIRED_GATE_IDS)}, "
            f"got {sorted(g.id for g in gates)}"
        )

    notes = tuple(
        _parse_note(entry, index) for index, entry in enumerate(_as_list(data, "standing_notes"))
    )
    if missing_notes := _REQUIRED_NOTE_IDS - {note.id for note in notes}:
        raise DecisionTableError(f"standing_notes: missing required {sorted(missing_notes)}")

    statutes = tuple(
        _parse_special_statute(entry, index)
        for index, entry in enumerate(_as_list(data, "special_statutes"))
    )

    return DecisionTable(
        table_version=_nonempty_str("table_version", data["table_version"]),
        statute=statute,
        fraction_standard=_as_fraction("fractions.standard", fractions_raw["standard"]),
        fraction_first_time_offender=_as_fraction(
            "fractions.first_time_offender", fractions_raw["first_time_offender"]
        ),
        gates=gates,
        standing_notes=notes,
        special_statutes=statutes,
        content_hash=hashlib.sha256(raw_bytes).hexdigest(),
    )


def _as_list(data: dict[str, Any], key: str) -> list[Any]:
    value = data[key]
    if not isinstance(value, list) or not value:
        raise DecisionTableError(f"{key}: must be a non-empty list")
    return value


def _parse_gate(entry: object, index: int) -> GateSpec:
    where = f"gates[{index}]"
    if not isinstance(entry, dict):
        raise DecisionTableError(f"{where}: must be a mapping")
    _check_keys(where, entry, _GATE_KEYS, _GATE_REQUIRED)
    if not isinstance(entry["id"], int):
        raise DecisionTableError(f"{where}.id: must be an integer")
    try:
        kind = GateKind(entry["kind"])
    except ValueError as exc:
        raise DecisionTableError(
            f"{where}.kind: {entry['kind']!r} is not one of {[k.value for k in GateKind]}"
        ) from exc
    text = entry["text"]
    if text is not None and not isinstance(text, str):
        raise DecisionTableError(f"{where}.text: must be a string or null")
    return GateSpec(
        id=entry["id"],
        name=_nonempty_str(f"{where}.name", entry["name"]),
        kind=kind,
        provision=_nonempty_str(f"{where}.provision", entry["provision"]),
        text=text.strip() if isinstance(text, str) else None,
        flag=entry.get("flag"),
        scope_default=entry.get("scope_default"),
        contested_flag=entry.get("contested_flag"),
        reaches_bond_route=entry.get("reaches_bond_route"),
    )


def _parse_note(entry: object, index: int) -> StandingNote:
    where = f"standing_notes[{index}]"
    if not isinstance(entry, dict):
        raise DecisionTableError(f"{where}: must be a mapping")
    _check_keys(where, entry, _NOTE_KEYS, _NOTE_KEYS)
    return StandingNote(
        id=_nonempty_str(f"{where}.id", entry["id"]),
        provision=_nonempty_str(f"{where}.provision", entry["provision"]),
        text=_nonempty_str(f"{where}.text", entry["text"]),
    )


def _parse_special_statute(entry: object, index: int) -> SpecialStatute:
    where = f"special_statutes[{index}]"
    if not isinstance(entry, dict):
        raise DecisionTableError(f"{where}: must be a mapping")
    _check_keys(where, entry, _STATUTE_SET_KEYS, _STATUTE_SET_REQUIRED)
    provision = entry["provision"]
    if provision is not None and not isinstance(provision, str):
        raise DecisionTableError(f"{where}.provision: must be a string or null")
    try:
        status = ProvisionStatus(entry["provision_status"])
    except ValueError as exc:
        raise DecisionTableError(
            f"{where}.provision_status: {entry['provision_status']!r} is not one of "
            f"{[s.value for s in ProvisionStatus]}"
        ) from exc
    text = entry.get("provision_text")
    if text is not None and not isinstance(text, str):
        raise DecisionTableError(f"{where}.provision_text: must be a string or null")
    currency = entry.get("currency_note")
    if currency is not None and not isinstance(currency, str):
        raise DecisionTableError(f"{where}.currency_note: must be a string or null")
    scope = entry.get("scope_note")
    if scope is not None and not isinstance(scope, str):
        raise DecisionTableError(f"{where}.scope_note: must be a string or null")
    return SpecialStatute(
        act=_nonempty_str(f"{where}.act", entry["act"]),
        short=_nonempty_str(f"{where}.short", entry["short"]),
        provision=provision,
        provision_status=status,
        provision_text=text.strip() if isinstance(text, str) else None,
        scope_note=scope.strip() if isinstance(scope, str) else None,
        currency_note=currency.strip() if isinstance(currency, str) else None,
    )
