"""Layer B — the seam, not the model (M5; Abhishek's direction, 2026-08-19).

An extractor turns free text into CANDIDATE offences: (regime, section, variant) keys with
the exact source span they came from. Candidates are unconfirmed by type — nothing in this
package can construct an engine input, and the package deliberately imports no engine
module (enforced by test): the only road from a candidate to a computation runs through
`confirmation.confirm`, a human act, and then through the API resolver, where D-060 already
forbids any extracted or supplied maximum from entering the gates.

**Fine-tuning feasibility, stated plainly:** NOT achievable in this environment, and no
partial training pipeline is built. The grounds: CPU-only torch (no training hardware); no
labelled charge-sheet corpus and no lawful way to build one here (real charge sheets are
sensitive personal data under the DPDP Act — the project's data discipline forbids them);
no annotation capacity (the same no-reviewer constraint the golden set records); and every
training-stack dependency would need its own D-078 decision. The recorded fallback when a
model occupies this seam is M5's own stub line: few-shot prompting with a pretrained model,
reported as such. The deterministic baseline in `baseline.py` gives P/R/F1 a real value
today and a comparison point for any future occupant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

__all__ = ["CandidateOffence", "ExtractionResult", "Extractor"]


@dataclass(frozen=True, slots=True)
class CandidateOffence:
    """One UNCONFIRMED extraction. Shows what was extracted and from what text.

    Deliberately carries no maximum, no label of legal effect, and no engine type: a
    model-guessed section number bypassing the provenance discipline would undo the
    schema-enforced source requirement, the page-level citations and the verified-row rule
    in a single step. The confirmation step is where a human takes responsibility."""

    regime: Literal["IPC_1860", "BNS_2023", "NDPS_1985"] | None
    """None when the text names a section but no recognisable enactment."""

    section: str
    variant: str | None
    matched_text: str
    """The exact characters the candidate came from — shown at confirmation."""

    span: tuple[int, int]
    """Start/end offsets into the source text, so the UI can highlight the origin."""

    source_snippet: str
    """The surrounding text (bounded), shown at confirmation beside the match."""


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    candidates: tuple[CandidateOffence, ...]
    extractor_name: str
    model_involved: bool
    """False for the deterministic baseline. Any future model occupant sets True, and the
    confirmation UI must say so."""


class Extractor(Protocol):
    def extract(self, text: str) -> ExtractionResult: ...
