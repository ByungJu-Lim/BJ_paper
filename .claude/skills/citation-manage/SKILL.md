---
name: citation-manage
description: Cross-checks every citation used in the draft against the retrieved-sources registry before allowing it into refs/references.bib. Use before finalizing citations, never to hand-author bibliography entries.
---

# Citation Management

## Hard rule

A citation may enter `refs/references.bib` **only if** its key already exists in `docs/notes/retrieved-sources.json`. This is a deterministic check, not a judgment call — run the script, don't eyeball it.

## Procedure

1. Validate the registry first. For journal and conference sources, online verification is mandatory:
   ```bash
   python scripts/verify_source_registry.py --registry docs/notes/retrieved-sources.json --online
   ```
2. Run:
   ```bash
   python scripts/verify_citations.py --registry docs/notes/retrieved-sources.json --sections docs/sections/*.md
   ```
3. For every verified key (present in both the sections and the registry), add one BibTeX entry to `refs/references.bib` using only verified registry metadata. Do not infer missing authors, years, venues, or identifiers.
4. For every key reported as unverified, or every source whose metadata validation fails: do **not** add it to `refs/references.bib`. Record it under `rejected-citations` in `.omc/paper-state.md` with the exact reason, then either run `lit-review` to verify the real source or remove the citation.
5. Update `verified-sources` in `.omc/paper-state.md` to the count of keys now in `refs/references.bib`.
6. Stop for the **citations-finalized user gate** before treating this stage as done.
7. Delegate review of this stage's outcome to `verifier`, per the `paper-supervise` loop.
