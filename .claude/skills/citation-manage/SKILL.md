---
name: citation-manage
description: Cross-checks every citation used in the draft against the retrieved-sources registry before allowing it into refs/references.bib. Use before finalizing citations, never to hand-author bibliography entries.
---

# Citation Management

## Hard rule

A citation may enter `refs/references.bib` **only if** its key already exists in `docs/notes/retrieved-sources.json`. This is a deterministic check, not a judgment call — run the script, don't eyeball it.

## Procedure

1. Run:
   ```bash
   python scripts/verify_citations.py --registry docs/notes/retrieved-sources.json --sections docs/sections/*.md
   ```
2. For every verified key (present in both the sections and the registry), add one BibTeX entry to `refs/references.bib` using the `title`/`url` fields already stored in `docs/notes/retrieved-sources.json` — do not add fields the registry doesn't have.
3. For every key the script reports as unverified: do **not** add it to `refs/references.bib`. Instead, record it under `rejected-citations` in the `citation-manage` stage of `.omc/paper-state.md` with the reason `"not in retrieved-sources.json"`, and tell the user — either run `lit-review` to register the real source, or remove the citation from the draft.
4. Update `verified-sources` in `.omc/paper-state.md` to the count of keys now in `refs/references.bib`.
5. Stop for the **citations-finalized user gate** before treating this stage as done.
6. Delegate review of this stage's outcome to `verifier`, per the `paper-supervise` loop.
