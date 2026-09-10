"""Golden-set case loading, execution and scoring (D-065).

Outside Layer C's purity boundary: this module reads files. The engine still receives only typed
values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from bail_reckoner.engine.gates import evaluate
from bail_reckoner.engine.types import (
    CaseInput,
    ChargedOffence,
    CustodyBreak,
    Decision,
    Flag,
    PriorConvictionStatus,
    Scope479_2,
    Verdict,
)
from bail_reckoner.statutes.decision_table import DecisionTable, load_decision_table
from bail_reckoner.statutes.models import MaximumPunishment, PunishmentKind, Regime

__all__ = [
    "GoldensetError",
    "CaseStatus",
    "GoldenCase",
    "CaseResult",
    "RunSummary",
    "FixtureProvider",
    "load_cases",
    "load_fixture_provider",
    "run_cases",
    "write_run_report",
]


class GoldensetError(ValueError):
    """A case or fixture file is malformed, or violates a binding rule (e.g. D-010)."""


class CaseStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    STALE = "STALE"
    """The pinned version no longer matches the row source: expected values must be re-derived
    by hand. Never a silent pass or fail (D-065)."""

    ABSTAIN_CONTESTED = "ABSTAIN_CONTESTED"
    """Correct routing of a contested case. Reported in its own row, never inside accuracy."""


@dataclass(frozen=True, slots=True)
class OffenceRef:
    """A reference to an offence limb. Never carries a maximum — no second copy of the law
    (D-065)."""

    regime: Regime
    section: str
    variant: str | None
    label: str
    special_statute: str | None = None
    in_gate3_set: bool = False


@dataclass(frozen=True, slots=True)
class GoldenCase:
    case_id: str
    tier: int
    smoke: bool
    scope: Scope479_2
    date_of_arrest: date
    evaluated_on: date
    prior: PriorConvictionStatus
    excluded_days: int
    date_of_first_remand: date | None
    custody_breaks: tuple[CustodyBreak, ...]
    case_groups: tuple[tuple[str, bool, tuple[OffenceRef, ...]], ...]
    expected_verdict: Verdict
    expected_gate: int | None
    expected_qualifying_date: date | None
    expected_flags: tuple[Flag, ...]
    expected_contested: bool
    pinned_version: str
    derived_by: str
    depends_on_olq: tuple[str, ...] = ()
    """Open legal questions this case's expected values depend on. A case pinned to current
    behaviour on an open question is a regression lock, not a check — this field exists so
    resolving the question surfaces every dependent case by query rather than by memory."""

    notes: str = ""


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    tier: int
    status: CaseStatus
    mismatches: tuple[str, ...] = ()
    flag_mismatch: tuple[str, ...] = ()
    """Recorded, never headlined: flag vocabulary churns (D-065 column 4)."""


@dataclass(frozen=True, slots=True)
class RunSummary:
    results: tuple[CaseResult, ...]
    provider_version: str

    def by_tier(self, tier: int) -> tuple[CaseResult, ...]:
        return tuple(r for r in self.results if r.tier == tier)

    def counts(self, tier: int) -> dict[str, int]:
        counts = {status.value: 0 for status in CaseStatus}
        for result in self.by_tier(tier):
            counts[result.status.value] += 1
        return counts


class FixtureProvider:
    """Maximum-sentence lookup from a SYNTHETIC fixture file, for smoke runs only.

    The file must declare itself synthetic in its header; this is fixture data standing in for
    the verified penalty database while it has no verified rows, and it must never be mistaken
    for law. `version_id` feeds the STALE check exactly as the real database's content hash will.
    """

    def __init__(
        self, version_id: str, rows: dict[tuple[str, str, str | None], MaximumPunishment]
    ) -> None:
        self.version_id = version_id
        self._rows = rows

    def resolve(
        self, regime: Regime, section: str, variant: str | None
    ) -> MaximumPunishment | None:
        return self._rows.get((regime.value, section, variant))


# ---------------------------------------------------------------------------- loading

_CASE_KEYS = {
    "case_id",
    "tier",
    "smoke",
    "scope_479_2",
    "inputs",
    "expected",
    "derived_against",
    "depends_on_olq",
    "notes",
}
_CASE_REQUIRED = _CASE_KEYS - {"notes", "depends_on_olq"}
_INPUT_KEYS = {
    "date_of_arrest",
    "evaluated_on",
    "date_of_first_remand",
    "prior_conviction_status",
    "excluded_days",
    "custody_breaks",
    "cases",
}
_EXPECTED_KEYS = {"verdict", "gate_fired", "qualifying_date", "flags", "contested"}


def _require(data: dict[str, Any], allowed: set[str], required: set[str], where: str) -> None:
    if unknown := set(data) - allowed:
        raise GoldensetError(f"{where}: unrecognised key(s) {sorted(unknown)}")
    if missing := required - set(data):
        raise GoldensetError(f"{where}: missing key(s) {sorted(missing)}")


def _as_date(value: object, where: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise GoldensetError(f"{where}: not a date: {value!r}")


def load_cases(path: Path) -> tuple[GoldenCase, ...]:
    """Load and validate a case file. D-010 is enforced here, at load time:

    a case whose expected verdict is anything but the two permitted states is refused before
    anything runs — the golden set must be structurally incapable of expecting "ineligible".
    """
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "cases" not in raw:
        raise GoldensetError(f"{path}: top level must be a mapping with 'cases'")
    cases: list[GoldenCase] = []
    for index, entry in enumerate(raw["cases"]):
        where = f"{path.name}[{index}]"
        _require(entry, _CASE_KEYS, _CASE_REQUIRED, where)
        inputs = entry["inputs"]
        _require(inputs, _INPUT_KEYS, _INPUT_KEYS, f"{where}.inputs")
        expected = entry["expected"]
        _require(expected, _EXPECTED_KEYS, _EXPECTED_KEYS, f"{where}.expected")

        verdict_name = expected["verdict"]
        try:
            verdict = Verdict[verdict_name]
        except KeyError as exc:
            raise GoldensetError(
                f"{where}: expected verdict {verdict_name!r} is not a permitted state — "
                f"only {[v.name for v in Verdict]} exist (D-010)"
            ) from exc

        flags = tuple(Flag[name] for name in (expected["flags"] or []))

        groups: list[tuple[str, bool, tuple[OffenceRef, ...]]] = []
        for group in inputs["cases"]:
            refs = tuple(
                OffenceRef(
                    regime=Regime(ref["ref"]["regime"]),
                    section=str(ref["ref"]["section"]),
                    variant=ref["ref"].get("variant"),
                    label=ref["label"],
                    special_statute=ref.get("special_statute"),
                    in_gate3_set=bool(ref.get("in_gate3_set", False)),
                )
                for ref in group["offences"]
            )
            groups.append((group["case_ref"], bool(group.get("is_pending", True)), refs))

        breaks = tuple(
            CustodyBreak(_as_date(b["start"], where), _as_date(b["end"], where))
            for b in (inputs["custody_breaks"] or [])
        )
        qualifying = expected["qualifying_date"]
        pin = entry["derived_against"]
        cases.append(
            GoldenCase(
                case_id=str(entry["case_id"]),
                tier=int(entry["tier"]),
                smoke=bool(entry["smoke"]),
                scope=Scope479_2(entry["scope_479_2"]),
                date_of_arrest=_as_date(inputs["date_of_arrest"], where),
                evaluated_on=_as_date(inputs["evaluated_on"], where),
                prior=PriorConvictionStatus[inputs["prior_conviction_status"]],
                excluded_days=int(inputs["excluded_days"]),
                date_of_first_remand=(
                    _as_date(inputs["date_of_first_remand"], where)
                    if inputs["date_of_first_remand"]
                    else None
                ),
                custody_breaks=breaks,
                case_groups=tuple(groups),
                expected_verdict=verdict,
                expected_gate=expected["gate_fired"],
                expected_qualifying_date=(_as_date(qualifying, where) if qualifying else None),
                expected_flags=flags,
                expected_contested=bool(expected["contested"]),
                pinned_version=str(pin["statute_version"]),
                derived_by=str(pin["derived_by"]),
                depends_on_olq=tuple(str(q) for q in (entry.get("depends_on_olq") or [])),
                notes=str(entry.get("notes", "")),
            )
        )
    return tuple(cases)


def load_fixture_provider(path: Path) -> FixtureProvider:
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    header = path.read_text(encoding="utf-8")[:400].upper()
    if "SYNTHETIC" not in header:
        raise GoldensetError(
            f"{path}: fixture files must declare themselves SYNTHETIC in the header — "
            f"fixture rows standing in for law without saying so is how a fixture becomes law"
        )
    rows: dict[tuple[str, str, str | None], MaximumPunishment] = {}
    for entry in raw["rows"]:
        maximum = MaximumPunishment(
            kinds=frozenset(PunishmentKind[k] for k in entry["kinds"]),
            term_months=entry.get("term_months"),
            fine_also=bool(entry.get("fine_also", False)),
            reference_note=entry.get("reference_note", ""),
        )
        rows[(entry["regime"], str(entry["section"]), entry.get("variant"))] = maximum
    return FixtureProvider(version_id=str(raw["version_id"]), rows=rows)


# ---------------------------------------------------------------------------- running


def run_cases(
    cases: tuple[GoldenCase, ...],
    provider: FixtureProvider,
    table: DecisionTable | None = None,
) -> RunSummary:
    """Run every case and score the three headline columns. STALE is checked first:

    expected values were hand-derived against a pinned row-source version; if the source has
    changed, the labels are bets, and running them as pass/fail would report agreement with a
    superseded world.
    """
    table = table or load_decision_table()
    results: list[CaseResult] = []
    for case in cases:
        if case.pinned_version != provider.version_id:
            results.append(CaseResult(case.case_id, case.tier, CaseStatus.STALE))
            continue
        decision = _evaluate(case, provider, table)

        mismatches: list[str] = []
        if decision.verdict is not case.expected_verdict:
            mismatches.append(
                f"verdict: expected {case.expected_verdict.name}, got {decision.verdict.name}"
            )
        if decision.gate_fired != case.expected_gate:
            mismatches.append(
                f"gate_fired: expected {case.expected_gate}, got {decision.gate_fired}"
            )
        if decision.qualifying_date != case.expected_qualifying_date:
            mismatches.append(
                f"qualifying_date: expected {case.expected_qualifying_date}, "
                f"got {decision.qualifying_date}"
            )

        # Guard: an expected DETAINED_BEYOND_MAXIMUM missing from the output is a failure
        # regardless of anything else — including a contested routing (D-034, council guard).
        if (
            Flag.DETAINED_BEYOND_MAXIMUM in case.expected_flags
            and Flag.DETAINED_BEYOND_MAXIMUM not in decision.flags
        ):
            mismatches.append("guard: expected DETAINED_BEYOND_MAXIMUM is absent (gate-0 mask)")

        actual_contested = Flag.CONTESTED_479_2_SCOPE in decision.flags
        if case.expected_contested and not actual_contested:
            # Guard: a confident answer on a contested-labelled case is a failure, not a pass.
            mismatches.append("guard: case labelled contested but engine answered confidently")

        flag_mismatch = tuple(
            sorted({f.name for f in case.expected_flags} ^ {f.name for f in decision.flags})
        )

        if mismatches:
            status = CaseStatus.FAIL
        elif case.expected_contested and actual_contested:
            status = CaseStatus.ABSTAIN_CONTESTED
        else:
            status = CaseStatus.PASS
        results.append(
            CaseResult(case.case_id, case.tier, status, tuple(mismatches), flag_mismatch)
        )
    return RunSummary(results=tuple(results), provider_version=provider.version_id)


def _evaluate(case: GoldenCase, provider: FixtureProvider, table: DecisionTable) -> Decision:
    from bail_reckoner.engine.types import PendingCase

    groups = []
    for case_ref, pending, refs in case.case_groups:
        offences = tuple(
            ChargedOffence(
                offence_id=(
                    f"{ref.regime.value}-{ref.section}" + (f"#{ref.variant}" if ref.variant else "")
                ),
                label=ref.label,
                section=ref.section,
                maximum=provider.resolve(ref.regime, ref.section, ref.variant),
                special_statute=ref.special_statute,
                special_statute_in_gate3_set=ref.in_gate3_set,
            )
            for ref in refs
        )
        groups.append(PendingCase(case_ref=case_ref, offences=offences, is_pending=pending))
    return evaluate(
        CaseInput(
            date_of_arrest=case.date_of_arrest,
            evaluated_on=case.evaluated_on,
            cases=tuple(groups),
            prior_conviction_status=case.prior,
            date_of_first_remand=case.date_of_first_remand,
            custody_breaks=case.custody_breaks,
            excluded_days=case.excluded_days,
            scope_479_2=case.scope,
        ),
        table,
    )


# ---------------------------------------------------------------------------- reporting


def write_run_report(summary: RunSummary, cases: tuple[GoldenCase, ...], out_dir: Path) -> Path:
    """Publish every failure (M3 gate: "all failures published"). Tier tables are separate and
    never summed into one figure (CLAUDE.md §7)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    by_id = {c.case_id: c for c in cases}
    lines = [
        "# Golden-set run report",
        "",
        "SYNTHETIC CASES. Labels are not advocate-verified. Tier-1 results are correct under",
        "the recorded arithmetic conventions (OLQ-9/OLQ-10), which are themselves unverified",
        "design choices. Tier-2 results are indicative only. No blended figure exists here.",
        "",
        f"Row-source version: `{summary.provider_version}`",
        "",
    ]
    for tier in (1, 2):
        counts = summary.counts(tier)
        lines += [
            f"## Tier {tier}",
            "",
            f"PASS {counts['PASS']} · FAIL {counts['FAIL']} · STALE {counts['STALE']}"
            f" · contested-abstain {counts['ABSTAIN_CONTESTED']}",
            "",
        ]
    failures = [r for r in summary.results if r.status is CaseStatus.FAIL]
    lines.append("## Failures (all published)")
    lines.append("")
    if not failures:
        lines.append("None.")
    for result in failures:
        case = by_id[result.case_id]
        lines += [f"### {result.case_id} (tier {result.tier})", ""]
        lines += [f"- {m}" for m in result.mismatches]
        if case.notes:
            lines.append(f"- notes: {case.notes}")
        lines.append("")
    stale = [r for r in summary.results if r.status is CaseStatus.STALE]
    if stale:
        lines += [
            "## STALE — expected values pinned to a superseded row-source version",
            "",
            "Re-derive by hand; do not re-run as pass/fail.",
            "",
        ]
        lines += [f"- {r.case_id}" for r in stale]
    flagged = [r for r in summary.results if r.flag_mismatch and r.status is CaseStatus.PASS]
    if flagged:
        lines += ["", "## Flag-set differences on passing cases (recorded, not headlined)", ""]
        lines += [f"- {r.case_id}: {', '.join(r.flag_mismatch)}" for r in flagged]
    target = out_dir / "golden_run_report.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target
