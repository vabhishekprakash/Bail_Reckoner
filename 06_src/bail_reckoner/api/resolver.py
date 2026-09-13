"""Server-side offence resolution — where D-060 is enforced at the API boundary.

A request names offences by (regime, section, variant); this module turns each into a
`ChargedOffence` with its maximum resolved from the verified penalty repository, or from the
labelled synthetic fixtures when the request asks for demonstration mode. No maximum ever
arrives from the caller, so a user-supplied number can never produce ENTITLEMENT_ESTABLISHED
(D-060). An unresolved offence gets `maximum=None` and the engine abstains
(OFFENCE_NOT_IN_DATABASE) — a reported gap, never a guess (D-064).

Special-statute membership comes from the decision table's *Antil* Category C set (D-054):
an offence whose regime maps to a Category-C statute carries the statute's short name and
provision; whether the charge is within the bar's own scope words stays the caller's
tri-state affirmation (D-074), defaulting to the contested routing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bail_reckoner.api.schemas import CaseIn, ComputeRequest, CustodyBreakIn, OffenceIn
from bail_reckoner.engine.types import (
    CaseInput,
    ChargedOffence,
    CustodyBreak,
    PendingCase,
    PriorConvictionStatus,
    Scope479_2,
)
from bail_reckoner.goldenset.harness import FixtureProvider, load_fixture_provider
from bail_reckoner.statutes.decision_table import DecisionTable
from bail_reckoner.statutes.models import Regime
from bail_reckoner.statutes.repository import PenaltyRepository

__all__ = ["Resolver", "DEFAULT_FIXTURE_PATH"]

DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "03_goldenset" / "fixtures" / "smoke_fixture_rows.yaml"
)

# Which regimes map to which Category-C statute short name. Only regimes the engine models
# appear; a statute with no regime in the input vocabulary cannot arrive through the API yet.
_REGIME_TO_CATEGORY_C = {"NDPS_1985": "NDPS"}


@dataclass(frozen=True, slots=True)
class Resolver:
    """Resolution against verified rows (default) or the synthetic fixture file.

    The repository is opened per operation, not held: SQLite connections are bound to their
    creating thread and an ASGI server dispatches requests across threads. Opening a
    file-backed SQLite database is cheap, the usage here is read-only, and the first open
    creates the (empty, derived) database file."""

    repository_path: Path
    table: DecisionTable
    fixtures: FixtureProvider

    @staticmethod
    def open(repository_path: Path, table: DecisionTable) -> Resolver:
        # Create the schema eagerly so the first request is not the first schema check.
        PenaltyRepository(repository_path).close()
        return Resolver(
            repository_path=repository_path,
            table=table,
            fixtures=load_fixture_provider(DEFAULT_FIXTURE_PATH),
        )

    def verified_row_count(self) -> int:
        with PenaltyRepository(self.repository_path) as repo:
            return sum(1 for _ in repo.all_rows(verified_only=True))

    def _charged(self, offence: OffenceIn, synthetic: bool) -> ChargedOffence:
        regime = Regime(offence.regime)
        maximum = None
        punishment_text: str | None = None
        punishment_citation: str | None = None
        if synthetic:
            maximum = self.fixtures.resolve(regime, offence.section, offence.variant)
            if maximum is not None:
                punishment_text = (
                    "SYNTHETIC FIXTURE — not a statute. No provision text exists for a "
                    "synthetic offence."
                )
                punishment_citation = f"synthetic fixture {self.fixtures.version_id}"
        else:
            with PenaltyRepository(self.repository_path) as repo:
                row = repo.resolve(regime, offence.section, variant=offence.variant)
            if row is not None:
                maximum = row.maximum
                punishment_text = row.provenance.quoted_text
                punishment_citation = row.provenance.verified_against

        short = _REGIME_TO_CATEGORY_C.get(offence.regime)
        statute = None
        provision = None
        in_set = False
        if short is not None:
            entry = next(s for s in self.table.special_statutes if s.short == short)
            statute = entry.short
            provision = entry.provision
            in_set = True

        suffix = f"#{offence.variant}" if offence.variant else ""
        return ChargedOffence(
            offence_id=f"{offence.regime}-{offence.section}{suffix}",
            label=offence.label,
            section=offence.section,
            maximum=maximum,
            special_statute=statute,
            special_statute_provision=provision,
            special_statute_in_gate3_set=in_set,
            special_statute_bar_in_scope=offence.bar_in_scope,
            punishment_text=punishment_text,
            punishment_citation=punishment_citation,
        )

    def _case(self, case: CaseIn, synthetic: bool) -> PendingCase:
        return PendingCase(
            case_ref=case.case_ref,
            offences=tuple(self._charged(o, synthetic) for o in case.offences),
            is_pending=case.is_pending,
        )

    @staticmethod
    def _break(item: CustodyBreakIn) -> CustodyBreak:
        return CustodyBreak(start=item.start, end=item.end)

    def case_input(self, request: ComputeRequest) -> CaseInput:
        synthetic = request.mode == "synthetic"
        return CaseInput(
            date_of_arrest=request.date_of_arrest,
            evaluated_on=request.evaluated_on,
            cases=tuple(self._case(c, synthetic) for c in request.cases),
            prior_conviction_status=PriorConvictionStatus(request.prior_conviction_status),
            date_of_first_remand=request.date_of_first_remand,
            custody_breaks=tuple(self._break(b) for b in request.custody_breaks),
            excluded_days=request.excluded_days,
            scope_479_2=Scope479_2(request.scope_479_2),
            case_list_verified=request.case_list_verified,
            prior_conviction_verified=request.prior_conviction_verified,
        )
