"""Load signed penalty rows from the review queue into the SQLite store (M1, D-046).

The review queue (`02_data/penalty_rows/REVIEW_QUEUE_2026-08-26.yaml`) is the reviewable text a
person signs, row by row, after reading the printed statute page. This module is the only path
from that file into `PenaltyRepository`, and it carries the design position of the whole
database: a row enters as DRAFT and is promoted by a named person, never inserted as VERIFIED.

Two failure classes are treated differently on purpose. An **unsigned** row (`status: DRAFT`)
is the normal state of most of the file and is skipped and counted. A row that **claims**
`VERIFIED` but is incomplete, or still carries the drafting placeholder, raises: downstream it
would be indistinguishable from a real row, and it would determine a release date.

Nothing here infers a statutory value. `special_statute` is read from the file, never derived
from the regime; `maximum` is built from what the reviewer typed, never from the extractor
output stored beside it (D-064).
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from bail_reckoner.statutes.curation import DRAFTED_BY
from bail_reckoner.statutes.models import (
    MaximumPunishment,
    OffenceRow,
    Provenance,
    PunishmentKind,
    Regime,
    RowStatus,
)
from bail_reckoner.statutes.repository import DEFAULT_DB_PATH, PenaltyRepository

__all__ = ["ReviewQueueError", "DEFAULT_QUEUE_PATH", "load_verified_rows", "build_database"]

DEFAULT_QUEUE_PATH = (
    Path(__file__).resolve().parents[3]
    / "02_data"
    / "penalty_rows"
    / "REVIEW_QUEUE_2026-08-26.yaml"
)


class ReviewQueueError(ValueError):
    """The queue file, or one row in it, cannot be loaded. The message names the row."""


# Keys a SIGNED row must carry. `READ_THIS_PAGE` is the row's `verified_against` (the mapping
# recorded in the file's header); `quoted_clause` is the row's `quoted_text` -- the YAML key
# says what the reviewer does, the model field says what it is.
_SIGNED_REQUIRED = {
    "offence_id",
    "label",
    "regime",
    "section",
    "variant",
    "counterpart_id",
    "special_statute",
    "special_statute_provision",
    "maximum",
    "min_term_months",
    "quoted_clause",
    "verified_on",
    "compoundable",
    "status",
    "source",
    "READ_THIS_PAGE",
    "verified_by",
}
# Review-sheet metadata the loader reads past. `notes` is emitted by export_drafts and kept.
_ROW_ALLOWED = _SIGNED_REQUIRED | {
    "priority",
    "definition_punishment_split",
    "state_amendment_present",
    "extractor_output_do_not_rely_on",
    "notes",
}
_MAXIMUM_ALLOWED = {"kinds", "term_months", "fine_also", "reference_note"}
# `fine_also` is required, not defaulted: it is a statutory fact the report shows, and a
# reviewer who left it out has not read for it (D-064). `term_months` and `reference_note`
# are conditional on `kinds`, which MaximumPunishment enforces.
_MAXIMUM_REQUIRED = {"kinds", "fine_also"}
# The four fields a signature consists of. Null or blank on a VERIFIED row is a half-signed
# row, the one failure that must never pass quietly.
_SIGNATURE_FIELDS = ("maximum", "quoted_clause", "verified_by", "verified_on")

_NONE_LITERAL = "None"


def _fail(where: str, message: str) -> ReviewQueueError:
    return ReviewQueueError(f"{where}: {message}")


def _check_keys(where: str, got: dict[str, Any], allowed: set[str], required: set[str]) -> None:
    if unknown := set(got) - allowed:
        raise _fail(where, f"unrecognised key(s) {sorted(unknown)}")
    if missing := required - set(got):
        raise _fail(where, f"missing required key(s) {sorted(missing)}")


def _str(where: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _fail(where, f"expected a non-empty string, got {value!r}")
    return value.strip()


def _opt_str(where: str, value: object) -> str | None:
    """A string or YAML null. The four-character string 'None' is refused.

    `export_drafts` once wrote Python's repr(None) here, which YAML reads as text. A row
    carrying it would enter the database with a variant literally named "None", so the loader
    surfaces it as a visible gap instead (the pattern curation.py uses for unresolved seeds).
    """
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == _NONE_LITERAL:
        raise _fail(where, "the string 'None' is not a null; use YAML null")
    return _str(where, value)


def _opt_positive_int(where: str, value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise _fail(where, f"expected a positive integer or null, got {value!r}")
    return value


def _opt_bool(where: str, value: object) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise _fail(where, f"expected true, false or null, got {value!r}")
    return value


def _as_date(where: str, value: object) -> date:
    """Accept a YAML-native date or an ISO-8601 string, as the decision-table loader does."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError as exc:
            raise _fail(where, f"not an ISO-8601 date: {value!r}") from exc
    raise _fail(where, f"expected a date, got {value!r}")


