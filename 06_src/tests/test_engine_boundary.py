"""The model boundary as a test, not a convention (Abhishek, 2026-08-19).

"No model in the decision path" (CLAUDE.md §5, D-050) has until now been an architectural
claim. This test makes it structural, on the pattern the FastAPI layer already follows:
import every engine module and assert that no ML, retrieval or network library entered
`sys.modules` as a consequence. A future contributor cannot wire a model into a gate
without this test failing.
"""

from __future__ import annotations

import subprocess
import sys

# Libraries that must never load as a consequence of importing the engine. Retrieval and
# extraction live OUTSIDE Layer C; the engine receives typed values only.
_FORBIDDEN = (
    "torch",
    "sentence_transformers",
    "transformers",
    "rank_bm25",
    "numpy",
    "sklearn",
    "faiss",
    "fastapi",
    "httpx",
    "requests",
    "urllib3",
)

_PROBE = """
import sys
import bail_reckoner.engine.types
import bail_reckoner.engine.custody
import bail_reckoner.engine.gates
loaded = [name for name in {forbidden!r} if name in sys.modules]
print(",".join(loaded) if loaded else "CLEAN")
"""


class TestEngineImportsNoModel:
    def test_importing_the_engine_loads_no_ml_or_network_library(self) -> None:
        # A fresh interpreter, so nothing this test process already imported can mask a
        # transitive import inside the engine.
        result = subprocess.run(
            [sys.executable, "-c", _PROBE.format(forbidden=_FORBIDDEN)],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "CLEAN", (
            f"importing the engine loaded forbidden libraries: {result.stdout.strip()} — "
            f"a model or network path has entered Layer C"
        )
