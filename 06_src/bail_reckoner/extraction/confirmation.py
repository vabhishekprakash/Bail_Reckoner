"""The human confirmation step — the only road from a candidate to a computation.

`ConfirmedOffence` cannot be constructed except through `confirm`, which requires a named
confirmer and refuses a candidate with no regime (the human must have picked one). What
comes out is the API's input vocabulary — (regime, section, variant) keys — never a
maximum and never an engine type: the resolver then resolves the maximum from verified
rows exactly as for hand-entered offences, so extraction changes WHO TYPES the keys and
nothing else about the provenance discipline (D-060 intact end to end).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bail_reckoner.extraction.interface import CandidateOffence

__all__ = ["ConfirmedOffence", "confirm"]


@dataclass(frozen=True, slots=True)
class ConfirmedOffence:
    """A candidate a named human has confirmed against the shown source text."""

    regime: Literal["IPC_1860", "BNS_2023", "NDPS_1985"]
    section: str
    variant: str | None
    label: str
    confirmed_by: str
    confirmed_from: str
    """The matched text the confirmer saw — travels so a later reader can check what the
    confirmation was actually of."""

    def as_api_offence(self) -> dict[str, str | None]:
        """The API request fragment. Keys only; the maximum resolves server-side."""
        payload: dict[str, str | None] = {
            "regime": self.regime,
            "section": self.section,
            "label": self.label,
        }
        if self.variant:
            payload["variant"] = self.variant
        return payload


def confirm(
    candidate: CandidateOffence,
    *,
    confirmed_by: str,
    label: str,
    regime: Literal["IPC_1860", "BNS_2023", "NDPS_1985"] | None = None,
    variant: str | None = None,
) -> ConfirmedOffence:
    """The human act. Refuses to proceed on machine guesses the human did not resolve."""
    if not confirmed_by.strip():
        raise ValueError("confirmation requires a named confirmer — never blank, never auto")
    resolved_regime = regime or candidate.regime
    if resolved_regime is None:
        raise ValueError(
            f"candidate {candidate.matched_text!r} names no enactment and the confirmer "
            f"did not supply one: an unresolved regime is a question for the human, not a "
            f"guess for the machine"
        )
    if not label.strip():
        raise ValueError("confirmation requires the offence description the human settled on")
    return ConfirmedOffence(
        regime=resolved_regime,
        section=candidate.section,
        variant=variant or candidate.variant,
        label=label.strip(),
        confirmed_by=confirmed_by.strip(),
        confirmed_from=candidate.matched_text,
    )
