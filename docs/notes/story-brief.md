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
| C1 | _입력 필요_ | assumed | |

## Falsifiers

What result would force each claim to be rewritten. Written *before* the
experiment, not after.

- **C1:** _입력 필요_

## Section coverage

Each section declares the claims it carries with a single comment line placed
directly under its heading:

```markdown
<!-- claims: C1, C3 -->
```

`scripts/verify_story_brief.py` cross-checks those declarations against this
ledger, so a claim cannot quietly drift out of the paper — or into the
conclusion while still `assumed`.
