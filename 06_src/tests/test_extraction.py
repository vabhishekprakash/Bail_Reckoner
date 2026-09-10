"""Layer B tests: the baseline, the confirmation gate, and the import boundary (M5).

Every fact pattern below is SYNTHETIC (DPDP discipline: no real charge sheets, ever)."""

from __future__ import annotations

import subprocess
import sys

import pytest

from bail_reckoner.extraction.baseline import BaselineExtractor
from bail_reckoner.extraction.confirmation import confirm
from bail_reckoner.extraction.interface import CandidateOffence

SYNTHETIC_TEXT = (
    "SYNTHETIC FACT PATTERN. The accused is charged under Section 379 IPC for theft of a "
    "vehicle, and under s. 303(2) BNS in the alternative. A further charge of cheating and "
    "dishonestly inducing delivery of property is under investigation. The complaint under "
    "section 154 CrPC was registered on the same day."
)


class TestBaseline:
    def test_extracts_citations_with_regimes_and_spans(self) -> None:
        result = BaselineExtractor().extract(SYNTHETIC_TEXT)
        assert result.extractor_name == "deterministic-baseline"
        assert result.model_involved is False
        keyed = {(c.regime, c.section) for c in result.candidates}
        assert ("IPC_1860", "379") in keyed
        assert ("BNS_2023", "303(2)") in keyed
        for candidate in result.candidates:
            start, end = candidate.span
            assert SYNTHETIC_TEXT[start:end] == candidate.matched_text

    def test_unnamed_enactment_yields_regime_none_not_a_guess(self) -> None:
        result = BaselineExtractor().extract("charged under section 154 CrPC")
        crpc = [c for c in result.candidates if c.section == "154"]
        assert crpc and crpc[0].regime is None

    def test_deterministic(self) -> None:
        first = BaselineExtractor().extract(SYNTHETIC_TEXT)
        second = BaselineExtractor().extract(SYNTHETIC_TEXT)
        assert first == second


class TestConfirmationGate:
    _candidate = CandidateOffence(
        regime="IPC_1860",
        section="379",
        variant=None,
        matched_text="Section 379 IPC",
        span=(0, 15),
        source_snippet="charged under Section 379 IPC for theft",
    )

    def test_confirmation_requires_a_named_human(self) -> None:
        with pytest.raises(ValueError, match="named confirmer"):
            confirm(self._candidate, confirmed_by="  ", label="Theft")

    def test_unresolved_regime_refuses_never_guesses(self) -> None:
        nameless = CandidateOffence(
            regime=None,
            section="154",
            variant=None,
            matched_text="section 154",
            span=(0, 11),
            source_snippet="the complaint under section 154",
        )
        with pytest.raises(ValueError, match="question for the human"):
            confirm(nameless, confirmed_by="Test Reviewer", label="x")

    def test_confirmed_offence_is_api_keys_never_a_maximum(self) -> None:
        confirmed = confirm(self._candidate, confirmed_by="Test Reviewer", label="Theft")
        payload = confirmed.as_api_offence()
        assert payload == {"regime": "IPC_1860", "section": "379", "label": "Theft"}
        assert "maximum" not in str(payload)
        assert confirmed.confirmed_from == "Section 379 IPC"


class TestSeamBoundary:
    def test_extraction_imports_no_engine_and_no_ml(self) -> None:
        """The seam's structural guarantee, on the engine-boundary pattern: importing the
        extraction package loads neither the engine (candidates cannot become engine
        inputs here) nor any ML library (the baseline is deterministic)."""
        probe = (
            "import sys\n"
            "import bail_reckoner.extraction.interface\n"
            "import bail_reckoner.extraction.baseline\n"
            "import bail_reckoner.extraction.confirmation\n"
            "bad = [m for m in ('bail_reckoner.engine.gates', 'bail_reckoner.engine.types',"
            " 'torch', 'sentence_transformers', 'transformers', 'numpy') if m in sys.modules]\n"
            "print(','.join(bad) if bad else 'CLEAN')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", probe], capture_output=True, text=True, check=True
        )
        assert result.stdout.strip() == "CLEAN", result.stdout
