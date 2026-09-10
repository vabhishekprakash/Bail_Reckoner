"""Tests for the golden-set harness (D-065).

SYNTHETIC TEST DATA throughout: the smoke cases and fixture rows are invented, say so in their
headers, and pin fake section numbers (9xx). No real accused person's data appears here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bail_reckoner.goldenset.harness import (
    CaseStatus,
    FixtureProvider,
    GoldenCase,
    GoldensetError,
    load_cases,
    load_fixture_provider,
    run_cases,
    write_run_report,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = REPO_ROOT / "03_goldenset" / "cases" / "smoke_batch0.yaml"
FIXTURE_PATH = REPO_ROOT / "03_goldenset" / "fixtures" / "smoke_fixture_rows.yaml"

needs_files = pytest.mark.skipif(
    not (CASES_PATH.exists() and FIXTURE_PATH.exists()),
    reason="03_goldenset smoke files not present in this checkout",
)

pytestmark = needs_files


@pytest.fixture(scope="module")
def smoke() -> tuple[tuple[GoldenCase, ...], FixtureProvider]:
    return load_cases(CASES_PATH), load_fixture_provider(FIXTURE_PATH)


class TestSmokeBatchRunsClean:
    def test_the_smoke_batch_loads(
        self, smoke: tuple[tuple[GoldenCase, ...], FixtureProvider]
    ) -> None:
        cases, _ = smoke
        assert len(cases) == 12  # 10 original + the two OLQ-11 band-edge cases (D-066)
        assert all(case.smoke for case in cases)

    def test_olq_dependent_cases_surface_by_query(
        self, smoke: tuple[tuple[GoldenCase, ...], FixtureProvider]
    ) -> None:
        """Item-3 property: resolving an OLQ must surface every dependent case mechanically. A
        case pinned to current behaviour on an open question is a regression lock, not a check."""
        cases, _ = smoke
        dependent = {c.case_id for c in cases if "OLQ-11" in c.depends_on_olq}
        assert dependent == {
            "SMOKE-05-gate2-bar-does-not-mask-gate0",
            "SMOKE-11-cap-band-lower-edge",
            "SMOKE-12-cap-band-upper-edge",
        }

    def test_every_case_passes_or_abstains_as_designed(
        self, smoke: tuple[tuple[GoldenCase, ...], FixtureProvider]
    ) -> None:
        """The D-065 first-step gate: the harness and the hand-computed expectations agree
        end-to-end before any real labelling opens."""
        cases, provider = smoke
        summary = run_cases(cases, provider)
        failures = {r.case_id: r.mismatches for r in summary.results if r.status is CaseStatus.FAIL}
        assert failures == {}, failures
        stale = [r.case_id for r in summary.results if r.status is CaseStatus.STALE]
        assert stale == []

    def test_the_contested_case_lands_in_the_abstention_row(
        self, smoke: tuple[tuple[GoldenCase, ...], FixtureProvider]
    ) -> None:
        cases, provider = smoke
        summary = run_cases(cases, provider)
        by_id = {r.case_id: r for r in summary.results}
        assert by_id["SMOKE-06-contested-single-fir-multi-section"].status is (
            CaseStatus.ABSTAIN_CONTESTED
        )

    def test_tier_tables_are_separate_and_never_blended(
        self, smoke: tuple[tuple[GoldenCase, ...], FixtureProvider]
    ) -> None:
        cases, provider = smoke
        summary = run_cases(cases, provider)
        assert len(summary.by_tier(1)) + len(summary.by_tier(2)) == len(summary.results)


class TestStale:
    def test_a_changed_row_source_marks_cases_stale_not_failed(
        self, smoke: tuple[tuple[GoldenCase, ...], FixtureProvider]
    ) -> None:
        """The council's drift guard: labels pinned to a superseded version must not be scored."""
        cases, provider = smoke
        provider.version_id = "FIXTURE-smoke-batch0-v2-CHANGED"
        try:
            summary = run_cases(cases, provider)
        finally:
            provider.version_id = "FIXTURE-smoke-batch0-v1"
        assert all(r.status is CaseStatus.STALE for r in summary.results)


class TestLoadTimeRefusals:
    def test_a_third_verdict_state_is_refused_at_load(self, tmp_path: Path) -> None:
        """D-010, enforced before anything runs: the golden set must be structurally incapable
        of expecting an 'ineligible' state."""
        raw = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))
        raw["cases"][0]["expected"]["verdict"] = "INELIGIBLE"
        bad = tmp_path / "bad.yaml"
        bad.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        with pytest.raises(GoldensetError, match="not a permitted state"):
            load_cases(bad)

    def test_an_unknown_case_key_is_refused(self, tmp_path: Path) -> None:
        raw = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))
        raw["cases"][0]["maximum_months"] = 36  # a label trying to embed the law
        bad = tmp_path / "bad.yaml"
        bad.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        with pytest.raises(GoldensetError, match="unrecognised key"):
            load_cases(bad)

    def test_a_fixture_without_a_synthetic_header_is_refused(self, tmp_path: Path) -> None:
        raw = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
        bad = tmp_path / "fixture.yaml"
        bad.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        with pytest.raises(GoldensetError, match="SYNTHETIC"):
            load_fixture_provider(bad)


class TestGuards:
    def test_a_confident_answer_on_a_contested_labelled_case_fails(
        self,
        tmp_path: Path,
        smoke: tuple[tuple[GoldenCase, ...], FixtureProvider],
    ) -> None:
        """The Executor's reverse check: mislabel a plainly uncontested case as contested and
        the harness must FAIL it, not pass it."""
        _, provider = smoke
        raw = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))
        first = raw["cases"][0]  # SMOKE-01: single offence, single case — nothing contested
        first["expected"]["contested"] = True
        bad = tmp_path / "cases.yaml"
        bad.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        summary = run_cases(load_cases(bad), provider)
        result = next(r for r in summary.results if r.case_id == first["case_id"])
        assert result.status is CaseStatus.FAIL
        assert any("answered confidently" in m for m in result.mismatches)

    def test_report_publishes_failures_and_isolates_tiers(
        self,
        tmp_path: Path,
        smoke: tuple[tuple[GoldenCase, ...], FixtureProvider],
    ) -> None:
        cases, provider = smoke
        summary = run_cases(cases, provider)
        report = write_run_report(summary, cases, tmp_path)
        text = report.read_text(encoding="utf-8")
        assert "## Tier 1" in text and "## Tier 2" in text
        assert "## Failures (all published)" in text
        assert "unverified" in text  # the convention-scoped claim wording is present
