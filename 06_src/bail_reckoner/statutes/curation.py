"""Draft penalty rows from the bare acts stored in `01_law/` (M1, D-046).

Curation tooling, outside Layer C. Every row it produces is **DRAFT**; a human reads the quoted
clause and promotes it (D-046). Nothing here can create a VERIFIED row.

The safety property that makes this usable at all: a seed entry names a *candidate* section and a
keyword that the section's own text must contain. If the extracted text does not contain the
keyword, **the row is not drafted** and the entry is reported as unresolved. So a wrong section
number produces a visible gap, never a plausible-looking row attaching the wrong punishment to an
offence — the failure mode that made two official IPC PDFs unusable (`01_law/SOURCES.md`).

Deciding the structured maximum from the clause is a legal reading, which is exactly why the row
lands as DRAFT with the clause quoted verbatim beside it: the reviewer checks a sentence, not a
database.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from bail_reckoner.statutes.bare_act import BareAct, SectionText
from bail_reckoner.statutes.models import (
    MaximumPunishment,
    OffenceRow,
    Provenance,
    PunishmentKind,
    Regime,
)

__all__ = [
    "SeedEntry",
    "DraftResult",
    "SEED_LIST",
    "count_punishment_limbs",
    "draft_rows",
    "export_drafts",
    "BNS_FILE",
    "IPC_FILE",
    "DRAFT_EXPORT_PATH",
]

BNS_FILE = "BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf"
IPC_FILE = "IPC_1860_Act45_IndiaCode_repealed_file.pdf"

DRAFTED_BY = "model-draft (unverified)"
"""Placeholder occupying `verified_by` until a person promotes the row.

