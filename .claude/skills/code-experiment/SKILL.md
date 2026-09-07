---
name: code-experiment
description: Writes and runs experiment/analysis code, producing processed data under data/processed/. Use when the paper needs new experimental or analytical results.
---

# Code and Experiments

## Procedure

1. Read the approved story brief and ensure every planned experiment can test a written falsifier. Run `python scripts/verify_story_brief.py --require-slots Context,Gap,Question,Approach --sections "docs/sections/*.md" --registry docs/notes/retrieved-sources.json` before execution. Commit the approved pre-experiment brief to preserve when the falsifiers were recorded. Delegate code under `code/`, reading only from `data/raw/`.
2. Run the code and write its output to `data/processed/` — never modify files under `data/raw/`.
3. Record what the code does and how to re-run it in a comment header at the top of the relevant file under `code/`.
4. Write a run manifest next to the output as `data/processed/<run-id>.manifest.json`. Reviewers and the Methods section both depend on it, and a result that cannot be regenerated cannot be defended:
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
5. Run `python scripts/verify_story_brief.py --check-manifests --sections "docs/sections/*.md" --registry docs/notes/retrieved-sources.json`. This checks structure and files, not scientific validity. Re-run the recorded command when verifying reproducibility, compare its results, then hand the evidence to `critic` through `paper-supervise`. Results/figures may consume it only after this stage is approved.
