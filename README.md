# Paper-Writing Agent Template

A Claude Code project template for writing English-language engineering/energy research papers (experiments, process analysis, AI design), built to be reused across papers via Gitea's Template Repository feature.

## Quick start for a new paper

1. On your Gitea instance, open this repository → **Settings** → enable **"Template Repository"** (one-time setup on this repo, not per paper).
2. For each new paper: this repo's page → **"Use this template"** → create a new, independent repository. No submodule or symlink dependency is created — the new repo is fully standalone.
3. Clone the new repo and fill in the 4 fields at the top of `CLAUDE.md` (working title, target venue, field, language).
4. Ask Claude Code to run the `paper-supervise` skill — it reads `.omc/paper-state.md` and tells you which stage to start on.

## Skills

| Skill | Purpose |
|---|---|
| `paper-supervise` | Orchestrates the whole pipeline; run this first and after every break |
| `lit-review` | Searches and registers real sources into `docs/notes/retrieved-sources.json` |
| `novelty-check` | Compares claims to prior work; flags self-redundancy |
| `outline-draft` | Outline, then section-by-section drafting |
| `results-discussion` | Analyzes `data/processed/` and writes Results + Discussion |
| `code-experiment` | Writes/runs experiment and analysis code |
| `figures-tables` | Generates figures and tables from processed data |
| `citation-manage` | The only path that may write to `refs/references.bib` |
| `polish-review` | Final full-draft pass before calling the paper done |

## Scripts

Dependency-free Python 3.10+ (stdlib only). Run tests with:
```bash
python -m unittest discover -s tests -v
```

- `scripts/verify_citations.py` — enforces that every citation key used in `docs/sections/*.md` exists in `docs/notes/retrieved-sources.json` before it can enter `refs/references.bib`.
- `scripts/check_paper_state.py` — validates `.omc/paper-state.md` (valid statuses, round format, and that no stage silently exceeds 3 review rounds without escalating).

## Design rationale

See `docs/superpowers/specs/2026-06-25-paper-writing-agent-template-design.md` for the full design (architecture decision, citation-hallucination defenses, novelty-check pipeline, and sources).
