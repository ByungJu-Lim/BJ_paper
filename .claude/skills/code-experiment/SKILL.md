---
name: code-experiment
description: Writes and runs experiment/analysis code, producing processed data under data/processed/. Use when the paper needs new experimental or analytical results.
---

# Code and Experiments

## Procedure

1. Delegate to `executor`: write the analysis/experiment code under `code/`, reading only from `data/raw/`.
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
     "random_seed": "<seed, or null if the run is deterministic>",
     "python_version": "<x.y.z>",
     "dependencies": {"<package>": "<version>"}
   }
   ```
   Fix every random seed explicitly rather than relying on a library default. If a result cannot be made deterministic (hardware timing, external service), say so in the manifest under `"nondeterminism"` and report the spread across repeated runs instead of a single number.
5. Hand off the code, the manifest, and a summary of what it produced to `critic` through the `paper-supervise` loop before `results-discussion` or `figures-tables` consume the output.
