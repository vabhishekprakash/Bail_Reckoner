"""Read section text out of the bare-act PDFs stored in `01_law/`.

This is **curation tooling, not engine code.** It performs file I/O and depends on `pypdf`, so it
sits outside Layer C's purity boundary (D-050) and is installed via the optional `statutes`
dependency group. Layer C never imports it.

Its purpose is narrow and important: when a penalty row records `quoted_text` and
`verified_against`, those must come from the statute itself rather than from anyone's
recollection of it (C5). This module produces the quotation and the page reference; a human then
reads the quotation, decides the maximum, and marks the row VERIFIED (D-046).

It deliberately does **not** parse a punishment clause into a `MaximumPunishment`. Turning
"imprisonment of either description for a term which may extend to three years, or with fine, or
with both" into a structured maximum is an act of legal reading, and a regex that appears to do
it would manufacture exactly the false confidence this project exists to avoid.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

__all__ = ["SectionText", "BareAct", "LAW_DIR"]

LAW_DIR = Path(__file__).resolve().parents[3] / "01_law"
"""`H:/Bail_Reckoner/01_law` — resolved from this file so it holds wherever the repo is checked
out. `parents[3]` walks statutes -> bail_reckoner -> 06_src -> repo root."""


@dataclass(frozen=True, slots=True)
class SectionText:
    """One section as it appears in a bare act, with enough detail to cite it."""

    section: str
    text: str
    page_index: int
    """0-based PDF page index, as `pypdf` counts them."""

    printed_page: str
    """The page number printed on the page itself, which is what a human checking the citation
    will look for. Empty when it could not be read."""

    source_file: str

    truncated: bool = False
    """True when extraction ran out of pages before finding the next section heading.

    This is the direct, mechanical tell for the session-9 truncation bug: the slice stopped
    because the continuation limit was reached, not because the section ended. In these acts the
    *punishment* limb is frequently the part that lands on a later page, so a truncated slice can
    silently drop the enhancement proviso a penalty row depends on. No legal judgement is needed
    to act on this flag — it says the text is incomplete, full stop.
    """

    def citation(self) -> str:
        """A `verified_against` string precise enough for a human to re-check by hand."""
        page = f"printed p. {self.printed_page}" if self.printed_page else "printed page unknown"
        return f"{self.source_file}, {page} (PDF page index {self.page_index}), s.{self.section}"


# The two stored acts print their page numbers in different places, and getting this wrong is
# not a cosmetic error: a citation that names the wrong page sends a human checker somewhere the
# text is not, and they may conclude the row is unverifiable rather than that the citation is off.
#
# India Code style (IPC): a standalone number on the first line of the page.
_STANDALONE_PAGE_RE = re.compile(r"^(\d{1,4})$")
# Gazette style (BNS, BNSS): the number sits in the running footer, at the start on left-hand
# pages and at the end on right-hand pages.
_GAZETTE_FOOTER_LEFT_RE = re.compile(r"^(\d{1,4})\s+THE GAZETTE OF INDIA")
_GAZETTE_FOOTER_RIGHT_RE = re.compile(r"THE GAZETTE OF INDIA EXTRAORDINARY\s+(\d{1,4})\b")


@lru_cache(maxsize=8)
def _cached_act(filename: str) -> BareAct:
    return BareAct(filename)


def successor_pattern(section: str) -> re.Pattern[str]:
    """A regex matching the heading of a section that could plausibly FOLLOW `section`.

    Replaces a "any line starting with a number and a dot" heuristic that failed in **both**
    directions on real documents, from one root cause — it did not know which section it was
    looking for:

    * **Premature cut.** IPC s.363 was truncated mid-definition by a *footnote* line
      (`1. The words ...`). A bare number is not evidence of a section heading; footnotes,
      illustrations and numbered clauses all start that way.
    * **Over-capture.** IPC s.304A ran on to `305.`, silently swallowing **s.304B** and its
      punishment clause — which is how a "causing death by negligence" row came to quote a life
      sentence. The old pattern could not see s.304B's heading and simply carried on.

    Anchoring on plausible successors fixes both at once: a footnote "1." is not a successor of
    s.363, and s.304B is. Looking a few numbers ahead absorbs repealed or omitted sections;
    letter suffixes absorb the 304A/304B family.
    """
    match = re.match(r"^(\d+)([A-Z]*)$", section.strip())
    if not match:
        # Sub-section-style references are not section headings; fall back to the generic form.
        return re.compile(rf"(?m)^\s*{_AMENDMENT_MARKER}\d+[A-Z]*\s*\.")
    number, suffix = int(match.group(1)), match.group(2)

    candidates: list[str] = []
    if suffix:
        last = suffix[-1]
        candidates += [f"{number}{suffix[:-1]}{chr(ord(last) + i)}" for i in range(1, 4)]
    else:
        candidates += [f"{number}{letter}" for letter in "ABC"]
    for following in range(number + 1, number + _SUCCESSOR_LOOKAHEAD + 1):
        candidates += [str(following), f"{following}A"]

    alternation = "|".join(re.escape(c) for c in candidates)
    return re.compile(rf"(?m)^\s*{_AMENDMENT_MARKER}(?:{alternation})\s*\.")


_SUCCESSOR_LOOKAHEAD = 6
"""How many section numbers ahead to accept as a successor.

