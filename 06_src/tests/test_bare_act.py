"""Tests for bare-act section extraction.

SYNTHETIC AND REAL-STATUTE TEST DATA. The page fixtures below are hand-written imitations of the
layouts found in the two acts stored in 01_law/. Tests marked `needs_law_pdfs` read the real
PDFs and are skipped when those files are absent, so the suite runs on a checkout without them.
No real accused person's data appears here.
"""

from __future__ import annotations

import pytest

from bail_reckoner.statutes.bare_act import (
    LAW_DIR,
    BareAct,
    SectionText,
    _printed_page_number,
    successor_pattern,
)

BNS_FILE = "BNS_2023_Act45_Gazette_2023-12-25_MHA.pdf"
IPC_FILE = "IPC_1860_Act45_IndiaCode_repealed_file.pdf"

needs_law_pdfs = pytest.mark.skipif(
    not (LAW_DIR / BNS_FILE).exists() or not (LAW_DIR / IPC_FILE).exists(),
    reason="bare-act PDFs from 01_law/ are not present in this checkout",
)


class TestPrintedPageNumber:
    """Regression tests for a bug that produced confidently wrong citations.

    The first implementation took the first numeric token on the page. Gazette pages open with a
    section continuing across the break, so page index 33 (printed page 34) reported "102" — the
    section number. Every citation looked well-formed and pointed at the wrong page.
    """

    def test_gazette_left_page_reads_the_footer_not_the_continuing_section(self) -> None:
        page = (
            "102.If a person, by doing anything which he intends or knows to be likely to cause\n"
            "death, causes the death of any other person...\n"
            "34 THE GAZETTE OF INDIA EXTRAORDINARY [Part II—\n"
        )
        assert _printed_page_number(page) == "34"

    def test_gazette_right_page_reads_the_trailing_footer_number(self) -> None:
        page = (
            "(2) When any person offending under sub-section (1) is under sentence...\n"
            "Sec. 1] THE GAZETTE OF INDIA EXTRAORDINARY 35\n"
        )
        assert _printed_page_number(page) == "35"

    def test_india_code_style_standalone_first_line(self) -> None:
        page = "74 \n302. Punishment for murder .—Whoever commits murder shall be punished...\n"
        assert _printed_page_number(page) == "74"

    def test_a_leading_section_number_is_never_mistaken_for_a_page_number(self) -> None:
        """The exact shape of the original bug: no recognisable page marker anywhere."""
        page = "301.Whoever, with the intention of wounding the feelings of any person...\n"
        assert _printed_page_number(page) == ""

    def test_unrecognised_layout_returns_empty_rather_than_guessing(self) -> None:
        assert _printed_page_number("some text with 42 in it\nand more text\n") == ""
        assert _printed_page_number("") == ""


class TestCitation:
    def test_citation_names_the_printed_page_when_known(self) -> None:
        section = SectionText(
            section="303", text="...", page_index=77, printed_page="78", source_file="BNS.pdf"
        )
        assert "printed p. 78" in section.citation()
        assert "PDF page index 77" in section.citation()

    def test_citation_says_so_when_the_printed_page_is_unknown(self) -> None:
        """The PDF index is always exact, so an unknown printed page degrades the citation
        without invalidating it."""
        section = SectionText(
            section="303", text="...", page_index=77, printed_page="", source_file="BNS.pdf"
        )
        assert "printed page unknown" in section.citation()
        assert "PDF page index 77" in section.citation()


class TestMissingFile:
    def test_missing_bare_act_points_at_the_provenance_process(self) -> None:
        with pytest.raises(FileNotFoundError, match="SOURCES.md"):
            BareAct("no_such_act.pdf")


