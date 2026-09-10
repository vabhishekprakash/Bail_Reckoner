"""Append-only audit log (CLAUDE.md §6: "Audit log is append-only. No update path, no
delete path." M7: not stubbable).

Every computation the API performs appends one JSON line: when, which endpoint, which mode,
the inputs hash, the statute version, and the verdict reached. No row is ever rewritten or
removed — the module exposes no update or delete, the file is opened in append mode only,
and each line carries the SHA-256 of the previous line so an edited or inserted line breaks
the chain visibly.

**Truncation (Abhishek, 2026-08-19):** a hash chain alone does not detect deletion from the
END — the survivors stay contiguous and the chain still verifies. So the log keeps a
head-state sidecar (`<log>.head.json`) holding the entry count and the hash of the last
line, updated on every append; `verify_chain` compares the log against it, so a truncated
log fails verification. Honest limit, stated rather than implied away: the sidecar lives on
the same host, so an attacker who can delete log lines may also delete or rewrite the
sidecar. Full protection requires the deployment to place or mirror the sidecar on storage
the log's writer cannot reach (a different volume, a write-once store, or periodic export);
the mechanism here makes truncation DETECTABLE on any host where the sidecar survives, which
is what the immutability claim in the Extended Abstract can honestly rest on.

Wall-clock time is permitted here, deliberately: the audit log records when the system was
USED, which is a fact about the world, not part of the deterministic computation. Layer C
still never touches a clock; `Decision.timestamp` remains the caller-supplied `evaluated_on`.
"""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

__all__ = ["AuditLog"]

_GENESIS = "0" * 64


class AuditLog:
    """Append-only JSONL with a hash chain and a head-state sidecar. One instance per file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._head_path = path.with_name(path.name + ".head.json")
        path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self) -> str:
        if not self._path.is_file():
            return _GENESIS
        last = ""
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last = line
        if not last:
            return _GENESIS
        return hashlib.sha256(last.strip().encode("utf-8")).hexdigest()

    def _read_head_state(self) -> tuple[int, str] | None:
        if not self._head_path.is_file():
            return None
        state = json.loads(self._head_path.read_text(encoding="utf-8"))
        return int(state["count"]), str(state["head"])

    def append(self, record: dict[str, str | int]) -> None:
        """Append one record and advance the head state. The only write operation."""
        entry = dict(record)
        entry["at"] = datetime.datetime.now(datetime.UTC).isoformat()
        entry["prev"] = self._last_hash()
        line = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        state = self._read_head_state()
        count = (state[0] if state else 0) + 1
        head = hashlib.sha256(line.encode("utf-8")).hexdigest()
        self._head_path.write_text(json.dumps({"count": count, "head": head}), encoding="utf-8")

    def verify_chain(self) -> bool:
        """True iff the chain links AND the log matches the persisted head state.

        The head-state comparison is what detects truncation: deletion from the end leaves
        a contiguous, internally-consistent chain, but the count shrinks and the head hash
        no longer matches the recorded one.
        """
        count = 0
        expected = _GENESIS
        last_line_hash = _GENESIS
        if self._path.is_file():
            with self._path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if entry.get("prev") != expected:
                        return False
                    expected = hashlib.sha256(line.strip().encode("utf-8")).hexdigest()
                    last_line_hash = expected
                    count += 1
        state = self._read_head_state()
        if state is None:
            # No head state: acceptable only for a log with no entries.
            return count == 0
        return state == (count, last_line_hash)
