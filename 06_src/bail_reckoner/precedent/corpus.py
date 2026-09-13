"""Judgment paragraph corpus for Layer D (M6).

One chunk = one numbered paragraph of a stored judgment, verbatim, keyed to the SHA-256
recorded at acquisition in SOURCES.md (the record the integrity test re-hashes). Paragraphs
the parser cannot number are NOT dropped: they attach to the preceding numbered paragraph,
so no verbatim text is silently lost — mis-attachment to a neighbouring paragraph is the
accepted cost, and the paragraph number always names where the extract STARTS.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from bail_reckoner.statutes.sources import LAW_DIR, accepted_sources

__all__ = ["JudgmentParagraph", "build_precedent_corpus", "CORPUS_STATUS", "JUDGMENTS"]

# The stored judgments, with their citations as verified at acquisition (SOURCES.md 11-13).
JUDGMENTS: dict[str, str] = {
    # D-091 (2026-09-02): swapped from the judiciary-hosted mirror to the Supreme
    # Court's own print (diary 27955/2021, api.sci.gov.in) once it was located. The
    # mirror stays on disk for the record; paragraph numbering differs between prints.
    "SatenderKumarAntil_v_CBI_SC_2022-07-11_sciAPI.pdf": (
        "Satender Kumar Antil v. CBI, MA 1849/2021 in SLP(Crl) 5191/2021, SC, 11 July 2022"
    ),
    "BadshahMajidMalik_v_ED_SC_Order_2024-10-18_sciAPI.pdf": (
        "Badshah Majid Malik v. Directorate of Enforcement, SLP(Crl) 10846/2024, SC, "
        "Order 18 October 2024"
    ),
    "UnionOfIndia_v_KANajeeb_SC_2021-02-01_sciAPI.pdf": (
        "Union of India v. K.A. Najeeb, Crl.A. 98/2021, SC, 1 February 2021"
    ),
}

CORPUS_STATUS = (
    "PRECEDENT CORPUS INCOMPLETE: 3 of 4 project-cited judgments on disk, all three now "
    "from the Supreme Court's own API (Satender Kumar Antil upgraded from a judiciary "
    "mirror on 2026-09-02, D-091). K. Ramakrishna (Karnataka HC, Crl.P. 9930/2024) is "
    "PERMANENTLY UNACQUIRED (captcha-gated primary, no aggregator substitution); "
    "citations of it remain secondary-sourced."
)

# A numbered paragraph opens at a line whose start is "<n>." followed by text. Judgments
# print these flush or lightly indented; page furniture is stripped by position.
_PARA_OPEN = re.compile(r"^\s{0,6}(\d{1,3})\s*\.\s*(?=[A-Z“\"'(])")


@dataclass(frozen=True, slots=True)
class JudgmentParagraph:
    citation: str
    para_number: int
    text: str
    source_file: str
    source_sha256: str


def _paragraphs(pages: list[str]) -> list[tuple[int, str]]:
    paragraphs: list[tuple[int, str]] = []
    current_number: int | None = None
    current_lines: list[str] = []
    last_number = 0
    for page in pages:
        for line in page.splitlines():
            match = _PARA_OPEN.match(line)
            number = int(match.group(1)) if match else None
            # Sequential-or-close guard: a "63." opening a paragraph must follow 62-ish;
            # a stray "2021." or a quoted statute's "(2)." never does.
            if number is not None and last_number < number <= last_number + 3:
                if current_number is not None:
                    paragraphs.append((current_number, " ".join(current_lines)))
                current_number = number
                last_number = number
                current_lines = [line[match.end() :].strip()] if match else []
            else:
                current_lines.append(line.strip())
    if current_number is not None:
        paragraphs.append((current_number, " ".join(current_lines)))
    return [(n, " ".join(t.split())) for n, t in paragraphs if t.strip()]


def build_precedent_corpus(law_dir: Path | None = None) -> list[JudgmentParagraph]:
    """Build the paragraph corpus from the acquired judgments.

    Hardened by the 2026-08-29 adversarial audit (a limb of the sixth-instance finding):
    this function used to `continue` past a missing judgment, default a missing SOURCES
    hash to "", and coerce a failed page extraction to "" — three silent paths that let
    the corpus shrink or lose provenance while `CORPUS_STATUS` still asserted "3 of 4 on
    disk". All three now refuse loudly: the status line is a promise about this build,
    not a slogan.
    """
    from pypdf import PdfReader

    directory = law_dir or LAW_DIR
    shas = {name: sha for name, sha, _ in accepted_sources()}
    corpus: list[JudgmentParagraph] = []
    for filename, citation in JUDGMENTS.items():
        path = directory / filename
        if not path.is_file():
            raise FileNotFoundError(
                f"{filename} is missing from {directory} — CORPUS_STATUS promises it is "
                "on disk, so building without it would attach a false status line to "
                "every result. Restore the file (its SHA-256 is in SOURCES.md) or amend "
                "JUDGMENTS and CORPUS_STATUS together, as a recorded decision."
            )
        if filename not in shas:
            raise ValueError(
                f"{filename} has no accepted-sources entry in SOURCES.md — a chunk is "
                "citable to a verified document version or it is not in the corpus."
            )
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        empty = [i for i, text in enumerate(pages) if not text.strip()]
        if empty:
            raise ValueError(
                f"{filename}: page(s) {empty} extracted no text — paragraphs on them "
                "would silently vanish from the corpus. All three judgments extract "
                "text on every page as acquired (checked 2026-08-29), so an empty page "
                "is a changed or damaged file, not a normal case."
            )
        for number, text in _paragraphs(pages):
            corpus.append(
                JudgmentParagraph(
                    citation=citation,
                    para_number=number,
                    text=text,
                    source_file=filename,
                    source_sha256=shas[filename],
                )
            )
    return corpus
