# Pipeline validation run 1 — archived paper content

This folder is a **snapshot** of the paper content produced while exercising
the pipeline described in the project's `CLAUDE.md`, taken after
`polish-review` was approved and a fixture submission attempt (`01-jpvs`,
"Journal of Pipeline Verification Studies" — not a real journal) was opened
and frozen at tag `submission/01-jpvs/v1`.

It is kept for reference only. The live repository (`docs/`, `data/`,
`code/`, `figures/`, `refs/`, `submissions/`, `.omc/paper-state.md`) has been
reset to a fresh template state via `scripts/reset_paper.py --confirm
--template-repo` so a new paper can start from `story-brief` without
inheriting this run's claims, sources, or state.

Layout mirrors the live repository at archive time:

- `docs/notes/`, `docs/sections/`, `docs/outline.md` — story brief, novelty
  matrix, topic note, and the six drafted sections
- `data/raw/`, `data/processed/` — the frozen experiment config and its
  run manifest/output (reproduces byte-for-byte via
  `scripts/rerun_manifest.py` if replayed against the matching
  `code/fouling_benchmark.py`)
- `code/` — the experiment and plotting scripts used for this run
- `figures/`, `refs/references.bib` — rendered figures/table and the
  12-entry bibliography
- `submissions/` — the fixture attempt `01-jpvs` and the submission log
  at archive time
- `paper-state-final.md` — `.omc/paper-state.md` as it stood before reset
  (every stage through `polish-review` approved)

See `docs/notes/pipeline-findings.md` in the live repository for what this
run found wrong with the pipeline itself.
