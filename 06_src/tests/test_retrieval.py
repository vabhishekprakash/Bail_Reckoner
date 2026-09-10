"""Layer A tests: corpus discipline and the lexical leg (M4).

Unit tests here stay model-free: the dense leg and reranker need a ~200MB model download
and are exercised by the evaluation run (whose report lands in 04_eval/), not by the unit
suite — a suite that quietly downloaded models would be a network dependency in disguise.
The lexical leg, the fusion arithmetic and the corpus contract are fully testable offline.
"""

from __future__ import annotations

import pytest

from bail_reckoner.retrieval.corpus import DEFAULT_CORPUS_PATH, Chunk, load_corpus
from bail_reckoner.retrieval.evaluation import build_query_set, evaluate_retriever
from bail_reckoner.retrieval.index import Bm25Index, HybridRetriever

needs_corpus = pytest.mark.skipif(
    not DEFAULT_CORPUS_PATH.is_file(),
    reason="statute corpus not built in this checkout (run build_corpus)",
)


@pytest.fixture(scope="module")
def corpus() -> list[Chunk]:
    return load_corpus()


@needs_corpus
class TestCorpusContract:
    def test_every_chunk_carries_version_and_date(self, corpus: list[Chunk]) -> None:
        assert corpus, "corpus is empty"
        for chunk in corpus:
            assert len(chunk.source_sha256) == 64, chunk.chunk_id
            assert chunk.as_on, chunk.chunk_id
            assert chunk.date_basis, chunk.chunk_id

    def test_shas_match_the_sources_record(self, corpus: list[Chunk]) -> None:
        """The chunk's statute version IS the acquisition-time hash the integrity test
        re-verifies — one record, two consumers."""
        from bail_reckoner.statutes.sources import accepted_sources

        recorded = {name: sha for name, sha, _ in accepted_sources()}
        for chunk in corpus:
            assert chunk.source_sha256 == recorded[chunk.source_file], chunk.chunk_id

    def test_the_seed_sections_are_all_present(self, corpus: list[Chunk]) -> None:
        """Every page-verified seed section must appear in the corpus: these are the 38
        sections the project has actually confirmed exist."""
        have = {(c.act, c.section) for c in corpus}
        for query in build_query_set():
            assert (query.expected_act, query.expected_section) in have, query

    def test_statutory_text_only(self, corpus: list[Chunk]) -> None:
        """DPDP discipline: every chunk's source is an accepted statutory document from
        01_law/ — nothing else can enter this corpus."""
        from bail_reckoner.statutes.sources import accepted_sources

        accepted = {name for name, _, _ in accepted_sources()}
        assert {c.source_file for c in corpus} <= accepted


@needs_corpus
class TestLexicalLeg:
    @pytest.fixture(scope="class")
    @staticmethod
    def bm25(corpus: list[Chunk]) -> Bm25Index:
        return Bm25Index(corpus)

    def test_finds_theft_in_both_regimes(self, bm25: Bm25Index) -> None:
        results = bm25.search("punishment for theft", 10)
        found = {(c.act, c.section) for c, _ in results}
        assert ("IPC 1860", "379") in found or ("BNS 2023", "303") in found

    def test_deterministic(self, bm25: Bm25Index) -> None:
        first = [c.chunk_id for c, _ in bm25.search("cheating and dishonestly", 5)]
        second = [c.chunk_id for c, _ in bm25.search("cheating and dishonestly", 5)]
        assert first == second

    def test_bm25_alone_scores_measurably_on_the_seed_queries(self, bm25: Bm25Index) -> None:
        """A floor, not a headline: the reported figures come from the evaluation run in
        04_eval/. This guards against the corpus or tokenizer silently degrading."""
        result = evaluate_retriever(bm25, build_query_set())
        assert result.query_count == 38
        assert result.recall_at[10] >= 0.5, result.misses_at_10


@needs_corpus
class TestFusion:
    def test_rrf_fuses_and_respects_k(self, corpus: list[Chunk]) -> None:
        """Fusion arithmetic without models: both legs are BM25 here, which makes RRF's
        rank handling testable offline (identical legs must reproduce the leg itself)."""
        bm25 = Bm25Index(corpus)
        hybrid = HybridRetriever(lexical=bm25, dense=bm25, reranker=None)
        results = hybrid.search("punishment for murder", 7)
        assert len(results) == 7
        assert [c.chunk_id for c, _ in results][:3] == [
            c.chunk_id for c, _ in bm25.search("punishment for murder", 3)
        ]


