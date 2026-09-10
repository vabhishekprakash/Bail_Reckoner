"""Enforce the synthetic-fixture convention (Abhishek, 2026-08-19).

The rule: **a real statutory section may only appear in a test fixture or golden file once it
comes from a verified row.** No verified rows exist yet, so today every section a fixture
cites must be synthetic — the 9xx convention, labelled as such. A convention recorded in a
comment fails the same way the vocabulary list did (D-070); this module is the enforcement.

When verified rows exist, the allowance widens: a section is then also acceptable if it is
resolved from a verified row at fixture-build time. Extend `_is_allowed_section` at that
point — deliberately, with the row's provenance — rather than weakening the pattern.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_TESTS_DIR = Path(__file__).parent
_GOLDEN_DIR = _TESTS_DIR / "golden"
_GOLDENSET_FIXTURES = _TESTS_DIR.parents[1] / "03_goldenset" / "fixtures"

# A synthetic section: 9xx, optionally with a sub-section, and labelled "(synthetic)" where
# it appears as display text. Examples: "901", "s.901 (synthetic)", "s.905 (synthetic)".
_SYNTHETIC_DISPLAY = re.compile(r"^s\.9\d\d\S*\s+\(synthetic\)$")
_SYNTHETIC_BARE = re.compile(r"^9\d\d[A-Z]?(\(\d+\))?$")


def _is_allowed_section(display: str) -> bool:
    # No verified rows exist yet; only synthetic sections are allowed. See module docstring
    # for how this widens once they do.
    return bool(_SYNTHETIC_DISPLAY.match(display.strip()))


class TestGoldenFilesCiteOnlySyntheticSections:
    def test_every_section_line_in_every_golden_is_synthetic(self) -> None:
        goldens = sorted(_GOLDEN_DIR.glob("*.txt"))
        assert goldens, "no golden files found — the convention has nothing to check"
        offenders: list[str] = []
        for golden in goldens:
            for line_no, line in enumerate(
                golden.read_text(encoding="utf-8").splitlines(), start=1
            ):
                match = re.match(r"^\s+Section:\s+(.+)$", line)
                if match and not _is_allowed_section(match.group(1)):
                    offenders.append(f"{golden.name}:{line_no}: {match.group(1)!r}")
        assert not offenders, (
            "golden files cite non-synthetic sections without a verified row:\n"
            + "\n".join(offenders)
        )

    def test_goldens_never_cite_real_code_names_with_sections(self) -> None:
        """Belt for the braces: no 'Section:' display text names IPC or BNS at all today."""
        for golden in sorted(_GOLDEN_DIR.glob("*.txt")):
            for line in golden.read_text(encoding="utf-8").splitlines():
                if re.match(r"^\s+Section:", line):
                    assert " IPC" not in line and " BNS" not in line, f"{golden.name}: {line}"


class TestGoldensetFixturesCiteOnlySyntheticSections:
    def test_smoke_fixture_rows_use_9xx_sections(self) -> None:
        fixture_files = sorted(_GOLDENSET_FIXTURES.glob("*.yaml"))
        assert fixture_files, "no goldenset fixture files found"
        for fixture in fixture_files:
            data = yaml.safe_load(fixture.read_text(encoding="utf-8"))
            rows = data.get("rows", data if isinstance(data, list) else [])
            for row in rows:
                if isinstance(row, dict) and "section" in row:
                    section = str(row["section"])
                    assert _SYNTHETIC_BARE.match(section), (
                        f"{fixture.name}: section {section!r} is not synthetic (9xx)"
                    )
