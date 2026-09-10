"""Re-execute a recorded run and check that it reproduces its own outputs.

`verify_story_brief.py --check-manifests` proves a manifest is *well formed* and
that the files it names exist. It never runs anything, so a `run:<run-id>`
evidence entry currently guarantees only that some file was produced once. This
script closes that gap: it re-runs the exact recorded command and compares the
regenerated outputs, byte for byte, against the ones already committed.

    python scripts/rerun_manifest.py data/processed/<run-id>.manifest.json
    python scripts/rerun_manifest.py --all
    python scripts/rerun_manifest.py --all --dry-run

The originals are copied aside before the command runs and restored afterwards,
so a failed or nondeterministic re-run cannot quietly overwrite the results the
manuscript already cites. Pass --keep-rerun to leave the regenerated files in
place instead - including the partial output of a run that failed, which is the
point of the flag and also its hazard.

Restoring covers the outputs the manifest declares. A run that writes anything
else under data/processed is reported as a failure rather than tidied away: an
untraceable file in the evidence directory is a manifest that does not describe
its own run.

A manifest may declare `nondeterminism` (a string saying what varies and why).
Differing bytes are then reported as declared variance rather than a failure -
but they are still printed, because "it varies" is a claim the reviewer has to
weigh, not a way to make the comparison go away.
"""
import argparse
import hashlib
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

DEFAULT_PROCESSED_DIR = Path('data/processed')


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('manifest must be an object')
    return data


def check_environment(manifest: dict) -> list[str]:
    """Version drift is the usual reason a rerun diverges; say so before blaming the code."""
    notes: list[str] = []
    recorded = str(manifest.get('python_version', '')).strip()
    running = '.'.join(str(part) for part in sys.version_info[:3])
    if recorded and recorded != running:
        notes.append(f'python {recorded} recorded, {running} running')

    dependencies = manifest.get('dependencies')
    if isinstance(dependencies, dict):
        from importlib.metadata import PackageNotFoundError, version as installed_version
        for package, pinned in sorted(dependencies.items()):
            try:
                found = installed_version(package)
            except PackageNotFoundError:
                notes.append(f'{package} {pinned} recorded, not installed')
                continue
            if found != pinned:
                notes.append(f'{package} {pinned} recorded, {found} installed')
    return notes


def resolve_outputs(manifest: dict, root: Path) -> tuple[list[Path], list[str]]:
    outputs: list[Path] = []
    errors: list[str] = []
    for value in manifest.get('outputs') or []:
        path = (root / str(value)).resolve()
        if not path.is_relative_to(root):
            errors.append(f'output escapes the project: {value}')
        elif not path.is_file():
            errors.append(f'declared output does not exist: {value}')
        else:
            outputs.append(path)
    if not outputs and not errors:
        errors.append('manifest declares no outputs')
    return outputs, errors


def command_is_safe(manifest: dict) -> str | None:
    """The command is repo content and this script executes it.

    Refuse anything that does not actually invoke the script the manifest
    declares - `validate_manifest` already pins that script under `code/`, so
    this keeps execution inside the same boundary.
    """
    command = str(manifest.get('command', '')).strip()
    script = str(manifest.get('script', '')).strip()
    if not command:
        return 'manifest records no command'
    if not script:
        return 'manifest records no script'
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError as exc:
        return f'command is not parseable: {exc}'
    wanted = script.replace('\\', '/')
    normalized = [token.strip('"').strip("'").replace('\\', '/') for token in tokens]
    if not any(token.endswith(wanted) for token in normalized):
        return f'command does not invoke the declared script {script}'
    return None


def _snapshot(directory: Path) -> dict[Path, int]:
    """Modification times for everything under the evidence directory.

    Detecting only files that *appear* would miss the usual case: a manifest is
    written after its run, so an undeclared result already exists by the time
    anyone re-runs. What marks it is that the re-run writes to it again.
    """
    if not directory.is_dir():
        return {}
    return {path: path.stat().st_mtime_ns for path in directory.rglob('*') if path.is_file()}


def _restore(outputs: list[Path], stash: Path) -> None:
    for index, path in enumerate(outputs):
        source = stash / f'{index}.bin'
        if source.is_file():
            shutil.copy2(source, path)


