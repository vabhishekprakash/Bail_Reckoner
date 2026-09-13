"""Regression tests for punishment-limb counting.

SYNTHETIC AND REAL-STATUTE DATA. Real sections are read from the bare acts in 01_law/.
No real accused person's data appears here.

These sit on the same footing as the s.363 boundary case: each is a named failure that shipped a
wrong number into a decision, not a hypothetical. An undercounted section becomes one row
asserting a single maximum for a section that has several, and IPC governs every pre-1-July-2024
offence.
"""

from __future__ import annotations

import pytest

from bail_reckoner.statutes.bare_act import LAW_DIR, BareAct
from bail_reckoner.statutes.curation import BNS_FILE, IPC_FILE, count_punishment_limbs

needs_law_pdfs = pytest.mark.skipif(
    not (LAW_DIR / BNS_FILE).exists() or not (LAW_DIR / IPC_FILE).exists(),
    reason="bare-act PDFs are not present in this checkout",
)


class TestIntraWordSpacesDoNotHideLimbs:
    """The defect that produced near-uniform IPC counts of 1.

    The India Code IPC PDF splits words at arbitrary points. Any pattern containing spaces
    silently fails on the IPC while succeeding on the cleaner gazette-sourced BNS — which is
    exactly the shape of a bug that looks like a fact about the statute.
    """

    def test_split_shall_be_punished_is_still_counted(self) -> None:
        assert count_punishment_limbs("Whoever ... shal l be punished with imprisonment.") == 1

    def test_split_shall_be_liable_either_to_is_counted(self) -> None:
        assert count_punishment_limbs("the offender shall be liab le either to life.") == 1

    def test_zero_is_reported_honestly(self) -> None:
        """An earlier caller floored the count at 1, converting total detection failure into a
        plausible-looking number."""
        assert count_punishment_limbs("A definition with no punishment clause at all.") == 0


class TestProseContinuationLimbs:
    def test_a_second_maximum_introduced_by_or_with_imprisonment_counts(self) -> None:
        """IPC s.304 Part II is a distinct maximum on a distinct mental state, introduced without
        repeating the operator."""
        text = (
            "shall be punished with imprisonment for life ... if the act is done with the "
            "intention of causing death; or with imprisonment of either description for a term "
            "which may extend to ten years ... if the act is done with the knowledge ..."
        )
        assert count_punishment_limbs(text) == 2


class TestAlternativesWithinOneLimbAreNotTwoLimbs:
    """Found by page-verifying BNS ss.331, 316 and 317, which the prose rule over-counted by
    exactly one each. The same words that introduce a second limb also join two alternatives
    inside one."""

    def test_life_or_a_term_is_a_single_limb(self) -> None:
        text = (
            "shall be punished with imprisonment for life, or with imprisonment of either "
            "description for a term which may extend to ten years, and shall also be liable to "
            "fine."
        )
        assert count_punishment_limbs(text) == 1

    def test_a_genuine_second_limb_still_counts(self) -> None:
        """The IPC s.304 shape must survive the fix: a new maximum on a new mental state."""
        text = (
            "shall be punished with imprisonment of either description for a term which may "
            "extend to ten years, if the act is done with the intention of causing death; "
            "or with imprisonment of either description for a term which may extend to ten "
            "years, if the act is done with the knowledge that it is likely to cause death."
        )
        assert count_punishment_limbs(text) == 2


class TestStateAmendmentsAreExcluded:
    def test_a_punishment_inside_a_state_amendment_is_not_a_limb_of_this_section(self) -> None:
        """India Code prints STATE AMENDMENTS inline. The block after IPC s.304A contains
        Himachal Pradesh's s.304-AA and its own punishment clause; that belongs to a different
        provision and to L-002, not to s.304A's limb count."""
        text = (
            "Whoever ... shall be punished with imprisonment ... two years. "
            "STATE AMENDMENTS Himachal Pradesh.— 304-AA ... shall be punished with "
            "imprisonment for life ..."
        )
        assert count_punishment_limbs(text) == 1


