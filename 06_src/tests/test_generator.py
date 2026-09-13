"""Tests for the fact-pattern generator. SYNTHETIC DATA throughout; fake 9xx sections."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from bail_reckoner.goldenset.generator import (
    OffencePoolEntry,
    generate_fact_patterns,
    write_fact_patterns,
)

POOL = (
    OffencePoolEntry("BNS_2023", "901", None, "Synthetic offence A"),
    OffencePoolEntry("BNS_2023", "902", None, "Synthetic offence B"),
    OffencePoolEntry("BNS_2023", "905", None, "Synthetic offence E"),
)


def _batch(count: int = 60) -> list[dict[str, object]]:
    return generate_fact_patterns(seed=479, count=count, pool=POOL)


class TestDeterminism:
    def test_same_seed_is_byte_identical(self, tmp_path: Path) -> None:
        """A regenerated batch must be identical, or labels silently detach from patterns."""
        first = write_fact_patterns(_batch(), tmp_path / "a.yaml", seed=479)
        second = write_fact_patterns(_batch(), tmp_path / "b.yaml", seed=479)
        assert first.read_bytes() == second.read_bytes()

    def test_a_different_seed_differs(self) -> None:
        assert _batch() != generate_fact_patterns(seed=480, count=60, pool=POOL)


class TestPatternsCarryNoLabels:
    def test_no_expected_values_anywhere(self) -> None:
        """The generator produces inputs only; a generated label would collapse the two
        channels the harness keeps apart."""
        for pattern in _batch():
            assert set(pattern) == {"pattern_id", "inputs"}
            assert "expected" not in pattern

    def test_no_maximum_appears_in_any_pattern(self, tmp_path: Path) -> None:
        """References only — no second copy of the law (D-065)."""
        path = write_fact_patterns(_batch(), tmp_path / "p.yaml", seed=479)
        assert "term_months" not in path.read_text(encoding="utf-8")


class TestInputSpaceCoverage:
    """The generator samples dimensions independently — not per gate (OLQ-11 provenance)."""

    def test_dimensions_vary_across_a_batch(self) -> None:
        batch = _batch()
        inputs = [cast(dict[str, Any], p["inputs"]) for p in batch]
        offence_counts = {
            sum(len(g["offences"]) for g in i["cases"] if g["is_pending"]) for i in inputs
        }
        priors = {i["prior_conviction_status"] for i in inputs}
        assert len(offence_counts) >= 2
        assert len(priors) == 3
        assert any(i["excluded_days"] > 0 for i in inputs)
        assert any(i["custody_breaks"] for i in inputs)
        assert any(i["date_of_first_remand"] for i in inputs)
        assert any(not g["is_pending"] for i in inputs for g in i["cases"])

    def test_dates_are_coherent(self) -> None:
        for pattern in _batch():
            inputs = cast(dict[str, Any], pattern["inputs"])
            arrest = date.fromisoformat(inputs["date_of_arrest"])
            evaluated = date.fromisoformat(inputs["evaluated_on"])
            assert evaluated > arrest
            for custody_break in inputs["custody_breaks"]:
                start = date.fromisoformat(custody_break["start"])
                end = date.fromisoformat(custody_break["end"])
                assert arrest < start <= end

    def test_header_says_unlabelled_and_synthetic(self, tmp_path: Path) -> None:
        path = write_fact_patterns(_batch(10), tmp_path / "p.yaml", seed=479)
        head = path.read_text(encoding="utf-8")[:400].upper()
        assert "UNLABELLED" in head and "SYNTHETIC" in head

    def test_empty_pool_is_refused(self) -> None:
        with pytest.raises(ValueError, match="pool"):
            generate_fact_patterns(seed=1, count=1, pool=())

    def test_written_file_round_trips(self, tmp_path: Path) -> None:
        path = write_fact_patterns(_batch(10), tmp_path / "p.yaml", seed=479)
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert loaded["seed"] == 479
        assert len(loaded["patterns"]) == 10
