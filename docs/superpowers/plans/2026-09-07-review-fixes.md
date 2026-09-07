# Project review corrections

Scope: repair the full-project review findings without changing research content,
inventing approvals, submitting a manuscript, or adding dependencies.

## Implementation and verification plan

1. Add failing regression cases for invented evidence, missing claim declarations,
   unwritten falsifiers, unbracketed citations, invalid approvals, submission
   revision history, unsafe figure paths, and PowerShell wildcard arguments.
2. Repair the story/evidence validator, citation and metadata contract, workflow
   state validator, and submission validator in separately owned changes.
3. Align the active skills, README, template files, and CI with those contracts.
   Historical design documents remain historical and point to the current rules.
4. Run targeted tests, the complete unittest suite, all offline validation CLIs,
   Python compile checks, and git diff checks. Review the integrated changes
   independently before declaring completion.

## Acceptance criteria

- Empty template scaffolding remains valid, but populated sections and claims
  cannot silently omit declarations or falsifiers.
- Evidence resolves to registered sources, valid reproducibility manifests and
  real section figures/tables; missing inputs fail with an actionable error.
- Citation checks cover narrative and bracketed forms and use recorded metadata.
- Review state cannot claim approval without a passing review and prerequisites.
- Each submitted revision has an immutable, traceable version; figure paths stay
  inside the attempt's figures directory.
- The documented commands work with both shell-expanded and literal globs.
- Validation checks structural consistency. Whether evidence supports a claim,
  a source was actually read, or human consent occurred remains an explicit
  review responsibility and is not represented as mechanically proven.

## Ownership

- Primary agent: shared validation helpers, story validator/tests, README,
  CLAUDE.md, story/outline/experiment/figure/polish skills, CI and integration.
- State lane: state validator/tests, state template and supervisor skill.
- Citation lane: citation/source/search validators/tests and citation/literature skills.
- Submission lane: submission validator/tests, submission artifacts and skill.

Independent review is performed after implementation; reviewers do not author
the changes they approve.

## Completion evidence (2026-09-07)

- Implemented the eight reported fixes and the falsifier/documentation corrections.
- Regression suite: 190 tests run, 189 passed, one Windows symlink-privilege skip.
- Ran the state, state-aware story, source registry, submission preflight,
  state-aware citation and strict citation CLIs against the shipped template.
  All passed. Python compileall and the repository-configured git diff whitespace
  check passed as well.
- CI now declares Windows/Ubuntu and Python 3.10/3.14; this session ran locally
  on Windows/Python 3.14. Remote CI and live DOI services were not exercised.
- Independent code review initially found indented prose could hide citations;
  fixed it and added paragraph/list and end-to-end CLI regressions. Re-review:
  APPROVE, 32 targeted tests passed.
- Independent architecture review found preflight, review ordering and
  intermediate-draft CI gaps. All three were implemented and regression-tested.
  Its final re-review failed because the workspace ran out of credits; final
  independent architectural clearance is therefore unavailable, not implied.
- No manuscript content, source records, external submissions, remote pushes,
  or real repository tags were created. Changes remain in the working tree.

Structural validation does not establish scientific support, actual human
approval, or reproducibility by itself; the active skills retain explicit review
responsibilities for these.
