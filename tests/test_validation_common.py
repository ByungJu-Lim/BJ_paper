import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.validation_common import expand_paths, visible_markdown


class TestValidationCommon(unittest.TestCase):
    def test_indented_paragraph_and_list_continuations_remain_visible(self):
        for text in ('A result continues\n    [@unknown]\n', '- A claim\n    continued [@unknown]\n'):
            self.assertIn('@unknown', visible_markdown(text))

    def test_literal_globs_and_expanded_paths_are_equivalent(self):
        with TemporaryDirectory() as tmp:
            paths = [Path(tmp) / name for name in ('a.md', 'b.md')]
            for path in paths:
                path.write_text('text', encoding='utf-8')
            self.assertEqual(expand_paths([Path(tmp) / '*.md']), paths)
            self.assertEqual(expand_paths(paths + paths), paths)

    def test_missing_paths_and_empty_globs_fail(self):
        with TemporaryDirectory() as tmp:
            for value in (Path(tmp) / '*.md', Path(tmp) / 'missing.md', Path(tmp)):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    expand_paths([value])

    def test_examples_and_comments_are_not_manuscript_prose(self):
        text = 'Real @one\n```md\n@fake\n```\n~~~\n@fake2\n~~~\n`@inline` <!-- @comment -->\n'
        visible = visible_markdown(text)
        self.assertIn('@one', visible)
        for key in ('@fake', '@fake2', '@inline', '@comment'):
            self.assertNotIn(key, visible)
