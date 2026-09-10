-- Statutory-penalty database schema (D-027: SQLite, written for mechanical PostgreSQL migration).
--
-- CLAUDE.md §6: "Every statutory row carries `source`, `verified_against`, `verified_on`. A row
-- without provenance does not enter the database."
--
-- That rule is enforced HERE, in CHECK constraints, rather than only in Python. A Python-only
-- guard is bypassed by any direct SQL insert -- a migration script, a fixture loader, someone at
-- a sqlite3 prompt. A maximum sentence that entered without provenance would be indistinguishable
-- from a verified one, and it determines a release date.
--
-- Portability notes for the PostgreSQL migration:
--   * INTEGER 0/1 booleans become BOOLEAN; the CHECK (x IN (0,1)) clauses are then redundant.
--   * TEXT dates in ISO-8601 become DATE.
--   * LIKE is used rather than SQLite's instr() so the CHECK clauses port unchanged.

-- Schema version. Bumped on any change to this file's shape; PenaltyRepository refuses to open
-- a database at a different version. The .sqlite3 file is a derived build artefact (gitignored)
-- regenerated from the reviewed YAML, so the correct response to a mismatch is to delete it and
-- rebuild -- never to limp along against half the columns.
PRAGMA user_version = 3;

CREATE TABLE IF NOT EXISTS offence (
    offence_id  TEXT PRIMARY KEY,
    label       TEXT NOT NULL CHECK (length(trim(label))   > 0),
    regime      TEXT NOT NULL CHECK (regime IN ('IPC_1860', 'BNS_2023', 'NDPS_1985')),
    section     TEXT NOT NULL CHECK (length(trim(section)) > 0),

    -- Which punishment limb of the section this row is (D-061). NULL only for single-limb
    -- sections. The variant is embedded in offence_id ('{regime}-{section}#{variant}') so two
    -- limbs can never share an identity; that binding is enforced below.
    variant     TEXT CHECK (variant IS NULL OR length(trim(variant)) > 0),

    -- Mandatory minimum in months where the limb prescribes one (D-061). Feeds no gate; shown
    -- in reports for honesty about what the person faces.
    min_term_months INTEGER CHECK (min_term_months IS NULL OR min_term_months > 0),

    -- Maximum punishment, as the tagged union in statutes/models.py.
    -- `kinds` is a sorted comma-separated set: DEATH, LIFE, TERM, FINE_ONLY, BY_REFERENCE.
    -- A set, not a single value, because one provision commonly prescribes several punishments
    -- (IPC s.302: "death, or imprisonment for life, and shall also be liable to fine").
    kinds           TEXT    NOT NULL CHECK (length(trim(kinds)) > 0),
    term_months     INTEGER          CHECK (term_months IS NULL OR term_months > 0),
    fine_also       INTEGER NOT NULL DEFAULT 0 CHECK (fine_also IN (0, 1)),
    reference_note  TEXT    NOT NULL DEFAULT '',

    -- Gate 3. `special_statute_provision` stays NULL for POCSO until the bare act is read
    -- (D-042/OLQ-4); the schema must permit a named statute with an unnamed provision so that
    -- nothing has to be invented to satisfy a NOT NULL.
    special_statute            TEXT,
    special_statute_provision  TEXT,

    -- NULL means not yet determined. Never defaulted to 0: unknown is not the same as "no".
    compoundable    INTEGER CHECK (compoundable IS NULL OR compoundable IN (0, 1)),

    -- The corresponding offence in the other regime. NULL is meaningful: BNS created offences
    -- with no IPC equivalent.
    counterpart_id  TEXT,
    notes           TEXT NOT NULL DEFAULT '',

    -- Provenance. Every column non-empty, enforced by the database.
    source            TEXT NOT NULL CHECK (length(trim(source))           > 0),
    verified_against  TEXT NOT NULL CHECK (length(trim(verified_against)) > 0),
    verified_on       TEXT NOT NULL CHECK (length(trim(verified_on))      > 0),
    verified_by       TEXT NOT NULL CHECK (length(trim(verified_by))      > 0),
    quoted_text       TEXT NOT NULL CHECK (length(trim(quoted_text))      > 0),

    -- DRAFT rows may be model-generated and may be wrong. Only a human moves a row to VERIFIED
    -- (D-046). DRAFT is the default: verified-by-default would make "forgot to review"
    -- indistinguishable from "reviewed".
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'VERIFIED')),

    -- A definite term and only a definite term carries a month count. Without this, a LIFE row
    -- could silently acquire a term and become arithmetic-eligible at gate 5.
    CHECK ((kinds LIKE '%TERM%') = (term_months IS NOT NULL)),

    -- A maximum defined by reference to another offence must quote the words that define it,
    -- or the row is unresolvable with no audit trail.
    CHECK ((kinds LIKE '%BY_REFERENCE%') = 0 OR length(trim(reference_note)) > 0),

    -- A provision cannot be recorded without the statute it belongs to.
    CHECK (special_statute_provision IS NULL OR special_statute IS NOT NULL),

    -- offence_id namespaces the regime, so an IPC maximum can never be read under a BNS id.
    CHECK (offence_id LIKE regime || '-%'),

    -- The variant is part of the key: an id must end '#<variant>' iff a variant is set.
    CHECK (variant IS NULL OR offence_id LIKE '%#' || variant),
    CHECK (variant IS NOT NULL OR offence_id NOT LIKE '%#%'),

    -- A minimum cannot exceed the maximum term it belongs to.
    CHECK (min_term_months IS NULL OR term_months IS NULL OR min_term_months <= term_months)
);

-- One row per (regime, section, variant). SQLite treats NULLs as distinct in UNIQUE, so
-- single-limb sections (variant NULL) rely on the offence_id PRIMARY KEY for uniqueness.
CREATE UNIQUE INDEX IF NOT EXISTS idx_offence_limb ON offence (regime, section, variant);

CREATE INDEX IF NOT EXISTS idx_offence_regime_section ON offence (regime, section);
CREATE INDEX IF NOT EXISTS idx_offence_status         ON offence (status);

-- The engine reads through this view and never the base table, so an unverified row cannot
-- reach a decision path even by mistake.
CREATE VIEW IF NOT EXISTS verified_offence AS
    SELECT * FROM offence WHERE status = 'VERIFIED';
