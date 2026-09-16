"""Tests for the review-queue loader: signed rows into SQLite (statutes/review_queue.py).

SYNTHETIC TEST DATA. Every row below is written inline into tmp_path; no real accused person's
data appears here. No test depends on the committed queue having signed rows -- the suite must
stay green whether that count is 0 or 86.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from bail_reckoner.statutes.bare_act import LAW_DIR
from bail_reckoner.statutes.curation import (
    BNS_FILE,
    DRAFTED_BY,
    IPC_FILE,
    NDPS_FILE,
    DraftResult,
    draft_ndps_rows,
    draft_rows,
    export_drafts,
)
from bail_reckoner.statutes.models import OffenceRow, PunishmentKind, Regime, RowStatus
from bail_reckoner.statutes.repository import PenaltyRepository
from bail_reckoner.statutes.review_queue import (
    DEFAULT_QUEUE_PATH,
    ReviewQueueError,
    build_database,
    load_verified_rows,
)

SIGNED_ON = date(2026, 9, 16)
REVIEWER = "Test Reviewer"
IPC_SOURCE = "IPC_1860_Act45_IndiaCode_repealed_file.pdf"


def signed_row(**over: object) -> dict[str, Any]:
    """A fully signed synthetic row in the queue's shape. Override any key."""
    row: dict[str, Any] = {
        "offence_id": "IPC_1860-379",
        "priority": True,
        "label": "Theft (synthetic fixture)",
        "regime": "IPC_1860",
        "section": "379",
        "variant": None,
        "counterpart_id": "BNS_2023-303",
        "special_statute": None,
        "special_statute_provision": None,
        "maximum": {"kinds": ["TERM"], "term_months": 36, "fine_also": True},
        "min_term_months": None,
        "quoted_clause": "synthetic punishment clause, typed from the page",
        "verified_on": SIGNED_ON,
        "compoundable": None,
        "status": "VERIFIED",
        "definition_punishment_split": False,
        "state_amendment_present": False,
        "source": IPC_SOURCE,
        "READ_THIS_PAGE": f"{IPC_SOURCE}, printed p. 76 (PDF page index 75), s.379",
        "verified_by": REVIEWER,
        "extractor_output_do_not_rely_on": "machine text; never the reviewed value",
    }
    row.update(over)
    return row


def unsigned_row(**over: object) -> dict[str, Any]:
    """The normal state of a queue row: drafted, nothing filled, placeholder in verified_by."""
    row = signed_row(
        status="DRAFT",
        maximum=None,
        quoted_clause=None,
        verified_on=None,
        verified_by=DRAFTED_BY,
    )
    row.update(over)
    return row