Generous enough to step over repealed or omitted sections, tight enough that a much later
heading cannot be mistaken for the end of this one.
"""

_AMENDMENT_MARKER = r"(?:\d+\s*\*?\s*\[\s*)?"
"""Optional footnote marker preceding a section number, e.g. `1[304A. ...`.

India Code marks sections inserted or substituted by amendment with a bracketed footnote
reference. Without tolerating it, **every amendment-inserted section is invisible to extraction**
-- and those are disproportionately the modern, frequently-charged offences (IPC s.304A causing
death by negligence, s.354A sexual harassment, s.376AB). A silent gap there would have quietly
excluded them from the penalty database.
"""


def _contains_phrase(haystack: str, phrase: str) -> bool:
    """Whitespace-insensitive, case-insensitive substring test.

    PDF text carries line breaks wherever the typesetter happened to wrap, so a phrase present in
    the statute can appear as "subjects such\\nwoman to cruelty". A naive `in` check then reports
    a correct section number as wrong -- which is worse than useless here, because the caller is
    using this guard to decide whether a section number can be trusted.
    """
    return _collapse(phrase) in _collapse(haystack)


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


_MAX_CONTINUATION_PAGES = 3
"""How far a section may run past its opening page before extraction gives up.

Three is generous for a penalty provision and short enough that a failed next-section match
cannot swallow half the act.
"""


def _strip_running_headers(page_text: str) -> str:
    """Remove page furniture so it is not spliced into the middle of a quoted provision."""
    keep: list[str] = []
    for line in page_text.splitlines():
        stripped = line.strip()
        if _STANDALONE_PAGE_RE.match(stripped):
            continue
        if "THE GAZETTE OF INDIA" in stripped:
            continue
        keep.append(line)
    return "\n".join(keep)


def _printed_page_number(page_text: str) -> str:
    """Read the page number printed on the page, or "" if it cannot be read confidently.

    Deliberately conservative. An earlier version took the first numeric token on the page, which
    silently misread gazette pages: those begin with a *continuing section*, so page index 33 —
    printed page 34 — reported itself as "102", the number of the section running across the
    break. Every citation it produced pointed at the wrong page while looking perfectly correct.

    Anything not matching a known page-number position returns "", and `SectionText.citation()`
    falls back to the PDF page index, which is always exact.
    """
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    if not lines:
        return ""

    if match := _STANDALONE_PAGE_RE.match(lines[0]):
        return match.group(1)

    for line in (lines[-1], lines[0]):
        for pattern in (_GAZETTE_FOOTER_LEFT_RE, _GAZETTE_FOOTER_RIGHT_RE):
            if match := pattern.search(line):
                return match.group(1)
    return ""


class BareAct:
    """A bare-act PDF in `01_law/`, addressable by section number.

    Pages are extracted once and cached, because these are 100-280 page documents and curation
    reads many sections in a run.
    """

    @staticmethod
    def open(filename: str) -> BareAct:
        """Return a shared instance, so repeated use does not re-extract the whole document.

        Text extraction over a 100-280 page act is seconds of work, and curation reads many
        sections across many runs. `BareAct(...)` constructs a fresh, uncached instance; prefer
        this in anything that may be called more than once.
        """
        return _cached_act(filename)

    def __init__(self, filename: str, law_dir: Path | None = None) -> None:
        self.path = (law_dir or LAW_DIR) / filename
        if not self.path.exists():
            raise FileNotFoundError(
                f"{self.path} not found. Bare acts are stored in 01_law/ with provenance "
                f"recorded in 01_law/SOURCES.md; see that file before adding one."
            )
        self.filename = filename

    @lru_cache(maxsize=1)  # noqa: B019
    def _pages(self) -> tuple[str, ...]:
        from pypdf import PdfReader  # imported lazily: optional dependency, curation-only

        reader = PdfReader(str(self.path))
        return tuple((page.extract_text() or "") for page in reader.pages)

    def find_section(
        self,
        section: str,
        *,
        must_contain: str | None = None,
        discards: list[str] | None = None,
    ) -> SectionText | None:
        """Return the text of `section`, or None if it cannot be located unambiguously.

        `section` is the bare number, e.g. "303" or "304A".

        `must_contain` is a disambiguator, matched case-insensitively. Section numbers recur
        throughout these documents — in the arrangement-of-sections table at the front, in
        cross-references, and in amendment footnotes — so the first textual match is frequently
        not the section itself. Passing a word from the section's own text (e.g. "theft") pins it.

        Returning None on ambiguity is deliberate. A wrong section quotation would attach the
        wrong punishment to an offence while looking perfectly well-formed, which is precisely
        the failure mode that made two official IPC PDFs unusable (see 01_law/SOURCES.md).

        `discards` (D-070, built before the filter fix it accompanies): pass a list and every
        candidate this method rejects is recorded in it with the page and the reason. A
        discarded section otherwise surfaces as "not found", indistinguishable from "not
        present" — the third instance of that failure shape this project met, and knowing WHY
        a candidate was dropped is worth more than any individual filter fix.
        """
        pattern = re.compile(rf"(?m)^\s*{_AMENDMENT_MARKER}{re.escape(section)}\s*\.")
        for index, page in enumerate(self._pages()):
            # Cheap pre-filter. Slicing and whitespace-normalising a candidate costs far more
            # than a substring test, and the section number is absent from almost every page.
            if section not in page:
                continue
            for match in pattern.finditer(page):
                body, truncated = self._slice_to_next_section(index, match.start(), section)
                if must_contain and not _contains_phrase(body, must_contain):
                    if discards is not None:
                        discards.append(
                            f"page index {index}: heading matched but body lacks {must_contain!r}"
                        )
                    continue
                if self._looks_like_a_contents_entry(body):
                    if discards is not None:
                        discards.append(
                            f"page index {index}: heading matched but body reads as a bare "
                            f"contents-entry title ({' '.join(body.split())[:60]!r})"
                        )
                    continue
                return SectionText(
                    section=section,
                    text=body.strip(),
                    page_index=index,
                    printed_page=_printed_page_number(page),
                    source_file=self.filename,
                    truncated=truncated,
                )
        return None

    def _slice_to_next_section(self, page_index: int, start: int, section: str) -> tuple[str, bool]:
        """Text from `start` to the next section heading, continuing across page breaks.

        Sections routinely run across a page break, and in these acts the *punishment* sub-section
        is frequently the part that lands on the following page: BNS s.303(1) defines theft and
        s.303(2) punishes it. An earlier version stopped at the page end, which silently truncated
        exactly the clause a penalty row needs and made correct section numbers look wrong.

        Continuation is capped at `_MAX_CONTINUATION_PAGES`. Running headers and footers are
        stripped from continued pages, since they would otherwise be spliced into the middle of a
        quoted provision.
        """
        pages = self._pages()
        collected = pages[page_index][start:]
        offset = len(section) + 1
        pattern = successor_pattern(section)
        for step in range(1, _MAX_CONTINUATION_PAGES + 1):
            heading = pattern.search(collected[offset:])
            if heading:
                return collected[: offset + heading.start()], False
            if page_index + step >= len(pages):
                break
            offset = len(collected)
            collected += "\n" + _strip_running_headers(pages[page_index + step])
        # Ran out of pages or hit the continuation cap without finding the next section: the
        # extraction is incomplete and the caller must be told, not left to infer it.
        return collected, True

    @staticmethod
    def _looks_like_a_contents_entry(body: str) -> bool:
        """True for arrangement-of-sections entries, which are bare titles without provisions.

        **Structural discrimination, per D-070.** The predecessor tested for IPC penal
        vocabulary ("whoever", "punished with", ...) — which does not distinguish contents
        entries from real sections; it distinguishes IPC's drafting register from everything
        else, and silently discarded NDPS ss.19/26/37 (procedural and non-"whoever" sections)
        while surviving on IPC/BNS only because those happen to speak the register. A
        vocabulary list fails differently on every new statute; the STRUCTURE does not:

        * a real section prints its marginal note, then an em dash, then running text
          ("37. Offences to be cognizable and non-bailable.—(1) Notwithstanding ...");
        * a contents entry is a bare title ending at its line, the next line being the next
          numbered title.

        One refinement, found by regression the moment this shipped: the em dash is a
        SEPARATOR CONVENTION, not the structure itself. India Code PDFs print the title,
        an em dash, then the body; the BNS/BNSS gazette PDFs extract with no em dash at
        all ("103.(1) Whoever commits murder ..."). Requiring the dash re-created the
        original defect one level up: a filter fitted to one source family's typography.
        The invariant that holds across every stored source is D-070's second half: a
        contents entry is a bare title ending at its line (the successor heading follows
        immediately, so the slice is short); a real section runs on.
        """
        flat = " ".join(body.split())
        # Both branches measure RUNNING TEXT ON THE WHOLE BODY, never inside a fixed
        # window: an em dash arriving near a window's edge would leave almost nothing
        # after it *in the window* and misclassify a real section (caught by regression
        # on BNS s.117, whose first em dash sits ~380 characters in).
        if "\u2014" in flat[:400]:
            return len(flat.split("\u2014", 1)[1]) < 30
        # No em dash near the head: judge by running text alone. The longest
        # arrangement-of-sections titles in the stored acts flatten to ~100 characters;
        # the shortest real punishment body runs to several hundred. Repealed stubs land
        # on the contents side, which is correct: they carry nothing to quote.
        return len(flat) < 160
