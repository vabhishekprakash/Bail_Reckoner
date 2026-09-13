"""Request and response schemas — the API contract (D-076).

Requests carry facts a caller can actually know: identifiers, dates, declarations and
affirmations. They never carry a maximum sentence (D-060) and never carry a person's name —
`CaseInput` has no name field by design, and the API adds none.

Responses are envelopes: `{mode, verified_row_count, data_warning, ...payload}`. The payload
for a report is the serialized `Report` object plus its canonical text rendering; for an
application it is a discriminated union — a generated filing or a refusal stating every
failed condition. A refusal is a successful computation with a refusal outcome, so it
travels as HTTP 200 with `kind: "refusal"`, never as an error status: an error status would
invite clients to treat the reasons as noise.
"""

from __future__ import annotations

import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "OffenceIn",
    "CaseIn",
    "CustodyBreakIn",
    "ComputeRequest",
    "Envelope",
    "ReportResponse",
    "ApplicationResponse",
    "MetaResponse",
]


class OffenceIn(BaseModel):
    """One charged offence, by key only. The maximum is resolved server-side (D-060)."""

    model_config = ConfigDict(extra="forbid")

    regime: Literal["IPC_1860", "BNS_2023", "NDPS_1985"]
    section: str = Field(min_length=1, max_length=32)
    variant: str | None = Field(default=None, max_length=64)
    label: str = Field(min_length=1, max_length=200)
    bar_in_scope: bool | None = Field(
        default=None,
        description=(
            "Whether this charge falls within the special-statute bar's own scope words "
            "(D-074), affirmed by the caller against the quoted scope note. Leave null when "
            "undetermined: the computation then routes the scope question to a human rather "
            "than defaulting to the test."
        ),
    )


class CaseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_ref: str = Field(min_length=1, max_length=120)
    is_pending: bool = True
    offences: list[OffenceIn] = Field(min_length=1)


class CustodyBreakIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: datetime.date
    end: datetime.date


class ComputeRequest(BaseModel):
    """Everything the engine needs, minus anything the caller must not assert (maxima).

    `case_list_verified` and `prior_conviction_verified` default to False and are
    affirmations, not conveniences: each states that the named fact was checked against
    records. A UI must never pre-tick them and must state what is being affirmed at the
    point of affirmation (D-077 constraint 6).
    """

    model_config = ConfigDict(extra="forbid")

    date_of_arrest: datetime.date
    evaluated_on: datetime.date
    date_of_first_remand: datetime.date | None = None
    cases: list[CaseIn] = Field(min_length=1)
    prior_conviction_status: Literal["NONE_DECLARED", "KNOWN_PRIOR", "UNKNOWN"] = "UNKNOWN"
    case_list_verified: bool = False
    prior_conviction_verified: bool = False
    excluded_days: int = Field(default=0, ge=0)
    custody_breaks: list[CustodyBreakIn] = Field(default_factory=list)
    scope_479_2: Literal["NARROW", "BROAD"] = "NARROW"
    mode: Literal["verified", "synthetic"] = Field(
        default="verified",
        description=(
            "'verified' resolves offences against the verified penalty database only — "
            "which, while zero verified rows exist, resolves nothing and abstains. "
            "'synthetic' resolves against the labelled synthetic fixtures (9xx sections) "
            "for demonstration, and every response says so unmissably."
        ),
    )


class Envelope(BaseModel):
    """Fields present on every computed response. The honesty layer (D-076)."""

    mode: Literal["verified", "synthetic"]
    verified_row_count: int
    data_warning: str
    """Unmissable while zero verified rows exist or the synthetic fixtures are in use.
    Clients must render it; it is part of the payload, not a header."""

    statute_version: str


class ReportResponse(Envelope):
    kind: Literal["report"] = "report"
    report: dict[str, Any]
    """The serialized `Report` object — reading order preserved, all prose resolved.
    `report.status_text` carries the full verdict sentence; a client renders it in full,
    never a shorthand (D-077 constraint 2)."""

    rendered_text: str
    """The canonical byte-comparable text rendering — the regression artefact's exact
    content, for clients that want the fixed layout."""


class ApplicationResponse(Envelope):
    kind: Literal["application", "refusal"]
    application: dict[str, Any] | None = None
    rendered_text: str | None = None
    refusal_reasons: list[dict[str, str]] | None = None
    """Every failed condition, reader-facing, when kind == 'refusal'."""


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=20000)
    """SYNTHETIC or redacted text only (DPDP discipline): real charge sheets are sensitive
    personal data and must never reach this system. The text is NOT persisted and NOT
    written to the audit log — only its length and hash are logged."""


class CandidateOut(BaseModel):
    regime: Literal["IPC_1860", "BNS_2023", "NDPS_1985"] | None
    section: str
    variant: str | None
    matched_text: str
    source_snippet: str
    unresolved: bool
    """True when the extractor could not resolve the enactment. DISPLAYED, never omitted:
    an omitted candidate is indistinguishable from no candidate — the fourth instance of
    that failure shape in this project (the max(1,·) floor, the counterpart ternary, the
    TOC discard). The human resolves it at confirmation or discards it knowingly."""


class ExtractResponse(BaseModel):
    kind: Literal["extraction"] = "extraction"
    candidates: list[CandidateOut]
    extractor_name: str
    model_involved: bool
    data_note: str
    """The standing extraction note: what the extractor is, what the candidates are not,
    and the confirmation requirement."""


class MetaResponse(BaseModel):
    statute_version: str
    report_language_version: str
    application_language_version: str
    sources_line: str
    verified_row_count: int
    data_warning: str
    verdict_values: list[str]
    """Both verdict strings, in full — the only two the system can produce (D-010)."""