@needs_law_pdfs
class TestAgainstTheRealSections:
    """Named cases, on the same footing as s.363 for boundaries."""

    def test_ipc_304_has_two_limbs(self) -> None:
        """Part I (intention) and Part II (knowledge) carry different maxima. Counted as 1
        before the fix, which would have shipped one maximum for a two-maximum section."""
        section = BareAct.open(IPC_FILE).find_section(
            "304", must_contain="culpable homicide not amounting to murder"
        )
        assert section is not None
        assert count_punishment_limbs(section.text) == 2

    def test_ipc_307_limbs_are_detected_at_all(self) -> None:
        """Ten years base, and life if hurt is caused. Counted as ZERO before the fix -- every
        operator in the section was split mid-word by the PDF."""
        section = BareAct.open(IPC_FILE).find_section("307", must_contain="such circumstances")
        assert section is not None
        assert count_punishment_limbs(section.text) >= 2

    def test_ipc_304a_is_one_limb_not_two(self) -> None:
        """It carries a single punishment. The second count came from the state-amendment block."""
        section = BareAct.open(IPC_FILE).find_section("304A", must_contain="rash or negligent act")
        assert section is not None
        assert count_punishment_limbs(section.text) == 1

    @pytest.mark.parametrize(
        ("section", "keyword", "expected"),
        [
            ("331", "house-trespass", 8),
            ("316", "criminal breach of trust", 4),
            ("317", "stolen property", 4),
            # s.351's count changed as a side effect of the same fix. Its removed hit was not
            # even a punishment of this section: it sat inside the description of the
            # THREATENED offence ("threat to cause an offence punishable with death or
            # imprisonment for life, or with imprisonment ...").
            ("351", "criminal intimidation", 3),
        ],
    )
    def test_the_four_recounted_bns_sections_stay_at_their_post_fix_counts(
        self, section: str, keyword: str, expected: int
    ) -> None:
        """PROVENANCE CORRECTED 2026-08-26 (Abhishek's audit): the originating commit
        (aeaecc2) claimed these counts were "page-verified by eye", but that verification
        was never reported for review — the three requested sections were never returned,
        and s.351 was never on the requested list — so the page-verification claim is
        UNESTABLISHED. What this test actually pins is the detector's post-fix output
        (the alternatives-within-one-limb false positive subtracted), as a regression
        guard. The counts get their human check in the consolidated review queue, where
        the page governs and rows are added or deleted to match it."""
        found = BareAct.open(BNS_FILE).find_section(section, must_contain=keyword)
        assert found is not None
        assert count_punishment_limbs(found.text) == expected

    def test_no_section_in_either_regime_returns_zero(self) -> None:
        """The BNS column was the control that made the IPC look anomalous, and that reasoning is
        what hid the failure. The control itself is now checked."""
        from bail_reckoner.statutes.curation import SEED_LIST
        from bail_reckoner.statutes.models import Regime

        acts = {Regime.BNS_2023: BareAct.open(BNS_FILE), Regime.IPC_1860: BareAct.open(IPC_FILE)}
        for entry in SEED_LIST:
            for regime, section in (
                (Regime.IPC_1860, entry.ipc_section),
                (Regime.BNS_2023, entry.bns_section),
            ):
                if section is None:
                    continue
                found = acts[regime].find_section(section, must_contain=entry.keyword_for(regime))
                assert found is not None, f"{regime.value}-{section} not located"
                assert count_punishment_limbs(found.text) > 0, f"{regime.value}-{section} ZERO"

    def test_the_swapped_in_offences_resolve(self) -> None:
        """Wrongful restraint (the sharpest gate-0 exerciser) and using a forged document as
        genuine both had to draft before the swap could be executed."""
        ipc, bns = BareAct.open(IPC_FILE), BareAct.open(BNS_FILE)
        assert ipc.find_section("341", must_contain="wrongfully restrains") is not None
        assert bns.find_section("126", must_contain="wrongfully restrains") is not None
        assert ipc.find_section("471", must_contain="fraudulently or dishonestly uses") is not None
        assert bns.find_section("340", must_contain="fraudulently or dishonestly uses") is not None
