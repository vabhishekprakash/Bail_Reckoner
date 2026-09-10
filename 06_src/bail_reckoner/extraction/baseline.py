"""The deterministic baseline extractor (M5): citation patterns plus an offence-name
gazetteer over the 38 known sections. No model, no network, no randomness — the number it
scores is a floor any future model occupant must beat on the same synthetic set.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from bail_reckoner.extraction.interface import CandidateOffence, ExtractionResult

Regime = Literal["IPC_1860", "BNS_2023", "NDPS_1985"]

__all__ = ["BaselineExtractor", "GAZETTEER"]

_ACT_TOKENS: dict[str, Regime] = {
    "ipc": "IPC_1860",
    "indian penal code": "IPC_1860",
    "bns": "BNS_2023",
    "bharatiya nyaya sanhita": "BNS_2023",
    "ndps": "NDPS_1985",
}

# One citation may carry a LIST of sections — "Sections 341 and 351 IPC",
# "u/s 379, 411 and 420 IPC" — which is ordinary charge-sheet drafting, not an edge case
# (Abhishek, 2026-08-19; the first synthetic eval missed exactly this). The lead accepts
# the u/s form; the act token at the tail distributes over every number in the chain.
_SECTION_TOKEN = r"\d+[A-Z]{0,2}(?:\([0-9a-z]+\))?"
_CITATION = re.compile(
    rf"(?i)(?:u/s\.?|s\.?|sec\.?|sections?)\s*"
    rf"(?P<chain>{_SECTION_TOKEN}(?:\s*(?:,|and|&)\s*{_SECTION_TOKEN})*)"
    rf"(?:\s*(?:of\s+the\s+)?(?P<act>IPC|BNS|NDPS|Indian Penal Code|"
    rf"Bharatiya Nyaya Sanhita))?"
)
_CHAIN_ITEM = re.compile(rf"(?P<section>{_SECTION_TOKEN})")


# Offence-name gazetteer: label phrase -> (regime, section). Derived from the 38 seed
# sections at import (the page-verified set), never hand-numbered here.
def _build_gazetteer() -> dict[str, tuple[Regime, str]]:
    from bail_reckoner.statutes.curation import SEED_LIST

    entries: dict[str, tuple[Regime, str]] = {}
    for entry in SEED_LIST:
        phrase = entry.label.lower()
        if entry.ipc_section:
            entries[f"{phrase}|ipc"] = ("IPC_1860", entry.ipc_section)
        if entry.bns_section:
            entries[f"{phrase}|bns"] = ("BNS_2023", entry.bns_section)
    return entries


GAZETTEER = _build_gazetteer()
_PHRASES = sorted({key.split("|")[0] for key in GAZETTEER}, key=len, reverse=True)


def _snippet(text: str, start: int, end: int, radius: int = 80) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)].strip()


@dataclass(frozen=True, slots=True)
class BaselineExtractor:
    """Deterministic. Citations always win over name matches at the same location."""

    def extract(self, text: str) -> ExtractionResult:
        candidates: list[CandidateOffence] = []
        claimed: list[tuple[int, int]] = []

        for match in _CITATION.finditer(text):
            act_token = (match.group("act") or "").lower()
            regime: Regime | None = _ACT_TOKENS.get(act_token)
            for item in _CHAIN_ITEM.finditer(match.group("chain")):
                start = match.start("chain") + item.start()
                end = match.start("chain") + item.end()
                candidates.append(
                    CandidateOffence(
                        regime=regime,  # None when no enactment named: shown, not guessed
                        section=item.group("section"),
                        variant=None,
                        matched_text=text[start:end],
                        span=(start, end),
                        source_snippet=_snippet(text, match.start(), match.end()),
                    )
                )
            claimed.append((match.start(), match.end()))

        lowered = text.lower()
        for phrase in _PHRASES:
            start = 0
            while (at := lowered.find(phrase, start)) != -1:
                end = at + len(phrase)
                start = end
                if any(a < end and at < b for a, b in claimed):
                    continue
                # The phrase alone cannot pick a regime (theft exists in both codes): the
                # candidate carries BOTH known keys' sections only when they agree, else
                # regime stays None and the human picks at confirmation.
                ipc = GAZETTEER.get(f"{phrase}|ipc")
                bns = GAZETTEER.get(f"{phrase}|bns")
                pick = ipc if (ipc and not bns) else bns if (bns and not ipc) else None
                candidates.append(
                    CandidateOffence(
                        regime=pick[0] if pick else None,
                        section=pick[1] if pick else phrase,
                        variant=None,
                        matched_text=text[at:end],
                        span=(at, end),
                        source_snippet=_snippet(text, at, end),
                    )
                )
                claimed.append((at, end))

        return ExtractionResult(
            candidates=tuple(candidates),
            extractor_name="deterministic-baseline",
            model_involved=False,
        )
