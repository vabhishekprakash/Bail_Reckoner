"""Tests for penalty-row drafting.

SYNTHETIC AND REAL-STATUTE DATA. Seed entries name real sections, checked against the bare acts
in 01_law/. No real accused person's data appears here.

The property under test is not "drafting works" but "drafting refuses to guess": a wrong section
number must produce a reported gap, never a plausible row attaching the wrong punishment.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from bail_reckoner.statutes.bare_act import LAW_DIR
from bail_reckoner.statutes.curation import (
    BNS_FILE,
    IPC_FILE,
    NDPS_QUANTITY_BANDS,
    NDPS_SEED_LIST,
    SEED_LIST,
    DraftResult,
    NdpsSeedEntry,
    SeedEntry,
    draft_ndps_rows,
    draft_rows,
    export_drafts,
)
from bail_reckoner.statutes.models import PunishmentKind, Regime, RowStatus

needs_law_pdfs = pytest.mark.skipif(
    not (LAW_DIR / BNS_FILE).exists() or not (LAW_DIR / IPC_FILE).exists(),
    reason="bare-act PDFs are not present in this checkout",
)

pytestmark = needs_law_pdfs


@pytest.fixture(scope="module")
def drafted() -> DraftResult:
    """Drafted once for the whole module.

    Each `draft_rows()` call scans both acts for 40 sections. Recomputing it per test turned this
    file into minutes of work for no extra coverage.
    """
    return draft_rows()


class TestDraftingRefusesToGuess:
    def test_a_wrong_section_number_is_reported_not_drafted(self) -> None:
        """The core safety property. A wrong candidate must leave a visible gap."""
        bogus = SeedEntry("bogus", "Nonexistent", "9998", "9999", "Whoever commits theft")
        result = draft_rows((bogus,))
        assert result.rows == ()
        assert len(result.unresolved) == 2
        assert all("unconfirmed" in message for message in result.unresolved)

    def test_a_right_section_with_a_wrong_keyword_is_also_refused(self) -> None:
        """IPC s.302 exists, but if the keyword does not match the section text the pairing is
        unproven, so the row is refused rather than trusted."""
        mismatched = SeedEntry("mismatch", "Murder", "302", None, "commits dacoity")
        result = draft_rows((mismatched,))
        assert result.rows == ()

    def test_a_missing_counterpart_is_recorded_not_silently_skipped(self) -> None:
        """BNS created offences with no IPC equivalent; the absence must be visible."""
        one_sided = SeedEntry("bns_only", "Theft", None, "303", "Whoever commits theft")
        result = draft_rows((one_sided,))
        # One row per limb now (D-061), so the BNS side yields several rows; the property under
        # test is that the missing IPC side is RECORDED, not how many limbs the BNS side has.
        assert result.rows, "the present side must still draft"
        assert all(r.offence_id.startswith("BNS_2023-303") for r in result.rows)
        assert any("no counterpart recorded" in message for message in result.unresolved)


class TestDraftedRows:
    def test_every_row_is_draft(self, drafted: DraftResult) -> None:
        """Nothing in curation can produce a VERIFIED row (D-046)."""
        result = drafted
        assert all(row.status is RowStatus.DRAFT for row in result.rows)
        assert all(not row.is_engine_visible for row in result.rows)

    def test_no_maximum_is_inferred(self, drafted: DraftResult) -> None:
        """Reading a punishment clause is legal judgement. Every drafted maximum is a
        BY_REFERENCE placeholder, which is not computable, so gate 5 refuses it even if the row
        were somehow promoted without review."""
        result = drafted
        for row in result.rows:
            assert row.maximum.kinds == frozenset({PunishmentKind.BY_REFERENCE})
            assert row.maximum.is_computable is False

    def test_every_row_carries_real_provenance(self, drafted: DraftResult) -> None:
        result = drafted
        for row in result.rows:
            assert row.provenance.source in (BNS_FILE, IPC_FILE)
            assert "PDF page index" in row.provenance.verified_against
            assert len(row.provenance.quoted_text) > 40

    def test_verified_by_does_not_impersonate_a_reviewer(self, drafted: DraftResult) -> None:
        """It must be non-empty to satisfy the provenance constraint, but must not read as a
        person having checked the row."""
        for row in drafted.rows:
            assert "unverified" in row.provenance.verified_by

    def test_offence_ids_namespace_their_regime(self, drafted: DraftResult) -> None:
        for row in drafted.rows:
            assert row.offence_id.startswith(f"{row.regime.value}-")

    def test_counterparts_point_at_the_other_regime(self, drafted: DraftResult) -> None:
        for row in drafted.rows:
            if row.counterpart_id:
                other = Regime.BNS_2023 if row.regime is Regime.IPC_1860 else Regime.IPC_1860
                assert row.counterpart_id.startswith(f"{other.value}-")

    def test_quoted_text_mentions_its_own_section(self, drafted: DraftResult) -> None:
        """Guards against an off-by-one slice quoting the neighbouring section."""
        for row in drafted.rows:
            assert row.section in row.provenance.quoted_text[:80]


class TestQuotedTextIsNeverTruncated:
    def test_a_long_section_keeps_its_punishment_clause(self, drafted: DraftResult) -> None:
        """Regression: a [:4000] cap cut BNS s.303's quote before its punishment sub-section
        began — the audit trail for theft omitted the clause the row exists to record. The
        session-9 truncation bug, reintroduced through a convenience cap (D-064)."""
        theft = next(r for r in drafted.rows if r.offence_id.startswith("BNS_2023-303#"))
        squeezed = "".join(theft.provenance.quoted_text.split()).lower()
        assert "shallbepunished" in squeezed

    def test_the_split_tell_fires_on_the_documented_case(self, drafted: DraftResult) -> None:
        """BNS s.303(1) defines theft and s.303(2) punishes it — the case the tell exists for.
        It read false while the cap was in place, because the truncated text had no (2)."""
        from bail_reckoner.statutes.curation import definition_punishment_split

        theft = next(r for r in drafted.rows if r.offence_id.startswith("BNS_2023-303#"))
        assert definition_punishment_split(theft.provenance.quoted_text) is True

    def test_the_split_tell_stays_quiet_where_punishment_opens_the_section(
        self, drafted: DraftResult
    ) -> None:
        """BNS s.103(1) punishes murder directly — definition and punishment are not split."""
        from bail_reckoner.statutes.curation import definition_punishment_split

        murder = next(r for r in drafted.rows if r.offence_id.startswith("BNS_2023-103#"))
        assert definition_punishment_split(murder.provenance.quoted_text) is False


class TestPerLimbDrafting:
    def test_row_count_matches_the_final_limb_count(self, drafted: DraftResult) -> None:
        assert len(drafted.rows) == 77
        sections = {(r.regime, r.section) for r in drafted.rows}
        assert len(sections) == 38

    def test_multi_limb_sections_get_one_row_per_limb(self, drafted: DraftResult) -> None:
        limbs_331 = [r for r in drafted.rows if r.offence_id.startswith("BNS_2023-331#")]
        assert [r.variant for r in limbs_331] == [f"L{i}" for i in range(1, 9)]

    def test_single_limb_sections_carry_no_variant(self, drafted: DraftResult) -> None:
        ipc_theft = next(r for r in drafted.rows if r.offence_id == "IPC_1860-379")
        assert ipc_theft.variant is None

    def test_variants_are_detector_labels_never_statutory_claims(
        self, drafted: DraftResult
    ) -> None:
        """`L2` asserts nothing about which sub-section it is; the reviewer renames it from the
        page. A drafted variant like `(2)` would be the machine asserting a statutory mapping."""
        for row in drafted.rows:
            if row.variant is not None:
                assert re.fullmatch(r"L\d+", row.variant), row.offence_id


class TestSeedListCoverage:
    """D-046 requires the coverage to be justified, not asserted."""

    def test_the_whole_seed_list_resolves(self, drafted: DraftResult) -> None:
        result = drafted
        assert result.unresolved == ()

    @pytest.mark.parametrize("criterion", ["i", "ii", "iii", "v", "vi"])
    def test_each_claimed_criterion_has_at_least_one_entry(self, criterion: str) -> None:
        assert any(criterion in entry.criteria for entry in SEED_LIST), criterion

    def test_criterion_iv_lives_in_the_ndps_pipeline_not_seed_list(self) -> None:
        """Criterion (iv) is covered by `draft_ndps_rows` (D-067), not by SEED_LIST: NDPS rows
        have no cross-regime counterpart, so they cannot ride the IPC/BNS pipeline. SEED_LIST
        must therefore still claim no (iv) entry — a claim there would double-count."""
        assert not any("iv" in entry.criteria for entry in SEED_LIST)
        assert NDPS_SEED_LIST


class TestExport:
    def test_export_writes_reviewable_text_with_no_maximum_filled(
        self, tmp_path: Path, drafted: DraftResult
    ) -> None:
        result = drafted
        path = export_drafts(result, tmp_path / "drafts.yaml")
        content = path.read_text(encoding="utf-8")
        assert "status: DRAFT" in content
        assert "maximum: null" in content
        assert "REVIEWER ACTION" in content
        assert content.count("offence_id:") == len(result.rows)


class TestNdpsDrafting:
    """D-067: quantity-band rows from the stored NDPS Act, keyword-guarded."""

    @pytest.fixture(scope="class")
    @staticmethod
    def ndps() -> DraftResult:
        return draft_ndps_rows()

    def test_every_seed_section_drafts_all_three_bands(self, ndps: DraftResult) -> None:
        assert ndps.unresolved == ()
        assert len(ndps.rows) == len(NDPS_SEED_LIST) * len(NDPS_QUANTITY_BANDS)
        ids = {r.offence_id for r in ndps.rows}
        for entry in NDPS_SEED_LIST:
            for band in NDPS_QUANTITY_BANDS:
                assert f"NDPS_1985-{entry.section}#{band}" in ids

    def test_rows_carry_gate3_membership_and_no_counterpart(self, ndps: DraftResult) -> None:
        for row_ in ndps.rows:
            assert row_.regime is Regime.NDPS_1985
            assert row_.special_statute == "NDPS"
            assert row_.special_statute_provision == "s.37"
            assert row_.counterpart_id is None

    def test_no_maximum_is_inferred(self, ndps: DraftResult) -> None:
        """Placeholder only: reading a punishment clause is a legal judgement (D-046)."""
        for row_ in ndps.rows:
            assert PunishmentKind.BY_REFERENCE in row_.maximum.kinds
            assert not row_.maximum.is_computable

    def test_quoted_text_names_both_band_phrases(self, ndps: DraftResult) -> None:
        for row_ in ndps.rows:
            squeezed = " ".join(row_.provenance.quoted_text.split()).lower()
            assert "small quantity" in squeezed
            assert "commercial quantity" in squeezed

    def test_band_phrase_guard_reports_a_gap_never_a_row(self) -> None:
        """s.37 (the bail bar) contains no quantity bands: the guard must refuse to draft
        band rows from it rather than emit three rows with unsupported variants (D-064).
        s.37 is the pointed choice and became findable when D-070's structural discriminator
        replaced the penal-vocabulary filter that had been discarding it; this test's earlier
        target (s.25) and its "amendment-marker heading" explanation both dated from the
        mis-attribution that D-070's entry corrects."""
        fake = (NdpsSeedEntry("fake_37", "Bail bar, not a band section", "37", "cognizable"),)
        result = draft_ndps_rows(seed=fake)
        assert result.rows == ()
        assert len(result.unresolved) == 1
        assert "band" in result.unresolved[0]

    def test_the_ipc_bns_pipeline_refuses_the_ndps_regime(self) -> None:
        """The counterpart resolution names every regime; NDPS reaching it is a wiring error,
        not a case to guess a counterpart for (D-067 discipline: no wildcard arm)."""
        from bail_reckoner.statutes.bare_act import SectionText
        from bail_reckoner.statutes.curation import _to_draft_row

        found = SectionText(
            section="20", text="stub", page_index=0, printed_page="1", source_file="stub.pdf"
        )
        with pytest.raises(ValueError, match="draft_ndps_rows"):
            _to_draft_row(
                SEED_LIST[0], Regime.NDPS_1985, "20", found, date(2026, 8, 19), None, 1, 1
            )
