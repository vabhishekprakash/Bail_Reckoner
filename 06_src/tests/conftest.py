"""Shared fixtures: the drafted penalty rows, computed once per test session.

`draft_rows()` scans two bare acts for 40 sections and `draft_ndps_rows()` scans a third; each
call costs minutes. The drafts are fixture setup for the curation tests and the review-queue
round trip, not the thing under test, so paying for them once per file was waste. Session scope
is the widening of the module-scope caching test_curation.py already carried. The results are
frozen dataclasses, so sharing them across files cannot leak state.
"""

from __future__ import annotations

import pytest

from bail_reckoner.statutes.bare_act import LAW_DIR
from bail_reckoner.statutes.curation import (
    BNS_FILE,
    IPC_FILE,
    NDPS_FILE,
    DraftResult,
    draft_ndps_rows,
    draft_rows,
)


def _require(*filenames: str) -> None:
    missing = [name for name in filenames if not (LAW_DIR / name).exists()]
    if missing:
        pytest.skip(f"bare-act PDFs are not present in this checkout: {missing}")


@pytest.fixture(scope="session")
def drafted() -> DraftResult:
    """The IPC/BNS seed list drafted from the stored acts (D-046)."""
    _require(BNS_FILE, IPC_FILE)
    return draft_rows()


@pytest.fixture(scope="session")
def ndps() -> DraftResult:
    """The NDPS quantity-band rows drafted from the stored Act (D-067)."""
    _require(NDPS_FILE)
    return draft_ndps_rows()