@needs_law_pdfs
class TestAgainstTheRealBareActs:
    """Reads the actual stored PDFs. These assert what the statute says, so a failure means
    either the extractor broke or the stored source changed — both worth stopping for."""

    def test_ipc_302_is_found_with_its_punishment_clause(self) -> None:
        section = BareAct.open(IPC_FILE).find_section("302", must_contain="murder")
        assert section is not None
        assert "Punishment for murder" in section.text
        assert "shall be punished with death" in section.text
        assert section.printed_page == "74"

    def test_ipc_379_theft_is_found(self) -> None:
        section = BareAct.open(IPC_FILE).find_section("379", must_contain="theft")
        assert section is not None
        assert "may extend to three years" in section.text
        assert section.printed_page == "95"

    def test_bns_103_murder_is_found_on_the_correct_printed_page(self) -> None:
        """Guards the page-number regression against the real document: PDF index 33 is printed
        page 34, not section number 102."""
        section = BareAct.open(BNS_FILE).find_section("103", must_contain="murder")
        assert section is not None
        assert "Whoever commits murder" in section.text
        assert section.page_index == 33
        assert section.printed_page == "34"

    def test_disambiguator_is_required_to_pin_a_section(self) -> None:
        """Section numbers recur in contents tables and cross-references; without a
        disambiguator the first match is often not the provision."""
        act = BareAct.open(IPC_FILE)
        assert act.find_section("302", must_contain="murder") is not None

    def test_unknown_section_returns_none_rather_than_a_wrong_match(self) -> None:
        assert BareAct.open(IPC_FILE).find_section("9999", must_contain="whoever") is None

    def test_amendment_inserted_sections_are_found(self) -> None:
        """IPC s.304A prints as `1[304A. ...`, the bracket being an amendment footnote marker.

        Regression test for a silent gap: requiring the section number at line start made EVERY
        amendment-inserted section invisible, and those are disproportionately the modern,
        frequently-charged offences (s.304A, s.354A, s.376AB).
        """
        section = BareAct.open(IPC_FILE).find_section("304A", must_contain="rash or negligent act")
        assert section is not None
        assert "Causing death by negligence" in section.text

    def test_a_section_spanning_a_page_break_is_captured_whole(self) -> None:
        """BNS s.303(1) defines theft and s.303(2) punishes it, across a page boundary.

        Regression test: stopping at the page end truncated exactly the punishment clause a
        penalty row needs, making a correct section number look wrong.
        """
        section = BareAct.open(BNS_FILE).find_section("303", must_contain="Whoever commits theft")
        assert section is not None
        assert "shall be punished" in section.text

    def test_ipc_363_is_not_cut_short_by_a_footnote(self) -> None:
        """THE load-bearing case. s.363 was truncated mid-definition by a footnote line
        (`1. The words ...`), and the `truncated` flag read False because a "heading" *was*
        found — so the flag structurally could not see this failure. A fix that repairs 304A and
        127 but not this one has not addressed the failure mode.
        """
        section = BareAct.open(IPC_FILE).find_section("363", must_contain="kidnaps any person")
        assert section is not None
        text = " ".join(section.text.split())
        assert not text.endswith("in order that such"), "still cut at the footnote"
        assert "shall be punished" in text, "punishment clause lost to the premature cut"

    def test_ipc_304a_does_not_swallow_the_following_section(self) -> None:
        """s.304A ran on to `305.`, absorbing s.304B. The boundary fix stops that.

        Its own punishment clause is two years, and that must survive intact.
        """
        section = BareAct.open(IPC_FILE).find_section("304A", must_contain="rash or negligent act")
        assert section is not None
        text = " ".join(section.text.split())
        assert "304B" not in text, "still captures the following section"
        assert "305." not in text, "still runs to the section after next"
        assert "may extend to two years" in text, "lost s.304A's own punishment clause"

    def test_state_amendment_apparatus_is_a_separate_hazard_from_over_capture(self) -> None:
        """A third failure category, found while fixing the first two, and NOT a boundary bug.

        India Code prints `STATE AMENDMENTS` inline after a section. For s.304A that block
        contains Himachal Pradesh's s.304-AA, which carries **imprisonment for life** — sitting
        directly beneath a section whose own maximum is two years.

        Correctly bounded extraction still yields text where a life clause is adjacent to a
        two-year offence. That is unfixable by boundary detection: the apparatus genuinely
        follows the section. It is precisely why the review sheet directs the reviewer to the
        PDF page rather than to this text (D-061).
        """
        section = BareAct.open(IPC_FILE).find_section("304A", must_contain="rash or negligent act")
        assert section is not None
        text = " ".join(section.text.split())
        assert "STATE AMENDMENTS" in text
        life_at = text.find("imprisonment for life")
        assert life_at > text.find("STATE AMENDMENTS"), (
            "a life clause appearing BEFORE the state-amendment block would be a real "
            "over-capture rather than apparatus"
        )

    def test_bns_127_keeps_its_own_sub_sections(self) -> None:
        """The opposite risk to 304A. s.127's sub-sections genuinely run across a page break, so
        a boundary fix must not truncate them: its several punishment limbs are real, not
        over-capture, and cutting them would lose maxima rather than invent them."""
        section = BareAct.open(BNS_FILE).find_section("127", must_contain="wrongfully confines")
        assert section is not None
        text = " ".join(section.text.split())
        assert "(3)" in text, "lost sub-section (3), which is on the following page"
        assert "128" not in text.split(".")[0], "ran into the next section's heading"


class TestSuccessorPattern:
    """Unit tests for the successor logic, independent of any PDF."""

    def test_a_footnote_number_is_not_a_successor(self) -> None:
        """The s.363 failure in miniature: footnotes, illustrations and numbered clauses all
        begin with a bare number, and none of them ends a section."""
        pattern = successor_pattern("363")
        assert pattern.search("\n1. The words were omitted by Act 2 of 1900.\n") is None
        assert pattern.search("\n2. Illustration\n") is None

    def test_the_immediate_next_section_matches(self) -> None:
        assert successor_pattern("363").search("\n364. Kidnapping in order to murder.\n")

    def test_a_lettered_sibling_matches(self) -> None:
        """s.304A's successor is s.304B, which the old pattern skipped entirely."""
        assert successor_pattern("304A").search("\n304B. Dowry death.\n")

    def test_an_amendment_marked_successor_matches(self) -> None:
        """Inserted sections print as `1[304B. ...`."""
        assert successor_pattern("304A").search("\n1[304B. Dowry death.\n")

    def test_a_distant_section_is_not_a_successor(self) -> None:
        """Guards against a much later heading being mistaken for this section's end."""
        assert successor_pattern("363").search("\n420. Cheating.\n") is None

    def test_repealed_sections_are_stepped_over(self) -> None:
        assert successor_pattern("363").search("\n367. Kidnapping to cause grievous hurt.\n")

    def test_keyword_matching_ignores_line_breaks(self) -> None:
        """PDF text wraps wherever the typesetter did, so a phrase present in the statute can
        appear split across lines. A raw substring check reports a correct section as wrong."""
        section = BareAct.open(BNS_FILE).find_section(
            "85", must_contain="subjects such woman to cruelty"
        )
        assert section is not None