def _blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _parse_maximum(where: str, raw: object) -> MaximumPunishment:
    if not isinstance(raw, dict):
        raise _fail(where, f"maximum must be a mapping with kinds and fine_also, got {raw!r}")
    _check_keys(where, raw, _MAXIMUM_ALLOWED, _MAXIMUM_REQUIRED)

    kinds_raw = raw["kinds"]
    if not isinstance(kinds_raw, list) or not kinds_raw:
        raise _fail(where, f"maximum.kinds must be a non-empty list, got {kinds_raw!r}")
    kinds: set[PunishmentKind] = set()
    for name in kinds_raw:
        if not isinstance(name, str) or name not in PunishmentKind.__members__:
            raise _fail(
                where,
                f"maximum.kinds entry {name!r} is not one of "
                f"{sorted(PunishmentKind.__members__)}",
            )
        kinds.add(PunishmentKind[name])

    fine_also = raw["fine_also"]
    if not isinstance(fine_also, bool):
        raise _fail(where, f"maximum.fine_also must be true or false, got {fine_also!r}")

    note_raw = raw.get("reference_note", "")
    if note_raw is None:
        note_raw = ""
    if not isinstance(note_raw, str):
        raise _fail(where, f"maximum.reference_note must be a string, got {note_raw!r}")

    try:
        return MaximumPunishment(
            kinds=frozenset(kinds),
            term_months=_opt_positive_int(f"{where} maximum.term_months", raw.get("term_months")),
            fine_also=fine_also,
            reference_note=note_raw.strip(),
        )
    except ValueError as exc:
        raise _fail(where, f"maximum is inconsistent: {exc}") from exc


def _row_status(where: str, raw: dict[str, Any]) -> RowStatus:
    """`DRAFT` or `VERIFIED`, exactly. A misspelt status is an error, not an unsigned row."""
    value = raw.get("status")
    if not isinstance(value, str) or value not in RowStatus.__members__:
        raise _fail(where, f"status must be DRAFT or VERIFIED, got {value!r}")
    return RowStatus[value]


def _parse_signed_row(where: str, raw: dict[str, Any], limbs_in_section: int) -> OffenceRow:
    _check_keys(where, raw, _ROW_ALLOWED, _SIGNED_REQUIRED)

    half_signed = [name for name in _SIGNATURE_FIELDS if _blank(raw[name])]
    if half_signed:
        raise _fail(
            where,
            f"claims VERIFIED but {half_signed} is null or blank -- a half-signed row; "
            f"fill every field from the page or set status back to DRAFT",
        )

    verified_by = _str(f"{where} verified_by", raw["verified_by"])
    if verified_by == DRAFTED_BY:
        raise _fail(
            where,
            f"claims VERIFIED but verified_by is still the drafting placeholder "
            f"{DRAFTED_BY!r}; a person's name is required",
        )

    regime_raw = raw["regime"]
    if not isinstance(regime_raw, str) or regime_raw not in Regime.__members__:
        raise _fail(where, f"regime {regime_raw!r} is not one of {sorted(Regime.__members__)}")
    regime = Regime[regime_raw]

    variant = _opt_str(f"{where} variant", raw["variant"])
    if variant is None and limbs_in_section > 1:
        raise _fail(
            where,
            f"section has {limbs_in_section} limb rows but this one names no variant; header "
            f"step 4 requires the statutory limb as printed and an offence_id ending '#<variant>'",
        )

    special_statute = _opt_str(f"{where} special_statute", raw["special_statute"])
    provision = _opt_str(f"{where} special_statute_provision", raw["special_statute_provision"])

    notes_raw = raw.get("notes", "")
    if notes_raw is None:
        notes_raw = ""
    if not isinstance(notes_raw, str):
        raise _fail(where, f"notes must be a string, got {notes_raw!r}")

    try:
        provenance = Provenance(
            source=_str(f"{where} source", raw["source"]),
            verified_against=_str(f"{where} READ_THIS_PAGE", raw["READ_THIS_PAGE"]),
            verified_on=_as_date(f"{where} verified_on", raw["verified_on"]),
            verified_by=verified_by,
            quoted_text=_str(f"{where} quoted_clause", raw["quoted_clause"]),
        )
        return OffenceRow(
            offence_id=_str(f"{where} offence_id", raw["offence_id"]),
            label=_str(f"{where} label", raw["label"]),
            regime=regime,
            section=_str(f"{where} section", raw["section"]),
            maximum=_parse_maximum(where, raw["maximum"]),
            provenance=provenance,
            # Inserted as DRAFT; `build_database` promotes it by name (D-046).
            status=RowStatus.DRAFT,
            special_statute=special_statute,
            special_statute_provision=provision,
            compoundable=_opt_bool(f"{where} compoundable", raw["compoundable"]),
            counterpart_id=_opt_str(f"{where} counterpart_id", raw["counterpart_id"]),
            variant=variant,
            min_term_months=_opt_positive_int(f"{where} min_term_months", raw["min_term_months"]),
            notes=notes_raw,
        )
    except ValueError as exc:  # ProvenanceError is a ValueError
        raise _fail(where, str(exc)) from exc


