---
name: code-experiment
description: Writes and runs experiment/analysis code, or re-runs and registers existing prior results, producing manifested processed data under data/processed/. Use when the paper needs experimental/analytical results, whether newly run or already in hand.
---

# Code and Experiments

## Procedure

1. Read the approved story brief and ensure every planned experiment can test a written falsifier — for a `retrospective` claim, the falsifier is checked against evidence already in hand, not a run yet to happen. Run `python scripts/verify_story_brief.py --require-slots Context,Gap,Question,Approach --sections "docs/sections/*.md" --registry docs/notes/retrieved-sources.json` before execution. Commit the approved pre-experiment brief to preserve when the falsifiers were recorded. Delegate code under `code/`, reading only from `data/raw/`.
2. If the code and its output already exist (a prior run predating this paper, moved under `code/` and `data/raw/`), re-run the existing command rather than writing new code — the manifest and reproducibility check below apply identically to a rerun of prior work and to a freshly written experiment. Only write new code where no prior run answers the claim.
3. Run the code and write its output to `data/processed/` — never modify files under `data/raw/`.
4. Record what the code does and how to re-run it in a comment header at the top of the relevant file under `code/`.
5. Write a run manifest next to the output as `data/processed/<run-id>.manifest.json`. Reviewers and the Methods section both depend on it, and a result that cannot be regenerated cannot be defended:
   ```json
   {
     "run_id": "<slug>-<YYYY-MM-DD>",
     "script": "code/<file>.py",
     "command": "<exact command line used>",
     "inputs": ["data/raw/<file>"],
     "outputs": ["data/processed/<file>"],
     "random_seed": 42,
     "python_version": "<x.y.z>",
     "dependencies": {"<package>": "<version>"}
   }
   ```
   Use an integer seed or JSON `null` for deterministic code without randomness. Paths are relative to the project root, remain inside it and must exist: script under `code/`, nonempty inputs, and result outputs under `data/processed/`. The manifest itself is not a result output. Record full package versions (or `{}` for stdlib-only code). For nondeterminism, record its cause under `nondeterminism` and report repeated-run variability.
6. Check the manifest's structure, then check that the run actually reproduces.
   These are two different questions and only the first one is cheap:
   ```bash
   python scripts/verify_story_brief.py --check-manifests --sections "docs/sections/*.md" --registry docs/notes/retrieved-sources.json
   python scripts/rerun_manifest.py --all
   ```
   The first proves the manifest is well formed and its files exist. The second
   re-executes the recorded command and compares the regenerated outputs byte for
   byte against the committed ones. Until it passes, `run:<run-id>` means "a file
   was produced once", not "this result reproduces" — and a result that cannot be
   regenerated cannot be defended to a reviewer.

   The originals are stashed and restored, so the check cannot overwrite results
   the manuscript already cites. It also fails when the run writes anything under
   `data/processed/` that the manifest does not declare — a result nothing names
   cannot be traced, which is the whole point of `run:<run-id>`. Add it to
   `outputs` or stop writing it. If the re-run diverges, do not paper over it:
   either seed the nondeterminism away, or record what varies and why in a
   `nondeterminism` field on the manifest and report the run-to-run spread in the
   Results section. A declared `nondeterminism` makes the difference reportable,
   not invisible.

   Then hand the evidence to `critic` through `paper-supervise`. Results and
   figures may consume it only after this stage is approved.

## Statistical design review

Run this before the experiment, not after the numbers arrive — every item is a
decision the story brief already made, and re-deciding it once you have seen the
result is how a comparison stops meaning anything.

| Check | Why it bites |
|---|---|
| Every reported comparison has a falsifier written in the brief, with its threshold and test named | A threshold chosen after seeing the gap is not a test |
| The test matches the design — paired data gets a paired test, and the pairing is real (same seeds, same splits, same tuning budget across arms) | An unpaired test on paired data throws away the design's own power |
| Repetition count is justified against the effect size the brief claims, not inherited from habit | 10 seeds is a choice; say what it can and cannot detect |
| What varies between repetitions is enumerated (initialization, split, noise draw) and what stays fixed is fixed | A "seed" that also changes the data is two experiments |
| Capacity/tuning parity between arms is measured and recorded, not asserted | "Matched" is a number in the manifest or it is not a fact |
| Every comparison actually run is reported, including the ones that went the wrong way | Reporting the surviving comparison is how a p-value stops meaning what it says |
| Multiple comparisons are counted and handled, or the family is declared and the count reported | Three tests at p<0.05 is not one test at p<0.05 |
| The metric, its units, and the target it is scored against (noisy or clean) are identical across arms and stated | Two arms scored differently are not compared |
| Held-out data was held out before tuning, not after | A test set used for selection is a validation set |
| The noise model and its magnitude are recorded in the manifest | A floor you cannot state is a floor you cannot claim to be above |

An item that fails is a `revise` verdict, not a footnote. If the design has
already been run and an item cannot be satisfied retroactively, say so in
Limitations rather than restating the claim more weakly.
