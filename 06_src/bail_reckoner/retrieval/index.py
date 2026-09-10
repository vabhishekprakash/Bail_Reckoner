"""Layer A retrieval: hybrid BM25 + dense with cross-encoder reranking (M4).

Dependency provenance, per D-078's ruling (plan-naming is intent, not approval): each
library here has its own decision entry — rank_bm25 and sentence-transformers ratified in
D-080/D-081 on Abhishek's naming; FAISS declined in D-082 (exact numpy search over a
corpus of ~a thousand sections is complete recall at negligible cost; an ANN index adds a
binary dependency to approximate what brute force does exactly at this scale).

**The engine never imports any of this.** Layer C's model-free claim is a TEST
(`test_engine_boundary.py`), not a convention: retrieval serves lookup and research
surfaces, and nothing retrieved feeds a gate without the human confirmation step Layer B's
seam enforces.

Heavy models load lazily and fail loudly with the install command; nothing here degrades
silently to a weaker search than was asked for (D-064's shape applied to retrieval:
a hybrid that quietly became BM25-only would misreport its own recall).
"""

from __future__ import annotations

import re as _re
from dataclasses import dataclass
from typing import Protocol

from bail_reckoner.retrieval.corpus import Chunk

__all__ = [
    "Retriever",
    "Bm25Index",
    "DenseIndex",
    "HybridRetriever",
    "RoutedRetriever",
    "RoutedResult",
    "CrossActAmbiguity",
    "CrossEncoderReranker",
    "tokenize",
]

_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def tokenize(text: str) -> list[str]:
    return [t for t in "".join(c.lower() if c.isalnum() else " " for c in text).split() if t]


class Retriever(Protocol):
    def search(self, query: str, k: int) -> list[tuple[Chunk, float]]: ...