def rerun(manifest_path: Path, root: Path, timeout: int, dry_run: bool,
          keep_rerun: bool, processed_dir: Path | None = None) -> tuple[bool, list[str]]:
    report: list[str] = []
    try:
        manifest = load_manifest(manifest_path)
    except (OSError, ValueError) as exc:
        return False, [f'{manifest_path}: {exc}']

    run_id = manifest.get('run_id') or manifest_path.name
    report.append(f'== {run_id}')

    refusal = command_is_safe(manifest)
    if refusal:
        report.append(f'  REFUSED: {refusal}')
        return False, report

    outputs, errors = resolve_outputs(manifest, root)
    if errors:
        report.extend(f'  ERROR: {error}' for error in errors)
        return False, report

    for note in check_environment(manifest):
        report.append(f'  environment: {note}')

    command = str(manifest['command'])
    report.append(f'  command: {command}')
    if dry_run:
        report.append('  dry-run: not executed')
        return True, report

    before = {path: digest(path) for path in outputs}
    evidence_dir = (processed_dir or (root / DEFAULT_PROCESSED_DIR)).resolve()
    before_files = _snapshot(evidence_dir)
    declared_variance = str(manifest.get('nondeterminism', '')).strip()
    differing: list[str] = []
    missing: list[str] = []

    with TemporaryDirectory() as tmp:
        stash = Path(tmp)
        for index, path in enumerate(outputs):
            shutil.copy2(path, stash / f'{index}.bin')
        try:
            completed = subprocess.run(command, cwd=root, shell=True, capture_output=True,
                                       text=True, encoding='utf-8', errors='replace',
                                       timeout=timeout)
        except subprocess.TimeoutExpired:
            if not keep_rerun:
                _restore(outputs, stash)
            report.append(f'  FAIL: command exceeded {timeout}s')
            return False, report

        if completed.returncode != 0:
            if not keep_rerun:
                _restore(outputs, stash)
            report.append(f'  FAIL: command exited {completed.returncode}')
            tail = (completed.stderr or completed.stdout or '').strip().splitlines()[-10:]
            report.extend(f'    | {line}' for line in tail)
            return False, report

        for path in outputs:
            relative = path.relative_to(root).as_posix()
            if not path.is_file():
                missing.append(relative)
            elif digest(path) != before[path]:
                differing.append(relative)

        declared = set(outputs) | {manifest_path.resolve()}
        undeclared = sorted(
            path.relative_to(root).as_posix()
            for path, mtime in _snapshot(evidence_dir).items()
            if path not in declared and before_files.get(path) != mtime)

        if not keep_rerun:
            _restore(outputs, stash)

    for relative in undeclared:
        report.append(f'  FAIL: wrote an undeclared result: {relative}')
    if undeclared:
        report.append('  add it to the manifest outputs, or stop writing it - a result '
                      'under the evidence directory that no manifest names cannot be traced')
        report.append('  left in place: removing a file this script did not create is not its call')
    for relative in missing:
        report.append(f'  FAIL: rerun did not regenerate {relative}')
    for relative in differing:
        label = 'declared variance' if declared_variance else 'FAIL: differs'
        report.append(f'  {label}: {relative}')
    if differing and declared_variance:
        report.append(f'  nondeterminism: {declared_variance}')
        report.append('  weigh the recorded run-to-run variability; differing bytes do not settle this')

    reproduced = not missing and not undeclared and (not differing or bool(declared_variance))
    if reproduced and not differing:
        report.append(f'  reproduced: {len(outputs)} output(s) identical')
    return reproduced, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('manifests', nargs='*', type=Path, help='manifest files to re-run')
    parser.add_argument('--all', action='store_true',
                        help=f're-run every manifest under {DEFAULT_PROCESSED_DIR}')
    parser.add_argument('--processed-dir', type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument('--timeout', type=int, default=1800,
                        help='seconds allowed per command (default 1800)')
    parser.add_argument('--dry-run', action='store_true',
                        help='report what would run, execute nothing')
    parser.add_argument('--keep-rerun', action='store_true',
                        help='leave regenerated outputs in place instead of restoring the originals; '
                             'this applies to a failed run too, so partial output can overwrite '
                             'a committed result')
    args = parser.parse_args()

    root = Path.cwd().resolve()
    manifests = list(dict.fromkeys(args.manifests))
    if args.all:
        found = sorted(args.processed_dir.glob('*.manifest.json'))
        manifests = list(dict.fromkeys(manifests + found))
        if not manifests:
            # Whether a paper is *required* to have runs is
            # `verify_story_brief.py --check-manifests`'s question, not this
            # script's. Sweeping an empty directory reproduced nothing and
            # failed nothing, so it must not fail the build either.
            print(f'no manifests under {args.processed_dir}; nothing to re-run')
            return 0
    if not manifests:
        print('no manifests given; pass paths or --all')
        return 1

    failures = 0
    for manifest_path in manifests:
        reproduced, report = rerun(manifest_path, root, args.timeout, args.dry_run,
                                   args.keep_rerun, args.processed_dir)
        print('\n'.join(report))
        if not reproduced:
            failures += 1

    if failures:
        print(f'\n{failures} of {len(manifests)} run(s) did not reproduce.')
        return 1
    print(f'\n{len(manifests)} run(s) reproduced.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
