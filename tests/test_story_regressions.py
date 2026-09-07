import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.verify_story_brief import validate_claims, validate_evidence, validate_sections


def claim(evidence='', status='supported'):
    return {'claims': [{'id': 'C1', 'claim': 'Efficiency improves',
                        'status': status, 'evidence': evidence}],
            'falsifiers': {'C1': 'Measured efficiency does not improve.'}}


class TestStoryRegressions(unittest.TestCase):
    def test_missing_registry_never_disables_resolution(self):
        with TemporaryDirectory() as tmp:
            for registry in (None, Path(tmp) / 'missing.json'):
                self.assertTrue(validate_evidence(claim('@ghost'), registry, Path(tmp)))

    def test_malformed_and_empty_manifests_fail(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'a.manifest.json'
            for value in ('not json', '{}', '[]'):
                path.write_text(value, encoding='utf-8')
                self.assertTrue(validate_evidence(claim('run:a'), None, Path(tmp)))

    def test_real_claim_requires_falsifier_before_experiment(self):
        brief = claim('', 'assumed')
        brief['falsifiers']['C1'] = '_입력 필요_'
        self.assertTrue(validate_claims(brief))

    def test_missing_figure_is_not_evidence(self):
        with TemporaryDirectory() as tmp:
            self.assertTrue(validate_evidence(claim('Fig. 999'), None, Path(tmp)))

    def test_written_section_cannot_omit_or_empty_its_declaration(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / '04-results.md'
            for declaration in ('', '<!-- claims: -->\n'):
                path.write_text('# Results\n' + declaration + 'Efficiency improves by 99%.', encoding='utf-8')
                self.assertTrue(validate_sections(claim('', 'assumed'), [path], False))

    def test_default_cli_accepts_literal_glob(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, str(root / 'scripts/verify_story_brief.py'),
                                 '--sections', 'docs/sections/*.md',
                                 '--registry', 'docs/notes/retrieved-sources.json'],
                                cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_valid_manifest_and_missing_artifact(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for directory in ('code', 'data/raw', 'data/processed'):
                (root / directory).mkdir(parents=True, exist_ok=True)
            for file in ('code/run.py', 'data/raw/input.csv', 'data/processed/output.csv'):
                (root / file).write_text('data', encoding='utf-8')
            data = {'run_id': 'a', 'script': 'code/run.py', 'command': 'python code/run.py',
                    'inputs': ['data/raw/input.csv'], 'outputs': ['data/processed/output.csv'],
                    'random_seed': 42, 'python_version': '3.10.0', 'dependencies': {}}
            processed = root / 'data/processed'
            manifest = processed / 'a.manifest.json'
            manifest.write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(validate_evidence(claim('run:a'), None, processed, project_root=root), [])
            for field, value in [('run_id', 'wrong'), ('script', '../outside.py'),
                                 ('inputs', ['missing.csv']), ('outputs', ['data/raw/input.csv']),
                                 ('random_seed', True), ('dependencies', [])]:
                with self.subTest(field=field):
                    bad = {**data, field: value}
                    manifest.write_text(json.dumps(bad), encoding='utf-8')
                    self.assertTrue(validate_evidence(claim('run:a'), None, processed, project_root=root))

    def test_caption_requires_adjacent_real_image_or_table(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            section = root / '04-results.md'
            (root / 'figure.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding='utf-8')
            section.write_text('Fig. 2: Efficiency\n![plot](figure.svg)\n\n'
                               'Table 3: Comparison\n| Method | Value |\n|---|---|\n| A | 1 |\n', encoding='utf-8')
            self.assertEqual(validate_evidence(claim('Fig. 2, Table 3'), None, root, [section], root), [])
            (root / 'figure.svg').unlink()
            self.assertTrue(validate_evidence(claim('Fig. 2'), None, root, [section], root))
            section.write_text('The result is shown in Fig. 2.', encoding='utf-8')
            self.assertTrue(validate_evidence(claim('Fig. 2'), None, root, [section], root))

    def test_code_example_cannot_supply_claim_declaration(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / '04-results.md'
            path.write_text('# Results\n```md\n<!-- claims: C1 -->\n```\nThe result improves.', encoding='utf-8')
            self.assertTrue(validate_sections(claim(), [path], False))

    def test_workflow_approval_cannot_bypass_unwritten_brief(self):
        root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as tmp:
            state = (root / '.omc/paper-state.md').read_text(encoding='utf-8')
            state = state.replace('status: not-started', 'status: approved', 1)
            state = state.replace('round: 0/3', 'round: 1/3', 1)
            state = state.replace('last-critic-verdict:', 'last-critic-verdict: pass', 1)
            path = Path(tmp) / 'state.md'
            path.write_text(state, encoding='utf-8')
            result = subprocess.run([sys.executable, 'scripts/verify_story_brief.py', '--state', str(path)],
                                    cwd=root, capture_output=True, text=True, encoding='utf-8')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('required', result.stdout)
