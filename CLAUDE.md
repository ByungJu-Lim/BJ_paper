# Paper Project

> Fill in the four fields below when you start a new paper from this template.

- **Working title:** _fill in_
- **Target venue:** _fill in (journal/conference)_
- **Field:** Engineering / Energy (experiments, process analysis, AI design)
- **Language:** English

## Workflow

This project is driven by `.omc/paper-state.md` and the skills under `.claude/skills/`. Do not skip stages or hand-write `refs/references.bib` directly.

Stage order:
1. `lit-review` — search and register real sources
2. `novelty-check` — compare claims against registered sources
3. `outline-draft` — outline, then section drafts
4. `results-discussion` + `code-experiment` + `figures-tables` — can run in any order once `code/` produces `data/processed/`
5. `citation-manage` — cross-check every citation against the registry before touching `refs/references.bib`
6. `polish-review` — final full-draft pass

Run `paper-supervise` to find out which stage is next, or to resume after a break — it reads `.omc/paper-state.md` and tells you what to do.

## Hard rules

- Never add a citation to `refs/references.bib` unless its key exists in `docs/notes/retrieved-sources.json`. Run `python scripts/verify_citations.py --registry docs/notes/retrieved-sources.json --sections docs/sections/*.md` before finalizing citations.
- Each stage gets at most 3 generate→review rounds. On the 4th failed review, stop and report to the user — do not keep retrying and do not auto-approve.
- Always stop for explicit user approval at: outline complete, each section draft complete, citations finalized, final polish — even if the reviewing agent already approved.
- All agent delegation reuses the existing OMC agents (`scientist`, `writer`, `executor`, `critic`, `verifier`). Do not invent new subagents for this project.