def load_verified_rows(path: Path | None = None) -> tuple[list[OffenceRow], int]:
    """Signed rows as `OffenceRow` objects, and the count of unsigned rows skipped.

    The skipped count is returned rather than logged because "loaded 5 rows" on its own says
    nothing about whether the other 81 were skipped as expected or lost to a parsing slip.
    Raises `ReviewQueueError` naming the file and the row on anything unexpected.
    """
    import yaml

    queue_path = path or DEFAULT_QUEUE_PATH
    try:
        raw_bytes = queue_path.read_bytes()
    except OSError as exc:
        raise ReviewQueueError(f"cannot read review queue at {queue_path}: {exc}") from exc
    try:
        data = yaml.safe_load(raw_bytes.decode("utf-8"))
    except yaml.YAMLError as exc:
        raise ReviewQueueError(f"{queue_path}: invalid YAML: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        raise ReviewQueueError(f"{queue_path}: top level must be a mapping with a `rows` list")
    rows_raw: list[object] = data["rows"]

    # Limb counts per (regime, section) over the WHOLE file, signed or not: a signed row of a
    # multi-limb section must name its limb even while its siblings are still unsigned.
    limbs: dict[tuple[object, object], int] = {}
    for entry in rows_raw:
        if isinstance(entry, dict):
            key = (entry.get("regime"), entry.get("section"))
            limbs[key] = limbs.get(key, 0) + 1

    loaded: list[OffenceRow] = []
    skipped = 0
    for index, entry in enumerate(rows_raw):
        if not isinstance(entry, dict):
            raise ReviewQueueError(f"{queue_path}: rows[{index}]: expected a mapping")
        where = f"{queue_path}: rows[{index}] {entry.get('offence_id', '<no offence_id>')!r}"
        if _row_status(where, entry) is RowStatus.DRAFT:
            skipped += 1
            continue
        loaded.append(
            _parse_signed_row(where, entry, limbs[(entry.get("regime"), entry.get("section"))])
        )
    return loaded, skipped


def build_database(path: Path | None = None, db_path: Path | None = None) -> dict[str, int]:
    """Rebuild the penalty store from the queue. Returns `PenaltyRepository.counts()`.

    The store is a derived artefact (gitignored), so an existing file is deleted first; that is
    also what `PenaltyRepository` asks for on a schema-version mismatch. Every row is added as
    DRAFT and then promoted through `promote_to_verified`, which demands the reviewer's name
    and refuses if no DRAFT row matched -- the stricter of the two paths `add` allows, and the
    one that matches the design position that promotion is a deliberate act by a person.
    """
    rows, _skipped = load_verified_rows(path)
    target = db_path or DEFAULT_DB_PATH
    if target.exists():
        target.unlink()
    with PenaltyRepository(target) as repository:
        for row in rows:
            repository.add(row)
            repository.promote_to_verified(
                row.offence_id,
                verified_by=row.provenance.verified_by,
                verified_on=row.provenance.verified_on,
            )
        return repository.counts()
