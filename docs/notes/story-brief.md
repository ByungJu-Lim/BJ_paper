# Story Brief

> Written by the `story-brief` skill before `lit-review`, and revised at every
> later stage. This is a **hypothesis document, not a plan**: when the evidence
> contradicts a line here, the line changes — never the evidence.
>
> Fill the narrative slots as evidence arrives. `Context`, `Gap`, and `Question`
> come first, before any literature search. `Approach` follows the methods.
> `Finding` and `Implication` stay unfilled until `data/processed/` exists.

## Narrative

One sentence per slot. If a slot needs two sentences, the argument is not yet
sharp enough.

| Slot | Sentence |
|---|---|
| Context | _입력 필요_ |
| Gap | _입력 필요_ |
| Question | _입력 필요_ |
| Approach | _입력 필요_ |
| Finding | _입력 필요_ |
| Implication | _입력 필요_ |

## Claims

Every load-bearing statement the paper makes, with what currently backs it.

- `assumed` — believed but not yet backed. **May not be stated as fact in
  Results, Discussion, or Conclusion.**
- `supported` — backed by the listed evidence.
- `refuted` — the evidence went the other way. Rewrite the narrative slot that
  depended on it; the claim stays here as a record.

Evidence entries are comma-separated and take one of three forms:

| Form | Meaning | Checked against |
|---|---|---|
| `@key` | a registered source | `docs/notes/retrieved-sources.json` |
| `run:<run-id>` | an experiment run | `data/processed/<run-id>.manifest.json` |
| `Fig. N` / `Table N` | a figure or table in this paper | the section that renders it |

| ID | Claim | Status | Evidence |
|---|---|---|---|

## Falsifiers

What result would force each claim to be rewritten. Written *before* the
experiment, not after.


## Section coverage

Each section declares the claims it carries with a single comment line placed
directly under its heading:

```markdown
<!-- claims: C1, C3 -->
```

`scripts/verify_story_brief.py` cross-checks those declarations against this
ledger, so a claim cannot quietly drift out of the paper — or into the
conclusion while still `assumed`.

Written prose requires exactly one nonempty declaration. Empty template headings
and HTML drafting notes are allowed before drafting, but not at final review.
The critic must also compare actual prose with its declarations; structural
checks cannot prove that the scientific argument is sound.

## Evidence format

Source evidence requires a readable registry containing the key. A run requires
`data/processed/<run-id>.manifest.json` with matching `run_id`, an existing `code/`
script, command, integer or null `random_seed`, Python/package versions, and
nonempty lists of existing project-relative input and processed output files.
An empty or malformed manifest is not evidence. The checker does not execute it;
the experiment review must verify reproducibility separately.

Figure and table evidence refers to a caption immediately followed by its object
in a manuscript section. Caption labels are unique across the manuscript. For a
section under `docs/sections/`, use:

```markdown
Fig. 1: Measured efficiency
![Measured efficiency](../../figures/fig1.png)

Table 1: Comparison
| Method | Efficiency |
|---|---|
| Baseline | 0.8 |
```

The image must be a nonempty local file inside the project; the table must have
a header, separator and data row. Mentioning `Fig. 1` in prose is insufficient.
Every written claim needs a written falsifier, including `assumed` claims. Keep
the approved pre-experiment version in Git; the validator cannot prove when a
falsifier was written. A written `Finding` needs run evidence in the claims ledger.

Use `--state .omc/paper-state.md` to apply requirements for approved stages,
`--check-manifests` after experiments, and `--require-slots all --require-coverage`
at final review. Run these checks from the project root.
