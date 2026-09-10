"""Tests for the statutory-penalty database.

SYNTHETIC TEST DATA. All rows below are constructed for testing. No real accused person's data
appears here.

The point of most of these tests is that the invariants hold at the *database* level, not merely
in Python: several deliberately bypass the repository and issue raw SQL, because a guard that
only lives in application code is bypassed by any migration script or sqlite3 prompt.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from bail_reckoner.statutes.models import (
    MaximumPunishment,
    OffenceRow,
    Provenance,
    PunishmentKind,
    Regime,
    RowStatus,
)
from bail_reckoner.statutes.repository import PenaltyRepository, RepositoryError


@pytest.fixture
def repo(tmp_path: Path) -> Iterator[PenaltyRepository]:
    with PenaltyRepository(tmp_path / "test.sqlite3") as repository:
        yield repository


def provenance(**over: object) -> Provenance:
    base: dict[str, object] = {
        "source": "BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf",
        "verified_against": "printed p. 301, s.303 (synthetic fixture)",
        "verified_on": date(2026, 8, 12),
        "verified_by": "test-fixture",
        "quoted_text": "synthetic punishment clause",
    }
    base.update(over)
    return Provenance(**base)  # type: ignore[arg-type]


def row(
    offence_id: str = "BNS_2023-303(2)",
    section: str = "303(2)",
    maximum: MaximumPunishment | None = None,
    **over: object,
) -> OffenceRow:
    return OffenceRow(
        offence_id=offence_id,
        label="Theft (synthetic)",
        regime=Regime.BNS_2023,
        section=section,
        maximum=maximum
        or MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=36),
        provenance=provenance(),
        **over,  # type: ignore[arg-type]
    )


class TestDraftRowsCannotReachTheEngine:
    def test_a_new_row_defaults_to_draft(self, repo: PenaltyRepository) -> None:
        repo.add(row())
        assert repo.counts() == {"DRAFT": 1, "VERIFIED": 0}

    def test_draft_rows_are_invisible_to_verified_reads(self, repo: PenaltyRepository) -> None:
        repo.add(row())
        assert repo.get("BNS_2023-303(2)") is None
        assert repo.get("BNS_2023-303(2)", verified_only=False) is not None

    def test_draft_rows_are_absent_from_find_variants(self, repo: PenaltyRepository) -> None:
        repo.add(row())
        assert repo.find_variants(Regime.BNS_2023, "303(2)") == ()
        assert repo.resolve(Regime.BNS_2023, "303(2)") is None

    def test_promotion_makes_a_row_readable(self, repo: PenaltyRepository) -> None:
        repo.add(row())
        repo.promote_to_verified(
            "BNS_2023-303(2)", verified_by="A. Reviewer", verified_on=date(2026, 8, 13)
        )
        stored = repo.get("BNS_2023-303(2)")
        assert stored is not None
        assert stored.status is RowStatus.VERIFIED
        assert stored.provenance.verified_by == "A. Reviewer"

    def test_promotion_requires_a_human_name(self, repo: PenaltyRepository) -> None:
        """D-046: a person accepts the row. An empty name would make the record meaningless."""
        repo.add(row())
        with pytest.raises(RepositoryError, match="name of the person"):
            repo.promote_to_verified(
                "BNS_2023-303(2)", verified_by="   ", verified_on=date(2026, 8, 13)
            )

    def test_promoting_an_unknown_row_fails_loudly(self, repo: PenaltyRepository) -> None:
        with pytest.raises(RepositoryError, match="no DRAFT row"):
            repo.promote_to_verified("BNS_2023-999", verified_by="X", verified_on=date(2026, 8, 13))

    def test_promotion_is_not_idempotent_and_says_so(self, repo: PenaltyRepository) -> None:
        """Re-promoting should fail rather than silently rewrite an existing verification."""
        repo.add(row())
        repo.promote_to_verified(
            "BNS_2023-303(2)", verified_by="First", verified_on=date(2026, 8, 13)
        )
        with pytest.raises(RepositoryError, match="no DRAFT row"):
            repo.promote_to_verified(
                "BNS_2023-303(2)", verified_by="Second", verified_on=date(2026, 8, 14)
            )


class TestProvenanceIsEnforcedByTheDatabase:
    """Raw SQL on purpose: a Python-only guard is bypassed by any migration or sqlite3 prompt."""

    @pytest.mark.parametrize(
        "column", ["source", "verified_against", "verified_on", "verified_by", "quoted_text"]
    )
    def test_empty_provenance_column_is_rejected_at_sql_level(
        self, repo: PenaltyRepository, column: str
    ) -> None:
        values = {
            "offence_id": "BNS_2023-1",
            "label": "X",
            "regime": "BNS_2023",
            "section": "1",
            "kinds": "TERM",
            "term_months": 12,
            "source": "s.pdf",
            "verified_against": "p.1",
            "verified_on": "2026-08-12",
            "verified_by": "someone",
            "quoted_text": "text",
        }
        values[column] = "   "
        columns = ", ".join(values)
        placeholders = ", ".join("?" * len(values))
        with pytest.raises(sqlite3.IntegrityError):
            repo._conn.execute(
                f"INSERT INTO offence ({columns}) VALUES ({placeholders})", tuple(values.values())
            )

    def test_null_provenance_column_is_rejected_at_sql_level(self, repo: PenaltyRepository) -> None:
        with pytest.raises(sqlite3.IntegrityError):
            repo._conn.execute(
                "INSERT INTO offence (offence_id, label, regime, section, kinds, term_months, "
                "source, verified_against, verified_on, verified_by, quoted_text) "
                "VALUES ('BNS_2023-1','X','BNS_2023','1','TERM',12,'s.pdf','p.1',"
                "'2026-08-12','someone', NULL)"
            )


class TestMaximumInvariantsAtSqlLevel:
    def test_a_life_row_cannot_carry_a_term(self, repo: PenaltyRepository) -> None:
        """Without this, a LIFE row could acquire a month count and become arithmetic-eligible
        at gate 5, which would compute a threshold for an offence s.479(1) excludes."""
        with pytest.raises(sqlite3.IntegrityError):
            repo._conn.execute(
                "INSERT INTO offence (offence_id, label, regime, section, kinds, term_months, "
                "source, verified_against, verified_on, verified_by, quoted_text) "
                "VALUES ('BNS_2023-103','Murder','BNS_2023','103','DEATH,LIFE',240,'s.pdf','p.1',"
                "'2026-08-12','someone','text')"
            )

    def test_a_term_row_must_carry_a_term(self, repo: PenaltyRepository) -> None:
        with pytest.raises(sqlite3.IntegrityError):
            repo._conn.execute(
                "INSERT INTO offence (offence_id, label, regime, section, kinds, "
                "source, verified_against, verified_on, verified_by, quoted_text) "
                "VALUES ('BNS_2023-1','X','BNS_2023','1','TERM','s.pdf','p.1',"
                "'2026-08-12','someone','text')"
            )

    def test_offence_id_must_namespace_its_regime(self, repo: PenaltyRepository) -> None:
        """Stops an IPC maximum being read under a BNS identifier after a copy-paste."""
        with pytest.raises(sqlite3.IntegrityError):
            repo._conn.execute(
                "INSERT INTO offence (offence_id, label, regime, section, kinds, term_months, "
                "source, verified_against, verified_on, verified_by, quoted_text) "
                "VALUES ('IPC_1860-379','Theft','BNS_2023','303','TERM',36,'s.pdf','p.1',"
                "'2026-08-12','someone','text')"
            )

    def test_a_provision_without_its_statute_is_rejected(self, repo: PenaltyRepository) -> None:
        with pytest.raises(sqlite3.IntegrityError):
            repo._conn.execute(
                "INSERT INTO offence (offence_id, label, regime, section, kinds, term_months, "
                "special_statute_provision, source, verified_against, verified_on, verified_by, "
                "quoted_text) VALUES ('BNS_2023-1','X','BNS_2023','1','TERM',12,'s.37','s.pdf',"
                "'p.1','2026-08-12','someone','text')"
            )

    def test_pocso_shaped_row_with_null_provision_is_allowed(self, repo: PenaltyRepository) -> None:
        """D-042/OLQ-4: a named statute with an unnamed provision must be expressible, so that
        nothing has to be invented to satisfy a NOT NULL."""
        repo.add(row(special_statute="POCSO", special_statute_provision=None))
        stored = repo.get("BNS_2023-303(2)", verified_only=False)
        assert stored is not None
        assert stored.special_statute == "POCSO"
        assert stored.special_statute_provision is None


class TestRoundTrip:
    def test_a_row_survives_storage_unchanged(self, repo: PenaltyRepository) -> None:
        original = row(
            maximum=MaximumPunishment(
                kinds=frozenset({PunishmentKind.TERM}), term_months=36, fine_also=True
            ),
            compoundable=False,
            counterpart_id="IPC_1860-379",
            notes="synthetic",
        )
        repo.add(original)
        repo.promote_to_verified(
            original.offence_id, verified_by="test-fixture", verified_on=date(2026, 8, 12)
        )
        stored = repo.get(original.offence_id)
        assert stored is not None
        assert stored.maximum == original.maximum
        assert stored.compoundable is False
        assert stored.counterpart_id == "IPC_1860-379"

    def test_death_or_life_round_trips_as_a_set(self, repo: PenaltyRepository) -> None:
        maximum = MaximumPunishment(
            kinds=frozenset({PunishmentKind.DEATH, PunishmentKind.LIFE}), fine_also=True
        )
        repo.add(row(offence_id="BNS_2023-103", section="103", maximum=maximum))
        stored = repo.get("BNS_2023-103", verified_only=False)
        assert stored is not None
        assert stored.maximum.excludes_s479 is True
        assert stored.maximum.term_months is None

    def test_unknown_compoundability_stays_none(self, repo: PenaltyRepository) -> None:
        repo.add(row())
        stored = repo.get("BNS_2023-303(2)", verified_only=False)
        assert stored is not None
        assert stored.compoundable is None

    def test_duplicate_offence_id_is_rejected(self, repo: PenaltyRepository) -> None:
        repo.add(row())
        with pytest.raises(RepositoryError):
            repo.add(row())

    def test_malformed_section_is_rejected_before_insert(self, repo: PenaltyRepository) -> None:
        with pytest.raises(RepositoryError, match="well-formed"):
            repo.add(row(offence_id="BNS_2023-s.303", section="s.303"))


class TestVariantKeying:
    """D-061: one row per punishment limb; the engine never picks a limb for the user (L-001)."""

    def _limb(self, variant: str, months: int) -> OffenceRow:
        return row(
            offence_id=f"BNS_2023-316#{variant}",
            section="316",
            maximum=MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=months),
            variant=variant,
        )

    def _add_verified(self, repo: PenaltyRepository, offence: OffenceRow) -> None:
        repo.add(offence)
        repo.promote_to_verified(
            offence.offence_id, verified_by="test-fixture", verified_on=date(2026, 8, 13)
        )

    def test_variant_and_minimum_round_trip(self, repo: PenaltyRepository) -> None:
        original = row(
            offence_id="BNS_2023-316#(2)",
            section="316",
            variant="(2)",
            min_term_months=12,
            maximum=MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=60),
        )
        self._add_verified(repo, original)
        stored = repo.get("BNS_2023-316#(2)")
        assert stored is not None
        assert stored.variant == "(2)"
        assert stored.min_term_months == 12

    def test_named_variant_resolves_exactly(self, repo: PenaltyRepository) -> None:
        self._add_verified(repo, self._limb("(2)", 60))
        self._add_verified(repo, self._limb("(4)", 120))
        resolved = repo.resolve(Regime.BNS_2023, "316", "(4)")
        assert resolved is not None and resolved.maximum.term_months == 120

    def test_unnamed_variant_on_a_multi_limb_section_abstains(
        self, repo: PenaltyRepository
    ) -> None:
        """The load-bearing semantics: ambiguity is OFFENCE_NOT_IN_DATABASE, never a guess.
        Returning the highest maximum here would quietly answer L-001."""
        self._add_verified(repo, self._limb("(2)", 60))
        self._add_verified(repo, self._limb("(4)", 120))
        assert repo.resolve(Regime.BNS_2023, "316") is None

    def test_unnamed_variant_on_a_single_limb_section_resolves(
        self, repo: PenaltyRepository
    ) -> None:
        self._add_verified(repo, row())
        assert repo.resolve(Regime.BNS_2023, "303(2)") is not None

    def test_unknown_named_variant_abstains(self, repo: PenaltyRepository) -> None:
        self._add_verified(repo, self._limb("(2)", 60))
        assert repo.resolve(Regime.BNS_2023, "316", "(9)") is None

    def test_variant_must_be_embedded_in_the_id(self, repo: PenaltyRepository) -> None:
        """Model-level: two limbs may never share an identity."""
        with pytest.raises(ValueError, match="must end with"):
            row(offence_id="BNS_2023-316", section="316", variant="(2)")

    def test_minimum_may_not_exceed_maximum_at_sql_level(self, repo: PenaltyRepository) -> None:
        with pytest.raises(sqlite3.IntegrityError):
            repo._conn.execute(
                "INSERT INTO offence (offence_id, label, regime, section, variant, "
                "min_term_months, kinds, term_months, source, verified_against, verified_on, "
                "verified_by, quoted_text) "
                "VALUES ('BNS_2023-316#(2)','X','BNS_2023','316','(2)',120,'TERM',60,"
                "'s.pdf','p.1','2026-08-13','someone','text')"
            )

    def test_duplicate_limb_is_rejected_at_sql_level(self, repo: PenaltyRepository) -> None:
        self._add_verified(repo, self._limb("(2)", 60))
        with pytest.raises(RepositoryError):
            repo.add(self._limb("(2)", 60))


class TestNdpsRegimeRows:
    def test_schema_v3_accepts_and_round_trips_an_ndps_band_row(
        self, repo: PenaltyRepository
    ) -> None:
        """D-067: the regime CHECK now admits NDPS_1985, and the band variant keys like a limb."""
        band_row = OffenceRow(
            offence_id="NDPS_1985-20#commercial_quantity",
            label="Contravention in relation to cannabis (synthetic)",
            regime=Regime.NDPS_1985,
            section="20",
            variant="commercial_quantity",
            min_term_months=120,
            maximum=MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=240),
            provenance=provenance(),
            special_statute="NDPS",
            special_statute_provision="s.37",
        )
        repo.add(band_row)
        repo.promote_to_verified(
            band_row.offence_id, verified_by="test-fixture", verified_on=date(2026, 8, 19)
        )
        got = repo.resolve(Regime.NDPS_1985, "20", variant="commercial_quantity")
        assert isinstance(got, OffenceRow)
        assert got.min_term_months == 120

    def test_unnamed_band_on_a_multi_band_section_abstains(self, repo: PenaltyRepository) -> None:
        """The quantity band is a case fact; not knowing it means not knowing the maximum."""
        for band, months in (("small_quantity", 12), ("commercial_quantity", 240)):
            r = OffenceRow(
                offence_id=f"NDPS_1985-22#{band}",
                label="Contravention in relation to psychotropic substances (synthetic)",
                regime=Regime.NDPS_1985,
                section="22",
                variant=band,
                maximum=MaximumPunishment(
                    kinds=frozenset({PunishmentKind.TERM}), term_months=months
                ),
                provenance=provenance(),
            )
            repo.add(r)
            repo.promote_to_verified(
                r.offence_id, verified_by="test-fixture", verified_on=date(2026, 8, 19)
            )
        assert repo.resolve(Regime.NDPS_1985, "22", variant=None) is None


class TestSchemaVersionGuard:
    def test_a_stale_database_is_refused_with_rebuild_instructions(self, tmp_path: Path) -> None:
        """The .sqlite3 is a derived artefact; a version mismatch must fail loudly, not run
        against half the columns."""
        stale = tmp_path / "stale.sqlite3"
        conn = sqlite3.connect(str(stale))
        conn.execute("PRAGMA user_version = 1")
        conn.execute("CREATE TABLE offence (offence_id TEXT PRIMARY KEY)")
        conn.commit()
        conn.close()
        with pytest.raises(RepositoryError, match="delete the file and rebuild"):
            PenaltyRepository(stale)


class TestContentHash:
    def test_hash_covers_only_verified_rows(self, repo: PenaltyRepository) -> None:
        """Only verified rows can affect a decision, so only they identify the snapshot."""
        empty = repo.content_hash()
        repo.add(row())
        assert repo.content_hash() == empty  # still DRAFT
        repo.promote_to_verified("BNS_2023-303(2)", verified_by="R", verified_on=date(2026, 8, 13))
        assert repo.content_hash() != empty

    def test_hash_is_stable_across_calls(self, repo: PenaltyRepository) -> None:
        repo.add(row())
        repo.promote_to_verified("BNS_2023-303(2)", verified_by="R", verified_on=date(2026, 8, 13))
        assert repo.content_hash() == repo.content_hash()

    def test_hash_is_independent_of_insertion_order(self, tmp_path: Path) -> None:
        """Two identical databases must not claim to be different statute snapshots."""
        second = row(offence_id="BNS_2023-304(2)", section="304(2)")
        hashes: list[str] = []
        for order in ((row(), second), (second, row())):
            with PenaltyRepository(tmp_path / f"db{len(hashes)}.sqlite3") as repository:
                for entry in order:
                    repository.add(entry)
                    repository.promote_to_verified(
                        entry.offence_id, verified_by="R", verified_on=date(2026, 8, 13)
                    )
                hashes.append(repository.content_hash())
        assert hashes[0] == hashes[1]
