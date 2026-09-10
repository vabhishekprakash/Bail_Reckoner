"""Statutory-penalty database access and statute versioning.

Maps offence -> maximum prescribed sentence across IPC 1860 and BNS 2023, and resolves which
regime governs a given case. Sits outside Layer C's purity boundary: this package does the I/O,
the engine receives plain values.

Provenance is a hard schema constraint, not a convention (CLAUDE.md section 6). Every row carries
`source`, `verified_against` and `verified_on`; a row without provenance does not enter the
database, and only rows at status `verified` are readable by the engine. An offence outside the
set returns OFFENCE_NOT_IN_DATABASE. The engine never guesses a maximum sentence -- not once, not
with a caveat, not "approximately".

`statute_version` is the composite snapshot id defined by D-049:
`BNSS-2023@<consolidation-date>+pdb-<semver>+<8-hex content hash>`. It is distinct from
`law_in_force_on`, which is the date whose law the computation applied and which drives IPC vs
BNS regime selection.
"""
