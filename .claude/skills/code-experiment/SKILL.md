---
name: code-experiment
description: Writes and runs experiment/analysis code, producing processed data under data/processed/. Use when the paper needs new experimental or analytical results.
---

# Code and Experiments

## Procedure

1. Delegate to `executor`: write the analysis/experiment code under `code/`, reading only from `data/raw/`.
2. Run the code and write its output to `data/processed/` — never modify files under `data/raw/`.
3. Record what the code does and how to re-run it in a comment header at the top of the relevant file under `code/`.
4. Hand off the code and a summary of what it produced to `critic` through the `paper-supervise` loop before `results-discussion` or `figures-tables` consume the output.
