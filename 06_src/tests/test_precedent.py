"""Layer D tests: the verbatim-only constraint, provenance, and the corpus label (M6)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from bail_reckoner.precedent import (
    CORPUS_STATUS,
    JudgmentParagraph,
    PrecedentExtract,
    PrecedentIndex,
    build_precedent_corpus,
)
from bail_reckoner.statutes.sources import LAW_DIR

needs_judgments = pytest.mark.skipif(
    not (LAW_DIR / "SatenderKumarAntil_v_CBI_SC_2022-07-11_sciAPI.pdf").is_file(),
    reason="judgments not acquired in this checkout",
)


@pytest.fixture(scope="module")
def corpus() -> list[JudgmentParagraph]:
    return build_precedent_corpus()


@needs_judgments
class TestVerbatimOnlyByConstruction:
    def test_extract_has_no_summary_or_headnote_field(self) -> None:
        """The output vocabulary is citation, paragraph number, verbatim text and
        provenance — a synthesised holding is a hallucinated citation waiting to be relied
        on in court. The constraint is structural, not editorial."""
        fields = {f.name for f in dataclasses.fields(PrecedentExtract)}
        assert fields == {
            "citation",
            "para_number",
            "verbatim_text",
            "source_file",
            "source_sha256",
            "corpus_status",
        }

    def test_extract_text_is_verbatim_corpus_text(self, corpus: list[JudgmentParagraph]) -> None:
        index = PrecedentIndex(corpus)
        for extract in index.search("bail undertrial maximum period", 5):
            assert any(
                p.text == extract.verbatim_text
                and p.citation == extract.citation
                and p.para_number == extract.para_number
                for p in corpus
            )

    def test_every_extract_carries_the_incomplete_corpus_status(
        self, corpus: list[JudgmentParagraph]
    ) -> None:
        index = PrecedentIndex(corpus)
        for extract in index.search("section 436A", 3):
            assert extract.corpus_status == CORPUS_STATUS
            assert "INCOMPLETE" in extract.corpus_status
            assert "Ramakrishna" in extract.corpus_status

    def test_provenance_is_the_sources_record(self, corpus: list[JudgmentParagraph]) -> None:
        from bail_reckoner.statutes.sources import accepted_sources

        recorded = {name: sha for name, sha, _ in accepted_sources()}
        for paragraph in corpus:
            assert paragraph.source_sha256 == recorded[paragraph.source_file]


@needs_judgments
class TestCorpusShape:
    def test_all_three_acquired_judgments_present(self, corpus: list[JudgmentParagraph]) -> None:
        files = {p.source_file for p in corpus}
        assert len(files) == 3

    def test_antil_paragraph_numbers_are_plausible(self, corpus: list[JudgmentParagraph]) -> None:
        numbers = [p.para_number for p in corpus if p.source_file.startswith("SatenderKumarAntil")]
        assert numbers == sorted(numbers)
        assert numbers[0] == 1 and numbers[-1] >= 60

    def test_the_436a_paragraphs_are_findable(self, corpus: list[JudgmentParagraph]) -> None:
        index = PrecedentIndex(corpus)
        top = index.search("undertrial detained one-half maximum period 436A", 5)
        assert any("436A" in e.verbatim_text for e in top)


class TestEmptyCorpusIsALabelledStub:
    def test_empty_corpus_refuses_loudly(self) -> None:
        with pytest.raises(ValueError, match="stub"):
            PrecedentIndex([])


class TestCorpusBuildRefusals:
    """Sixth-instance audit (2026-08-29): the builder must never let the corpus shrink
    or lose provenance while CORPUS_STATUS still asserts '3 of 4 on disk'."""

    def test_missing_judgment_raises_instead_of_silently_shrinking(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError, match="CORPUS_STATUS"):
            build_precedent_corpus(law_dir=tmp_path)
