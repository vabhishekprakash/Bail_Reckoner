"""Tests for the report stack: language loader, report builder, text renderer (D-068).

Golden files live in `tests/golden/` and are byte-compared. To regenerate after a deliberate
wording or layout change, run pytest with `BR_UPDATE_GOLDENS=1` and review the diff like any
other legal-wording change — the golden diff IS the review artefact.

Fixtures are synthetic and labelled as such; no real accused person's data appears here.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest
import yaml

from bail_reckoner.engine.gates import evaluate
from bail_reckoner.engine.types import (
    CaseInput,
    ChargedOffence,
    Flag,
    PendingCase,
    PriorConvictionStatus,
    Verdict,
)
from bail_reckoner.reporting.language import (
    DEFAULT_LANGUAGE_PATH,
    ReportLanguageError,
    load_report_language,
)
from bail_reckoner.reporting.render_text import render_text
from bail_reckoner.reporting.report import build_report
from bail_reckoner.statutes.decision_table import load_decision_table
from bail_reckoner.statutes.models import MaximumPunishment, PunishmentKind
from bail_reckoner.statutes.sources import source_inventory_line

GOLDEN_DIR = Path(__file__).parent / "golden"

TABLE = load_decision_table()
LANGUAGE = load_report_language()
SOURCES_LINE = source_inventory_line()


def _term(months: int) -> MaximumPunishment:
    return MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=months)


# 9xx synthetic-section convention: a real section may only appear once it comes from a
# verified row. Enforced by test_fixture_conventions.py, not by this comment. (The earlier
# real-section fixtures were checked against the bare acts before conversion: IPC s.304A at
# 24 months was correct; BNS s.303(2) at 84 months was NOT -- the act says three years.)
def _offence(offence_id: str, label: str, section: str, months: int | None) -> ChargedOffence:
    return ChargedOffence(
        offence_id=offence_id,
        label=label,
        section=section,
        maximum=_term(months) if months is not None else None,
    )


def _entitled_case() -> CaseInput:
    """SYNTHETIC. Single case, 7-year maximum, first-time declared, past one-third."""
    return CaseInput(
        date_of_arrest=date(2024, 1, 10),
        evaluated_on=date(2026, 8, 1),
        cases=(
            PendingCase(
                case_ref="FIR 101/2024, PS Test-Town",
                offences=(_offence("SYN-901", "Synthetic offence A", "s.901 (synthetic)", 84),),
            ),
        ),
        prior_conviction_status=PriorConvictionStatus.NONE_DECLARED,
        date_of_first_remand=date(2024, 1, 11),
    )


def _barred_case() -> CaseInput:
    """SYNTHETIC. Two pending cases: the s.479(2) bar fires; thresholds crossed, but
    custody stays below the maxima so gate 0 stays quiet and the golden shows a pure bar."""
    return CaseInput(
        date_of_arrest=date(2024, 8, 10),
        evaluated_on=date(2026, 8, 1),
        cases=(
            PendingCase(
                case_ref="FIR 55/2023, PS Alpha",
                offences=(_offence("SYN-902", "Synthetic offence B", "s.902 (synthetic)", 36),),
            ),
            PendingCase(
                case_ref="FIR 91/2024, PS Beta",
                offences=(_offence("SYN-903", "Synthetic offence C", "s.903 (synthetic)", 36),),
            ),
        ),
        prior_conviction_status=PriorConvictionStatus.UNKNOWN,
    )


def _urgent_case() -> CaseInput:
    """SYNTHETIC. Custody past the 2-year maximum itself: gate 0, DETAINED_BEYOND_MAXIMUM."""
    return CaseInput(
        date_of_arrest=date(2024, 4, 1),
        evaluated_on=date(2026, 8, 1),
        cases=(
            PendingCase(
                case_ref="FIR 7/2024, PS Gamma",
                offences=(_offence("SYN-904", "Synthetic offence D", "s.904 (synthetic)", 24),),
            ),
        ),
        prior_conviction_status=PriorConvictionStatus.UNKNOWN,
    )


def _concluded_case_on_record() -> CaseInput:
    """SYNTHETIC. One pending offence past its one-half threshold, plus a concluded case with
    a larger maximum: the report must show the concluded offence marked as taking no part
    (D-072's inert rendering), and the pending offence's dates must be undisturbed."""
    return CaseInput(
        date_of_arrest=date(2022, 6, 1),
        evaluated_on=date(2026, 8, 1),
        cases=(
            PendingCase(
                case_ref="FIR 12/2022, PS Epsilon",
                offences=(_offence("SYN-905", "Synthetic offence E", "s.905 (synthetic)", 84),),
            ),
            PendingCase(
                case_ref="SC 3/2019, PS Zeta (concluded)",
                offences=(_offence("SYN-906", "Synthetic offence F", "s.906 (synthetic)", 240),),
                is_pending=False,
            ),
        ),
        prior_conviction_status=PriorConvictionStatus.KNOWN_PRIOR,
    )


def _contested_threshold_case() -> CaseInput:
    """SYNTHETIC. Two pending cases, 12- and 120-month maxima, custody 12 months: the lower
    offence's own threshold (6 months) is crossed, the governing threshold (60 months) is
    not — the D-075 band. depends_on_olq: [OLQ-2, OLQ-11]."""
    return CaseInput(
        date_of_arrest=date(2024, 1, 1),
        evaluated_on=date(2025, 1, 1),
        cases=(
            PendingCase(
                case_ref="FIR 21/2024, PS Eta",
                offences=(_offence("SYN-907", "Synthetic offence G", "s.907 (synthetic)", 12),),
            ),
            PendingCase(
                case_ref="FIR 34/2024, PS Theta",
                offences=(_offence("SYN-908", "Synthetic offence H", "s.908 (synthetic)", 120),),
            ),
        ),
        prior_conviction_status=PriorConvictionStatus.KNOWN_PRIOR,
    )


def _render(case: CaseInput) -> str:
    decision = evaluate(case, TABLE)
    report = build_report(case, decision, TABLE, LANGUAGE, SOURCES_LINE)
    return render_text(report)


def _check_golden(name: str, rendered: str) -> None:
    path = GOLDEN_DIR / name
    if os.environ.get("BR_UPDATE_GOLDENS") == "1":
        GOLDEN_DIR.mkdir(exist_ok=True)
        path.write_bytes(rendered.encode("utf-8"))
    expected = path.read_bytes().decode("utf-8")
    assert rendered == expected, f"golden mismatch for {name}; diff the file to review"


class TestLanguageLoader:
    def test_loads_and_covers_every_flag(self) -> None:
        assert set(LANGUAGE.flags) == set(Flag)
        assert set(LANGUAGE.verdicts) == set(Verdict)

    def test_missing_flag_entry_refused(self, tmp_path: Path) -> None:
        data = yaml.safe_load(DEFAULT_LANGUAGE_PATH.read_text(encoding="utf-8"))
        del data["flags"]["CASE_LIST_UNVERIFIED"]
        p = tmp_path / "lang.yaml"
        p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        with pytest.raises(ReportLanguageError, match="CASE_LIST_UNVERIFIED"):
            load_report_language(p)

    def test_unknown_flag_entry_refused(self, tmp_path: Path) -> None:
        data = yaml.safe_load(DEFAULT_LANGUAGE_PATH.read_text(encoding="utf-8"))
        data["flags"]["NOT_A_REAL_FLAG"] = "words for a flag that does not exist"
        p = tmp_path / "lang.yaml"
        p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        with pytest.raises(ReportLanguageError, match="NOT_A_REAL_FLAG"):
            load_report_language(p)

    def test_softened_barred_notice_refused(self, tmp_path: Path) -> None:
        """The mandated sentence is checked verbatim at load; edits cannot soften it."""
        data = yaml.safe_load(DEFAULT_LANGUAGE_PATH.read_text(encoding="utf-8"))
        data["barred_report_notice"] = "Bail is not available."
        p = tmp_path / "lang.yaml"
        p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        with pytest.raises(ReportLanguageError, match="mandated"):
            load_report_language(p)


class TestReportLanguageRules:
    """The D-058 answers, asserted on rendered output."""

    def test_no_internal_gate_vocabulary(self) -> None:
        for case in (_entitled_case(), _barred_case(), _urgent_case()):
            rendered = _render(case)
            lowered = rendered.lower()
            assert "gate" not in lowered
            for flag in Flag:
                assert flag.name not in rendered
            for verdict in Verdict:
                assert verdict.name not in rendered

    def test_barred_report_carries_mandated_sentence(self) -> None:
        rendered = _render(_barred_case())
        # Wrapping is layout; the sentence must survive verbatim in content, so compare on
        # whitespace-normalised text. The loader separately refuses any non-verbatim edit.
        flat = " ".join(rendered.split())
        assert (
            "This is not a finding that bail should be refused. It means the s.479(1) "
            "route is not established on these inputs." in flat
        )

    def test_entitled_report_omits_barred_notice(self) -> None:
        rendered = _render(_entitled_case())
        assert "not a finding that bail should be refused" not in rendered

    def test_status_precedes_legal_basis_precedes_working(self) -> None:
        rendered = _render(_barred_case())
        assert (
            rendered.index("STATUS")
            < rendered.index("LEGAL BASIS")
            < rendered.index("CUSTODY")
            < rendered.index("CASE FIR")
        )

    def test_urgent_box_sits_above_everything_including_status(self) -> None:
        rendered = _render(_urgent_case())
        box_at = rendered.index("MOST URGENT")
        assert box_at < rendered.index("STATUS")
        # Boxed, not merely mentioned: the heading line is inside border characters.
        heading_line = next(line for line in rendered.splitlines() if "MOST URGENT" in line)
        assert heading_line.startswith("| ") and heading_line.endswith(" |")

    def test_cases_considered_names_cases_and_caveat(self) -> None:
        rendered = _render(_barred_case())
        assert "FIR 55/2023, PS Alpha" in rendered
        assert "FIR 91/2024, PS Beta" in rendered
        assert "An undisclosed pending case would change this result." in rendered

    def test_no_ansi_colour_ever(self) -> None:
        for case in (_entitled_case(), _barred_case(), _urgent_case()):
            assert "\x1b[" not in _render(case)

    def test_review_field_present_and_empty(self) -> None:
        rendered = _render(_entitled_case())
        assert "Legally reviewed by: ______________________" in rendered


class TestGoldenFiles:
    def test_entitled(self) -> None:
        _check_golden("report_entitled.txt", _render(_entitled_case()))

    def test_barred_multiple_cases(self) -> None:
        _check_golden("report_barred_479_2.txt", _render(_barred_case()))

    def test_urgent_beyond_maximum(self) -> None:
        _check_golden("report_urgent_cap.txt", _render(_urgent_case()))

    def test_concluded_case_on_record(self) -> None:
        _check_golden("report_concluded_case.txt", _render(_concluded_case_on_record()))

    def test_concluded_offence_rendered_inert(self) -> None:
        """The "listed for the record only" wording is pinned in the golden above; this
        asserts the substance so a wording tweak cannot silently drop it."""
        rendered = _render(_concluded_case_on_record())
        flat = " ".join(rendered.split())
        assert "takes no part in the s.479(1) computation" in flat
        assert "Listed for the record only" in flat
        assert "SC 3/2019, PS Zeta (concluded)" in rendered

    def test_contested_threshold_dual_dates(self) -> None:
        _check_golden("report_contested_threshold.txt", _render(_contested_threshold_case()))

    def test_both_dates_named_with_their_rules(self) -> None:
        """D-075 (Abhishek): the qualifying date is the instruction a jail officer acts on;
        a bare flag would leave them acting on the later date anyway. Both dates must appear
        with the rule that yields each, and the unsettledness stated."""
        flat = " ".join(_render(_contested_threshold_case()).split())
        assert "Two qualifying dates arise" in flat
        assert "the qualifying date is 1 January 2029" in flat
        assert "the earliest threshold was reached on 1 July 2024" in flat
        assert "has not been settled; this report does not choose" in flat

    def test_uniformity_note_stands_on_every_report(self) -> None:
        """L-002, second audit finding: silence implies uniformity, which nothing
        establishes. The note is unconditional — the cases where the engine would be
        confidently wrong are precisely the ones where nothing else fires."""
        for case in (_entitled_case(), _barred_case(), _urgent_case()):
            flat = " ".join(_render(case).split())
            assert "assume national uniformity" in flat
            assert "cannot be detected" in flat

    def test_render_is_deterministic(self) -> None:
        case = _barred_case()
        assert _render(case) == _render(case)
