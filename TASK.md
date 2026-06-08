# TASK.md

## Human Objective

Build the Agentic AI Coding Loop project from start to finish as a phase-gated local orchestration system where:

- Codex plans the work, updates task state, reviews implementation, and generates fix prompts
- Claude Code implements only the active phase
- the local orchestrator captures evidence and enforces loop state
- each phase stops for human approval before the next phase begins
- the system never auto-commits or auto-pushes

## Project Intent

The goal is to let a human provide the desired outcome once, then have the Codex and Claude loop carry the project forward phase by phase with review, fixes, and human gating between phases.

## Active Phase

Phase 5 - Approval Modes

## Active Sub-Phase

Phase 5F - Automatic Phase-Start Claude Prompt Bootstrap

## Phase Status

Phase 5E (Post-Review Artifact Reconciliation) is closed and approved for human review. Phase 5F is now active as the next implementation slice for Phase 5. This sub-phase should implement automatic phase-start Claude prompt bootstrap so Codex can synthesize `.agent-loop/claude-prompt.md` directly from the newly activated phase/task artifacts while refusing if the phase definition is incomplete, inconsistent, or not safe to hand off. The goal is to remove the remaining manual prompt-bootstrap step between phase activation and Claude implementation without weakening the existing review, ownership, or safety boundaries.

## Active Task

Implement automatic phase-start Claude prompt bootstrap in `scripts/agent_loop.py`. This slice should synthesize `.agent-loop/claude-prompt.md` from the active phase/task artifacts at the start of a newly activated sub-phase, validate that the required source artifacts are complete and mutually consistent, refuse/stop on incomplete or contradictory phase definitions, and preserve the existing Claude fix-prompt path from Phase 5E unchanged.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 5 / 5F as active
- `.agent-loop/phase-plan.md` marks Phase 5E complete history and contains a `## Phase 5F - Automatic Phase-Start Claude Prompt Bootstrap` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` can synthesize `.agent-loop/claude-prompt.md` from the active phase/task artifacts for a newly activated phase-start handoff
- automatic prompt bootstrap validates that the required source artifacts are present, ordered, non-empty where required, and mutually consistent before writing a Claude implementation prompt
- prompt bootstrap refuses/halts instead of guessing when the phase definition is incomplete, contradictory, or would produce an unsafe / stale implementation handoff
- the shipped post-review reconciliation behavior from Phase 5E remains intact, including Claude-owned `.agent-loop/fix-prompt.md` generation on `NEEDS_FIXES`
- the shipped `review`, `strict`, and `autonomous` runtime behavior from Phases 5B, 5C, and 5D remain unchanged in effect
- focused tests cover successful phase-start prompt generation, refusal on incomplete/inconsistent source artifacts, preservation of the existing fix-prompt path, and non-regression of the shipped approval-mode paths
- `README.md` reflects that Phase 5F is active and that automatic phase-start Claude prompt bootstrap is now the implementation focus

## Next-Phase Gate

Do not start the next 5x sub-phase after Phase 5F until:

- this Phase 5F slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- changing current planner, activator, adapter, or evidence-collection behavior beyond the narrow phase-start prompt-bootstrap logic and its interaction with the shipped approval-mode runtime state
- durable memory, token-reset continuation, checkpoint-resume logic, and continuation chaining (Phase 6)
- editor integration (Phase 7)
- MCP support (future)
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- any change to `AGENTS.md` or `CLAUDE.md`
- adding any project-wide CI suite to the repository beyond focused approval-mode coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
