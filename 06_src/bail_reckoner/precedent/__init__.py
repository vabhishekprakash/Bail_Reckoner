"""Layer D — precedent retrieval, verbatim-extract-only (M6).

Output is constrained BY CONSTRUCTION to citation, paragraph number and verbatim extract:
`PrecedentExtract` has no summary field, no headnote field, and nothing in this package
generates text — a synthesised holding is a hallucinated citation waiting to be relied on
in court (Abhishek's direction, 2026-08-19).

**Corpus status, on its face: INCOMPLETE — 3 of 4 judgments.** *Satender Kumar Antil*
(judiciary-mirror provenance, caveat in SOURCES.md entry 11), *Badshah Majid Malik* and
*K.A. Najeeb* (both from the Supreme Court's own API) are on disk with SHA-256 records;
*K. Ramakrishna* (Karnataka HC) failed acquisition at primary and is recorded as absent in
SOURCES.md, not substituted from an aggregator. Every search result carries this status.
"""

from bail_reckoner.precedent.corpus import (
    CORPUS_STATUS,
    JudgmentParagraph,
    build_precedent_corpus,
)
from bail_reckoner.precedent.search import PrecedentExtract, PrecedentIndex

__all__ = [
    "CORPUS_STATUS",
    "JudgmentParagraph",
    "build_precedent_corpus",
    "PrecedentExtract",
    "PrecedentIndex",
]
