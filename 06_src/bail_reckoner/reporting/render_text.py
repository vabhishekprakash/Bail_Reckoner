"""Plain-text renderer — the first renderer over the report object (D-068).

Fixed layout, UTF-8, byte-comparable: the same `Report` always renders to the same bytes, so
golden-file regression tests can diff output exactly. Newlines are always ``\\n``, never the
platform default.

Styling rules this renderer enforces (D-068, recording D-058's answers):

* **No colour encodes status — in either direction.** The rule is symmetric: celebration
  styling on entitlement (D-035) and alarm styling on "no entitlement" are equally barred,
  because red on a negative report reads as a finding of ineligibility, which D-010 says the
  system cannot make. Typographic hierarchy — position, casing, rules, the box — is the only
  emphasis available here or in any later renderer.
* **The urgent notice is a boxed block above everything**, including the status line. Its
  prominence comes from position and wording alone.
* **No internal vocabulary.** This module contains no display words of its own beyond layout
  furniture (labels for the fixed report shape); every sentence comes from the report object,
  which resolved it from the versioned language file.
"""

from __future__ import annotations

import textwrap
from datetime import date

from bail_reckoner.reporting.report import Report

__all__ = ["render_text"]

_WIDTH = 78
_RULE = "=" * _WIDTH
_THIN = "-" * _WIDTH


def _wrap(text: str, indent: str = "") -> list[str]:
    return textwrap.wrap(
        text,
        width=_WIDTH,
        initial_indent=indent,
        subsequent_indent=indent,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _box(heading: str, body: str) -> list[str]:
    inner = _WIDTH - 4
    lines = [f"| {heading:<{inner}} |", f"| {'':<{inner}} |"]
    for line in textwrap.wrap(body, width=inner, break_long_words=False, break_on_hyphens=False):
        lines.append(f"| {line:<{inner}} |")
    border = "+" + "-" * (_WIDTH - 2) + "+"
    return [border, *lines, border]


def _field(label: str, value: str) -> str:
    return f"  {label:<22}{value}"


def _date(value: date) -> str:
    return f"{value.day} {value.strftime('%B %Y')}"


def render_text(report: Report) -> str:
    """Render the report to plain text. Deterministic; ends with a single newline."""
    out: list[str] = []

    out.append(_RULE)
    out.append(f" {report.title}")
    out.append(_RULE)
    out.extend(_wrap(report.facilitator_line))
    out.append("")

    if report.urgent_notice is not None:
        out.extend(_box(report.urgent_notice.heading, report.urgent_notice.body))
        out.append("")

    out.append("STATUS")
    out.extend(_wrap(report.status_text, indent="  "))
    if report.barred_notice is not None:
        out.append("")
        out.extend(_wrap(report.barred_notice, indent="  "))
    out.append("")

    if report.legal_basis is not None:
        out.append("LEGAL BASIS")
        out.extend(_wrap(report.legal_basis.reason_text, indent="  "))
        if report.legal_basis.provision_cite:
            out.append(_field("Provision:", report.legal_basis.provision_cite))
        if report.legal_basis.provision_quote:
            out.extend(_wrap(f'"{report.legal_basis.provision_quote}"', indent="    "))
        out.append("")

    if report.contested_threshold_text is not None:
        out.append("TWO QUALIFYING DATES ARISE")
        out.extend(_wrap(report.contested_threshold_text, indent="  "))
        out.append("")

    custody = report.custody
    out.append("CUSTODY")
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

    for section in report.case_sections:
        pending = "pending" if section.is_pending else "not pending"
        out.append(f"CASE {section.case_ref}  ({pending})")
        for row in section.offences:
            out.append(f"  Offence: {row.label}")
            out.append(_field("  Section:", row.section))
            out.append(_field("  Maximum sentence:", row.max_sentence_text))
            if row.fraction_text is not None:
                out.append(_field("  Fraction applied:", row.fraction_text))
            if row.threshold_text is not None:
                out.append(_field("  Threshold:", row.threshold_text))
            for line in _wrap(f"Status: {row.status_text}", indent="    "):
                out.append(line)
            if row.note:
                out.extend(_wrap(f"Note: {row.note}", indent="    "))
        out.append("")

    out.append("CASES CONSIDERED")
    out.extend(_wrap(report.cases_considered.intro, indent="  "))
    for ref in report.cases_considered.case_refs:
        out.append(f"    - {ref}")
    out.extend(_wrap(report.cases_considered.caveat, indent="  "))
    out.append("")

    if report.findings:
        out.append("FOR HUMAN ATTENTION")
        for finding in report.findings:
            wrapped = textwrap.wrap(
                finding.text,
                width=_WIDTH,
                initial_indent="  * ",
                subsequent_indent="    ",
                break_long_words=False,
                break_on_hyphens=False,
            )
            out.extend(wrapped)
        out.append("")

    out.extend(_wrap(report.uniformity_note, indent="  "))
    out.append("")
    out.extend(_wrap(report.special_statute_set_note, indent="  "))
    out.append("")
    out.append(_THIN)
    out.append(report.footer_review_line)
    out.append("")
    out.extend(_wrap(report.footer_caption))
    prov = report.provenance
    out.append(_field("Statute version:", prov.statute_version))
    out.append(_field("Language version:", f"{prov.language_version} ({prov.language_hash[:12]})"))
    out.append(_field("Law in force on:", prov.law_in_force_on.isoformat()))
    out.append(_field("Inputs hash:", prov.inputs_hash))
    out.append(_field("Computed on:", prov.computed_on.isoformat()))
    out.extend(_wrap(prov.sources_line, indent="  "))
    out.append(_RULE)

    return "\n".join(out) + "\n"
