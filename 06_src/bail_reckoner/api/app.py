"""The FastAPI application — the REST contract over Report and Application (D-076).

Endpoints:

* ``GET  /v1/meta``              — versions, sources line, verified-row count, the warning.
* ``POST /v1/reports``           — compute and return the serialized Report + canonical text.
* ``POST /v1/applications``      — the s.479(3) filing, or a refusal naming every failed
  condition (HTTP 200 either way: a refusal is a computed outcome, not an error).
* ``POST /v1/applications/pdf``  — the filing as deterministic PDF bytes; a refusal returns
  exactly what ``POST /v1/applications`` returns (HTTP 200, ``kind: "refusal"``): a refusal
  is a computed outcome on both endpoints, and a client distinguishes the cases by
  content type, never by guessing at status codes.

No model and no chat sits on any path here (D-077 constraint 7): requests are typed facts,
responses are computed documents, and the only intelligence involved is the statute.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, JSONResponse

from bail_reckoner.api.resolver import Resolver
from bail_reckoner.api.schemas import (
    ApplicationResponse,
    CandidateOut,
    ComputeRequest,
    ExtractRequest,
    ExtractResponse,
    MetaResponse,
    ReportResponse,
)
from bail_reckoner.api.serialize import to_jsonable
from bail_reckoner.audit import AuditLog
from bail_reckoner.engine.gates import evaluate
from bail_reckoner.engine.types import Verdict
from bail_reckoner.reporting.application import (
    Application,
    ApplicationLanguage,
    build_application,
    load_application_language,
)
from bail_reckoner.reporting.language import ReportLanguage, load_report_language
from bail_reckoner.reporting.render_application_pdf import render_application_pdf
from bail_reckoner.reporting.render_application_text import render_application_text
from bail_reckoner.reporting.render_text import render_text
from bail_reckoner.reporting.report import build_report
from bail_reckoner.statutes.decision_table import DecisionTable, load_decision_table
from bail_reckoner.statutes.sources import source_inventory_line

__all__ = ["create_app", "DEFAULT_AUDIT_PATH", "DEFAULT_REPOSITORY_PATH"]

# Runtime artefacts stay on H:\ (C1); both are derived/append-only and gitignored.
DEFAULT_REPOSITORY_PATH = Path(__file__).resolve().parents[3] / ".cache" / "api_penalty.sqlite3"
DEFAULT_AUDIT_PATH = Path(__file__).resolve().parents[3] / "07_runtime" / "audit_log.jsonl"


def _warning(mode: str, verified_rows: int) -> str:
    """The unmissable honesty line (D-076). Present until real verified rows exist."""
    if mode == "synthetic":
        return (
            "SYNTHETIC FIXTURES IN USE: every figure in this output is computed from "
            "labelled synthetic test fixtures, not from any statute. Nothing here describes "
            "a real offence or a real entitlement."
        )
    if verified_rows == 0:
        return (
            "ZERO VERIFIED PENALTY ROWS EXIST: the verified database is empty, so no "
            "offence can be resolved and every computation abstains "
            "(OFFENCE_NOT_IN_DATABASE). This system is not yet operational; outputs "
            "demonstrate the abstention behaviour only."
        )
    return (
        f"Resolved against the verified penalty database ({verified_rows} verified rows). "
        f"Offences outside it abstain rather than guess."
    )


def create_app(
    repository_path: Path | None = None,
    audit_path: Path | None = None,
) -> FastAPI:
    """Build the application with its long-lived, load-once collaborators."""
    table: DecisionTable = load_decision_table()
    report_language: ReportLanguage = load_report_language()
    application_language: ApplicationLanguage = load_application_language()
    sources_line = source_inventory_line()
    resolver = Resolver.open(repository_path or DEFAULT_REPOSITORY_PATH, table)
    audit = AuditLog(audit_path or DEFAULT_AUDIT_PATH)

    app = FastAPI(
        title="Bail Reckoner API",
        description=(
            "Computes statutory entitlement to release under Section 479 BNSS 2023, shows "
            "the arithmetic, and cites the provision behind every step. A decision-support "
            "aid — never an autonomous decision-maker."
        ),
        version="0.1.0",
    )

    @app.exception_handler(ValueError)
    def engine_refusal(request: object, exc: ValueError) -> JSONResponse:
        """D-092: an engine refusal is a deliberate output, not a crash, and the API must
        not strip its reason. Engine `ValueError`s (e.g. the custody-contradiction
        refusal, `as_on` preceding `custody_start`) carry the refusal text; a reason-less
        500 misrepresented them as server failures. Cost accepted and recorded in D-092:
        any bare ValueError escaping an endpoint is now dressed as a refusal — the
        verbatim message keeps nonsense visible as nonsense."""
        return JSONResponse(
            status_code=422,
            content={
                "engine_refusal": str(exc),
                "note": (
                    "This is a refusal, not a crash: the engine declined to compute "
                    "because the inputs contradict each other or fall outside the "
                    "provision's terms. Correct the inputs and resubmit."
                ),
            },
        )

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def demonstrator() -> HTMLResponse:
        """The server-rendered interface (D-077 constraints; stack RULED server-first,
        D-084). Plain HTML + fetch over the API contract; a React client remains addable
        later over the same unchanged API. Interface chrome is localisable under
        D-087/D-090 — documents stay English."""
        page = Path(__file__).resolve().parent / "static" / "index.html"
        return HTMLResponse(page.read_text(encoding="utf-8"))

    @app.get("/v1/meta", response_model=MetaResponse)
    def meta() -> MetaResponse:
        rows = resolver.verified_row_count()
        return MetaResponse(
            statute_version=f"{table.statute.short_name}@{table.statute.law_as_on.isoformat()}"
            f"+dt-{table.table_version}+{table.content_hash[:8]}",
            report_language_version=report_language.language_version,
            application_language_version=application_language.language_version,
            sources_line=sources_line,
            verified_row_count=rows,
            data_warning=_warning("verified", rows),
            verdict_values=[v.value for v in Verdict],
        )

    @app.post("/v1/reports", response_model=ReportResponse)
    def compute_report(request: ComputeRequest) -> ReportResponse:
        case = resolver.case_input(request)
        decision = evaluate(case, table)
        report = build_report(case, decision, table, report_language, sources_line)
        rows = resolver.verified_row_count()
        audit.append(
            {
                "endpoint": "reports",
                "mode": request.mode,
                "inputs_hash": decision.inputs_hash,
                "statute_version": decision.statute_version,
                "verdict": decision.verdict.name,
            }
        )
        return ReportResponse(
            mode=request.mode,
            verified_row_count=rows,
            data_warning=_warning(request.mode, rows),
            statute_version=decision.statute_version,
            report=to_jsonable(report),
            rendered_text=render_text(report),
        )

    def _application(
        request: ComputeRequest,
    ) -> tuple[ApplicationResponse, Application | None]:
        case = resolver.case_input(request)
        decision = evaluate(case, table)
        result = build_application(case, decision, table, application_language, sources_line)
        rows = resolver.verified_row_count()
        audit.append(
            {
                "endpoint": "applications",
                "mode": request.mode,
                "inputs_hash": decision.inputs_hash,
                "statute_version": decision.statute_version,
                "verdict": decision.verdict.name,
                "outcome": "application" if isinstance(result, Application) else "refusal",
            }
        )
        common = {
            "mode": request.mode,
            "verified_row_count": rows,
            "data_warning": _warning(request.mode, rows),
            "statute_version": decision.statute_version,
        }
        if isinstance(result, Application):
            return (
                ApplicationResponse(
                    kind="application",
                    application=to_jsonable(result),
                    rendered_text=render_application_text(result),
                    **common,  # type: ignore[arg-type]
                ),
                result,
            )
        return (
            ApplicationResponse(
                kind="refusal",
                refusal_reasons=[
                    {"condition": r.condition, "text": r.text} for r in result.reasons
                ],
                **common,  # type: ignore[arg-type]
            ),
            None,
        )

    @app.post("/v1/extract", response_model=ExtractResponse)
    def extract(request: ExtractRequest) -> ExtractResponse:
        """Layer B's seam over HTTP. Candidates only — nothing here computes: the road to
        a computation runs through the human confirmation step in the UI and then the
        ordinary /v1/reports request, where maxima resolve server-side (D-060)."""
        import hashlib as _hashlib

        from bail_reckoner.extraction.baseline import BaselineExtractor

        result = BaselineExtractor().extract(request.text)
        # DPDP: the text itself is never logged — length and hash only.
        audit.append(
            {
                "endpoint": "extract",
                "text_sha256": _hashlib.sha256(request.text.encode("utf-8")).hexdigest(),
                "text_length": len(request.text),
                "candidates": len(result.candidates),
            }
        )
        return ExtractResponse(
            candidates=[
                CandidateOut(
                    regime=c.regime,
                    section=c.section,
                    variant=c.variant,
                    matched_text=c.matched_text,
                    source_snippet=c.source_snippet,
                    unresolved=c.regime is None,
                )
                for c in result.candidates
            ],
            extractor_name=result.extractor_name,
            model_involved=result.model_involved,
            data_note=(
                "Candidates from a deterministic extractor over synthetic or redacted "
                "text — not legal findings and not engine inputs. Every candidate, "
                "including unresolved ones, must be confirmed by a named person against "
                "the shown source text before it enters any computation; unresolved "
                "candidates are displayed, never omitted."
            ),
        )

    @app.post("/v1/applications", response_model=ApplicationResponse)
    def compute_application(request: ComputeRequest) -> ApplicationResponse:
        response, _ = _application(request)
        return response

    @app.post("/v1/applications/pdf")
    def compute_application_pdf(request: ComputeRequest) -> Response:
        response, application = _application(request)
        if application is None:
            # A refusal is a computed outcome on both endpoints (Abhishek, 2026-08-19):
            # same status, same body shape as /v1/applications. The content type is what
            # distinguishes a document from a refusal.
            return JSONResponse(status_code=200, content=response.model_dump())
        return Response(
            content=render_application_pdf(application),
            media_type="application/pdf",
            headers={"X-Data-Warning": "see /v1/meta"},
        )

    return app
