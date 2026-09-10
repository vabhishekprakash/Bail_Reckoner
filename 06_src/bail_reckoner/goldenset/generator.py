"""Parametric fact-pattern generator for golden-set labelling (D-065).

Produces UNLABELLED fact patterns — inputs only, never expected values. Humans label them blind
to engine output; the generator writing a label would collapse the two channels the harness
exists to keep apart.

**Deliberately not organised per gate.** A gate-shaped generator inherits the engine's mental
model and confirms it: it produces exactly the situations the engine already distinguishes, and
none of the ones it wrongly conflates. OLQ-11 is the standing proof — it was found by a
hand-written case disagreeing with the engine, a case no per-gate sweep would have produced,
because the sweep would have asked "which maximum?" the same way the engine does. So this module
samples the *input space* — custody durations, offence counts and maxima, arrest and remand
dates, custody breaks, excluded days, first-timer status — independently and in combination, and
lets the combinations land where they land. Hand-written adversarial cases continue alongside it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

__all__ = ["OffencePoolEntry", "generate_fact_patterns", "write_fact_patterns"]


@dataclass(frozen=True, slots=True)
class OffencePoolEntry:
    """An offence reference available to the generator. References only — no maxima here."""

    regime: str
    section: str
    variant: str | None
    label: str


_PRIORS = ("KNOWN_PRIOR", "NONE_DECLARED", "UNKNOWN")


def generate_fact_patterns(
    *,
    seed: int,
    count: int,
    pool: tuple[OffencePoolEntry, ...],
    earliest_arrest: date = date(2018, 1, 1),
    latest_arrest: date = date(2026, 1, 1),
) -> list[dict[str, object]]:
    """Generate `count` fact patterns deterministically from `seed`.

    Determinism matters: a labelling batch must be reproducible, and a regenerated batch must be
    byte-identical so labels can never silently detach from their patterns.
    """
    if not pool:
        raise ValueError("offence pool must not be empty")
    rng = random.Random(seed)
    span_days = (latest_arrest - earliest_arrest).days
    patterns: list[dict[str, object]] = []

    for index in range(count):
        arrest = earliest_arrest + timedelta(days=rng.randrange(span_days + 1))
        evaluated = arrest + timedelta(days=rng.randrange(1, 3001))

        offence_count = rng.choice((1, 1, 1, 2, 2, 3))  # single-offence cases stay common
        chosen = rng.sample(pool, k=min(offence_count, len(pool)))

        # Group offences into 1..n pending cases; occasionally add a disposed case, which must
        # never influence gate 2.
        group_count = rng.randrange(1, len(chosen) + 1)
        offence_lists: list[list[dict[str, object]]] = [[] for _ in range(group_count)]
        for position, entry in enumerate(chosen):
            offence_lists[position % group_count].append(
                {
                    "ref": {
                        "regime": entry.regime,
                        "section": entry.section,
                        "variant": entry.variant,
                    },
                    "label": entry.label,
                }
            )
        groups: list[dict[str, object]] = [
            {"case_ref": f"GEN-{index:04d}-{g}", "is_pending": True, "offences": offence_lists[g]}
            for g in range(group_count)
        ]
        if rng.random() < 0.15:
            groups.append(
                {
                    "case_ref": f"GEN-{index:04d}-disposed",
                    "is_pending": False,
                    "offences": [
                        {
                            "ref": {
                                "regime": pool[0].regime,
                                "section": pool[0].section,
                                "variant": pool[0].variant,
                            },
                            "label": pool[0].label,
                        }
                    ],
                }
            )

        excluded_roll = rng.random()
        excluded_days = (
            0
            if excluded_roll < 0.6
            else rng.randrange(1, 31)
            if excluded_roll < 0.85
            else rng.randrange(31, 401)
        )

        breaks: list[dict[str, str]] = []
        custody_days = (evaluated - arrest).days
        for _ in range(rng.choice((0, 0, 0, 1, 1, 2))):
            if custody_days < 10:
                break
            start_offset = rng.randrange(1, custody_days - 5)
            length = rng.randrange(1, min(60, custody_days - start_offset))
            start = arrest + timedelta(days=start_offset)
            breaks.append(
                {
                    "start": start.isoformat(),
                    "end": (start + timedelta(days=length - 1)).isoformat(),
                }
            )

        remand_roll = rng.random()
        remand = (
            None
            if remand_roll < 0.5
            else arrest.isoformat()
            if remand_roll < 0.75
            else (arrest + timedelta(days=rng.randrange(1, 31))).isoformat()
        )

        patterns.append(
            {
                "pattern_id": f"GEN-{seed}-{index:04d}",
                "inputs": {
                    "date_of_arrest": arrest.isoformat(),
                    "evaluated_on": evaluated.isoformat(),
                    "date_of_first_remand": remand,
                    "prior_conviction_status": rng.choice(_PRIORS),
                    "excluded_days": excluded_days,
                    "custody_breaks": breaks,
                    "cases": groups,
                },
            }
        )
    return patterns


def write_fact_patterns(patterns: list[dict[str, object]], path: Path, seed: int) -> Path:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# UNLABELLED FACT PATTERNS — SYNTHETIC, inputs only, NO expected values (D-065).\n"
        "# Labels are written by humans BLIND to engine output; a generated label would\n"
        "# collapse the two channels the harness keeps apart. Generated deterministically\n"
        f"# from seed {seed}; regeneration with the same seed and pool is byte-identical.\n"
        "# Not organised per gate, on purpose — see generator.py's docstring and OLQ-11.\n"
    )
    body = yaml.safe_dump({"seed": seed, "patterns": patterns}, sort_keys=False, allow_unicode=True)
    path.write_text(header + body, encoding="utf-8")
    return path
