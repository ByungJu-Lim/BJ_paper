import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_paper_state import REQUIRED_STAGE_IDS
from tests.state_fixture import write_state, with_stage


ROOT = Path(__file__).resolve().parents[1]


class TestCitationWorkflow(unittest.TestCase):
    def run_check(self, directory: Path, *extra: str):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/verify_citations.py'),
                               '--registry', str(directory / 'sources.json'),
                               '--sections', str(directory / '*.md'),
                               '--bib', str(directory / 'references.bib'), *extra],
                              cwd=ROOT, capture_output=True, text=True)

    def fixture(self, directory: Path):
        entry = {'key': 'real2024', 'title': 'Measured Results', 'authors': ['Jane Doe'],
                 'year': 2024, 'venue': 'Example Journal', 'doi': '10.1234/example'}
        (directory / 'sources.json').write_text(json.dumps([entry]), encoding='utf-8')
        (directory / 'paper.md').write_text('A paragraph\n    cites @real2024.\n', encoding='utf-8')
        (directory / 'references.bib').write_text('', encoding='utf-8')

    def test_draft_defers_only_bibliography_completeness(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.fixture(directory)
            # A drafting-phase state, not the live one: bibliography completeness
            # is deferred until citation-manage is under review, and that must
            # not depend on how far the real manuscript happens to have got.
            state = write_state(directory / 'drafting-state.md', with_stage('outline-draft', 'in-progress'))
            args = ('--state', str(state))
            result = self.run_check(directory, *args)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('deferred', result.stdout)
            self.assertNotEqual(self.run_check(directory).returncode, 0)
            (directory / 'paper.md').write_text('- A claim\n    cites @invented.\n', encoding='utf-8')
            result = self.run_check(directory, *args)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('invented', result.stdout)

    def test_citation_review_requires_bibliography_even_with_state(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.fixture(directory)
            blocks = []
            for stage in REQUIRED_STAGE_IDS:
                status, number, verdict = 'approved', 1, 'pass'
                if stage == 'citation-manage':
                    status, verdict = 'awaiting-review', ''
                elif stage == 'polish-review':
                    status, number, verdict = 'not-started', 0, ''
                blocks.append(f'## Stage: {stage}\nstatus: {status}\nround: {number}/3\nlast-critic-verdict: {verdict}\nlast-critic-issues:\n')
                if stage == 'outline-draft':
                    blocks.append(
                        'artifacts:\n'
                        '- outline: approved, round 1/3, verdict pass\n'
                    )
                if stage == 'citation-manage':
                    blocks.append('verified-sources: 0\nrejected-citations:\n')
            state = directory / 'state.txt'
            state.write_text('\n'.join(blocks), encoding='utf-8')
            result = self.run_check(directory, '--state', str(state))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('no entry', result.stdout)

    def test_existing_wrong_metadata_is_rejected_during_drafting(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.fixture(directory)
            (directory / 'references.bib').write_text(
                '@article{real2024,title={Invented},author={Jane Doe},year={2024},'
                'doi={10.1234/example},journal={Example Journal}}', encoding='utf-8')
            state = write_state(directory / 'drafting-state.md', with_stage('outline-draft', 'in-progress'))
            result = self.run_check(directory, '--state', str(state))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('title differs', result.stdout)