@dataclass
class Bm25Index:
    """Lexical leg. rank_bm25 (D-080), BM25Okapi with default parameters."""

    chunks: list[Chunk]

    def __post_init__(self) -> None:
        from rank_bm25 import BM25Okapi

        self._bm25 = BM25Okapi([tokenize(c.text) for c in self.chunks])

    def search(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        scores = self._bm25.get_scores(tokenize(query))
        order = sorted(range(len(self.chunks)), key=lambda i: -scores[i])[:k]
        return [(self.chunks[i], float(scores[i])) for i in order]


@dataclass
class DenseIndex:
    """Dense leg. sentence-transformers (D-081); exact numpy search, FAISS declined (D-082)."""

    chunks: list[Chunk]

    def __post_init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(_EMBED_MODEL)
        # Untyped third-party return (an ndarray); the numpy stubs need a 3.12 parse our
        # 3.11 floor forbids, so no annotation here — the boundary type is Retriever.
        self._embeddings = self._model.encode(
            [c.text[:2000] for c in self.chunks],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def search(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        query_vector = self._model.encode([query], normalize_embeddings=True)[0]
        scores = self._embeddings @ query_vector
        order = sorted(range(len(self.chunks)), key=lambda i: -float(scores[i]))[:k]
        return [(self.chunks[i], float(scores[i])) for i in order]


@dataclass
class HybridRetriever:
    """Reciprocal-rank fusion over the two legs, optional cross-encoder rerank on top.

    RRF rather than score interpolation: BM25 and cosine scores live on incomparable
    scales, and rank fusion needs no tuned weight that nobody here could justify.
    """

    lexical: Retriever
    dense: Retriever
    reranker: CrossEncoderReranker | None = None
    rrf_k: int = 60

    def search(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        pool = max(k * 5, 25)
        fused: dict[str, tuple[Chunk, float]] = {}
        for leg in (self.lexical, self.dense):
            for rank, (chunk, _) in enumerate(leg.search(query, pool)):
                score = 1.0 / (self.rrf_k + rank + 1)
                if chunk.chunk_id in fused:
                    fused[chunk.chunk_id] = (chunk, fused[chunk.chunk_id][1] + score)
                else:
                    fused[chunk.chunk_id] = (chunk, score)
        candidates = sorted(fused.values(), key=lambda item: -item[1])
        if self.reranker is not None:
            candidates = self.reranker.rerank(query, [c for c, _ in candidates[:pool]])
        return candidates[:k]


_CITATION_SHAPED = _re.compile(r"(?i)\b(?:s\.?|sec\.?|section)\s*(?P<num>\d+[A-Z]{0,2})")

# Aliases a query can name an act by. Word-boundary matched, so "BNS" never fires inside
# "BNSS". Keys are the corpus's act labels.
_ACT_ALIASES: dict[str, tuple[str, ...]] = {
    "IPC 1860": ("IPC", "Indian Penal Code"),
    "BNS 2023": ("BNS", "Bharatiya Nyaya Sanhita"),
    "BNSS 2023": ("BNSS", "Bharatiya Nagarik Suraksha Sanhita"),
    "NDPS 1985": ("NDPS", "Narcotic Drugs"),
    "PMLA 2002": ("PMLA", "Money-Laundering", "Money Laundering"),
    "UAPA 1967": ("UAPA", "Unlawful Activities"),
    "Companies Act 2013": ("Companies",),
    "POCSO 2012": ("POCSO", "Protection of Children"),
}


def _acts_named_in(query: str) -> set[str]:
    named: set[str] = set()
    for act, aliases in _ACT_ALIASES.items():
        for alias in aliases:
            if _re.search(rf"(?i)\b{_re.escape(alias)}\b", query):
                named.add(act)
                break
    return named


@dataclass(frozen=True)
class CrossActAmbiguity:
    """A citation query named a section but no act, and that section number exists in more
    than one act of the corpus (510 of 723 distinct numbers do — the collision is the norm,
    not an edge case). Ranking one act's section as if the question were answered is the
    project's recorded failure shape: a plausible answer where a refusal belongs."""

    section: str
    acts: tuple[str, ...]
    note: str


@dataclass
class RoutedResult:
    """`results` plus what the router knows about the query. When `ambiguity` is set, the
    leading results are one chunk per colliding act — DIRECTORY LOOKUPS in act-name order,
    scored 0.0 because nothing ranked them — followed by ordinary lexical results."""

    results: list[tuple[Chunk, float]]
    query_class: str
    ambiguity: CrossActAmbiguity | None


@dataclass
class RoutedRetriever:
    """Deterministic query-class routing (measured, 2026-08-19): a citation-shaped query
    ("section 479 BNSS") goes to the lexical leg alone, everything else to the hybrid.

    The measurement that forced this: dense retrieval scores 0.000 on citation queries —
    embeddings cannot distinguish "section 479" from "section 480" — and through RRF that
    zero POISONS the hybrid (citation R@10: BM25 0.842, hybrid 0.158). The router is a
    regex, not a model; nothing here guesses.

    Cross-act mitigation (D-086): pass `chunks` and an act-less citation query whose
    section number exists in several acts surfaces every act's section, labelled, instead
    of silently ranking one. Without `chunks` the collision stays unmitigated — callers
    that can supply the corpus should."""

    lexical: Retriever
    hybrid: Retriever
    chunks: tuple[Chunk, ...] | None = None

    def __post_init__(self) -> None:
        directory: dict[str, dict[str, Chunk]] = {}
        for chunk in self.chunks or ():
            directory.setdefault(chunk.section, {}).setdefault(chunk.act, chunk)
        self._by_section = directory

    def search(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        return self.route(query, k).results

    def route(self, query: str, k: int) -> RoutedResult:
        match = _CITATION_SHAPED.search(query)
        if not match:
            return RoutedResult(self.hybrid.search(query, k), "natural", None)
        section = match.group("num")
        holders = self._by_section.get(section, {})
        if len(holders) > 1 and not _acts_named_in(query):
            acts = tuple(sorted(holders))
            exact = [(holders[act], 0.0) for act in acts]
            seen = {chunk.chunk_id for chunk, _ in exact}
            fill = [
                (c, s) for c, s in self.lexical.search(query, k) if c.chunk_id not in seen
            ]
            note = (
                f"Section {section} exists in {len(acts)} acts in this corpus "
                f"({', '.join(acts)}) and the query names none of them. All are shown; "
                f"none was chosen for you — name the act to disambiguate."
            )
            return RoutedResult(
                (exact + fill)[: max(k, len(exact))],
                "citation",
                CrossActAmbiguity(section=section, acts=acts, note=note),
            )
        return RoutedResult(self.lexical.search(query, k), "citation", None)


@dataclass
class CrossEncoderReranker:
    """Cross-encoder rerank (D-081; the Extended Abstract's named final stage)."""

    def __post_init__(self) -> None:
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(_RERANK_MODEL)

    def rerank(self, query: str, chunks: list[Chunk]) -> list[tuple[Chunk, float]]:
        if not chunks:
            return []
        scores = self._model.predict([(query, c.text[:2000]) for c in chunks])
        order = sorted(range(len(chunks)), key=lambda i: -float(scores[i]))
        return [(chunks[i], float(scores[i])) for i in order]
