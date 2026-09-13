"""Plain-text renderer for the s.479(3) application (D-071).

Same contract as the report renderer (D-068): fixed layout, UTF-8, byte-comparable, ``\\n``
newlines, no colour in either direction, golden-file regression tested. The PDF renderer comes
later over the same `Application` object — a PDF embeds creation timestamps and object IDs and
can never be the regression artefact.

Blanks render as labelled underscore fields. This module writes no words of its own beyond
layout furniture; every sentence comes from the application object, which resolved it from the
versioned application-language file and the verified decision table.
"""

from __future__ import annotations

import textwrap
from datetime import date

from bail_reckoner.reporting.application import Application

__all__ = ["render_application_text"]

_WIDTH = 78
_RULE = "=" * _WIDTH
_THIN = "-" * _WIDTH
_BLANK = "_" * 34


def _wrap(text: str, indent: str = "") -> list[str]:
    return textwrap.wrap(
        text,
        width=_WIDTH,
        initial_indent=indent,
        subsequent_indent=indent,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _numbered(number: int, text: str) -> list[str]:
    prefix = f"{number}. "
    return textwrap.wrap(
        text,
        width=_WIDTH,
        initial_indent=prefix,
        subsequent_indent=" " * len(prefix),
        break_long_words=False,
        break_on_hyphens=False,
    )


def _blank_line(label: str) -> str:
    return f"{label}: {_BLANK}"


def _field(label: str, value: str) -> str:
    return f"  {label:<22}{value}"


def _date(value: date) -> str:
    return f"{value.day} {value.strftime('%B %Y')}"


def render_application_text(application: Application) -> str:
    """Render the application draft to plain text. Deterministic; single trailing newline."""
    out: list[str] = []
    blanks = application.blanks

    out.append(_RULE)
    out.append(f" {application.title}")
    out.append(_RULE)
    out.extend(_wrap(application.draft_notice))
    out.append("")

    out.append(_blank_line(blanks["court"]))
    out.append(_blank_line(blanks["case_number"]))
    out.append(_blank_line(blanks["person"]))
    out.append(_blank_line(blanks["jail"]))
    out.append("")

    out.extend(_wrap(application.opening_text))
    out.append("")

    for number, paragraph in enumerate(application.paragraphs, start=1):
        out.extend(_numbered(number, paragraph))
        out.append("")

    for section in application.case_sections:
        out.append(f"CASE {section.case_ref}")
        for row in section.offences:
            out.append(f"  Offence: {row.label}")
            out.append(_field("  Section:", row.section))
            out.append(_field("  Maximum sentence:", row.max_sentence_text))
            if row.fraction_text is not None:
                out.append(_field("  Fraction applied:", row.fraction_text))
            if row.threshold_text is not None:
                out.append(_field("  Threshold:", row.threshold_text))
            out.append(_field("  Threshold status:", row.status_text))
            # The maximum is the number every other figure derives from; it must not appear
            # as a bare assertion. Text plus citation where supplied; citation alone is the
            # floor; absence is stated, never passed over.
            if row.punishment_text:
                out.append("    Punishment provision, verbatim:")
                out.extend(_wrap(f'"{row.punishment_text}"', indent="      "))
            if row.punishment_citation:
                out.extend(_wrap(f"Source: {row.punishment_citation}", indent="    "))
            if not row.punishment_text and not row.punishment_citation:
                out.extend(
                    _wrap(
                        "Punishment provision: not supplied with the inputs — the provision "
                        "text and its source citation must be attached before filing.",
                        indent="    ",
                    )
                )
        out.append("")

    custody = application.custody
    out.append("CUSTODY, AS COMPUTED")
    out.append(_field("Date of arrest:", _date(custody.date_of_arrest)))
    if custody.date_of_first_remand is not None:
        out.append(_field("Date of first remand:", _date(custody.date_of_first_remand)))
    out.append(_field("Computed as on:", _date(custody.evaluated_on)))
    out.append(_field("Custody undergone:", f"{custody.custody_days} days"))
    if custody.break_days:
        out.append(_field("Not in custody:", f"{custody.break_days} days"))
    if custody.excluded_days:
        out.append(_field("Excluded (court):", f"{custody.excluded_days} days"))
    out.append(_field("Effective custody:", f"{custody.effective_custody_days} days"))
    out.append("")

    out.append("STATUTORY BASIS")
    for basis in application.statutory_basis:
        out.append(f"  {basis.cite}:")
        # Quotes may span paragraphs (the full s.479(1) carries three provisos and the
        # Explanation). Paragraph breaks are part of the statute's structure; keep them.
        paragraphs = basis.quote.split("\n")
        for index, paragraph in enumerate(paragraphs):
            prefix = '"' if index == 0 else ""
            suffix = '"' if index == len(paragraphs) - 1 else ""
            out.extend(_wrap(f"{prefix}{paragraph.strip()}{suffix}", indent="    "))
        out.append("")

    # A qualification on a substantive assertion belongs where the assertion is: here,
    # immediately after the provision quotes, never in the metadata footer.
    out.extend(_wrap(application.uniformity_note, indent="  "))
    out.append("")
    out.extend(_wrap(application.special_statute_set_note, indent="  "))
    out.append("")

    out.append("PRAYER")
    out.extend(_wrap(application.prayer_text, indent="  "))
    out.append("")

    out.append(_blank_line(blanks["place"]))
    out.append(_blank_line(blanks["signature_date"]))
    out.append(_blank_line(blanks["signature"]))
    out.append(_blank_line(blanks["officer_name"]))
    out.append(_blank_line(blanks["designation"]))
    out.append("")

    out.append(_THIN)
    out.append(application.review_line)
    out.append("")
    out.extend(_wrap(application.footer_caption))
    prov = application.provenance
    out.append(_field("Statute version:", prov.statute_version))
    out.append(_field("Language version:", f"{prov.language_version} ({prov.language_hash[:12]})"))
    out.append(_field("Law in force on:", prov.law_in_force_on.isoformat()))
    out.append(_field("Inputs hash:", prov.inputs_hash))
    out.append(_field("Computed on:", prov.computed_on.isoformat()))
    out.extend(_wrap(prov.sources_line, indent="  "))
    out.append(_RULE)

    return "\n".join(out) + "\n"
