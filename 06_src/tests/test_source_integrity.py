"""Recurring source-document integrity check (Abhishek, 2026-08-19; D-073 context).

Every accepted source in `01_law/SOURCES.md` records a SHA-256 and a byte size taken at
acquisition. This test re-hashes each stored document against that record on every run.

The one-time verification during the CRLF episode worked because someone suspected something;
a bad copy, an editor write, or an LFS misconfiguration corrupts the same way and won't
announce itself. The hashing practice — adopted to prove documents are what they claim to
be — is what proved history was clean then; this test makes the proof recurring rather than
occasioned by suspicion.

A missing accepted file fails too: an accepted source that has vanished is a worse state
than a corrupted one, because nothing else would notice.
"""

from __future__ import annotations

import hashlib

from bail_reckoner.statutes.sources import LAW_DIR as _LAW_DIR
from bail_reckoner.statutes.sources import accepted_sources as _accepted_entries


class TestStoredSourcesMatchTheirRecordedHashes:
    def test_the_record_itself_is_non_trivial(self) -> None:
        entries = _accepted_entries()
        assert len(entries) >= 9, (
            "SOURCES.md parsed fewer accepted entries than are known to exist — the parser "
            "or the file structure changed; fix the test, do not weaken it"
        )

    def test_every_accepted_source_exists_and_hashes_to_its_record(self) -> None:
        failures: list[str] = []
        for filename, recorded_sha, recorded_size in _accepted_entries():
            path = _LAW_DIR / filename
            if not path.is_file():
                failures.append(f"{filename}: MISSING from 01_law/")
                continue
            data = path.read_bytes()
            if len(data) != recorded_size:
                failures.append(f"{filename}: size {len(data)} != recorded {recorded_size}")
            actual = hashlib.sha256(data).hexdigest().upper()
            if actual != recorded_sha:
                failures.append(
                    f"{filename}: SHA-256 {actual[:16]}... != recorded {recorded_sha[:16]}..."
                )
        assert not failures, "source-document integrity check failed:\n" + "\n".join(failures)
