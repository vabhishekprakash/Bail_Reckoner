"""Load the versioned report language (D-068, executing D-058).

Report wording is legal wording. By D-055's own test — if answering a legal question would
change it, it is data — the words a reader sees live in `02_data/report_language/`, where a
lawyer can read and diff them, never inside a renderer.

Strictness mirrors `decision_table.py`, and for the same reason: a language file that loads
with a missing flag entry produces a report that silently says nothing about a condition the
engine found. So coverage is enforced **in both directions** — every `Flag` the engine can
raise must have prose, and every prose entry must name a real `Flag`. A new flag cannot ship
without its reader-facing words being written deliberately, and a renamed flag cannot leave
orphaned words behind.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from bail_reckoner.engine.types import Flag, Verdict

__all__ = [
    "ReportLanguage",
    "ReportLanguageError",
    "load_report_language",
    "DEFAULT_LANGUAGE_PATH",
]

DEFAULT_LANGUAGE_PATH = (
    Path(__file__).resolve().parents[3] / "02_data" / "report_language" / "report_language.yaml"
)

# The reasons the engine can attach to a negative verdict: gates 1, 2, 3, 5, plus the
# data-gap path where `Decision.gate_fired` is None (see `gates._decide`). Gates 0 and 4
# never carry the verdict — 0 is a flag above everything, 4 only selects the fraction.
_REASON_KEYS = frozenset({"1", "2", "3", "5", "data_gap"})
_REASON_SHORT_KEYS = frozenset({"1", "2", "3", "data_gap"})
_OFFENCE_STATUS_KEYS = frozenset(
    {"crossed_entitled", "crossed_not_entitled", "not_crossed", "not_computable"}
)

_TOP_KEYS = frozenset(
    {
        "language_version",
        "facilitator_line",
        "verdicts",
        "barred_report_notice",
        "reasons",
        "offence_status",
        "reason_short",
        "contested_threshold_line",
        "uniformity_note",
        "special_statute_set_note",
        "cases_considered_intro",
        "cases_considered_caveat",
        "urgent_block_heading",
        "urgent_block_body",
        "discretionary_caption",
        "flags",
        "footer_review_line",
        "footer_caption",
    }
)

# Mandated on every barred report, verbatim (Abhishek, 2026-08-13). Checked at load so an
# edit to the language file cannot quietly drop or soften the sentence.
_MANDATED_BARRED_NOTICE = (
    "This is not a finding that bail should be refused. It means the s.479(1) route is not "
    "established on these inputs."
)


class ReportLanguageError(ValueError):
    """The report-language file is missing, malformed, or incomplete. Always fatal."""


@dataclass(frozen=True, slots=True)
class ReportLanguage:
    """The loaded language. Immutable; renderers read strings off it and never invent any."""

    language_version: str
    facilitator_line: str
    verdicts: Mapping[Verdict, str]
    barred_report_notice: str
    reasons: Mapping[str, str]
    offence_status: Mapping[str, str]
    reason_short: Mapping[str, str]
    contested_threshold_line: str
    uniformity_note: str
    special_statute_set_note: str
    cases_considered_intro: str
    cases_considered_caveat: str
    urgent_block_heading: str
    urgent_block_body: str
    discretionary_caption: str
    flags: Mapping[Flag, str]
    footer_review_line: str
    footer_caption: str
    content_hash: str
    """SHA-256 of the raw file bytes, stamped on every report so the exact wording a reader
    saw can be re-derived (the D-049 pattern, applied to language)."""

    def reason_for(self, gate_fired: int | None) -> str:
        """The legal reason accompanying a negative verdict. Internal ids never surface."""
        return self.reasons[_reason_key(gate_fired)]

    def reason_short_for(self, gate_fired: int | None) -> str:
        return self.reason_short[_reason_short_key(gate_fired)]


def _reason_key(gate_fired: int | None) -> str:
    return "data_gap" if gate_fired is None else str(gate_fired)


def _reason_short_key(gate_fired: int | None) -> str:
    # Gate 5 never combines with a crossed threshold, so it has no short form.
    if gate_fired == 5:
        raise ReportLanguageError(
            "no short reason exists for gate 5: a not-yet-reached threshold cannot "
            "accompany a crossed one"
        )
    return "data_gap" if gate_fired is None else str(gate_fired)


def _nonempty(where: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportLanguageError(f"{where}: expected a non-empty string, got {value!r}")
    return value.strip()


def _str_map(where: str, value: object, required_keys: frozenset[str]) -> Mapping[str, str]:
    if not isinstance(value, dict):
        raise ReportLanguageError(f"{where}: must be a mapping")
    keys = {str(k) for k in value}
    if unknown := keys - required_keys:
        raise ReportLanguageError(f"{where}: unrecognised key(s) {sorted(unknown)}")
    if missing := required_keys - keys:
        raise ReportLanguageError(f"{where}: missing key(s) {sorted(missing)}")
    return MappingProxyType({str(k): _nonempty(f"{where}.{k}", v) for k, v in value.items()})


def _validated_contested_line(data: dict[str, object]) -> str:
    line = _nonempty("contested_threshold_line", data["contested_threshold_line"])
    for placeholder in ("{governing_date}", "{lowest_crossed_date}"):
        if placeholder not in line:
            raise ReportLanguageError(f"contested_threshold_line: must contain {placeholder}")
    return line


def load_report_language(path: Path | None = None) -> ReportLanguage:
    """Load and validate the report language. Raises `ReportLanguageError` on anything odd."""
    import yaml

    language_path = path or DEFAULT_LANGUAGE_PATH
    try:
        raw_bytes = language_path.read_bytes()
    except OSError as exc:
        raise ReportLanguageError(f"cannot read report language at {language_path}: {exc}") from exc

    try:
        data: Any = yaml.safe_load(raw_bytes.decode("utf-8"))
    except yaml.YAMLError as exc:
        raise ReportLanguageError(f"{language_path}: invalid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ReportLanguageError(f"{language_path}: top level must be a mapping")
    keys = set(data)
    if unknown := keys - _TOP_KEYS:
        raise ReportLanguageError(f"top level: unrecognised key(s) {sorted(unknown)}")
    if missing := _TOP_KEYS - keys:
        raise ReportLanguageError(f"top level: missing key(s) {sorted(missing)}")

    # Verdict coverage, both directions: keyed by enum *name*, not the display value —
    # NO_ENTITLEMENT_IDENTIFIED's enum value embeds an em dash and would make the YAML key
    # depend on typography.
    verdicts_raw = _str_map("verdicts", data["verdicts"], frozenset(v.name for v in Verdict))
    verdicts: Mapping[Verdict, str] = MappingProxyType(
        {Verdict[name]: text for name, text in verdicts_raw.items()}
    )

    # Flag coverage, both directions. This is the check that makes the file a contract.
    flags_raw = _str_map("flags", data["flags"], frozenset(f.name for f in Flag))
    flags: Mapping[Flag, str] = MappingProxyType(
        {Flag[name]: text for name, text in flags_raw.items()}
    )

    barred = _nonempty("barred_report_notice", data["barred_report_notice"])
    if barred != _MANDATED_BARRED_NOTICE:
        raise ReportLanguageError(
            "barred_report_notice differs from the mandated sentence; it must read verbatim: "
            f"{_MANDATED_BARRED_NOTICE!r}"
        )

    offence_status = _str_map("offence_status", data["offence_status"], _OFFENCE_STATUS_KEYS)
    for key, template in offence_status.items():
        if key != "not_computable" and "{date}" not in template:
            raise ReportLanguageError(f"offence_status.{key}: must contain a {{date}} placeholder")
    if "{why}" not in offence_status["not_computable"]:
        raise ReportLanguageError("offence_status.not_computable: must contain {why}")
    if "{reason_short}" not in offence_status["crossed_not_entitled"]:
        raise ReportLanguageError(
            "offence_status.crossed_not_entitled: must contain {reason_short}"
        )

    return ReportLanguage(
        language_version=_nonempty("language_version", data["language_version"]),
        facilitator_line=_nonempty("facilitator_line", data["facilitator_line"]),
        verdicts=verdicts,
        barred_report_notice=barred,
        reasons=_str_map("reasons", data["reasons"], _REASON_KEYS),
        offence_status=offence_status,
        reason_short=_str_map("reason_short", data["reason_short"], _REASON_SHORT_KEYS),
        contested_threshold_line=_validated_contested_line(data),
        uniformity_note=_nonempty("uniformity_note", data["uniformity_note"]),
        special_statute_set_note=_nonempty(
            "special_statute_set_note", data["special_statute_set_note"]
        ),
        cases_considered_intro=_nonempty("cases_considered_intro", data["cases_considered_intro"]),
        cases_considered_caveat=_nonempty(
            "cases_considered_caveat", data["cases_considered_caveat"]
        ),
        urgent_block_heading=_nonempty("urgent_block_heading", data["urgent_block_heading"]),
        urgent_block_body=_nonempty("urgent_block_body", data["urgent_block_body"]),
        discretionary_caption=_nonempty("discretionary_caption", data["discretionary_caption"]),
        flags=flags,
        footer_review_line=_nonempty("footer_review_line", data["footer_review_line"]),
        footer_caption=_nonempty("footer_caption", data["footer_caption"]),
        content_hash=hashlib.sha256(raw_bytes).hexdigest(),
    )