def write_queue(tmp_path: Path, *rows: dict[str, Any]) -> Path:
    path = tmp_path / "queue.yaml"
    path.write_text(
        yaml.safe_dump({"rows": list(rows)}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


class TestSkipAndFail:
    def test_an_unsigned_row_is_skipped_and_counted_not_raised_on(self, tmp_path: Path) -> None:
        path = write_queue(
            tmp_path,
            unsigned_row(offence_id="IPC_1860-304A", section="304A"),
            signed_row(),
        )
        rows, skipped = load_verified_rows(path)
        assert [r.offence_id for r in rows] == ["IPC_1860-379"]
        assert skipped == 1

    def test_an_unsigned_row_in_the_pre_b1_shape_is_still_skipped(self, tmp_path: Path) -> None:
        """A DRAFT row lacking the newer keys (quoted_clause, verified_on, special_statute)
        is skipped without being read; only a signed row has to carry the full shape."""
        old_shape = {
            "offence_id": "IPC_1860-304A",
            "regime": "IPC_1860",
            "section": "304A",
            "status": "DRAFT",
        }
        rows, skipped = load_verified_rows(write_queue(tmp_path, old_shape, signed_row()))
        assert len(rows) == 1 and skipped == 1

    def test_a_misspelt_status_is_an_error_not_an_unsigned_row(self, tmp_path: Path) -> None:
        path = write_queue(tmp_path, signed_row(status="Verified"))
        with pytest.raises(ReviewQueueError, match="status must be DRAFT or VERIFIED"):
            load_verified_rows(path)

    def test_verified_with_null_maximum_raises(self, tmp_path: Path) -> None:
        path = write_queue(tmp_path, signed_row(maximum=None))
        with pytest.raises(ReviewQueueError, match="half-signed") as info:
            load_verified_rows(path)
        assert "IPC_1860-379" in str(info.value) and "maximum" in str(info.value)

    @pytest.mark.parametrize(
        "field, value",
        [
            ("quoted_clause", ""),
            ("quoted_clause", "   "),
            ("verified_by", ""),
            ("verified_on", None),
        ],
    )
    def test_verified_with_a_blank_signature_field_raises(
        self, tmp_path: Path, field: str, value: object
    ) -> None:
        path = write_queue(tmp_path, signed_row(**{field: value}))
        with pytest.raises(ReviewQueueError, match="half-signed") as info:
            load_verified_rows(path)
        assert field in str(info.value)

    def test_the_drafting_placeholder_is_rejected_on_a_verified_row(self, tmp_path: Path) -> None:
        path = write_queue(tmp_path, signed_row(verified_by=DRAFTED_BY))
        with pytest.raises(ReviewQueueError, match="drafting placeholder"):
            load_verified_rows(path)


class TestRowShape:
    @pytest.mark.parametrize("field", ["variant", "counterpart_id"])
    def test_the_string_none_is_rejected_with_a_pointer_to_null(
        self, tmp_path: Path, field: str
    ) -> None:
        path = write_queue(tmp_path, signed_row(**{field: "None"}))
        with pytest.raises(ReviewQueueError, match="null") as info:
            load_verified_rows(path)
        assert field in str(info.value)

    def test_a_multi_limb_row_without_a_variant_is_rejected(self, tmp_path: Path) -> None:
        """Two rows for BNS s.316 in the file; the signed one names no limb. Header step 4
        requires the statutory limb and an offence_id ending '#<variant>'."""
        signed = signed_row(
            offence_id="BNS_2023-316",
            regime="BNS_2023",
            section="316",
            counterpart_id="IPC_1860-406",
            source="BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf",
        )
        sibling = unsigned_row(
            offence_id="BNS_2023-316#L2",
            regime="BNS_2023",
            section="316",
            variant="L2",
            counterpart_id="IPC_1860-406",
        )
        with pytest.raises(ReviewQueueError, match=r"#<variant>"):
            load_verified_rows(write_queue(tmp_path, signed, sibling))

    def test_a_variant_that_does_not_match_the_offence_id_is_rejected(
        self, tmp_path: Path
    ) -> None:
        path = write_queue(tmp_path, signed_row(variant="(2)"))
        with pytest.raises(ReviewQueueError, match="must end with"):
            load_verified_rows(path)

    def test_term_kind_without_term_months_raises_naming_the_row(self, tmp_path: Path) -> None:
        path = write_queue(tmp_path, signed_row(maximum={"kinds": ["TERM"], "fine_also": False}))
        with pytest.raises(ReviewQueueError, match="term_months") as info:
            load_verified_rows(path)
        assert "IPC_1860-379" in str(info.value)

    def test_fine_also_is_required_not_defaulted(self, tmp_path: Path) -> None:
        """A missing fine_also is a reviewer who did not read for it, not a False (D-064)."""
        path = write_queue(tmp_path, signed_row(maximum={"kinds": ["TERM"], "term_months": 36}))
        with pytest.raises(ReviewQueueError, match="fine_also"):
            load_verified_rows(path)

    def test_an_unknown_kind_is_rejected(self, tmp_path: Path) -> None:
        path = write_queue(tmp_path, signed_row(maximum={"kinds": ["JAIL"], "fine_also": False}))
        with pytest.raises(ReviewQueueError, match="JAIL"):
            load_verified_rows(path)

    def test_an_unrecognised_key_on_a_signed_row_is_rejected(self, tmp_path: Path) -> None:
        path = write_queue(tmp_path, signed_row(maxmium={"kinds": ["TERM"]}))
        with pytest.raises(ReviewQueueError, match="unrecognised key"):
            load_verified_rows(path)

    def test_special_statute_survives_the_load(self, tmp_path: Path) -> None:
        ndps = signed_row(
            offence_id="NDPS_1985-20#commercial_quantity",
            regime="NDPS_1985",
            section="20",
            variant="commercial_quantity",
            counterpart_id=None,
            special_statute="NDPS",
            special_statute_provision="s.37",
            maximum={"kinds": ["TERM"], "term_months": 240, "fine_also": True},
            min_term_months=120,
            source=NDPS_FILE,
            READ_THIS_PAGE=f"{NDPS_FILE}, printed p. 16 (PDF page index 15), s.20",
        )
        rows, _ = load_verified_rows(write_queue(tmp_path, ndps))
        (row,) = rows
        assert row.special_statute == "NDPS"
        assert row.special_statute_provision == "s.37"
        assert row.regime is Regime.NDPS_1985
        assert row.maximum.kinds == frozenset({PunishmentKind.TERM})
        assert row.maximum.term_months == 240
        assert row.min_term_months == 120

    def test_loaded_rows_are_draft_until_promoted(self, tmp_path: Path) -> None:
        rows, _ = load_verified_rows(write_queue(tmp_path, signed_row()))
        assert rows[0].status is RowStatus.DRAFT
        assert rows[0].provenance.verified_by == REVIEWER
        assert rows[0].provenance.quoted_text.startswith("synthetic punishment clause")
        assert rows[0].provenance.verified_against.endswith("s.379")


class TestBuildDatabase:
    def test_end_to_end_signed_row_resolves_as_verified(self, tmp_path: Path) -> None:
        queue = write_queue(tmp_path, unsigned_row(offence_id="IPC_1860-304A", section="304A"),
                            signed_row())
        db = tmp_path / "p.sqlite3"
        counts = build_database(queue, db_path=db)
        assert counts == {"DRAFT": 0, "VERIFIED": 1}
        with PenaltyRepository(db) as repo:
            row = repo.resolve(Regime.IPC_1860, "379")
            assert row is not None
            assert row.status is RowStatus.VERIFIED
            assert row.provenance.verified_by == REVIEWER
            assert row.provenance.verified_on == SIGNED_ON
            assert repo.counts()["VERIFIED"] == 1

    def test_rebuild_replaces_an_existing_store(self, tmp_path: Path) -> None:
        db = tmp_path / "p.sqlite3"
        build_database(write_queue(tmp_path, signed_row()), db_path=db)
        counts = build_database(write_queue(tmp_path, unsigned_row()), db_path=db)
        assert counts == {"DRAFT": 0, "VERIFIED": 0}


needs_law_pdfs = pytest.mark.skipif(
    not (LAW_DIR / BNS_FILE).exists()
    or not (LAW_DIR / IPC_FILE).exists()
    or not (LAW_DIR / NDPS_FILE).exists(),
    reason="bare-act PDFs are not present in this checkout",
)

_ROUND_TRIP_FIELDS = (
    "offence_id",
    "label",
    "regime",
    "section",
    "variant",
    "counterpart_id",
    "special_statute",
    "special_statute_provision",
    "min_term_months",
    "compoundable",
    "notes",
)


@needs_law_pdfs
class TestRoundTrip:
    def test_draft_export_sign_load_is_lossless(self, tmp_path: Path) -> None:
        """draft_rows -> export_drafts -> (sign every row) -> load_verified_rows.

        Every field the reviewer does not touch must arrive unchanged. This is the test that
        catches a key silently dropped by the export: `special_statute` went missing that
        way and would have silenced gate 3 for every NDPS row.
        """
        ipc_bns = draft_rows()
        ndps = draft_ndps_rows()
        drafted = DraftResult(
            rows=ipc_bns.rows + ndps.rows, unresolved=ipc_bns.unresolved + ndps.unresolved
        )
        assert drafted.rows, "nothing drafted; the PDFs are present so this is a regression"

        exported = export_drafts(drafted, tmp_path / "q.yaml")
        data = yaml.safe_load(exported.read_text(encoding="utf-8"))
        for entry in data["rows"]:
            entry["status"] = "VERIFIED"
            entry["verified_by"] = REVIEWER
            entry["verified_on"] = SIGNED_ON
            entry["quoted_clause"] = "clause typed from the page (synthetic)"
            entry["maximum"] = {"kinds": ["TERM"], "term_months": 12, "fine_also": False}
        signed_path = tmp_path / "signed.yaml"
        signed_path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )

        loaded, skipped = load_verified_rows(signed_path)
        assert skipped == 0
        by_id: dict[str, OffenceRow] = {row.offence_id: row for row in loaded}
        assert set(by_id) == {row.offence_id for row in drafted.rows}
        for original in drafted.rows:
            reloaded = by_id[original.offence_id]
            for name in _ROUND_TRIP_FIELDS:
                assert getattr(reloaded, name) == getattr(original, name), (
                    original.offence_id,
                    name,
                )
            assert reloaded.provenance.source == original.provenance.source
            assert reloaded.provenance.verified_against == original.provenance.verified_against
        assert any(row.special_statute == "NDPS" for row in loaded)


class TestCommittedQueue:
    def test_the_committed_queue_loads_whatever_the_signed_count(self) -> None:
        """Keeps a malformed signed row from reaching main. Makes no claim about how many
        rows are signed -- that number is the reviewer's, not the suite's."""
        assert DEFAULT_QUEUE_PATH.is_file(), DEFAULT_QUEUE_PATH
        rows, skipped = load_verified_rows()
        assert len(rows) + skipped > 0
        assert all(row.provenance.verified_by != DRAFTED_BY for row in rows)