@needs_corpus
class TestCitationQueries:
    """Citation-style queries, the adjacent-section failure the Extended Abstract names."""

    def test_citation_query_set_mirrors_the_seed_set(self) -> None:
        from bail_reckoner.retrieval.evaluation import build_citation_query_set

        queries = build_citation_query_set()
        assert len(queries) == 38
        assert all(q.text.startswith("section ") for q in queries)

    def test_section_479_bnss_is_not_confused_with_adjacent_sections(
        self, corpus: list[Chunk]
    ) -> None:
        """The named failure: s.480 returned for s.479. BM25 on a citation query must rank
        the asked-for section above its neighbours."""
        bm25 = Bm25Index(corpus)
        results = bm25.search("section 479 BNSS", 5)
        top = [(c.act, c.section) for c, _ in results]
        assert ("BNSS 2023", "479") in top
        rank_479 = top.index(("BNSS 2023", "479"))
        for neighbour in ("478", "480"):
            if ("BNSS 2023", neighbour) in top:
                assert top.index(("BNSS 2023", neighbour)) > rank_479


@needs_corpus
class TestRouting:
    def test_citation_shaped_queries_route_to_the_lexical_leg(self, corpus: list[Chunk]) -> None:
        """Measured basis: dense scores 0.000 on citation queries and poisons the hybrid
        through RRF. The router is a regex, not a model."""
        from bail_reckoner.retrieval.index import RoutedRetriever

        bm25 = Bm25Index(corpus)
        poison = Bm25Index(corpus[:5])  # a deliberately useless "hybrid" stand-in
        routed = RoutedRetriever(lexical=bm25, hybrid=poison)
        assert [c.chunk_id for c, _ in routed.search("section 479 BNSS", 5)] == [
            c.chunk_id for c, _ in bm25.search("section 479 BNSS", 5)
        ]
        assert [c.chunk_id for c, _ in routed.search("punishment for theft", 5)] == [
            c.chunk_id for c, _ in poison.search("punishment for theft", 5)
        ]


@needs_corpus
class TestCrossActMitigation:
    """D-086: an act-less citation query over colliding section numbers must surface the
    collision, never silently rank one act's section as the answer (the fourth-instance
    failure shape applied to retrieval). 510 of 723 distinct section numbers in this corpus
    exist in more than one act."""

    @pytest.fixture(scope="class")
    @staticmethod
    def routed(corpus: list[Chunk]) -> object:
        from bail_reckoner.retrieval.index import RoutedRetriever

        bm25 = Bm25Index(corpus)
        return RoutedRetriever(lexical=bm25, hybrid=bm25, chunks=tuple(corpus))

    def test_actless_colliding_query_surfaces_every_act(self, routed: object) -> None:
        result = routed.route("section 303", 5)  # type: ignore[attr-defined]
        assert result.ambiguity is not None
        assert set(result.ambiguity.acts) == {
            "BNS 2023",
            "BNSS 2023",
            "Companies Act 2013",
            "IPC 1860",
        }
        leading = [(c.act, c.section) for c, _ in result.results[:4]]
        assert leading == [(act, "303") for act in result.ambiguity.acts]
        assert "none was chosen for you" in result.ambiguity.note

    def test_leading_ambiguity_results_are_lookups_not_rankings(self, routed: object) -> None:
        result = routed.route("section 303", 5)  # type: ignore[attr-defined]
        assert all(score == 0.0 for _, score in result.results[:4])

    def test_act_named_query_is_not_flagged(self, routed: object) -> None:
        for query in ("section 303 BNS", "section 303 of the Indian Penal Code"):
            result = routed.route(query, 5)  # type: ignore[attr-defined]
            assert result.ambiguity is None, query

    def test_bns_alias_does_not_fire_inside_bnss(self, routed: object) -> None:
        """Word boundaries: "section 479 BNSS" names BNSS, not BNS — a substring match
        would mis-derive the act and suppress a real ambiguity elsewhere."""
        from bail_reckoner.retrieval.index import _acts_named_in

        assert _acts_named_in("section 479 BNSS") == {"BNSS 2023"}

    def test_every_colliding_act_survives_a_small_k(self, routed: object) -> None:
        result = routed.route("section 303", 2)  # type: ignore[attr-defined]
        assert len(result.results) >= 4

    def test_natural_language_query_carries_no_ambiguity(self, routed: object) -> None:
        result = routed.route("punishment for theft", 5)  # type: ignore[attr-defined]
        assert result.query_class == "natural"
        assert result.ambiguity is None

    def test_without_chunks_the_collision_stays_unmitigated(self, corpus: list[Chunk]) -> None:
        """The pre-D-086 behaviour, pinned so the difference is visible: no directory, no
        ambiguity — exactly why callers that can supply the corpus should."""
        from bail_reckoner.retrieval.index import RoutedRetriever

        bm25 = Bm25Index(corpus)
        bare = RoutedRetriever(lexical=bm25, hybrid=bm25)
        assert bare.route("section 303", 5).ambiguity is None
