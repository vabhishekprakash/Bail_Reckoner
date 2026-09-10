"""Source-document inventory, read from `01_law/SOURCES.md` (Abhishek, 2026-08-19).

Every report and filing carries one line stating what statutory source material is on record
and how it is verified. The motivation is operational, not decorative: two acquisition
directives were issued in one day for material already on disk, because nothing the system
produced ever said what it held. The document that leaves the system is where that knowledge
has to live.

The parser here is the same one the recurring integrity test uses — one definition of "an
accepted source entry", shared, so the inventory line and the hash check can never disagree
about what the record contains.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["accepted_sources", "source_inventory_line", "LAW_DIR", "SOURCES_PATH"]

LAW_DIR = Path(__file__).resolve().parents[3] / "01_law"
SOURCES_PATH = LAW_DIR / "SOURCES.md"

# Accepted entries only: "### n. `file`" headings followed by "- **SHA-256** `HASH` · N bytes".
# The REJECTED section's headings are URLs with no local file and are out of scope.
_ENTRY = re.compile(
    r"^### \d+\. `(?P<file>[^`]+)`.*?"
    r"^- \*\*SHA-256\*\* `(?P<sha>[0-9A-Fa-f]{64})` · (?P<size>[\d,]+) bytes",
    re.MULTILINE | re.DOTALL,
)


def accepted_sources(sources_path: Path | None = None) -> list[tuple[str, str, int]]:
    """Every accepted source entry as (filename, SHA-256 uppercase, byte size)."""
    text = (sources_path or SOURCES_PATH).read_text(encoding="utf-8")
    accepted = text.split("## REJECTED")[0]
    return [
        (m.group("file"), m.group("sha").upper(), int(m.group("size").replace(",", "")))
        for m in _ENTRY.finditer(accepted)
    ]


def source_inventory_line(sources_path: Path | None = None) -> str:
    """The one-line inventory a report or filing carries.

    Deliberately count-and-pointer, not a listing: the full inventory with hashes IS
    SOURCES.md, and duplicating it per report would rot. The count is live, so an acquisition
    changes every subsequent document's line — which is the point.
    """
    count = len(accepted_sources(sources_path))
    return (
        f"Statutory sources on record: {count} accepted documents in 01_law/ "
        f"(SOURCES.md; SHA-256 recorded at acquisition and re-verified by test)"
    )
