"""Storage and retrieval for the statutory-penalty database (D-027).

Outside Layer C's purity boundary: this module opens files and talks to SQLite. The engine is
handed plain `OffenceRow` values and never queries anything.

Two invariants, both enforced by the database rather than only here (see `schema.sql`):

* **A row without provenance does not enter the database.** CHECK constraints on every provenance
  column, so a direct SQL insert cannot bypass the rule either.
* **DRAFT rows are unreachable from the engine.** Engine-facing reads go through the
  `verified_offence` view, so an unverified maximum cannot reach a decision path by mistake.

Promotion from DRAFT to VERIFIED is a separate, explicit call that demands a human's name. A
model may draft a row; a person accepts it (D-046).
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from bail_reckoner.statutes.models import (
    MaximumPunishment,
    OffenceRow,
    Provenance,
    PunishmentKind,
    Regime,
    RowStatus,
    is_wellformed_section,
)

__all__ = ["PenaltyRepository", "RepositoryError", "DEFAULT_DB_PATH", "SCHEMA_PATH"]

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "02_data" / "penalties.sqlite3"


class RepositoryError(RuntimeError):
    """A row was rejected, or an operation would have violated an invariant."""


_COLUMNS = (
    "offence_id, label, regime, section, variant, min_term_months, "
    "kinds, term_months, fine_also, reference_note, "
    "special_statute, special_statute_provision, compoundable, counterpart_id, notes, "
    "source, verified_against, verified_on, verified_by, quoted_text, status"
)
_COLUMN_COUNT = 21

_SCHEMA_VERSION = 3
"""Must match `PRAGMA user_version` in schema.sql. The .sqlite3 file is a derived artefact; on a
mismatch the honest move is delete-and-rebuild, and the repository says so rather than running
against half the columns."""


class PenaltyRepository:
    """SQLite-backed store for offence -> maximum-sentence rows.

    Usable as a context manager. The connection is opened with foreign keys and, importantly,
    with CHECK enforcement left at SQLite's default (always on) -- there is no "fast" mode that
    skips constraints, by design.
    """

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        if self.db_path.parent != Path(":memory:").parent:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        existing = self._conn.execute("PRAGMA user_version").fetchone()[0]
        has_tables = self._conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0]
        if has_tables and existing != _SCHEMA_VERSION:
            self._conn.close()
            raise RepositoryError(
                f"{self.db_path} is at schema version {existing}, this code expects "
                f"{_SCHEMA_VERSION}. The database is a derived build artefact regenerated from "
                f"the reviewed YAML in 02_data/penalty_rows/ — delete the file and rebuild it. "
                f"Running against a mismatched schema would fail on some columns and silently "
                f"succeed on others."
            )
        self._conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        self._conn.commit()

    def __enter__(self) -> PenaltyRepository:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    # ---------------------------------------------------------------- writes

    def add(self, row: OffenceRow) -> None:
        """Insert a row. Raises `RepositoryError` if the database rejects it.

        Rows arrive as DRAFT unless explicitly constructed otherwise; nothing here promotes one.
        """
        if not is_wellformed_section(row.section):
            raise RepositoryError(
                f"{row.offence_id}: section {row.section!r} is not a well-formed reference"
            )
        try:
            self._conn.execute(
                f"INSERT INTO offence ({_COLUMNS}) VALUES ({', '.join('?' * _COLUMN_COUNT)})",
                (
                    row.offence_id,
                    row.label,
                    row.regime.value,
                    row.section,
                    row.variant,
                    row.min_term_months,
                    ",".join(sorted(k.value for k in row.maximum.kinds)),
                    row.maximum.term_months,
                    int(row.maximum.fine_also),
                    row.maximum.reference_note,
                    row.special_statute,
                    row.special_statute_provision,
                    None if row.compoundable is None else int(row.compoundable),
                    row.counterpart_id,
                    row.notes,
                    row.provenance.source,
                    row.provenance.verified_against,
                    row.provenance.verified_on.isoformat(),
                    row.provenance.verified_by,
                    row.provenance.quoted_text,
                    row.status.value,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise RepositoryError(f"{row.offence_id}: rejected by the database — {exc}") from exc
        self._conn.commit()

    def promote_to_verified(self, offence_id: str, *, verified_by: str, verified_on: date) -> None:
        """Mark a DRAFT row VERIFIED after a human has checked it against the bare act (D-046).

        A separate, explicit call rather than a flag on `add`, and it demands a person's name.
        The whole value of the draft/verified split is that promotion is a deliberate act by
        someone who read the statute, not a default that happens on the way in.
        """
        if not verified_by.strip():
            raise RepositoryError("promotion requires the name of the person who verified the row")
        cursor = self._conn.execute(
            "UPDATE offence SET status = 'VERIFIED', verified_by = ?, verified_on = ? "
            "WHERE offence_id = ? AND status = 'DRAFT'",
            (verified_by.strip(), verified_on.isoformat(), offence_id),
        )
        if cursor.rowcount == 0:
            raise RepositoryError(f"{offence_id}: no DRAFT row to promote")
        self._conn.commit()

    # ----------------------------------------------------------------- reads

    def get(self, offence_id: str, *, verified_only: bool = True) -> OffenceRow | None:
        """Fetch one row. Reads the verified view by default.

        `verified_only=False` exists for curation and review tooling only. Nothing on a decision
        path may pass it.
        """
        table = "verified_offence" if verified_only else "offence"
        cursor = self._conn.execute(
            f"SELECT {_COLUMNS} FROM {table} WHERE offence_id = ?", (offence_id,)
        )
        record = cursor.fetchone()
        return _to_row(record) if record else None

    def find_variants(
        self, regime: Regime, section: str, *, verified_only: bool = True
    ) -> tuple[OffenceRow, ...]:
        """Every limb of a section, in variant order. May be empty."""
        table = "verified_offence" if verified_only else "offence"
        cursor = self._conn.execute(
            f"SELECT {_COLUMNS} FROM {table} WHERE regime = ? AND section = ? ORDER BY offence_id",
            (regime.value, section),
        )
        return tuple(_to_row(record) for record in cursor)

    def resolve(
        self, regime: Regime, section: str, variant: str | None = None
    ) -> OffenceRow | None:
        """The row for a charge, or None where the engine must abstain.

        Provision context: which limb applies is a fact about the charge as framed (L-001), so
        the engine never picks one for the user. Semantics, in order:

        * variant named → that exact limb, or None if it does not exist;
        * variant not named and the section has exactly one verified limb → that limb, since
          there is nothing to choose between;
        * variant not named and the section has several limbs → **None**. Ambiguity is
          `OFFENCE_NOT_IN_DATABASE`, not a guess — returning the highest maximum here would
          quietly answer L-001, and returning any limb would attach a maximum nobody charged.

        Reads verified rows only: this is the lookup that feeds gates 0 and 5.
        """
        rows = self.find_variants(regime, section, verified_only=True)
        if variant is not None:
            for row in rows:
                if row.variant == variant:
                    return row
            return None
        if len(rows) == 1:
            return rows[0]
        return None

    def all_rows(self, *, verified_only: bool = True) -> Iterator[OffenceRow]:
        table = "verified_offence" if verified_only else "offence"
        for record in self._conn.execute(f"SELECT {_COLUMNS} FROM {table} ORDER BY offence_id"):
            yield _to_row(record)

    def counts(self) -> dict[str, int]:
        """Row counts by status, for milestone reporting."""
        rows = self._conn.execute("SELECT status, COUNT(*) AS n FROM offence GROUP BY status")
        result = {"DRAFT": 0, "VERIFIED": 0}
        for record in rows:
            result[record["status"]] = record["n"]
        return result

    def content_hash(self) -> str:
        """SHA-256 over every VERIFIED row, for `statute_version` (D-049).

        Only verified rows count, because only they can affect a decision. Ordered by
        `offence_id` so the hash is stable regardless of insertion order -- an unstable hash
        would make two identical databases claim to be different statute snapshots.
        """
        digest = hashlib.sha256()
        for record in self._conn.execute(
            f"SELECT {_COLUMNS} FROM verified_offence ORDER BY offence_id"
        ):
            digest.update("".join(str(value) for value in tuple(record)).encode("utf-8"))
            digest.update(b"")
        return digest.hexdigest()


def _to_row(record: sqlite3.Row) -> OffenceRow:
    kinds = frozenset(PunishmentKind(k) for k in record["kinds"].split(","))
    maximum = MaximumPunishment(
        kinds=kinds,
        term_months=record["term_months"],
        fine_also=bool(record["fine_also"]),
        reference_note=record["reference_note"],
    )
    provenance = Provenance(
        source=record["source"],
        verified_against=record["verified_against"],
        verified_on=date.fromisoformat(record["verified_on"]),
        verified_by=record["verified_by"],
        quoted_text=record["quoted_text"],
    )
    return OffenceRow(
        offence_id=record["offence_id"],
        label=record["label"],
        regime=Regime(record["regime"]),
        section=record["section"],
        maximum=maximum,
        provenance=provenance,
        status=RowStatus(record["status"]),
        special_statute=record["special_statute"],
        special_statute_provision=record["special_statute_provision"],
        compoundable=None if record["compoundable"] is None else bool(record["compoundable"]),
        counterpart_id=record["counterpart_id"],
        variant=record["variant"],
        min_term_months=record["min_term_months"],
        notes=record["notes"],
    )
