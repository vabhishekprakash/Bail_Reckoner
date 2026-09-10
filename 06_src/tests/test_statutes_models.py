"""Tests for the statutory-penalty value objects.

SYNTHETIC TEST DATA. Every offence row below is constructed for testing. Where a row carries a
real section number and a real punishment clause, it is quoted from the bare acts stored in
01_law/ and is used to test the *code*, not to seed the database — the database is populated by
the verified curation path, never from a test file. No real accused person's data appears here.
"""

from __future__ import annotations

from datetime import date
from fractions import Fraction

import pytest

from bail_reckoner.statutes.models import (
    MaximumPunishment,
    OffenceRow,
    Provenance,
    ProvenanceError,
    PunishmentKind,
    Regime,
    RowStatus,
    is_wellformed_section,
)


def _provenance(**overrides: object) -> Provenance:
    """A complete, valid provenance record. Overrides let each test break exactly one field."""
    base: dict[str, object] = {
        "source": "BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf",
        "verified_against": "gazette p. 1, s.1 (synthetic fixture)",
        "verified_on": date(2026, 8, 12),
        "verified_by": "test-fixture",
        "quoted_text": "synthetic punishment clause for testing",
    }
    base.update(overrides)
    return Provenance(**base)  # type: ignore[arg-type]


class TestProvenanceIsMandatory:
    """CLAUDE.md §6: a row without provenance does not enter the database."""

    @pytest.mark.parametrize(
        "blank_field", ["source", "verified_against", "verified_by", "quoted_text"]
    )
    def test_empty_provenance_field_is_rejected(self, blank_field: str) -> None:
        with pytest.raises(ProvenanceError, match=blank_field):
            _provenance(**{blank_field: ""})

    @pytest.mark.parametrize(
        "blank_field", ["source", "verified_against", "verified_by", "quoted_text"]
    )
    def test_whitespace_only_provenance_field_is_rejected(self, blank_field: str) -> None:
        """Whitespace is not provenance. A space would otherwise satisfy a naive emptiness check."""
        with pytest.raises(ProvenanceError):
            _provenance(**{blank_field: "   "})

    def test_complete_provenance_is_accepted(self) -> None:
        assert _provenance().source.endswith(".pdf")


class TestGate1DeathOrLifeExclusion:
    """s.479(1) main clause: the sub-section does not apply where death or life imprisonment
    "has been specified as one of the punishments"."""

    def test_death_or_life_excludes_even_when_a_term_is_also_prescribed(self) -> None:
        """IPC s.302 shape: "death, or imprisonment for life, and shall also be liable to fine".

        The statute says *one of the punishments*, so the presence of an alternative term must
        not rescue the offence into s.479(1). This is the case a naive "is the maximum a number?"
        check gets wrong.
        """
        maximum = MaximumPunishment(
            kinds=frozenset({PunishmentKind.DEATH, PunishmentKind.LIFE}), fine_also=True
        )
        assert maximum.excludes_s479 is True

    def test_life_alone_excludes(self) -> None:
        assert MaximumPunishment(kinds=frozenset({PunishmentKind.LIFE})).excludes_s479 is True

    def test_definite_term_does_not_exclude(self) -> None:
        maximum = MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=36)
        assert maximum.excludes_s479 is False

    def test_term_exceeding_seven_years_still_does_not_exclude(self) -> None:
        """A >7-year offence is *Antil* Category B but remains fully s.479(1)-eligible unless
        death or life is prescribed. Interrogation finding F-08: the deck left this unstated."""
        maximum = MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=120)
        assert maximum.excludes_s479 is False
        assert maximum.is_computable is True


class TestMaximumPunishmentInvariants:
    def test_term_without_months_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="term_months is required"):
            MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}))

    def test_months_without_term_kind_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be None"):
            MaximumPunishment(kinds=frozenset({PunishmentKind.LIFE}), term_months=36)

    def test_empty_kinds_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            MaximumPunishment(kinds=frozenset())

    def test_by_reference_requires_the_provision_quoted(self) -> None:
        """IPC s.511 shape: the maximum is defined by reference to another offence. Storing that
        without the provision's own words would leave an unresolvable row with no audit trail."""
        with pytest.raises(ValueError, match="reference_note"):
            MaximumPunishment(kinds=frozenset({PunishmentKind.BY_REFERENCE}))

    def test_fine_only_is_not_computable(self) -> None:
        maximum = MaximumPunishment(kinds=frozenset({PunishmentKind.FINE_ONLY}))
        assert maximum.is_computable is False
        assert maximum.excludes_s479 is False

    def test_threshold_on_a_non_term_maximum_raises_rather_than_guessing(self) -> None:
        maximum = MaximumPunishment(kinds=frozenset({PunishmentKind.LIFE}))
        with pytest.raises(ValueError, match="not computable"):
            maximum.threshold_months(Fraction(1, 2))


