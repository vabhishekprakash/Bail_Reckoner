"""D-089's fact parser and refusal contract — fast tests, no OCR runtime.

The OCR engine itself (~19s/page) runs only in the reconciliation script, whose output
lands in 04_eval/; a suite that quietly ran OCR would hide a 30-minute dependency the
way a model download would (the Layer A precedent)."""

from __future__ import annotations

from bail_reckoner.statutes.ocr_channel import (
    PunishmentFacts,
    _heading_pattern,
    _next_section_number,
    parse_punishment_facts,
)


class TestFactParser:
    def test_word_and_digit_quantities_normalise_to_months(self) -> None:
        facts = parse_punishment_facts(
            "shall be punished with rigorous imprisonment for a term which may extend "
            "to twenty years and shall not be less than ten years; a lesser limb may "
            "extend to 6 months."
        )
        assert facts.maxima_months == (6, 240)
        assert facts.minima_months == (120,)

    def test_life_and_death_are_mention_flags_not_terms(self) -> None:
        facts = parse_punishment_facts(
            "shall be punishable with death, or imprisonment for life."
        )
        assert facts.death_mentioned and facts.life_mentioned
        assert facts.maxima_months == ()

    def test_definition_deaths_do_not_count_as_punishment_mentions(self) -> None:
        """'causes the death of any person' is an offence definition, not a punishment;
        counting it would make nearly every homicide section 'mention death'."""
        facts = parse_punishment_facts("Whoever causes the death of any person by doing")
        assert not facts.death_mentioned

    def test_ocr_spacing_does_not_change_the_facts(self) -> None:
        """The channels' whitespace differs; the comparison must not manufacture
        disagreement from it."""
        clean = "may extend to three years, or with fine, or with both"
        spaced = "may  extend   to three  years , or with fine, or with both"
        assert parse_punishment_facts(clean) == parse_punishment_facts(spaced)

    def test_facets_disagreeing_names_each_differing_facet(self) -> None:
        a = parse_punishment_facts("may extend to three years")
        b = parse_punishment_facts("may extend to seven years")
        assert a.facets_disagreeing_with(b) == ("maxima",)
        assert a.facets_disagreeing_with(a) == ()

    def test_empty_text_yields_empty_facts_not_defaults(self) -> None:
        """No convenience default (D-064): nothing found is empty tuples and zero,
        reported as such — the comparison layer treats it as data, never fills it."""
        assert parse_punishment_facts("") == PunishmentFacts((), (), False, False, 0)


class TestHeadingPattern:
    def test_footnote_apparatus_is_not_a_heading(self) -> None:
        pattern = _heading_pattern("7")
        assert pattern.search("Subs. by Act 16 of 2014, s. 7, for six months") is None
        assert pattern.search("(7) Whoever, whilst committing") is None

    def test_fused_ocr_heading_matches(self) -> None:
        assert _heading_pattern("20").search("rupees. 20.Punishment for contravention")

    def test_lettered_sections_fall_through_to_next_integer(self) -> None:
        assert _next_section_number("304A") == "305"
        assert _next_section_number("331") == "332"
