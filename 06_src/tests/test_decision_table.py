"""Tests for the statutory decision table and its loader.

SYNTHETIC TEST DATA where tables are constructed inline; the real-table tests read the actual
versioned table in 02_data/decision_table/ and assert what the gazette-verified statute says.
No real accused person's data appears here.

D-055 accepted one cost explicitly: a malformed table is a runtime failure where rules-as-code
would have given a type error. That trade is only sound if the loader refuses anything it does
not fully understand, so most of these tests are about *rejection*.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
import yaml

from bail_reckoner.statutes.decision_table import (
    DEFAULT_TABLE_PATH,
    DecisionTableError,
    GateKind,
    ProvisionStatus,
    SpecialStatute,
    load_decision_table,
)

needs_real_table = pytest.mark.skipif(
    not DEFAULT_TABLE_PATH.exists(), reason="02_data/decision_table/ not present in this checkout"
)


@pytest.fixture
def table_dict() -> dict[str, Any]:
    """The real table, parsed, so mutation tests break exactly one thing from a valid baseline."""
    loaded = yaml.safe_load(DEFAULT_TABLE_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _write(tmp_path: Path, data: object) -> Path:
    path = tmp_path / "table.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


@needs_real_table
class TestTheRealTableMatchesTheVerifiedStatute:
    """A failure means the table drifted from 01_law/Section_479_BNSS_2023.md, which governs."""

    def test_it_loads(self) -> None:
        table = load_decision_table()
        assert table.statute.act_number == "46 of 2023"
        assert table.statute.section == "479"

    def test_fractions_are_exact_rationals_not_floats(self) -> None:
        table = load_decision_table()
        assert table.fraction_standard == Fraction(1, 2)
        assert table.fraction_first_time_offender == Fraction(1, 3)
        assert isinstance(table.fraction_standard, Fraction)

    def test_all_six_gates_are_present_with_the_right_kinds(self) -> None:
        """Gate 0 is the cap (D-034); gate 3 is a FLAG, never a bar (D-033); gate 4 selects the
        fraction and is not a bar."""
        table = load_decision_table()
        assert table.gate(0).kind is GateKind.CAP
        assert table.gate(1).kind is GateKind.BAR
        assert table.gate(2).kind is GateKind.BAR
        assert table.gate(3).kind is GateKind.FLAG
        assert table.gate(4).kind is GateKind.SELECTOR
        assert table.gate(5).kind is GateKind.TEST

    def test_no_gate_kind_means_ineligible(self) -> None:
        """D-010: there is no third verdict anywhere in the system."""
        assert "INELIGIBLE" not in {kind.value for kind in GateKind}

    def test_gate_0_carries_the_third_proviso_verbatim(self) -> None:
        text = load_decision_table().gate(0).text
        assert text is not None
        assert "no such person shall in any case be detained" in text
        assert "more than the maximum period of imprisonment" in text

    def test_gate_2_carries_the_subject_to_third_proviso_limb(self) -> None:
        """The limb that makes gate 0 outrank gate 2 (D-034). Deck slide 4 elided it."""
        text = load_decision_table().gate(2).text
        assert text is not None
        assert "subject to the third proviso thereof" in text

    def test_gate_3_has_no_statutory_text_because_it_is_judicial_gloss(self) -> None:
        gate = load_decision_table().gate(3)
        assert gate.text is None
        assert "Antil" in gate.provision

    def test_the_explanation_is_present(self) -> None:
        """Absent from every pre-M0 project document; found at gazette verification (D-045)."""
        note = load_decision_table().standing_note("explanation")
        assert "delay in proceeding caused by the accused shall be excluded" in note.text

    def test_the_second_proviso_is_a_standing_note_not_a_gate(self) -> None:
        """D-040: a judicial power exercised after entitlement is established."""
        table = load_decision_table()
        assert "second_proviso" in {note.id for note in table.standing_notes}
        assert all("second proviso" not in gate.provision for gate in table.gates if gate.id != 0)

    def test_pocso_is_listed_with_no_invented_provision(self) -> None:
        """D-042/OLQ-4: POCSO is in Category C but no barring provision has been read."""
        table = load_decision_table()
        pocso = next(s for s in table.special_statutes if s.short == "POCSO")
        assert pocso.provision is None
        assert pocso.is_citable is False

    def test_sc_st_and_it_acts_are_absent_per_d054(self) -> None:
        """OLQ-8: the prose lists in EA §1 and v1 §3 add these; the Antil list does not."""
        shorts = {s.short for s in load_decision_table().special_statutes}
        assert shorts == {"NDPS", "PMLA", "UAPA", "Companies Act", "POCSO"}

    def test_the_real_table_exercises_present_and_absent(self) -> None:
        """The Category C set is COMPLETE as of 2026-08-19 (Companies Act s.212(6) acquired):
        every statute is now read, so NOT_YET_READ is rightly unrepresented in the real table.
        Its loader path stays exercised by the synthetic-table test below — the state remains
        defined-and-tested, just no longer by real data, which is the goal state."""
        statuses = {s.provision_status for s in load_decision_table().special_statutes}
        assert statuses == {ProvisionStatus.VERIFIED_PRESENT, ProvisionStatus.VERIFIED_ABSENT}

    def test_not_yet_read_state_still_loads_from_a_synthetic_table(self) -> None:
        """NOT_YET_READ must not decay into a defined-but-untested state now that no real
        entry uses it: the next special statute proposed for the set starts life here."""
        statute = SpecialStatute(
            act="Synthetic Act, 2099",
            short="SYN",
            provision=None,
            provision_status=ProvisionStatus.NOT_YET_READ,
        )
        assert statute.is_citable is False
        assert "not yet read" in statute.report_line()

    def test_provision_states_are_assigned_as_the_evidence_supports(self) -> None:
        by_short = {s.short: s for s in load_decision_table().special_statutes}
        # Read, bar found: quotable.
        assert by_short["NDPS"].provision_status is ProvisionStatus.VERIFIED_PRESENT
        assert by_short["NDPS"].is_citable is True
        # Read, no bar found: a finding, not a gap.
        assert by_short["POCSO"].provision_status is ProvisionStatus.VERIFIED_ABSENT
        assert by_short["PMLA"].provision_status is ProvisionStatus.VERIFIED_PRESENT
        assert by_short["UAPA"].provision_status is ProvisionStatus.VERIFIED_PRESENT
        # Acquired 2026-08-19: s.212(6) verified, scope narrowed by Act 21 of 2015 to s.447.
        assert by_short["Companies Act"].provision_status is ProvisionStatus.VERIFIED_PRESENT
        assert by_short["Companies Act"].is_citable is True
        # Sources with no printed as-on date carry the caveat on the record itself.
        for short in ("PMLA", "UAPA", "Companies Act"):
            assert by_short[short].currency_note, short

    def test_verified_present_statutes_quote_their_provision(self) -> None:
        """Naming a section is not enough: the three verified bars apply structurally different
        tests, and a reader told only 's.43-D(5) applies' learns nothing about which they face."""
        for statute in load_decision_table().special_statutes:
            if statute.provision_status is ProvisionStatus.VERIFIED_PRESENT:
                assert statute.provision_text, statute.short
                assert len(statute.provision_text) > 80, statute.short

    def test_uapa_records_the_inverted_test_not_the_ndps_one(self) -> None:
        """UAPA s.43-D(5) bars bail on a positive finding that the accusation is prima facie
        true; NDPS/PMLA instead require a positive finding of probable innocence to grant it.
        Storing only a section number would have flattened that difference."""
        by_short = {s.short: s for s in load_decision_table().special_statutes}
        uapa = by_short["UAPA"].provision_text or ""
        assert "prima facie true" in uapa
        assert "case diary" in uapa
        for other in ("NDPS", "PMLA"):
            text = by_short[other].provision_text or ""
            assert "not guilty of such offence" in text
            assert "prima facie true" not in text

    def test_only_a_verified_present_statute_may_name_a_provision(self) -> None:
        """C5: an unread Act must not carry a section number in data, however commonly it is
        cited. The commonly-cited numbers live in YAML comments instead."""
        for statute in load_decision_table().special_statutes:
            if statute.provision is not None:
                assert statute.provision_status is ProvisionStatus.VERIFIED_PRESENT, statute.short

    def test_report_text_differs_per_state(self) -> None:
        by_short = {s.short: s for s in load_decision_table().special_statutes}
        present = by_short["NDPS"].report_line()
        absent = by_short["POCSO"].report_line()
        # No real entry is NOT_YET_READ any more; a synthetic one keeps the branch covered.
        unread = SpecialStatute(
            act="Synthetic Act, 2099",
            short="SYN",
            provision=None,
            provision_status=ProvisionStatus.NOT_YET_READ,
        ).report_line()
        assert len({present, absent, unread}) == 3
        assert "s.37" in present
        assert "found no twin-condition bail bar" in absent
        assert "not yet read" in unread

    def test_verified_absent_does_not_read_as_a_clearance(self) -> None:
        """VERIFIED_ABSENT changes what the report says, never whether a human sees the case
        (D-054). The text must still send the reader to review."""
        by_short = {s.short: s for s in load_decision_table().special_statutes}
        assert "human review" in by_short["POCSO"].report_line()

    def test_content_hash_is_stable_and_feeds_statute_version(self) -> None:
        assert load_decision_table().content_hash == load_decision_table().content_hash
        assert len(load_decision_table().content_hash) == 64


@needs_real_table
class TestLoaderRejectsMalformedTables:
    """Strictness is the price of D-055. A table that loads with a provision quietly missing
    would produce reports citing nothing."""

    def test_unknown_top_level_key_is_rejected(
        self, tmp_path: Path, table_dict: dict[str, Any]
    ) -> None:
        """A typo'd key silently ignored is a provision silently absent."""
        table_dict["fracions"] = {}
        with pytest.raises(DecisionTableError, match="unrecognised key"):
            load_decision_table(_write(tmp_path, table_dict))

    def test_missing_top_level_key_is_rejected(
        self, tmp_path: Path, table_dict: dict[str, Any]
    ) -> None:
        del table_dict["fractions"]
        with pytest.raises(DecisionTableError, match="missing required key"):
            load_decision_table(_write(tmp_path, table_dict))

    def test_a_missing_gate_is_rejected(self, tmp_path: Path, table_dict: dict[str, Any]) -> None:
        """Losing gate 0 would silently disable the absolute cap — the highest-severity
        condition the system can detect."""
        table_dict["gates"] = [g for g in table_dict["gates"] if g["id"] != 0]
        with pytest.raises(DecisionTableError, match="expected exactly ids"):
            load_decision_table(_write(tmp_path, table_dict))

    def test_an_unknown_gate_kind_is_rejected(
        self, tmp_path: Path, table_dict: dict[str, Any]
    ) -> None:
        table_dict["gates"][3]["kind"] = "INELIGIBLE"
        with pytest.raises(DecisionTableError, match="not one of"):
            load_decision_table(_write(tmp_path, table_dict))

    def test_float_fractions_are_rejected(self, tmp_path: Path, table_dict: dict[str, Any]) -> None:
        """0.5 would reintroduce rounding invisibly. Rationals only."""
        table_dict["fractions"]["standard"] = 0.5
        with pytest.raises(DecisionTableError, match="must be a string"):
            load_decision_table(_write(tmp_path, table_dict))

    def test_a_missing_standing_note_is_rejected(
        self, tmp_path: Path, table_dict: dict[str, Any]
    ) -> None:
        """Dropping the Explanation would silently restore the pre-gazette arithmetic."""
        table_dict["standing_notes"] = [
            n for n in table_dict["standing_notes"] if n["id"] != "explanation"
        ]
        with pytest.raises(DecisionTableError, match="missing required"):
            load_decision_table(_write(tmp_path, table_dict))

    def test_verified_present_without_a_named_provision_is_rejected(
        self, tmp_path: Path, table_dict: dict[str, Any]
    ) -> None:
        """The exact shape of a C5 breach: claiming a bar was verified while naming nothing."""
        for statute in table_dict["special_statutes"]:
            if statute["short"] == "POCSO":
                statute["provision_status"] = "VERIFIED_PRESENT"
        with pytest.raises(DecisionTableError, match="requires the provision to be named"):
            load_decision_table(_write(tmp_path, table_dict))

    def test_naming_a_provision_on_an_unread_act_is_rejected(
        self, tmp_path: Path, table_dict: dict[str, Any]
    ) -> None:
        """The other direction: a section number asserted for an Act nobody has opened.
        The real table no longer has an unread entry (Category C is complete), so one is
        planted synthetically."""
        table_dict["special_statutes"].append(
            {
                "act": "Synthetic Act, 2099",
                "short": "SYN",
                "provision": "s.1",
                "provision_status": "NOT_YET_READ",
            }
        )
        with pytest.raises(DecisionTableError, match="only be named when VERIFIED_PRESENT"):
            load_decision_table(_write(tmp_path, table_dict))

    def test_verified_present_without_the_provision_text_is_rejected(
        self, tmp_path: Path, table_dict: dict[str, Any]
    ) -> None:
        """A named bar with no quoted text would leave a report unable to say what test applies."""
        for statute in table_dict["special_statutes"]:
            if statute["short"] == "NDPS":
                statute["provision_text"] = "   "
        with pytest.raises(DecisionTableError, match="requires the provision text"):
            load_decision_table(_write(tmp_path, table_dict))

    def test_an_unknown_provision_status_is_rejected(
        self, tmp_path: Path, table_dict: dict[str, Any]
    ) -> None:
        for statute in table_dict["special_statutes"]:
            if statute["short"] == "PMLA":
                statute["provision_status"] = "PROBABLY_FINE"
        with pytest.raises(DecisionTableError, match="not one of"):
            load_decision_table(_write(tmp_path, table_dict))

    def test_empty_gate_text_is_rejected(self, tmp_path: Path, table_dict: dict[str, Any]) -> None:
        """Null means "this gate has no statutory text" (gate 3). Empty means someone lost it."""
        table_dict["gates"][1]["text"] = "   "
        with pytest.raises(DecisionTableError, match="text present but empty"):
            load_decision_table(_write(tmp_path, table_dict))

    def test_invalid_yaml_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "table.yaml"
        path.write_text("gates: [unclosed\n", encoding="utf-8")
        with pytest.raises(DecisionTableError, match="invalid YAML"):
            load_decision_table(path)

    def test_a_missing_file_names_the_path(self, tmp_path: Path) -> None:
        with pytest.raises(DecisionTableError, match="cannot read decision table"):
            load_decision_table(tmp_path / "absent.yaml")
