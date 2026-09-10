"""Precedent search: BM25 over judgment paragraphs, verbatim extracts out (M6).

`PrecedentExtract` is the whole output vocabulary: citation, paragraph number, verbatim
text, source provenance, and the standing corpus-status line. There is no summary field to
fill and no path that generates text.
"""

from __future__ import annotations

from dataclasses import dataclass

from bail_reckoner.precedent.corpus import CORPUS_STATUS, JudgmentParagraph
from bail_reckoner.retrieval.index import tokenize

__all__ = ["PrecedentExtract", "PrecedentIndex"]


@dataclass(frozen=True, slots=True)
class PrecedentExtract:
    """One verbatim extract. No summary, no headnote — by construction."""

    citation: str
    para_number: int
    verbatim_text: str
    source_file: str
    source_sha256: str
    corpus_status: str


@dataclass
class PrecedentIndex:
    paragraphs: list[JudgmentParagraph]

    def __post_init__(self) -> None:
        from rank_bm25 import BM25Okapi

        if not self.paragraphs:
            raise ValueError(
                "precedent corpus is empty — Layer D over an empty corpus is a stub and "
                "must be labelled one, never silently instantiated"
            )
        self._bm25 = BM25Okapi([tokenize(p.text) for p in self.paragraphs])

    def search(self, query: str, k: int = 5) -> list[PrecedentExtract]:
        scores = self._bm25.get_scores(tokenize(query))
        order = sorted(range(len(self.paragraphs)), key=lambda i: -scores[i])[:k]
        return [
            PrecedentExtract(
                citation=self.paragraphs[i].citation,
                para_number=self.paragraphs[i].para_number,
                verbatim_text=self.paragraphs[i].text,
                source_file=self.paragraphs[i].source_file,
                source_sha256=self.paragraphs[i].source_sha256,
                corpus_status=CORPUS_STATUS,
            )
            for i in order
            if scores[i] > 0
        ]
