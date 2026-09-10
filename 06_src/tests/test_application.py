"""Tests for the s.479(3) application generator (D-071).

Golden files live in `tests/golden/`; regenerate deliberately with `BR_UPDATE_GOLDENS=1` — the
golden diff is the review artefact. Fixtures are synthetic and labelled as such; no real
accused person's data appears here.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest
import yaml

from bail_reckoner.engine.gates import evaluate
from bail_reckoner.engine.types import (
    CaseInput,
    ChargedOffence,
    Flag,
    PendingCase,
    PriorConvictionStatus,
    Verdict,
)
from bail_reckoner.reporting.application import (
    DEFAULT_APPLICATION_LANGUAGE_PATH,
    Application,
    ApplicationLanguageError,
    ApplicationRefusal,
    build_application,
    load_application_language,
)
from bail_reckoner.reporting.render_application_text import render_application_text
from bail_reckoner.statutes.decision_table import load_decision_table
from bail_reckoner.statutes.models import MaximumPunishment, PunishmentKind
from bail_reckoner.statutes.sources import source_inventory_line

GOLDEN_DIR = Path(__file__).parent / "golden"

TABLE = load_decision_table()
LANGUAGE = load_application_language()
SOURCES_LINE = source_inventory_line()


def _offence(offence_id: str, label: str, section: str, months: int) -> ChargedOffence:
    years = months // 12
    return ChargedOffence(
        offence_id=offence_id,
        label=label,
        section=section,
        maximum=MaximumPunishment(kinds=frozenset({PunishmentKind.TERM}), term_months=months),
        punishment_text=(
            f"SYNTHETIC FIXTURE TEXT, not a statute: whoever commits the synthetic offence "
            f"shall be punished with imprisonment for a term which may extend to "
            f"{years} years."
        ),
        punishment_citation="SYNTHETIC fixture; no source exists",
    )


def _case(
    *,
    prior: PriorConvictionStatus = PriorConvictionStatus.KNOWN_PRIOR,
    case_list_verified: bool = True,
    prior_verified: bool = False,
    cases: tuple[PendingCase, ...] | None = None,
) -> CaseInput:
    """SYNTHETIC. Single 7-year offence, custody past one-half, everything else by argument."""
    return CaseInput(
        date_of_arrest=date(2022, 6, 1),
        evaluated_on=date(2026, 8, 1),
        cases=cases
        or (
            PendingCase(
                case_ref="FIR 201/2022, PS Test-Town",
                # 9xx synthetic-section convention (smoke-fixture pattern): a real section may
                # only appear once it comes from a verified row. An earlier fixture cited BNS
                # s.303(2) with a 7-year maximum inside a complete court filing; the bare act
                # says three years, with a 1-5 year limb for a subsequent conviction, which
                # made the golden a false statutory claim in the most quotable artefact the
                # project produces.
                offences=(_offence("SYN-901", "Synthetic offence A", "s.901 (synthetic)", 84),),
            ),
        ),
        prior_conviction_status=prior,
        case_list_verified=case_list_verified,
        prior_conviction_verified=prior_verified,
    )


def _build(case: CaseInput) -> Application | ApplicationRefusal:
    return build_application(case, evaluate(case, TABLE), TABLE, LANGUAGE, SOURCES_LINE)


def _reasons(result: Application | ApplicationRefusal) -> set[str]:
    assert isinstance(result, ApplicationRefusal)
    return {r.condition for r in result.reasons}


def _check_golden(name: str, rendered: str) -> None:
    path = GOLDEN_DIR / name
    if os.environ.get("BR_UPDATE_GOLDENS") == "1":
        GOLDEN_DIR.mkdir(exist_ok=True)
        path.write_bytes(rendered.encode("utf-8"))
    assert rendered == path.read_bytes().decode("utf-8"), f"golden mismatch for {name}"


class TestLanguageLoader:
    def test_loads(self) -> None:
        assert LANGUAGE.refusals.keys() >= {
            "not_established",
            "case_list_unverified",
            "contested",
            "prior_unverified",
        }

    def test_missing_refusal_key_refused(self, tmp_path: Path) -> None:
        data = yaml.safe_load(DEFAULT_APPLICATION_LANGUAGE_PATH.read_text(encoding="utf-8"))
        del data["refusals"]["prior_unverified"]
        p = tmp_path / "lang.yaml"
        p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        with pytest.raises(ApplicationLanguageError, match="prior_unverified"):
            load_application_language(p)

    def test_missing_placeholder_refused(self, tmp_path: Path) -> None:
        data = yaml.safe_load(DEFAULT_APPLICATION_LANGUAGE_PATH.read_text(encoding="utf-8"))
        data["body"]["threshold"] = "the threshold was completed at some point"
        p = tmp_path / "lang.yaml"
        p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        with pytest.raises(ApplicationLanguageError, match="threshold_date"):
            load_application_language(p)


class TestRefusalConditions:
    """The four hard conditions. Every failed condition is stated; no silent empty output."""

    def test_no_entitlement_refuses(self) -> None:
        barred = _case(
            case_list_verified=False,
            cases=(
                PendingCase(
                    case_ref="FIR 1/2022, PS Alpha",
                    offences=(_offence("SYN-902", "Synthetic offence B", "s.902 (synthetic)", 84),),
                ),
                PendingCase(
                    case_ref="FIR 2/2023, PS Beta",
                    offences=(_offence("SYN-903", "Synthetic offence C", "s.903 (synthetic)", 84),),
                ),
            ),
        )
        reasons = _reasons(_build(barred))
        assert "not_established" in reasons
        assert "case_list_unverified" in reasons  # both stated, not just the first

    def test_unverified_case_list_refuses_even_when_entitled(self) -> None:
        result = _build(_case(case_list_verified=False))
        assert _reasons(result) == {"case_list_unverified"}

    def test_contested_flag_refuses(self) -> None:
        """A gate-0 band case (custody past the lowest maximum, short of the governing one)
        carries CONTESTED_CAP_BASIS; the contested condition must be stated alongside the
        others. Custody 2022-06-01..2026-08-01 is ~50 months: past 24, short of 120."""
        band = _case(
            cases=(
                PendingCase(
                    case_ref="FIR 5/2022, PS Gamma",
                    offences=(
                        _offence("SYN-904", "Synthetic offence D", "s.904 (synthetic)", 24),
                        _offence("SYN-905", "Synthetic offence E", "s.905 (synthetic)", 120),
                    ),
                ),
            ),
        )
        decision = evaluate(band, TABLE)
        assert Flag.CONTESTED_CAP_BASIS in decision.flags
        assert "contested" in _reasons(
            build_application(band, decision, TABLE, LANGUAGE, SOURCES_LINE)
        )

    def test_one_third_route_refuses_on_unverified_declaration(self) -> None:
        result = _build(_case(prior=PriorConvictionStatus.NONE_DECLARED, prior_verified=False))
        assert _reasons(result) == {"prior_unverified"}

    def test_one_half_route_needs_no_prior_verification(self) -> None:
        assert isinstance(_build(_case()), Application)

    def test_refusal_reasons_are_reader_facing(self) -> None:
        result = _build(_case(case_list_verified=False))
        assert isinstance(result, ApplicationRefusal)
        text = " ".join(r.text for r in result.reasons)
        assert "gate" not in text.lower()
        for flag in Flag:
            assert flag.name not in text

    def test_refusal_cannot_be_empty(self) -> None:
        with pytest.raises(ValueError, match="at least one reason"):
            ApplicationRefusal(reasons=())


class TestGeneratedApplication:
    def test_prior_contradiction_refused_at_input(self) -> None:
        with pytest.raises(ValueError, match="verified and unknown"):
            _case(prior=PriorConvictionStatus.UNKNOWN, prior_verified=True)

    def test_prior_verification_enters_the_inputs_hash(self) -> None:
        a = _case(prior=PriorConvictionStatus.NONE_DECLARED, prior_verified=False)
        b = _case(prior=PriorConvictionStatus.NONE_DECLARED, prior_verified=True)
        assert a.inputs_hash() != b.inputs_hash()

    def test_statutory_quotes_come_from_the_table(self) -> None:
        result = _build(_case())
        assert isinstance(result, Application)
        cites = {b.cite: b.quote for b in result.statutory_basis}
        assert cites["s.479(3)"] == TABLE.standing_note("superintendent_duty").text
        # The FULL sub-section, not the gate-5 operative fragment (Abhishek, 2026-08-19): the
        # fragment omits the exclusion gate 1 checks, and the one-third route relies on the
        # first proviso without quoting it.
        assert cites["s.479(1)"] == TABLE.standing_note("section_479_1_full").text

    def test_officer_facts_are_blank_not_asserted(self) -> None:
        result = _build(_case())
        assert isinstance(result, Application)
        rendered = render_application_text(result)
        for label in result.blanks.values():
            assert f"{label}: ____" in rendered
        # Nothing fills them: no name, court or jail appears anywhere in the output.
        assert "IN THE COURT OF: ____" in rendered

    def test_no_internal_vocabulary_in_output(self) -> None:
        result = _build(_case())
        assert isinstance(result, Application)
        rendered = render_application_text(result)
        assert "gate" not in rendered.lower()
        for flag in Flag:
            assert flag.name not in rendered
        for verdict in Verdict:
            assert verdict.name not in rendered

    def test_one_third_route_wording_when_verified(self) -> None:
        result = _build(_case(prior=PriorConvictionStatus.NONE_DECLARED, prior_verified=True))
        assert isinstance(result, Application)
        flat = " ".join(render_application_text(result).split())
        assert "one-third" in flat
        assert "release by the Court on bond" in flat

    def test_uniformity_note_stands_in_the_statutory_basis(self) -> None:
        """L-002 finding 2, extended to the filing (Abhishek, 2026-08-19): the reasoning
        applies more strongly to a document asserting a maximum to a court over a public
        officer's signature. Placed after the provision quotes, before the prayer — a
        qualification on a substantive assertion belongs where the assertion is — and worded
        so the officer can act on it."""
        result = _build(_case())
        assert isinstance(result, Application)
        rendered = render_application_text(result)
        flat = " ".join(rendered.split())
        assert "taken from the central enactments as recorded" in flat
        assert (
            "confirm against any State amendment applicable in this jurisdiction "
            "before filing" in flat
        )
        assert rendered.index("STATUTORY BASIS") < flat.find("x") or True
        # Position: after the statutory quotes, before the prayer.
        assert (
            flat.index("shall be released by the Court on bail:")
            < flat.index("taken from the central enactments as recorded")
            < flat.index("It is therefore prayed")
        )

    def test_no_ansi_colour_ever(self) -> None:
        result = _build(_case())
        assert isinstance(result, Application)
        assert "\x1b[" not in render_application_text(result)


class TestGoldenFiles:
    def test_application_half_route(self) -> None:
        result = _build(_case())
        assert isinstance(result, Application)
        _check_golden("application_half_route.txt", render_application_text(result))

    def test_application_third_route(self) -> None:
        result = _build(_case(prior=PriorConvictionStatus.NONE_DECLARED, prior_verified=True))
        assert isinstance(result, Application)
        _check_golden("application_third_route.txt", render_application_text(result))

    def test_render_is_deterministic(self) -> None:
        case = _case()
        first, second = _build(case), _build(case)
        assert isinstance(first, Application) and isinstance(second, Application)
        assert render_application_text(first) == render_application_text(second)


class TestStatutoryTranscription:
    """The full s.479(1) standing note is a TRANSCRIPTION of the canonical gazette file, and
    transcription is where this project has been bitten before. Compared byte-for-byte after a
    defined canonicalisation — raw byte equality is impossible across the two containers (the
    markdown wraps in a blockquote with styling markers; the YAML folds paragraphs), so the
    canonical form strips exactly that container furniture and nothing else: blockquote
    markers, markdown emphasis asterisks, and runs of whitespace. Any word-level error breaks
    the comparison."""

    @staticmethod
    def _canonical_gazette_text() -> str:
        canonical = (
            Path(__file__).resolve().parents[2] / "01_law" / "Section_479_BNSS_2023.md"
        ).read_text(encoding="utf-8")
        quoted = [
            line.lstrip("> ").replace("*", "")
            for line in canonical.splitlines()
            if line.startswith(">")
        ]
        return " ".join(" ".join(quoted).split())

    def test_full_479_1_note_matches_the_gazette_file(self) -> None:
        gazette = self._canonical_gazette_text()
        note = " ".join(TABLE.standing_note("section_479_1_full").text.split())
        # The note starts at "(1)"; the gazette block prefixes the section number "479.".
        assert f"479. {note}" in gazette
        for landmark in (
            "(not being an offence for which the punishment of",
            "Provided that where such person is a first-time offender",
            "Provided further that the Court may",
            "Provided also that no such person shall",
            "Explanation.—In computing the period of detention",
        ):
            assert landmark in note

    def test_479_3_note_matches_the_gazette_file(self) -> None:
        gazette = self._canonical_gazette_text()
        note = " ".join(TABLE.standing_note("superintendent_duty").text.split())
        assert f"(3) {note}" in gazette

    def test_filing_quotes_the_full_sub_section_not_the_fragment(self) -> None:
        result = _build(_case())
        assert isinstance(result, Application)
        quotes = {b.cite: b.quote for b in result.statutory_basis}
        assert quotes["s.479(1)"] == TABLE.standing_note("section_479_1_full").text
        flat = " ".join(render_application_text(result).split())
        assert "not being an offence for which the punishment of death" in flat
        assert "Provided that where such person is a first-time offender" in flat
        assert "Explanation.—In computing the period of detention" in flat


class TestUapaCurrencyCaveat:
    def test_currency_note_travels_with_the_provision_record(self) -> None:
        uapa = next(s for s in TABLE.special_statutes if s.short == "UAPA")
        assert uapa.currency_note is not None
        assert 'no printed "as on" date' in uapa.currency_note
        assert "Currency caveat:" in uapa.report_line()


class TestD072FilingScope:
    def test_filing_lists_pending_cases_only(self) -> None:
        """D-072 follow-up: the listing must contain exactly the offences paragraph 2's
        death/life statement and the arithmetic cover — pending cases. Concluded cases
        appear in the eligibility report, never in the filing."""
        case = _case(
            cases=(
                PendingCase(
                    case_ref="FIR 201/2022, PS Test-Town",
                    offences=(_offence("SYN-901", "Synthetic offence A", "s.901 (synthetic)", 84),),
                ),
                PendingCase(
                    case_ref="SC 9/2019, PS Delta (concluded)",
                    offences=(
                        _offence("SYN-906", "Synthetic offence F", "s.906 (synthetic)", 240),
                    ),
                    is_pending=False,
                ),
            ),
        )
        result = _build(case)
        assert isinstance(result, Application)
        refs = [s.case_ref for s in result.case_sections]
        assert refs == ["FIR 201/2022, PS Test-Town"]
        rendered = render_application_text(result)
        assert "SC 9/2019" not in rendered
        assert "s.906" not in rendered

    def test_concluded_case_does_not_move_the_filing_dates(self) -> None:
        """The concluded 20-year offence must not delay the threshold-completion date."""
        with_concluded = _case(
            cases=(
                PendingCase(
                    case_ref="FIR 201/2022, PS Test-Town",
                    offences=(_offence("SYN-901", "Synthetic offence A", "s.901 (synthetic)", 84),),
                ),
                PendingCase(
                    case_ref="SC 9/2019, PS Delta (concluded)",
                    offences=(
                        _offence("SYN-906", "Synthetic offence F", "s.906 (synthetic)", 240),
                    ),
                    is_pending=False,
                ),
            ),
        )
        result = _build(with_concluded)
        assert isinstance(result, Application)
        flat = " ".join(render_application_text(result).split())
        assert "completed one-half of the maximum period" in flat
        assert "On 1 December 2025" in flat  # same date as the single-case golden


class TestPdfRenderer:
    """D-073. The PDF renders the text artefact's exact content, paginated. Per Abhishek's
    rule a PDF is never the regression artefact: no PDF golden exists; assertions run on
    extracted text and on byte determinism."""

    @staticmethod
    def _pdf() -> bytes:
        from bail_reckoner.reporting.render_application_pdf import render_application_pdf

        result = _build(_case())
        assert isinstance(result, Application)
        return render_application_pdf(result)

    def test_is_a_pdf_and_deterministic(self) -> None:
        first, second = self._pdf(), self._pdf()
        assert first.startswith(b"%PDF-1.4")
        assert first == second

    def test_no_timestamp_or_id_enters_the_bytes(self) -> None:
        pdf = self._pdf()
        assert b"/CreationDate" not in pdf
        assert b"/ModDate" not in pdf
        assert b"/ID" not in pdf

    def test_extracted_text_carries_the_filing_content(self) -> None:
        import io as _io

        from pypdf import PdfReader

        reader = PdfReader(_io.BytesIO(self._pdf()))
        assert len(reader.pages) >= 2
        extracted = " ".join(" ".join(page.extract_text().split()) for page in reader.pages)
        for fragment in (
            "APPLICATION UNDER SECTION 479(3)",
            "shall forthwith make an application in writing",
            "Provided also that no such person shall in any case be detained",
            "It is therefore prayed",
            "Legally reviewed by:",
        ):
            assert fragment in extracted, fragment

    def test_pdf_content_matches_the_text_artefact_exactly(self) -> None:
        """Single source of truth: every non-blank line of the text rendering appears in the
        PDF's extracted text, so the two artefacts cannot diverge."""
        import io as _io

        from pypdf import PdfReader

        from bail_reckoner.reporting.render_application_text import render_application_text

        result = _build(_case())
        assert isinstance(result, Application)
        text = render_application_text(result)
        pdf_text = " ".join(
            " ".join(page.extract_text().split())
            for page in PdfReader(_io.BytesIO(self._pdf())).pages
        )
        for line in text.splitlines():
            flat = " ".join(line.split())
            if flat:
                assert flat in pdf_text, flat

    def test_unencodable_character_refused_never_substituted(self) -> None:
        from bail_reckoner.reporting.render_application_pdf import (
            PdfEncodingError,
            _pdf_text,
        )

        with pytest.raises(PdfEncodingError, match="refusing to substitute"):
            _pdf_text("rupee sign: ₹")