Deliberately not a person's name and deliberately not empty: empty would fail the provenance
constraint, and a name would assert a verification that has not happened.
"""


@dataclass(frozen=True, slots=True)
class SeedEntry:
    """One offence to draft, in both regimes where a counterpart exists.

    `must_contain` is the guard. It is a distinctive phrase from the section's own text; if the
    extracted section does not contain it, the candidate section number was wrong and the row is
    refused rather than drafted.
    """

    key: str
    label: str
    ipc_section: str | None
    bns_section: str | None
    must_contain: str
    criteria: tuple[str, ...] = ()
    """Which D-046 coverage criteria this entry is here to satisfy."""

    priority: bool = False
    """In the first review pass. Chosen to exercise gates 0, 1, 3 and 5 end-to-end on the
    smallest set of rows, so the engine can be run against real maxima before all 40 are done."""

    ipc_must_contain: str | None = None
    """Override for the IPC side. The two codes phrase the same offence differently -- IPC s.323
    says "voluntarily causes hurt" where BNS s.115 says "causing hurt to any person" -- so one
    shared keyword cannot guard both. Falls back to `must_contain` when unset."""

    def keyword_for(self, regime: Regime) -> str:
        if regime is Regime.IPC_1860 and self.ipc_must_contain:
            return self.ipc_must_contain
        return self.must_contain


@dataclass(frozen=True, slots=True)
class DraftResult:
    """What drafting produced, including what it refused to produce."""

    rows: tuple[OffenceRow, ...]
    unresolved: tuple[str, ...]
    """`entry.key: reason` for each candidate that failed its keyword guard."""


# The seed list. Section numbers here are CANDIDATES to be checked against the bare acts by the
# keyword guard, never assertions. An entry whose guard fails is reported, not guessed at.
#
# Coverage criteria are from D-046:
#   (i)   common undertrial offence profile
#   (ii)  a matched IPC<->BNS pair for every entry where one exists
#   (iii) at least one death/life offence, to exercise gates 0 and 1
#   (iv)  at least one Category-C special-statute offence
#   (v)   at least one offence whose maximum differs between IPC and BNS
#   (vi)  at least one compoundable and one non-compoundable offence
#
# `priority=True` marks the first review pass: 10 entries = 20 rows, chosen to exercise gates
# 0, 1, 3 and 5 end-to-end on the smallest set, so the engine can run against real maxima before
# all 40 rows are reviewed. It contains the death/life pair (gates 0 and 1), the IPC 304A /
# BNS 106 divergence pair (transitional path), and the highest-volume common offences.
SEED_LIST: tuple[SeedEntry, ...] = (
    SeedEntry("theft", "Theft", "379", "303", "Whoever commits theft", ("i", "ii"), priority=True),
    SeedEntry(
        "murder",
        "Murder",
        "302",
        "103",
        "Whoever commits murder",
        ("i", "ii", "iii"),
        priority=True,
    ),
    SeedEntry(
        "culpable_homicide",
        "Culpable homicide not amounting to murder",
        "304",
        "105",
        "culpable homicide not amounting to murder",
        ("i", "ii", "iii"),
    ),
    SeedEntry(
        "death_by_negligence",
        "Causing death by negligence",
        "304A",
        "106",
        "rash or negligent act",
        ("i", "ii", "v"),
        priority=True,
    ),
    SeedEntry(
        "attempt_murder", "Attempt to murder", "307", "109", "such circumstances", ("i", "ii")
    ),
    SeedEntry(
        "voluntarily_causing_hurt",
        "Voluntarily causing hurt",
        "323",
        "115",
        "causing hurt to any person",
        ("i", "ii", "vi"),
        priority=True,
        ipc_must_contain="voluntarily causes hurt",
    ),
    SeedEntry(
        "grievous_hurt",
        "Voluntarily causing grievous hurt",
        "325",
        "117",
        "grievous hurt",
        ("i", "ii"),
    ),
    # Wrongful RESTRAINT, not confinement. Its very low maximum makes it the sharpest gate-0
    # exerciser in the set: the absolute cap is reached fastest where the maximum is smallest,
    # which is exactly where s.479 bites. Worth its limbs on its own merits.
    SeedEntry(
        "wrongful_restraint",
        "Wrongful restraint",
        "341",
        "126",
        "wrongfully restrains",
        ("i", "ii", "vi"),
        priority=True,
    ),
    # Using a forged document as genuine — the forgery-family limb that actually appears in
    # charge sheets, retained in place of plain forgery.
    SeedEntry(
        "using_forged_document",
        "Using as genuine a forged document",
        "471",
        "340",
        "fraudulently or dishonestly uses as genuine",
        ("i", "ii"),
    ),
    SeedEntry(
        "robbery", "Robbery", "392", "309", "commits robbery", ("i", "ii", "vi"), priority=True
    ),
    # CUT 2026-08-12: dacoity carries life, so gate 1 bars it and gate 0 cannot fire against a
    # life maximum — the precision of its rows cannot change any verdict. Murder is retained and
    # covers gate-1 exercise. Removed on that ground, NOT on its limb count.
    #   SeedEntry("dacoity", "Dacoity", "395", "310", "commits dacoity", ("i", "ii")),
    SeedEntry(
        "criminal_breach_of_trust",
        "Criminal breach of trust",
        "406",
        "316",
        "criminal breach of trust",
        ("i", "ii"),
        priority=True,
    ),
    SeedEntry(
        "cheating",
        "Cheating",
        "420",
        "318",
        "cheats and thereby",
        ("i", "ii", "vi"),
        priority=True,
    ),
    SeedEntry(
        "receiving_stolen_property",
        "Dishonestly receiving stolen property",
        "411",
        "317",
        "stolen property",
        ("i", "ii"),
    ),
    SeedEntry(
        "mischief", "Mischief", "426", "324", "commits mischief", ("i", "ii", "vi"), priority=True
    ),
    SeedEntry(
        "house_trespass",
        "House-trespass",
        "448",
        "331",
        "house-trespass",
        ("i", "ii"),
        priority=True,
    ),
    # CUT 2026-08-12, swapped for `using_forged_document` above: the forgery-family limb that
    # appears in charge sheets is using a forged document as genuine, not plain forgery.
    #   SeedEntry("forgery", "Forgery", "465", "336", "commits forgery", ("i", "ii")),
    SeedEntry(
        "criminal_intimidation",
        "Criminal intimidation",
        "506",
        "351",
        "criminal intimidation",
        ("i", "ii", "vi"),
        priority=True,
    ),
    SeedEntry(
        "cruelty_by_husband",
        "Cruelty by husband or relative of husband",
        "498A",
        "85",
        "subjects such woman to cruelty",
        ("i", "ii"),
    ),
    SeedEntry(
        "kidnapping",
        "Kidnapping",
        "363",
        "137",
        "kidnaps any person",
        ("i", "ii"),
    ),
    SeedEntry(
        "rioting",
        "Rioting",
        "147",
        "191",
        "guilty of rioting",
        ("i", "ii"),
    ),
)


def draft_rows(
    seed: tuple[SeedEntry, ...] = SEED_LIST, *, drafted_on: date | None = None
) -> DraftResult:
    """Extract each seed offence from the bare acts and return DRAFT rows.

    Rows carry the section's verbatim text as `quoted_text` and a page-level citation as
    `verified_against`, so a reviewer can check the maximum against the clause without reopening
    the PDF. `verified_by` records that the row is a model draft, not a verification.

    The structured maximum is **not** inferred here. Every drafted row is stored with a
    placeholder maximum flagged in `notes`, and the reviewer sets the real one. Parsing
    "imprisonment of either description for a term which may extend to three years, or with fine,
    or with both" into a structured maximum is a legal reading, and a regex that appeared to do it
    would manufacture exactly the false confidence this project exists to avoid.
    """
    stamp = drafted_on or date(2026, 8, 12)
    # Shared instances: extraction over both acts is ~220 pages, and this runs repeatedly.
    acts = {Regime.BNS_2023: BareAct.open(BNS_FILE), Regime.IPC_1860: BareAct.open(IPC_FILE)}
    rows: list[OffenceRow] = []
    unresolved: list[str] = []

    for entry in seed:
        for regime, section in (
            (Regime.IPC_1860, entry.ipc_section),
            (Regime.BNS_2023, entry.bns_section),
        ):
            if section is None:
                unresolved.append(f"{entry.key}/{regime.value}: no counterpart recorded")
                continue
            keyword = entry.keyword_for(regime)
            found = acts[regime].find_section(section, must_contain=keyword)
            if found is None:
                unresolved.append(
                    f"{entry.key}/{regime.value}: s.{section} not found containing "
                    f"{keyword!r} — candidate section number unconfirmed"
                )
                continue
            limbs = count_punishment_limbs(found.text)
            if limbs == 0:
                # D-064: zero on a statutory-value path is a failed detection, reported as a
                # gap. Drafting a single default row here would be exactly the max(1, ...)
                # pattern this project has now hit three times.
                unresolved.append(
                    f"{entry.key}/{regime.value}: s.{section} located but ZERO punishment "
                    f"limbs detected — detector failure or a definition-only section; "
                    f"resolve by reading the page, never by defaulting a row"
                )
                continue
            # One row per punishment limb (D-061). Variants are detector labels L1..Ln that the
            # reviewer renames to the statutory limb as printed on the page; the count itself is
            # an estimate the reviewer corrects against the page.
            if limbs == 1:
                rows.append(_to_draft_row(entry, regime, section, found, stamp, None, 1, 1))
            else:
                for index in range(1, limbs + 1):
                    rows.append(
                        _to_draft_row(
                            entry, regime, section, found, stamp, f"L{index}", index, limbs
                        )
                    )

    return DraftResult(rows=tuple(rows), unresolved=tuple(unresolved))


_STATE_AMENDMENT = re.compile(r"STATE\s*AMENDMENTS?", re.I)

# Matched against text with ALL whitespace removed. The India Code IPC PDF splits words at
# arbitrary points -- "shal l be punished", "shall be liab le either to" -- so any pattern with
# spaces in it silently fails on the IPC while succeeding on the cleaner gazette-sourced BNS.
_LIMB_OPERATORS = (
    "shallbepunished",
    "shallbeliableto",
    "shallbeliableeitherto",
    "maybepunished",
)

# Prose continuation limbs: a second maximum introduced without repeating the operator.
# IPC s.304 Part II reads "...; or with imprisonment ... if the act is done with the knowledge",
# a distinct maximum on a distinct mental state.
_PROSE_LIMB = "orwithimprisonment"

# ...but the SAME words also join two alternatives WITHIN one limb: "shall be punished with
# imprisonment for life, or with imprisonment of either description for a term which may extend
# to ten years" is one punishment offering a choice, not two punishments. Page-verifying BNS
# ss.331, 316 and 317 showed the prose rule over-counting every one of them by exactly this.
# The tell is the immediately preceding "life," — an alternative to life, not a new limb.
_PROSE_FALSE_POSITIVE = "life,orwithimprisonment"


def count_punishment_limbs(section_text: str) -> int:
    """Count distinct punishment limbs in a section's text.

    Used to size the row count for per-limb keying (D-061). Wrong counts drive a real decision --
    an undercounted section ships as one row asserting a single maximum for a section that has
    several, and IPC governs every pre-1-July-2024 offence.

    Three defects this exists to avoid, all found on real text:

    * **Intra-word spaces.** The India Code IPC renders "shal l be punished". Matching on spaced
      patterns returned **zero** limbs for IPC s.307 and near-uniform 1s across the IPC. All
      matching here is done on whitespace-stripped text.
    * **Prose continuation limbs.** IPC s.304's Part II maximum is introduced by "or with
      imprisonment", not by repeating "shall be punished".
    * **State-amendment contamination.** India Code prints `STATE AMENDMENTS` inline; the block
      after IPC s.304A contains Himachal Pradesh's s.304-AA and its own punishment clause. Those
      belong to a different provision and to L-002, not to this section's limb count.

    Returns 0 honestly when nothing matches. An earlier caller floored this at 1, which converted
    a total detection failure into a plausible-looking count.
    """
    body = section_text
    match = _STATE_AMENDMENT.search(body)
    if match:
        body = body[: match.start()]
    squeezed = re.sub(r"\s+", "", body).lower()
    operators = sum(squeezed.count(op) for op in _LIMB_OPERATORS)
    prose = squeezed.count(_PROSE_LIMB) - squeezed.count(_PROSE_FALSE_POSITIVE)
    return operators + max(prose, 0)


_PRIORITY_KEYS = frozenset(entry.key for entry in SEED_LIST if entry.priority)


def _is_priority(row: OffenceRow) -> bool:
    """A drafted row is priority iff its seed entry is. Recovered from the notes line, which
    records the seed key, so the flag survives the row/entry boundary without a new field."""
    match = re.search(r"seed '([^']+)'", row.notes)
    return bool(match and match.group(1) in _PRIORITY_KEYS)


# NOTE (2026-08-26): the reviewable copy of these rows now lives in the consolidated
# REVIEW_QUEUE_2026-08-26.yaml (one file, both batches, sanity-pass order — Abhishek's
# direction). This export path is the GENERATOR's target only; re-running the export
# does not update the consolidated queue, which must be re-merged deliberately.
DRAFT_EXPORT_PATH = (
    Path(__file__).resolve().parents[3] / "02_data" / "penalty_rows" / "draft_seed_batch1.yaml"
)


def export_drafts(result: DraftResult, path: Path | None = None) -> Path:
    """Write drafted rows to a reviewable YAML file.

    The rows are versioned as **text**, not as a SQLite binary, for the same reason the decision
    table is (D-055): a reviewer has to read the quoted clause and set the maximum, and that is a
    review of a document, not of a database. The SQLite store is then a build artefact derived
    from this file, so the reviewable source is what git tracks.

    Every row is written with `maximum: null` and an explicit `REVIEWER ACTION` line. Nothing here
    fills in a maximum -- reading a punishment clause is a legal judgement (D-046).
    """
    target = path or DRAFT_EXPORT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    groups = _group_and_sort(result.rows)
    section_count = len(groups)
    priority_sections = sum(1 for g in groups if g.priority)

    lines: list[str] = [
        "# DRAFT penalty rows, ONE ROW PER PUNISHMENT LIMB (D-061).",
        "# NOT VERIFIED, NOT USABLE BY THE ENGINE. The engine reads only VERIFIED rows.",
        "#",
        "# REVIEWER ACTION, per SECTION:",
        "#   1. OPEN THE PDF at the page named in `READ_THIS_PAGE` and read the section THERE.",
        "#      DO NOT work from `extractor_output_do_not_rely_on`.",
        "#   2. The number of limb rows under each section is a DETECTOR ESTIMATE. The page",
        "#      governs: if the section has more limbs than rows, add rows; fewer, delete rows.",
        "#   3. Per limb row: rename `variant` from the detector label (L1, L2, ...) to the",
        "#      statutory limb as printed on the page — e.g. '(2)', '(4)', 'Part II' — and update",
        "#      `offence_id` to match (it must end '#<variant>').",
        "#   4. Per limb row, set from what the PAGE says:",
        "#        maximum          — kinds (DEATH/LIFE/TERM/FINE_ONLY/BY_REFERENCE),",
        "#                           term_months where a definite term is prescribed, fine_also",
        "#        min_term_months  — ONLY where the limb prescribes a mandatory minimum;",
        "#                           otherwise leave null. Feeds no gate; shown for honesty.",
        "#   Then put your name in `verified_by`, today's date in `verified_on`,",
        "#   and set `status: VERIFIED`.",
        "#",
        "# WHY THE PAGE AND NOT THE EXTRACTOR OUTPUT — this is the point of the whole review:",
        "# the extractor output is the machine's belief. You are the independent channel. Its",
        "# documented failures include truncating at page breaks, over-running into the next",
        "# section, missing amendment-inserted sections, mis-reading page numbers, and counting",
        "# a threatened offence's punishment as a limb. If the page and the output disagree,",
        "# THE PAGE WINS, and the disagreement is worth reporting — it is an extractor bug.",
        "#",
        "# Sections marked `definition_punishment_split: true` (the BNS s.303(1)/(2) shape) and",
        "# `state_amendment_present: true` (L-002) are exactly where extractor output is least",
        "# trustworthy — the split/apparatus is inside the section itself.",
        "#",
        "# `compoundable` is NOT your job here: it lives in the compounding table, feeds no gate,",
        "# and gets its own pass with the table entry quoted (D-036 vi).",
        "#",
        "# ORDER (D-061 review sort): priority sections first; within priority, multi-limb",
        "# sections first with limbs adjacent in text order (base limb, then aggravated limbs,",
        "# then enhancement provisos, as the statute prints them); gate coverage is the second",
        "# sort key. A too-high maximum inflates gate 5 AND suppresses gate 0 — the silent",
        "# false negative — which is why the multi-limb sections come first.",
        "",
        f"generated_on: {date.today().isoformat()}",
        f"row_count: {len(result.rows)}",
        f"section_count: {section_count}",
        f"priority_section_count: {priority_sections}",
        "rows:",
    ]
    for group in groups:
        quoted = " ".join(group.rows[0].provenance.quoted_text.split())
        marks = []
        if group.split_tell:
            marks.append("DEFINITION/PUNISHMENT SPLIT")
        if group.state_amendment:
            marks.append("STATE AMENDMENT PRESENT (L-002)")
        lines.append(
            f"  # ── {group.rows[0].regime.value}-{group.section} · {group.rows[0].label}"
            f" · {len(group.rows)} limb(s){' · ' + ' · '.join(marks) if marks else ''}"
        )
        for index, row in enumerate(group.rows):
            lines.extend(
                [
                    f"  - offence_id: {row.offence_id!r}",
                    f"    priority: {str(group.priority).lower()}",
                    f"    label: {row.label!r}",
                    f"    regime: {row.regime.value}",
                    f"    section: {row.section!r}",
                    f"    variant: {row.variant!r}"
                    + ("   # REVIEWER: rename to the limb as printed" if row.variant else ""),
                    f"    counterpart_id: {row.counterpart_id!r}",
                    "    maximum: null            # REVIEWER: set from the PAGE",
                    "    min_term_months: null    # REVIEWER: only if the limb prescribes one",
                    "    compoundable: null       # not this pass (D-036 vi)",
                    "    status: DRAFT",
                    f"    definition_punishment_split: {str(group.split_tell).lower()}",
                    f"    state_amendment_present: {str(group.state_amendment).lower()}",
                    f"    source: {row.provenance.source!r}",
                    f"    READ_THIS_PAGE: {row.provenance.verified_against!r}",
                    f"    verified_by: {row.provenance.verified_by!r}",
                    (
                        f"    extractor_output_do_not_rely_on: {quoted!r}"
                        if index == 0
                        else (
                            "    extractor_output_do_not_rely_on: "
                            "SAME_SECTION_TEXT_AS_FIRST_LIMB_ABOVE"
                        )
                    ),
                    "",
                ]
            )
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


@dataclass(frozen=True, slots=True)
class _SectionGroup:
    section: str
    rows: tuple[OffenceRow, ...]
    priority: bool
    gate_rank: int
    split_tell: bool
    state_amendment: bool


def _group_and_sort(rows: tuple[OffenceRow, ...]) -> list[_SectionGroup]:
    """Group limb rows by (regime, section) and apply the D-061 review sort.

    Sort: priority sections first; then multi-limb sections before single-limb (a too-high
    maximum both inflates the gate-5 threshold and suppresses gate 0, so the sections where a
    wrong single maximum is most likely come first); then gate coverage; then id for stability.
    Limbs stay adjacent and in text order within their section.
    """
    grouped: dict[tuple[str, str], list[OffenceRow]] = {}
    for row in rows:
        grouped.setdefault((row.regime.value, row.section), []).append(row)

    result: list[_SectionGroup] = []
    for (_, section), members in grouped.items():
        first = members[0]
        result.append(
            _SectionGroup(
                section=section,
                rows=tuple(members),
                priority=_is_priority(first),
                gate_rank=_gate_rank(first.notes),
                split_tell=definition_punishment_split(first.provenance.quoted_text),
                state_amendment=bool(_STATE_AMENDMENT.search(first.provenance.quoted_text)),
            )
        )
    result.sort(key=lambda g: (not g.priority, -len(g.rows), g.gate_rank, g.rows[0].offence_id))
    return result


def _gate_rank(notes: str) -> int:
    """Second sort key: which gates the section's coverage criteria exercise.

    iii (death/life) exercises gates 0 and 1 → first; v (IPC/BNS divergence) exercises the
    transitional path into gate 5 → second; vi (compoundability spread) → third; the rest by
    profile order. Reads the criteria recorded in the row's notes.
    """
    match = re.search(r"Coverage criteria: ([^.]*)\.", notes)
    criteria = {c.strip() for c in match.group(1).split(",")} if match else set()
    if "iii" in criteria:
        return 0
    if "v" in criteria:
        return 1
    if "vi" in criteria:
        return 2
    return 3


def definition_punishment_split(section_text: str) -> bool:
    """True where the punishment lives in a different sub-section than the definition.

    The documented case is BNS s.303: s.303(1) defines theft and s.303(2) punishes it. These
    sections stay page-checked even after the boundary fix, because the boundary the extractor
    must find is *inside* the section. A mechanical proxy, used only to order and mark the review
    sheet — it feeds no gate and no statutory value: sub-section (1) exists, sub-section (2)
    exists, and the first punishment operator appears only after (2) opens.
    """
    squeezed = re.sub(r"\s+", "", section_text).lower()
    sub1, sub2 = squeezed.find("(1)"), squeezed.find("(2)")
    if sub1 == -1 or sub2 == -1:
        return False
    positions = [squeezed.find(op) for op in (*_LIMB_OPERATORS, _PROSE_LIMB)]
    hits = [p for p in positions if p != -1]
    return bool(hits) and min(hits) > sub2


def _to_draft_row(
    entry: SeedEntry,
    regime: Regime,
    section: str,
    found: SectionText,
    stamp: date,
    variant: str | None,
    limb_index: int,
    limb_total: int,
) -> OffenceRow:
    # Explicit per-regime resolution, no else-arm (D-067 discipline): when NDPS_1985 was
    # added to Regime, the old ternary would silently have treated it as BNS and invented an
    # IPC counterpart for a statute that has none. Every regime is named; a new one breaks here.
    if regime is Regime.IPC_1860:
        counterpart, other = entry.bns_section, Regime.BNS_2023
    elif regime is Regime.BNS_2023:
        counterpart, other = entry.ipc_section, Regime.IPC_1860
    elif regime is Regime.NDPS_1985:
        raise ValueError(
            "the IPC/BNS seed pipeline cannot draft NDPS rows: NDPS has no cross-regime "
            "counterpart section; use draft_ndps_rows()"
        )
    else:  # pragma: no cover - unreachable until Regime grows again
        raise ValueError(f"unhandled regime {regime!r}: add it here deliberately")
    suffix = f"#{variant}" if variant else ""
    return OffenceRow(
        offence_id=f"{regime.value}-{section}{suffix}",
        label=entry.label,
        regime=regime,
        section=section,
        variant=variant,
        # Placeholder. The reviewer replaces this with the maximum read off the quoted clause.
        # BY_REFERENCE is used rather than a guessed term so that an unpromoted row can never be
        # mistaken for a computable maximum: it is not `is_computable`, so gate 5 refuses it.
        maximum=MaximumPunishment(
            kinds=frozenset({PunishmentKind.BY_REFERENCE}),
            reference_note="Maximum not yet determined; read it off quoted_text and set it.",
        ),
        provenance=Provenance(
            source=found.source_file,
            verified_against=found.citation(),
            verified_on=stamp,
            verified_by=DRAFTED_BY,
            # FULL text, never capped. An earlier [:4000] cap silently cut BNS s.303's quote
            # BEFORE its punishment sub-section began (the section runs ~6,400 chars with the
            # definition, explanations and illustrations first) — the audit trail for theft
            # omitted the very clause the row exists to record, and the split tell computed on
            # the truncated text read false for the documented case. A cap on an audit-trail
            # field is a convenience default in disguise (D-064).
            quoted_text=found.text,
        ),
        counterpart_id=f"{other.value}-{counterpart}" if counterpart else None,
        notes=(
            f"DRAFT from seed '{entry.key}'. Limb {limb_index} of {limb_total} "
            f"(detector estimate; the page governs). Coverage criteria: "
            f"{', '.join(entry.criteria) or 'none recorded'}. "
            f"Maximum MUST be set by a reviewer from the cited page before promotion."
        ),
    )


# ---------------------------------------------------------------------------
# NDPS quantity-band drafting (D-067, executing D-046 criterion iv)
# ---------------------------------------------------------------------------

NDPS_FILE = "NDPS_1985_Act61_IndiaCode_asOn_2022-01-03.pdf"

NDPS_QUANTITY_BANDS: tuple[str, ...] = (
    "small_quantity",
    "lesser_than_commercial",
    "commercial_quantity",
)
"""The three punishment bands of the post-2001 NDPS scheme. Unlike an IPC/BNS limb, the band
is a **case fact** (the quantity seized), not a sub-section of the charge — which is exactly
why D-067 chose these rows: they exercise variant keying on a new dimension, and an unknown
band abstains via OFFENCE_NOT_IN_DATABASE like any unnamed limb (D-061)."""


@dataclass(frozen=True, slots=True)
class NdpsSeedEntry:
    """One NDPS section candidate. The keyword guard, not this entry, decides if rows draft."""

    key: str
    label: str
    section: str
    must_contain: str


# Scope: the possession-charge sections named by D-046 criterion (iv) ("NDPS possession,
# small vs commercial quantity rows"): cannabis, manufactured drugs, psychotropic substances —
# the highest-volume NDPS charges. Sections 15/17/18 (poppy straw, prepared opium, opium)
# share the band structure and can be drafted the same way if the review scope widens; not
# drafting them is a stated scope choice, not an oversight. Non-band limbs inside these
# sections (e.g. s.20(a) cultivation) are outside criterion (iv) and are NOT drafted; the
# reviewer sheet says so per section.
NDPS_SEED_LIST: tuple[NdpsSeedEntry, ...] = (
    NdpsSeedEntry(
        "ndps_cannabis",
        "Contravention in relation to cannabis plant and cannabis",
        "20",
        "cannabis",
    ),
    NdpsSeedEntry(
        "ndps_manufactured",
        "Contravention in relation to manufactured drugs and preparations",
        "21",
        "manufactured drug",
    ),
    NdpsSeedEntry(
        "ndps_psychotropic",
        "Contravention in relation to psychotropic substances",
        "22",
        "psychotropic substance",
    ),
)

# Same note as DRAFT_EXPORT_PATH: the reviewable copy is the consolidated queue.
NDPS_DRAFT_EXPORT_PATH = (
    Path(__file__).resolve().parents[3] / "02_data" / "penalty_rows" / "draft_ndps_batch1.yaml"
)


def draft_ndps_rows(
    seed: tuple[NdpsSeedEntry, ...] = NDPS_SEED_LIST, drafted_on: date | None = None
) -> DraftResult:
    """Draft NDPS quantity-band rows from the stored Act, under the keyword guard (D-067).

    Provision: quantity bands per the substituted punishment sections of the NDPS Act, 1985
    (Act 61 of 1985), text as stored in `01_law/` (India Code, as on 2022-01-03). s.37's bail
    bar is separately verified and lives in the decision table; these rows carry the gate-3
    membership fields only.

    Guards, in addition to the section keyword: the extracted text must contain BOTH
    "small quantity" and "commercial quantity". A section failing the guard produces no rows
    and a reported gap — never a defaulted row (D-064). Maxima and the mandatory minimums are
    NOT inferred here; every row ships a placeholder the reviewer must replace from the page,
    exactly as in the IPC/BNS pass.
    """
    stamp = drafted_on or date(2026, 8, 19)
    act = BareAct.open(NDPS_FILE)
    rows: list[OffenceRow] = []
    unresolved: list[str] = []

    for entry in seed:
        found = act.find_section(entry.section, must_contain=entry.must_contain)
        if found is None:
            unresolved.append(
                f"{entry.key}/NDPS_1985: s.{entry.section} not found containing "
                f"{entry.must_contain!r}"
            )
            continue
        lowered = " ".join(found.text.split()).lower()
        missing = [
            phrase for phrase in ("small quantity", "commercial quantity") if phrase not in lowered
        ]
        if missing:
            unresolved.append(
                f"{entry.key}/NDPS_1985: s.{entry.section} extracted text lacks the band "
                f"phrase(s) {missing} — bands not drafted; check the extraction, not the seed"
            )
            continue
        for index, band in enumerate(NDPS_QUANTITY_BANDS, start=1):
            rows.append(
                OffenceRow(
                    offence_id=f"NDPS_1985-{entry.section}#{band}",
                    label=entry.label,
                    regime=Regime.NDPS_1985,
                    section=entry.section,
                    variant=band,
                    maximum=MaximumPunishment(
                        kinds=frozenset({PunishmentKind.BY_REFERENCE}),
                        reference_note=(
                            "Maximum not yet determined; read it off quoted_text and set it."
                        ),
                    ),
                    provenance=Provenance(
                        source=found.source_file,
                        verified_against=found.citation(),
                        verified_on=stamp,
                        verified_by=DRAFTED_BY,
                        quoted_text=found.text,
                    ),
                    special_statute="NDPS",
                    special_statute_provision="s.37",
                    counterpart_id=None,
                    notes=(
                        f"DRAFT from NDPS seed '{entry.key}' (D-067). Band {index} of "
                        f"{len(NDPS_QUANTITY_BANDS)}: the variant is the QUANTITY BAND — a case "
                        f"fact, not a sub-section. Set maximum AND min_term_months (bands above "
                        f"small quantity carry mandatory minimums) from the cited page. "
                        f"Non-band limbs of this section (e.g. cultivation) are outside "
                        f"criterion (iv) and are not drafted here."
                    ),
                )
            )
    return DraftResult(rows=tuple(rows), unresolved=tuple(unresolved))
