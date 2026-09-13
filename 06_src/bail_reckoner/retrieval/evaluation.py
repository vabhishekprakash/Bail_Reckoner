"""Layer A evaluation: Recall@k and MRR against ground truth the project already owns (M4).

The query set derives from the 38 seed sections: each seed entry's offence label becomes a
natural-language query ("Punishment for theft"), and the correct answer is the seed's own
(regime, section) — established when the sections were located and page-verified for the
penalty pipeline. **No legal judgement enters this measurement**: it asks "does the
retriever find the section this label names", which is a retrieval fact, not a legal one.
It is therefore reportable as a claimable figure, DISTINCT from any Tier-2 number — and the
report says so on its face.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path

from bail_reckoner.retrieval.corpus import Chunk
from bail_reckoner.retrieval.index import Retriever
from bail_reckoner.statutes.curation import SEED_LIST

__all__ = [
    "Query",
    "build_query_set",
    "build_citation_query_set",
    "evaluate_retriever",
    "EvalResult",
    "write_report",
]

DEFAULT_EVAL_DIR = Path(__file__).resolve().parents[3] / "04_eval"

_ACT_BY_REGIME = {"IPC_1860": "IPC 1860", "BNS_2023": "BNS 2023"}


@dataclass(frozen=True, slots=True)
class Query:
    text: str
    expected_act: str
    expected_section: str


def build_query_set() -> list[Query]:
    """One query per seed offence per regime — 38 queries over the drafted sections."""
    queries: list[Query] = []
    for entry in SEED_LIST:
        for regime, section in (
            ("IPC_1860", entry.ipc_section),
            ("BNS_2023", entry.bns_section),
        ):
            if section is None:
                continue
            queries.append(
                Query(
                    text=f"punishment for {entry.label.lower()}",
                    expected_act=_ACT_BY_REGIME[regime],
                    expected_section=section,
                )
            )
    return queries


_CITATION_STYLE = {"IPC 1860": "IPC", "BNS 2023": "BNS"}


def build_citation_query_set() -> list[Query]:
    """Citation-style queries ("s.303 BNS"), reported SEPARATELY from natural language.

    The Extended Abstract names adjacent-section confusion as the specific failure —
    s.480 returned for s.479 — and only citation-style queries exercise it: a natural-
    language query never contains the section number at all."""
    queries: list[Query] = []
    for entry in SEED_LIST:
        for regime, section in (
            ("IPC_1860", entry.ipc_section),
            ("BNS_2023", entry.bns_section),
        ):
            if section is None:
                continue
            act = _ACT_BY_REGIME[regime]
            queries.append(
                Query(
                    text=f"section {section} {_CITATION_STYLE[act]}",
                    expected_act=act,
                    expected_section=section,
                )
            )
    return queries


@dataclass(frozen=True, slots=True)
class EvalResult:
    query_count: int
    recall_at: dict[int, float]
    mrr: float
    misses_at_10: tuple[str, ...]


def _hit(chunk: Chunk, query: Query) -> bool:
    return chunk.act == query.expected_act and chunk.section == query.expected_section


def evaluate_retriever(
    retriever: Retriever, queries: list[Query], ks: tuple[int, ...] = (1, 5, 10)
) -> EvalResult:
    max_k = max(ks)
    hits_at = dict.fromkeys(ks, 0)
    reciprocal_sum = 0.0
    misses: list[str] = []
    for query in queries:
        results = retriever.search(query.text, max_k)
        rank = next((i + 1 for i, (chunk, _) in enumerate(results) if _hit(chunk, query)), None)
        if rank is not None:
            reciprocal_sum += 1.0 / rank
            for k in ks:
                if rank <= k:
                    hits_at[k] += 1
        else:
            misses.append(
                f"{query.text!r} -> expected {query.expected_act} s.{query.expected_section}"
            )
    n = len(queries)
    return EvalResult(
        query_count=n,
        recall_at={k: hits_at[k] / n for k in ks},
        mrr=reciprocal_sum / n,
        misses_at_10=tuple(misses),
    )


def write_report(
    named_results: dict[str, EvalResult],
    corpus_size: int,
    out_dir: Path | None = None,
    run_date: datetime.date | None = None,
) -> Path:
    """Write the Layer A metric report. Caller supplies the date (determinism discipline)."""
    target_dir = out_dir or DEFAULT_EVAL_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = (run_date or datetime.date.today()).isoformat()
    lines = [
        f"# Layer A retrieval evaluation — {stamp}",
        "",
        "**Claim class: retrieval measurement, no legal judgement involved.** The query set",
        "derives from the 38 seed sections (offence label -> its own page-verified section).",
        "This figure is DISTINCT from any Tier-2 number and must never be blended with one.",
        "",
        f"Corpus: {corpus_size} statutory sections from the accepted primary acts, each",
        "chunk carrying its source SHA-256 and as-on date.",
        "",
        "| Configuration | Recall@1 | Recall@5 | Recall@10 | MRR |",
        "|---|---|---|---|---|",
    ]
    for name, result in named_results.items():
        r = result.recall_at
        lines.append(f"| {name} | {r[1]:.3f} | {r[5]:.3f} | {r[10]:.3f} | {result.mrr:.3f} |")
    lines.append("")
    for name, result in named_results.items():
        if result.misses_at_10:
            lines.append(f"## Misses at k=10 — {name}")
            lines.extend(f"* {miss}" for miss in result.misses_at_10)
            lines.append("")
    path = target_dir / f"layer_a_retrieval_{stamp}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
