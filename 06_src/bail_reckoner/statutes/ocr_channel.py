"""The second, independent extraction channel (D-089): rasterise the cited page and read
it by OCR, never touching the PDF text layer.

The point is DISJOINT FAILURE MODES. The text-layer channel's documented failures —
intra-word spaces, page-break truncation, heading-pattern misfires on the embedded text,
state-amendment run-on — cannot occur here, because this channel renders pixels
(pypdfium2, D-085) and reads them with RapidOCR (D-089). It has its OWN failure modes
(character confusion, line-ordering, its own section-location misses), which is exactly
what makes cross-channel agreement informative and cross-channel disagreement worth a
human's eyes.

Every failure REFUSES loudly: a section that cannot be located, or whose end never
appears within the page budget, returns an `OcrReadFailure` naming the reason — never a
partial text passed off as the section (the recorded failure shape, D-064).

CLAIM CLASS of anything derived from this module: cross-channel agreement measurement —
not a verification, not an accuracy figure. Machine readings from either channel NEVER
enter the penalty database; only a human's page-reading does (D-046).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bail_reckoner.statutes.curation import count_punishment_limbs

if TYPE_CHECKING:
    from PIL.Image import Image

__all__ = [
    "PunishmentFacts",
    "OcrSectionRead",
    "OcrReadFailure",
    "parse_punishment_facts",
    "read_section_via_ocr",
    "MONTHS_PER_UNIT",
]

# ---------------------------------------------------------------- fact extraction

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fourteen": 14,
    "fifteen": 15, "twenty": 20, "thirty": 30,
}
MONTHS_PER_UNIT = {"year": 12, "years": 12, "month": 1, "months": 1}

_QUANTITY = r"(?P<num>\d+|" + "|".join(_NUMBER_WORDS) + r")\s*(?P<unit>years?|months?)"
_MAXIMUM = re.compile(rf"(?i)may\s+extend\s+to\s+{_QUANTITY}")
_MINIMUM = re.compile(rf"(?i)shall\s+not\s+be\s+less\s+than\s+{_QUANTITY}")
_LIFE = re.compile(r"(?i)imprisonment\s+for\s+life")
_DEATH = re.compile(r"(?i)(?:punish(?:able|ed)\s+with|punishment\s+of)\s+death")


def _to_months(num: str, unit: str) -> int:
    value = int(num) if num.isdigit() else _NUMBER_WORDS[num.lower()]
    return value * MONTHS_PER_UNIT[unit.lower()]


@dataclass(frozen=True, slots=True)
class PunishmentFacts:
    """Mechanically extracted, channel-agnostic comparison facts for ONE section's text.

    Multisets are kept as sorted tuples so equality is order-free. These are COMPARISON
    ARTEFACTS between two machine channels — never statutory values (D-046/D-064): a
    row's `maximum` is set only by a human reading the page.
    """

    maxima_months: tuple[int, ...]
    minima_months: tuple[int, ...]
    life_mentioned: bool
    death_mentioned: bool
    limb_count: int

    def facets_disagreeing_with(self, other: PunishmentFacts) -> tuple[str, ...]:
        out = []
        if self.maxima_months != other.maxima_months:
            out.append("maxima")
        if self.minima_months != other.minima_months:
            out.append("minima")
        if (self.life_mentioned, self.death_mentioned) != (
            other.life_mentioned,
            other.death_mentioned,
        ):
            out.append("life/death mentions")
        if self.limb_count != other.limb_count:
            out.append("limb count")
        return tuple(out)


def parse_punishment_facts(text: str) -> PunishmentFacts:
    """One shared parser for BOTH channels, so a parsing quirk cancels out in the
    comparison instead of manufacturing disagreement. Whitespace differences (including
    OCR's own spacing) are neutralised by regexes tolerant of runs and by
    `count_punishment_limbs`, which squeezes all whitespace before counting."""
    return PunishmentFacts(
        maxima_months=tuple(
            sorted(_to_months(m["num"], m["unit"]) for m in _MAXIMUM.finditer(text))
        ),
        minima_months=tuple(
            sorted(_to_months(m["num"], m["unit"]) for m in _MINIMUM.finditer(text))
        ),
        life_mentioned=bool(_LIFE.search(text)),
        death_mentioned=bool(_DEATH.search(text)),
        limb_count=count_punishment_limbs(text),
    )


# ---------------------------------------------------------------- the OCR read

_MAX_EXTRA_PAGES = 3
_RENDER_SCALE = 3.0

_ENGINE: Any = None


def _engine() -> Any:  # noqa: ANN401 — RapidOCR ships no types (mypy override in pyproject)
    """One engine for the process — model loading dwarfs a page read."""
    global _ENGINE
    if _ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR

        _ENGINE = RapidOCR()
    return _ENGINE


@dataclass(frozen=True, slots=True)
class OcrSectionRead:
    section: str
    text: str
    page_indexes: tuple[int, ...]
    """0-based PDF page indexes actually consumed."""

    crop_top: float
    crop_bottom: float
    crop_page_index: int
    """Vertical band (pixel rows at the render scale) of the section's first page — for
    cropping the disagreement evidence image."""


@dataclass(frozen=True, slots=True)
class OcrReadFailure:
    section: str
    reason: str
    page_indexes: tuple[int, ...]


def _next_section_number(section: str) -> str:
    """The heading that ends a section is the NEXT section's number: 331 -> 332, and a
    lettered section falls through to the next integer (304A -> 305). Sub-lettered
    successors (304A -> 304B) are also accepted by the end pattern below."""
    digits = re.match(r"\d+", section)
    assert digits is not None
    return str(int(digits.group()) + 1)


def _heading_pattern(number: str) -> re.Pattern[str]:
    # OCR often fuses the dot with the following word ("20.Punishment"); a heading is the
    # number at a plausible boundary followed by '.', not preceded by 's', 'ss', 'Act' or
    # a digit (footnote apparatus: "s. 7,", "Act 16 of 2014").
    return re.compile(
        rf"(?<![0-9(])\b{number}\s*\.\s*(?=[A-Z(—-])"
    )


def read_section_via_ocr(
    pdf_path: Path,
    page_index0: int,
    section: str,
    *,
    _page_cache: dict[tuple[str, int], tuple[str, list[tuple[float, float, str]]]]
    | None = None,
) -> OcrSectionRead | OcrReadFailure:
    """Locate `section` starting at 0-based `page_index0`, reading forward page by page
    until the next section's heading appears. Refuses (`OcrReadFailure`) when the start
    heading is absent on the named page and the one after it, or when the end never
    appears within the page budget — a truncated read is a failed read, never 'close
    enough' (D-064)."""
    import numpy as np
    import pypdfium2 as pdfium

    ocr = _engine()
    pdf = pdfium.PdfDocument(str(pdf_path))
    cache = _page_cache if _page_cache is not None else {}

    def page_lines(index: int) -> tuple[str, list[tuple[float, float, str]]]:
        key = (str(pdf_path), index)
        if key not in cache:
            image: Image = pdf[index].render(scale=_RENDER_SCALE).to_pil()
            result, _ = ocr(np.array(image))
            lines = [
                (min(p[1] for p in box), max(p[1] for p in box), str(txt))
                for box, txt, _conf in (result or [])
            ]
            cache[key] = (" ".join(t for _, _, t in lines), lines)
        return cache[key]

    start_re = _heading_pattern(section)
    end_re = _heading_pattern(rf"(?:{_next_section_number(section)}|{re.escape(section)}[A-Z])")

    consumed: list[int] = []
    collected = ""
    start_seen_at: int | None = None
    for index in range(page_index0, min(page_index0 + 1 + _MAX_EXTRA_PAGES, len(pdf))):
        if start_seen_at is None and index > page_index0 + 1:
            break
        text, _lines = page_lines(index)
        consumed.append(index)
        if start_seen_at is None:
            start = start_re.search(text)
            if start is None:
                continue
            start_seen_at = index
            collected = text[start.start() :]
        else:
            collected += " " + text
        end = end_re.search(collected)
        if end is not None:
            collected = collected[: end.start()]
            first_text, first_lines = page_lines(start_seen_at)
            offset = first_text.find(collected[:60])
            tops = [t for t, _b, txt in first_lines if txt and txt in collected]
            bottoms = [b for _t, b, txt in first_lines if txt and txt in collected]
            return OcrSectionRead(
                section=section,
                text=collected,
                page_indexes=tuple(consumed),
                crop_top=min(tops) if tops else 0.0,
                crop_bottom=max(bottoms) if bottoms else 0.0,
                crop_page_index=start_seen_at if offset >= 0 else start_seen_at,
            )
    if start_seen_at is None:
        return OcrReadFailure(
            section=section,
            reason=(
                f"heading '{section}.' not found by OCR on page index {page_index0} or "
                f"{page_index0 + 1}"
            ),
            page_indexes=tuple(consumed),
        )
    return OcrReadFailure(
        section=section,
        reason=(
            f"section start found on page index {start_seen_at} but the next section's "
            f"heading never appeared within {_MAX_EXTRA_PAGES} further pages — a "
            "truncated read is a failed read, not a result"
        ),
        page_indexes=tuple(consumed),
    )
