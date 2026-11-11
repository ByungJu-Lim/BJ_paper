import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_prose import MAX_SENTENCE_WORDS, check_text, main, sentences
from tests.state_fixture import absent_outline, with_stage, write_state

SHORT = "The membrane recovered 92% of its flux after cleaning."


def long_sentence(words: int) -> str:
    return " ".join(["word"] * (words - 1)) + " end."


class TestSentenceSplitting(unittest.TestCase):
    def test_abbreviations_and_decimals_do_not_split(self):
        text = "Flux fell by 3.5 L m⁻² h⁻¹ (Fig. 2), e.g. at 25 °C. Rejection held."
        self.assertEqual(len(sentences(text)), 2)

    def test_sentence_starting_with_abbreviation_or_math_is_split(self):
        self.assertEqual(len(sentences("Table 1 lists the cases. Fig. 2 shows the trend.")), 2)
        self.assertEqual(len(sentences("The rate rose. $T_m$ fell in the second run.")), 2)


class TestCheckText(unittest.TestCase):
    def test_concise_prose_passes(self):
        errors, _, stats = check_text("\n\n".join([SHORT] * 6), "s.md")
        self.assertEqual(errors, [])
        self.assertEqual(stats["sentences"], 6)

    def test_long_sentence_fails(self):
        errors, _, _ = check_text(long_sentence(MAX_SENTENCE_WORDS + 1), "s.md")
        self.assertTrue(any("sentence has" in error for error in errors))

    def test_citations_and_inline_math_do_not_inflate_counts(self):
        text = long_sentence(MAX_SENTENCE_WORDS - 1)[:-1] + " $a+b=c$ [@smith2021; @lee2022]."
        errors, _, _ = check_text(text, "s.md")
        self.assertFalse(any("sentence has" in error for error in errors))

    def test_high_mean_fails_even_without_one_long_sentence(self):
        text = "\n\n".join([long_sentence(30)] * 6)
        errors, _, _ = check_text(text, "s.md")
        self.assertTrue(any("mean sentence length" in error for error in errors))

    def test_clause_chaining_fails(self):
        errors, _, _ = check_text("Three cases ran: low load; high load; and pulsed load.", "s.md")
        self.assertTrue(any("chains clauses" in error for error in errors))

    def test_inline_enumeration_fails_but_equation_numbers_do_not(self):
        errors, _, _ = check_text("The test required (a) less waste, (b) no damage and (c) more uptime.", "s.md")
        self.assertTrue(any("enumeration" in error for error in errors))
        errors, _, _ = check_text("Equations (3), (6) and (7) define the flux.", "s.md")
        self.assertFalse(any("enumeration" in error for error in errors))

    def test_figure_panel_references_are_not_an_inline_list(self):
        for text in ("Panels (a), (b) and (c) of Fig. 3 show the flux.",
                     "Fig. 3(a), (b) and (c) show the flux.",
                     "Figs. 2(a)–(c) and 4(a) show the flux."):
            errors, _, _ = check_text(text, "s.md")
            self.assertFalse(any("enumeration" in error for error in errors), text)

    def test_multiline_comments_are_not_prose(self):
        text = "<!--\nTODO: it is important to note this; check: later\n-->\n\n" + SHORT
        errors, _, stats = check_text(text, "s.md")
        self.assertEqual(errors, [])
        self.assertEqual(stats["sentences"], 1)

    def test_korean_text_is_skipped_with_a_note(self):
        text = " ".join(["막의 투과율은 세정 후 92% 회복되었다."] * 20)
        errors, notes, _ = check_text(text, "s.md")
        self.assertEqual(errors, [])
        self.assertTrue(any("Korean" in note for note in notes))

    def test_banned_phrase_fails(self):
        errors, _, _ = check_text("It is important to note that flux fell.", "s.md")
        self.assertTrue(any("banned phrase" in error for error in errors))

    def test_non_prose_blocks_are_skipped(self):
        text = "\n".join([
            "# " + long_sentence(50),
            "<!-- claims: C1 -->",
            "| a | b |",
            "|---|---|",
            "| " + long_sentence(50) + " | x |",
            "Fig. 1: " + long_sentence(50),
            "$$",
            long_sentence(50),
            "$$",
            "",
            SHORT,
        ])
        errors, _, stats = check_text(text, "s.md")
        self.assertEqual(errors, [])
        self.assertEqual(stats["sentences"], 1)

    def test_waiver_exempts_length_but_is_reported(self):
        text = "<!-- prose-ok: defines all symbols of Eq. (2) -->\n" + long_sentence(50)
        errors, notes, _ = check_text(text, "s.md")
        self.assertEqual(errors, [])
        self.assertTrue(any("defines all symbols" in note for note in notes))

    def test_waived_paragraph_does_not_count_toward_mean(self):
        text = "<!-- prose-ok: symbol table -->\n" + long_sentence(200) + "\n\n" + "\n\n".join([SHORT] * 5)
        errors, _, stats = check_text(text, "s.md")
        self.assertEqual(errors, [])
        self.assertLess(stats["mean"], 22)

    def test_waiver_does_not_reach_past_another_block(self):
        text = "<!-- prose-ok: symbols -->\n\n## Heading\n\n" + long_sentence(50)
        errors, notes, _ = check_text(text, "s.md")
        self.assertTrue(any("not followed by a prose paragraph" in error for error in errors))
        self.assertTrue(any("sentence has" in error for error in errors))
        self.assertEqual(notes, [])

    def test_waiver_does_not_exempt_banned_phrases(self):
        text = "<!-- prose-ok: reason -->\nIt should be noted that flux fell."
        errors, _, _ = check_text(text, "s.md")
        self.assertTrue(any("banned phrase" in error for error in errors))


class TestMain(unittest.TestCase):
    def test_exit_codes(self):
        with TemporaryDirectory() as tmp:
            good = Path(tmp) / "01-good.md"
            good.write_text(SHORT, encoding="utf-8")
            bad = Path(tmp) / "02-bad.md"
            bad.write_text(long_sentence(60), encoding="utf-8")
            self.assertEqual(main(["--sections", str(good)]), 0)
            self.assertEqual(main(["--sections", str(Path(tmp) / "*.md")]), 1)

    def test_state_mode_skips_sections_not_yet_under_review(self):
        with TemporaryDirectory() as tmp:
            bad = Path(tmp) / "04-results.md"
            bad.write_text(long_sentence(60), encoding="utf-8")
            drafting = write_state(Path(tmp) / "drafting.md", with_stage("results-discussion", "in-progress"))
            reviewing = write_state(Path(tmp) / "reviewing.md", with_stage("results-discussion", "awaiting-review"))
            outline = absent_outline(drafting)
            self.assertEqual(main(["--sections", str(bad), "--state", str(drafting), "--outline", str(outline)]), 0)
            self.assertEqual(main(["--sections", str(bad), "--state", str(reviewing), "--outline", str(outline)]), 1)

    def test_empty_glob_passes_for_template_state(self):
        with TemporaryDirectory() as tmp:
            self.assertEqual(main(["--sections", str(Path(tmp) / "*.md")]), 0)


if __name__ == "__main__":
    unittest.main()
