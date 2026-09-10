"""Synthetic `paper-state.md` fixtures for the test suite.

Tests assert what the *code* does. Reading the live `.omc/paper-state.md` makes
them assert what the *manuscript* currently is instead, so they turn red as the
research advances — and `submission-manage` runs the whole suite as a
pre-submission gate, which means a half-finished draft would block its own
submission for a reason that has nothing to do with the draft.

Build a state here instead. `write_state` produces a file that
`check_paper_state.validate_all` accepts, so a test can pin the exact workflow
position it needs without touching the real one.
"""
from pathlib import Path

try:  # package import when the suite runs from the project root
    from scripts.check_paper_state import REQUIRED_STAGE_IDS, STAGE_DEPENDENCIES
except ImportError:  # direct import when scripts/ is already on the path
    from check_paper_state import REQUIRED_STAGE_IDS, STAGE_DEPENDENCIES

CITATION_STAGE_ID = "citation-manage"

# Round and verdict are not free variables: check_paper_state ties them to the
# status. Keep the mapping here so a fixture cannot drift into an invalid state.
_ROUND_AND_VERDICT = {
    "not-started": ("0/3", ""),
    "in-progress": ("1/3", ""),
    "awaiting-review": ("1/3", ""),
    "awaiting-user": ("1/3", "pass"),
    "approved": ("1/3", "pass"),
    "escalated": ("3/3", "revise"),
}


def build_state(statuses: dict[str, str] | None = None, verified_sources: int | None = None,
                preconditions: dict[str, list[str]] | None = None) -> str:
    """Render a full state file, defaulting every unnamed stage to not-started.

    `verified_sources` defaults to 1 when citation-manage is approved, because
    an approved citation stage that verified nothing is rejected as an accident.

    `preconditions` maps a stage id to entries already spelled "open: ..." or
    "resolved: ...", so a fixture can exercise the malformed case too.
    """
    statuses = dict(statuses or {})
    unknown = sorted(set(statuses) - set(REQUIRED_STAGE_IDS))
    if unknown:
        raise ValueError(f"unknown stage(s): {', '.join(unknown)}")

    citation_status = statuses.get(CITATION_STAGE_ID, "not-started")
    if verified_sources is None:
        verified_sources = 1 if citation_status == "approved" else 0

    blocks = ["# Paper State", ""]
    for stage_id in REQUIRED_STAGE_IDS:
        status = statuses.get(stage_id, "not-started")
        if status not in _ROUND_AND_VERDICT:
            raise ValueError(f"unknown status '{status}' for {stage_id}")
        round_value, verdict = _ROUND_AND_VERDICT[status]
        blocks.append(f"## Stage: {stage_id}")
        blocks.append(f"status: {status}")
        blocks.append(f"round: {round_value}")
        blocks.append(f"last-critic-verdict: {verdict}")
        blocks.append("last-critic-issues:")
        stage_preconditions = (preconditions or {}).get(stage_id, [])
        if stage_preconditions:
            blocks.append("preconditions:")
            blocks.extend(f"- {entry}" for entry in stage_preconditions)
        if stage_id == CITATION_STAGE_ID:
            blocks.append(f"verified-sources: {verified_sources}")
            blocks.append("rejected-citations:")
        blocks.append("")
    return "\n".join(blocks)


def approved_through(stage_id: str) -> dict[str, str]:
    """Every stage up to and including `stage_id`, approved in dependency order."""
    if stage_id not in REQUIRED_STAGE_IDS:
        raise ValueError(f"unknown stage: {stage_id}")
    cutoff = REQUIRED_STAGE_IDS.index(stage_id)
    return {stage: "approved" for stage in REQUIRED_STAGE_IDS[: cutoff + 1]}


def with_stage(stage_id: str, status: str) -> dict[str, str]:
    """`stage_id` at `status`, with everything it depends on approved.

    Approving a stage requires its prerequisites approved, so a fixture that
    only flips one stage produces an invalid state rather than the situation the
    test meant to describe.
    """
    statuses: dict[str, str] = {}
    pending = list(STAGE_DEPENDENCIES.get(stage_id, ()))
    while pending:
        dependency = pending.pop()
        if statuses.get(dependency) == "approved":
            continue
        statuses[dependency] = "approved"
        pending.extend(STAGE_DEPENDENCIES.get(dependency, ()))
    statuses[stage_id] = status
    return statuses


def write_state(path: Path, statuses: dict[str, str] | None = None,
                verified_sources: int | None = None,
                preconditions: dict[str, list[str]] | None = None) -> Path:
    path.write_text(build_state(statuses, verified_sources, preconditions), encoding="utf-8")
    return path
