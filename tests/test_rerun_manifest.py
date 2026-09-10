import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.rerun_manifest import command_is_safe, rerun

DETERMINISTIC = """import csv
rows = list(csv.reader(open('data/raw/input.csv')))
with open('data/processed/out.csv', 'w', newline='') as handle:
    csv.writer(handle).writerows(rows)
"""

VARYING = """import random
open('data/processed/out.csv', 'w').write(str(random.random()))
"""

FAILING = """import sys
sys.exit(3)
"""

CORRUPTS_THEN_FAILS = """open('data/processed/out.csv', 'w').write('PARTIAL')
import sys
sys.exit(3)
"""

WRITES_UNDECLARED = """import csv
rows = list(csv.reader(open('data/raw/input.csv')))
with open('data/processed/out.csv', 'w', newline='') as handle:
    csv.writer(handle).writerows(rows)
open('data/processed/extra.csv', 'w').write('undeclared')
"""


def sandbox(tmp: str, body: str, manifest_extra: dict | None = None,
            command: str | None = None) -> tuple[Path, Path]:
    """A minimal project tree with one runnable script and one manifest."""
    root = Path(tmp).resolve()
    for directory in ('code', 'data/raw', 'data/processed'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / 'code/run.py').write_text(body, encoding='utf-8')
    (root / 'data/raw/input.csv').write_text('seed,value\n1,10\n', encoding='utf-8')

    manifest = {
        'run_id': 'example-2026-01-01',
        'script': 'code/run.py',
        'command': command or f'"{sys.executable}" code/run.py',
        'inputs': ['data/raw/input.csv'],
        'outputs': ['data/processed/out.csv'],
        'random_seed': 42,
        'python_version': '.'.join(str(part) for part in sys.version_info[:3]),
        'dependencies': {},
    }
    manifest.update(manifest_extra or {})
    path = root / 'data/processed/example-2026-01-01.manifest.json'
    path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return root, path


def produce(root: Path) -> None:
    subprocess.run([sys.executable, 'code/run.py'], cwd=root, check=False, capture_output=True)


