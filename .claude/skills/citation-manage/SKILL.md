---
name: citation-manage
description: Cross-checks every citation used in the draft against the retrieved-sources registry before allowing it into refs/references.bib. Use before finalizing citations, never to hand-author bibliography entries.
---

# Citation Management

## Hard rule

A citation may enter `refs/references.bib` **only if** its key already exists in `docs/notes/retrieved-sources.json`. This is a deterministic check, not a judgment call — run the script, don't eyeball it.

`verify_citations.py` enforces four invariants, and all four must be clean:

| | Invariant | What it stops |
|---|---|---|
| A | every citation key in a section is registered | invented in-text citations |
| B | every BibTeX entry is registered | a fabricated entry appended straight to the `.bib` |
| C | every citation key in a section has a BibTeX entry | dangling citations that render as `[?]` |
| D | bibliography title, ordered full authors, year, DOI and venue match verified registry metadata | fabricated fields under a real key |

Narrative `@key`, bracketed `[@key]`, and suppressed-author `-@key` citations are checked. Code, HTML comments, escaped at-signs, and email addresses are ignored. Section globs are expanded by the script on both PowerShell and Bash.

## Procedure

1. Validate the registry first. Online verification is mandatory for every entry carrying a DOI — it resolves the DOI, matches the title, full ordered author names, year, and venue, and screens the work for retractions:
   ```bash
   python scripts/verify_source_registry.py --registry docs/notes/retrieved-sources.json --online
   ```
2. Run:
   ```bash
   python scripts/verify_citations.py --state .omc/paper-state.md --registry docs/notes/retrieved-sources.json --sections "docs/sections/*.md" --bib refs/references.bib
   ```
3. For every verified key (present in both the sections and the registry), add one BibTeX entry to `refs/references.bib` using only verified registry metadata. The registry stores `authors` as a complete ordered list of names, `year` as a four-digit integer, and `venue` for journal/conference/preprint sources. Populate BibTeX `title`, `author`, `year`, and `doi` when registered; map `venue` to `journal`, `booktitle`, `publisher`, or `institution` as appropriate. Full names may use `Given Family` or `Family, Given` syntax; initials or abbreviations require reconciliation with the registry. Do not infer missing authors, years, venues, or identifiers.
4. For every key reported as unverified, or every source whose metadata validation fails: do **not** add it to `refs/references.bib`. Record it under `rejected-citations` in `.omc/paper-state.md` with the exact reason, then either run `lit-review` to verify the real source or remove the citation.
5. After editing, run the same command **without `--state`** to require complete bibliography coverage before review. CI uses `--state` and defers only missing entries while this stage is not yet ready for review; unknown citation keys and invalid existing BibTeX entries always fail. Invariants B, C and D must hold before this stage reaches `awaiting-review`.
6. Update `verified-sources` in `.omc/paper-state.md` to the count of keys now in `refs/references.bib`. `check_paper_state.py` rejects this stage if it is approved while `verified-sources` is still 0.
7. Delegate review of this stage's outcome to `verifier`, per the `paper-supervise` loop.
8. After verifier passes, stop for the **citations-finalized user gate** before treating this stage as approved.