class TestThresholdArithmeticIsExact:
    """s.479(1) one-half; first proviso one-third. Rounding a threshold rounds a release date."""

    def test_one_half_of_three_years(self) -> None:
        maximum = MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=36)
        assert maximum.threshold_months(Fraction(1, 2)) == Fraction(18)

    def test_one_third_of_three_years(self) -> None:
        maximum = MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=36)
        assert maximum.threshold_months(Fraction(1, 3)) == Fraction(12)

    def test_one_third_of_a_term_not_divisible_by_three_stays_exact(self) -> None:
        """10 years / 3 is 40 months exactly; 5 years / 3 is not a whole number of months.

        The fraction is preserved rather than truncated: truncating 20 months toward 20 would
        move a qualifying date by days in the direction that keeps someone in custody longer.
        """
        maximum = MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=60)
        assert maximum.threshold_months(Fraction(1, 3)) == Fraction(20)

        seven_years = MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=84)
        assert seven_years.threshold_months(Fraction(1, 3)) == Fraction(28)

        odd = MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=10)
        assert odd.threshold_months(Fraction(1, 3)) == Fraction(10, 3)
        assert odd.threshold_months(Fraction(1, 2)) == Fraction(5)


class TestDraftRowsAreInvisibleToTheEngine:
    """D-046: a model may draft a row; only a human moves it to VERIFIED.

    A DRAFT row reaching Layer C would mean a generated maximum sentence silently determining a
    release date — the exact failure the draft/verified split exists to prevent.
    """

    def _row(self, status: RowStatus) -> OffenceRow:
        return OffenceRow(
            offence_id="BNS_2023-303(2)",
            label="Theft (synthetic fixture)",
            regime=Regime.BNS_2023,
            section="303(2)",
            maximum=MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=36),
            provenance=_provenance(),
            status=status,
        )

    def test_draft_row_is_not_engine_visible(self) -> None:
        assert self._row(RowStatus.DRAFT).is_engine_visible is False

    def test_verified_row_is_engine_visible(self) -> None:
        assert self._row(RowStatus.VERIFIED).is_engine_visible is True

    def test_draft_is_the_default_status(self) -> None:
        """Verified-by-default would make forgetting to review a row indistinguishable from
        having reviewed it."""
        row = OffenceRow(
            offence_id="BNS_2023-303(2)",
            label="Theft (synthetic fixture)",
            regime=Regime.BNS_2023,
            section="303(2)",
            maximum=MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=36),
            provenance=_provenance(),
        )
        assert row.status is RowStatus.DRAFT
        assert row.is_engine_visible is False


class TestOffenceRowInvariants:
    def _valid_kwargs(self) -> dict[str, object]:
        return {
            "offence_id": "IPC_1860-379",
            "label": "Theft (synthetic fixture)",
            "regime": Regime.IPC_1860,
            "section": "379",
            "maximum": MaximumPunishment(
                kinds=frozenset({PunishmentKind.TERM}), term_months=36, fine_also=True
            ),
            "provenance": _provenance(),
        }

    def test_offence_id_must_match_its_regime(self) -> None:
        """Catches the copy-paste error of duplicating an IPC row for BNS without renaming it,
        which would silently attach one regime's maximum to the other's identifier."""
        kwargs = self._valid_kwargs() | {"regime": Regime.BNS_2023}
        with pytest.raises(ValueError, match="must start with"):
            OffenceRow(**kwargs)  # type: ignore[arg-type]

    def test_special_statute_provision_requires_the_statute(self) -> None:
        kwargs = self._valid_kwargs() | {"special_statute_provision": "s.37"}
        with pytest.raises(ValueError, match="requires special_statute"):
            OffenceRow(**kwargs)  # type: ignore[arg-type]

    def test_pocso_style_row_may_carry_a_null_provision(self) -> None:
        """D-042/OLQ-4: POCSO is in *Antil* Category C but no barring provision has been read.
        The row must be expressible with the provision absent rather than invented."""
        row = OffenceRow(
            **(self._valid_kwargs() | {"special_statute": "POCSO"})  # type: ignore[arg-type]
        )
        assert row.special_statute == "POCSO"
        assert row.special_statute_provision is None

    def test_compoundable_defaults_to_unknown_not_false(self) -> None:
        """False would assert non-compoundability the project has not verified."""
        assert OffenceRow(**self._valid_kwargs()).compoundable is None  # type: ignore[arg-type]

    def test_counterpart_may_be_absent_for_bns_only_offences(self) -> None:
        """BNS created offences with no IPC equivalent; None is a fact, not a gap."""
        assert OffenceRow(**self._valid_kwargs()).counterpart_id is None  # type: ignore[arg-type]

    def test_rows_are_immutable_once_constructed(self) -> None:
        row = OffenceRow(**self._valid_kwargs())  # type: ignore[arg-type]
        with pytest.raises((AttributeError, TypeError)):
            row.status = RowStatus.VERIFIED  # type: ignore[misc]


@pytest.mark.parametrize("section", ["302", "304A", "303(2)", "376(1)", "43D(5)"])
def test_wellformed_sections_are_accepted(section: str) -> None:
    assert is_wellformed_section(section) is True


@pytest.mark.parametrize("section", ["", "s.302", "302.", "three-oh-two", "302 IPC"])
def test_malformed_sections_are_rejected(section: str) -> None:
    assert is_wellformed_section(section) is False