class TestRerunManifest(unittest.TestCase):
    def test_deterministic_run_reproduces(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, DETERMINISTIC)
            produce(root)
            reproduced, report = rerun(manifest, root, 120, False, False)
            self.assertTrue(reproduced, '\n'.join(report))
            self.assertIn('reproduced', '\n'.join(report))

    def test_undeclared_variation_fails(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, VARYING)
            produce(root)
            reproduced, report = rerun(manifest, root, 120, False, False)
            self.assertFalse(reproduced)
            self.assertIn('differs', '\n'.join(report))

    def test_declared_nondeterminism_is_reported_not_hidden(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, VARYING,
                                     {'nondeterminism': 'unseeded RNG; spread reported in Table 2'})
            produce(root)
            reproduced, report = rerun(manifest, root, 120, False, False)
            text = '\n'.join(report)
            self.assertTrue(reproduced, text)
            # It passes, but the difference stays on the page for the reviewer.
            self.assertIn('declared variance', text)
            self.assertIn('unseeded RNG', text)

    def test_originals_are_restored_after_a_varying_rerun(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, VARYING)
            produce(root)
            output = root / 'data/processed/out.csv'
            before = output.read_bytes()
            rerun(manifest, root, 120, False, False)
            self.assertEqual(output.read_bytes(), before)

    def test_keep_rerun_leaves_the_regenerated_output(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, VARYING)
            produce(root)
            output = root / 'data/processed/out.csv'
            before = output.read_bytes()
            rerun(manifest, root, 120, False, True)
            self.assertNotEqual(output.read_bytes(), before)

    def test_nonzero_exit_fails_and_restores(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, DETERMINISTIC)
            produce(root)
            output = root / 'data/processed/out.csv'
            before = output.read_bytes()
            (root / 'code/run.py').write_text(FAILING, encoding='utf-8')
            reproduced, report = rerun(manifest, root, 120, False, False)
            self.assertFalse(reproduced)
            self.assertIn('exited 3', '\n'.join(report))
            self.assertEqual(output.read_bytes(), before)

    def test_missing_output_is_an_error_not_a_pass(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, DETERMINISTIC)
            reproduced, report = rerun(manifest, root, 120, False, False)
            self.assertFalse(reproduced)
            self.assertIn('declared output does not exist', '\n'.join(report))

    def test_dry_run_executes_nothing(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, VARYING)
            produce(root)
            output = root / 'data/processed/out.csv'
            before = output.read_bytes()
            reproduced, report = rerun(manifest, root, 120, True, False)
            self.assertTrue(reproduced)
            self.assertIn('dry-run', '\n'.join(report))
            self.assertEqual(output.read_bytes(), before)

    def test_command_must_invoke_the_declared_script(self):
        self.assertIsNone(command_is_safe({'script': 'code/run.py',
                                           'command': 'python code/run.py --seed 42'}))
        self.assertIsNotNone(command_is_safe({'script': 'code/run.py',
                                              'command': 'python -c "print(1)"'}))
        self.assertIsNotNone(command_is_safe({'script': 'code/run.py', 'command': ''}))
        self.assertIsNotNone(command_is_safe({'script': '', 'command': 'python code/run.py'}))

    def test_refused_command_is_never_executed(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, DETERMINISTIC,
                                     command=f'"{sys.executable}" -c "print(1)"')
            produce(root)
            output = root / 'data/processed/out.csv'
            before = output.read_bytes()
            reproduced, report = rerun(manifest, root, 120, False, False)
            self.assertFalse(reproduced)
            self.assertIn('REFUSED', '\n'.join(report))
            self.assertEqual(output.read_bytes(), before)

    def test_environment_drift_is_reported(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, DETERMINISTIC, {'python_version': '0.0.0'})
            produce(root)
            _, report = rerun(manifest, root, 120, True, False)
            self.assertIn('python 0.0.0 recorded', '\n'.join(report))

    def test_keep_rerun_is_honoured_when_the_command_fails(self):
        # The flag is an explicit opt-in; overriding it on the failure path
        # would silently withhold exactly the partial output you asked to see.
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, DETERMINISTIC)
            produce(root)
            (root / 'code/run.py').write_text(CORRUPTS_THEN_FAILS, encoding='utf-8')
            output = root / 'data/processed/out.csv'
            reproduced, _ = rerun(manifest, root, 120, False, True)
            self.assertFalse(reproduced)
            self.assertEqual(output.read_text(encoding='utf-8'), 'PARTIAL')

    def test_default_still_restores_when_the_command_fails(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, DETERMINISTIC)
            produce(root)
            output = root / 'data/processed/out.csv'
            before = output.read_bytes()
            (root / 'code/run.py').write_text(CORRUPTS_THEN_FAILS, encoding='utf-8')
            rerun(manifest, root, 120, False, False)
            self.assertEqual(output.read_bytes(), before)

    def test_undeclared_result_fails_the_run(self):
        # A file under the evidence directory that no manifest names cannot be
        # traced back to a run, which is the invariant run:<run-id> rests on.
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, WRITES_UNDECLARED)
            produce(root)
            reproduced, report = rerun(manifest, root, 120, False, False)
            text = chr(10).join(report)
            self.assertFalse(reproduced, text)
            self.assertIn('undeclared result', text)
            self.assertIn('data/processed/extra.csv', text)

    def test_undeclared_result_is_left_in_place(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(tmp, WRITES_UNDECLARED)
            produce(root)
            rerun(manifest, root, 120, False, False)
            self.assertTrue((root / 'data/processed/extra.csv').is_file())

    def test_declaring_the_extra_output_makes_the_run_pass(self):
        with TemporaryDirectory() as tmp:
            root, manifest = sandbox(
                tmp, WRITES_UNDECLARED,
                {'outputs': ['data/processed/out.csv', 'data/processed/extra.csv']})
            produce(root)
            reproduced, report = rerun(manifest, root, 120, False, False)
            self.assertTrue(reproduced, chr(10).join(report))


class TestSweep(unittest.TestCase):
    """`--all` over an empty processed dir must not fail CI.

    Whether a paper is *required* to have runs is
    `verify_story_brief.py --check-manifests`'s question. Sweeping an empty
    directory reproduced nothing and failed nothing.
    """

    def sweep(self, cwd: Path, *extra: str) -> subprocess.CompletedProcess:
        script = Path(__file__).resolve().parents[1] / 'scripts/rerun_manifest.py'
        return subprocess.run([sys.executable, str(script), *extra], cwd=cwd,
                              capture_output=True, text=True, encoding='utf-8')

    def test_empty_sweep_passes(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / 'data/processed').mkdir(parents=True)
            result = self.sweep(Path(tmp), '--all')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('nothing to re-run', result.stdout)

    def test_no_arguments_is_a_usage_error(self):
        with TemporaryDirectory() as tmp:
            result = self.sweep(Path(tmp))
            self.assertNotEqual(result.returncode, 0)

    def test_sweep_finds_and_runs_a_manifest(self):
        with TemporaryDirectory() as tmp:
            root, _ = sandbox(tmp, DETERMINISTIC)
            produce(root)
            result = self.sweep(root, '--all')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('1 run(s) reproduced', result.stdout)


if __name__ == '__main__':
    unittest.main()
