"""Recurring audit-log integrity check (Abhishek, 2026-08-19).

A chain nobody runs is decoration — and a check that passes vacuously on an absent log is
decoration too (his round-13 correction): in CI or a fresh clone the runtime log does not
exist, so the original version verified nothing. On the source-integrity pattern, the
mechanism itself is now exercised on every run against a purpose-built log (append, verify,
truncate, verify again), non-vacuity asserted; the real runtime log is additionally verified
whenever it exists, and its absence is a visible SKIP, never a silent pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bail_reckoner.api.app import DEFAULT_AUDIT_PATH
from bail_reckoner.audit import AuditLog


class TestTheMechanismIsExercisedEveryRun:
    def test_chain_and_sidecar_verify_and_catch_truncation(self, tmp_path: Path) -> None:
        log_path = tmp_path / "purpose_built.jsonl"
        log = AuditLog(log_path)
        for i in range(3):
            log.append({"endpoint": "integrity-exercise", "inputs_hash": str(i)})
        assert log.verify_chain()
        # Non-vacuity guard: something was actually verified.
        lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln]
        assert len(lines) == 3, "the purpose-built log must contain what was appended"
        # And the sidecar catches truncation from the end.
        log_path.write_text("\n".join(lines[:1]) + "\n", encoding="utf-8")
        assert not AuditLog(log_path).verify_chain()


class TestRuntimeAuditLogIntegrity:
    def test_the_runtime_log_verifies_when_present(self) -> None:
        if not DEFAULT_AUDIT_PATH.is_file():
            pytest.skip(
                "runtime audit log absent (fresh clone or CI) — the mechanism is exercised "
                "by the purpose-built test above; this skip is visible, not a silent pass"
            )
        assert AuditLog(DEFAULT_AUDIT_PATH).verify_chain(), (
            f"the runtime audit log at {DEFAULT_AUDIT_PATH} fails verification — the chain "
            f"is broken or the log was truncated; investigate before trusting any entry"
        )
