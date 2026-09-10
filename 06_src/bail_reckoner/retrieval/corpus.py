"""Layer A corpus: hierarchy-aware chunks from the stored bare acts (M4).

The chunker IS the existing section parser (Abhishek's direction): `bare_act` carries four
fixed extraction defects, structural boundary discrimination (D-070) and discard reporting,
none of which a fresh chunker would have. One chunk = one statutory section, sliced exactly
as the penalty-row pipeline slices it.

Every chunk carries the source document's SHA-256 (from SOURCES.md — the same record the
integrity test re-hashes) and the act's in-force/as-on date, so a retrieved chunk is
citable to a verified document version, never to "the corpus".

Data discipline (DPDP Act, Abhishek's direction): this corpus is STATUTORY TEXT ONLY —
gazette and India Code documents. No charge sheets, no case records, no scraping, and
nothing in this module accepts a path outside `01_law/`.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from bail_reckoner.statutes.bare_act import _AMENDMENT_MARKER, BareAct
from bail_reckoner.statutes.sources import LAW_DIR, accepted_sources

__all__ = ["Chunk", "build_corpus", "load_corpus", "DEFAULT_CORPUS_PATH"]

# Derived artefact (02_data per the repo layout: "corpora, indexes"); rebuilt from 01_law,
# never edited by hand, gitignored.
DEFAULT_CORPUS_PATH = (
    Path(__file__).resolve().parents[3] / "02_data" / "corpus" / "statute_chunks.jsonl"
)

# Which accepted sources are section-structured acts this chunker understands. The two
# cross-check copies are deliberately excluded (their primaries are in), as is nothing else:
# every accepted primary act is in the corpus.
_ACT_FILES: dict[str, str] = {
    "BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf": "BNS 2023",
    "IPC_1860_Act45_IndiaCode_repealed_file.pdf": "IPC 1860",
    "BNSS_2023_Act46_Gazette_2023-12-25_MHA.pdf": "BNSS 2023",
    "NDPS_1985_Act61_IndiaCode_asOn_2022-01-03.pdf": "NDPS 1985",
    "POCSO_2012_Act32_IndiaCode_asOn_2023-02-28.pdf": "POCSO 2012",
    "UAPA_1967_Act37_MHA_amended_to_2019.pdf": "UAPA 1967",
    "PMLA_2002_Act15_IndiaCode_amended_to_2019.pdf": "PMLA 2002",
    "CompaniesAct_2013_Act18_IndiaCode_amended_to_2021.pdf": "Companies Act 2013",
}

# The in-force / as-on date each stored copy represents, from SOURCES.md's provenance notes.
# Where the source prints no as-on date, this is the inferred-from-apparatus date and the
# chunk says so via `date_basis`.
_AS_ON: dict[str, tuple[str, str]] = {
    "BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf": ("2023-12-25", "gazette publication date"),
    "IPC_1860_Act45_IndiaCode_repealed_file.pdf": ("2023-12-25", "repealed text; apparatus"),
    "BNSS_2023_Act46_Gazette_2023-12-25_MHA.pdf": ("2023-12-25", "gazette publication date"),
    "NDPS_1985_Act61_IndiaCode_asOn_2022-01-03.pdf": ("2022-01-03", "printed as-on date"),
    "POCSO_2012_Act32_IndiaCode_asOn_2023-02-28.pdf": ("2023-02-28", "printed as-on date"),
    "UAPA_1967_Act37_MHA_amended_to_2019.pdf": ("2019-12-31", "inferred from apparatus"),
    "PMLA_2002_Act15_IndiaCode_amended_to_2019.pdf": ("2019-12-31", "inferred from apparatus"),
    "CompaniesAct_2013_Act18_IndiaCode_amended_to_2021.pdf": (
        "2021-12-31",
        "inferred from apparatus",
    ),
}


@dataclass(frozen=True, slots=True)
class Chunk:
    """One statutory section, citable to a verified document version."""

    chunk_id: str
    act: str
    section: str
    text: str
    source_file: str
    source_sha256: str
    """The acquisition-time SHA-256 from SOURCES.md — the chunk's statute version."""

    as_on: str
    date_basis: str
    printed_page: str


_HEADING = re.compile(rf"(?m)^\s*{_AMENDMENT_MARKER}(?P<num>\d+[A-Z]{{0,2}})\s*\.")


def _sections_in(act: BareAct) -> list[str]:
    """Every section number whose heading appears somewhere in the act, in numeric order."""
    seen: set[str] = set()
    for page in act._pages():
        for match in _HEADING.finditer(page):
            seen.add(match.group("num"))

    def key(section: str) -> tuple[int, str]:
        digits = re.match(r"\d+", section)
        return (int(digits.group()) if digits else 0, section)

    return sorted(seen, key=key)


def build_corpus(out_path: Path | None = None) -> tuple[list[Chunk], list[str]]:
    """Chunk every accepted primary act. Returns (chunks, discard/report lines).

    Discards are REPORTED, never silent (D-070): a section number whose every candidate
    body was rejected appears in the report with the parser's stated reasons.
    """
    shas = {name: sha for name, sha, _ in accepted_sources()}
    chunks: list[Chunk] = []
    report: list[str] = []

    for filename, act_name in _ACT_FILES.items():
        if not (LAW_DIR / filename).is_file():
            report.append(f"{filename}: MISSING from 01_law/ — act skipped, not silently")
            continue
        act = BareAct.open(filename)
        as_on, basis = _AS_ON[filename]
        sha = shas.get(filename, "")
        if not sha:
            report.append(f"{filename}: no SHA-256 in SOURCES.md — act skipped (C5)")
            continue
        found = 0
        for section in _sections_in(act):
            discards: list[str] = []
            result = act.find_section(section, discards=discards)
            if result is None:
                for line in discards:
                    report.append(f"{act_name} s.{section}: {line}")
                continue
            found += 1
            chunks.append(
                Chunk(
                    chunk_id=f"{act_name.replace(' ', '_')}-s{section}",
                    act=act_name,
                    section=section,
                    text=" ".join(result.text.split()),
                    source_file=filename,
                    source_sha256=sha,
                    as_on=as_on,
                    date_basis=basis,
                    printed_page=result.printed_page,
                )
            )
        report.append(f"{act_name}: {found} sections chunked")

    target = out_path or DEFAULT_CORPUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
    return chunks, report


def load_corpus(path: Path | None = None) -> list[Chunk]:
    source = path or DEFAULT_CORPUS_PATH
    chunks: list[Chunk] = []
    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                chunks.append(Chunk(**json.loads(line)))
    return chunks
