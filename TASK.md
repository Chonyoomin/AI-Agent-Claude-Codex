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

Phase 5C - Strict Mode Pauses

## Phase Status

Phase 5B (Review Mode Initial Slice) is closed and approved for human review. Phase 5C is now active as the second implementation slice for Phase 5. This sub-phase should implement the `strict` runtime pause behavior defined in the Phase 5A contract while preserving the shipped `review`-mode baseline and keeping `autonomous` deferred. The goal is to make strict human checkpoints enforceable in runtime state and control flow without broadening autonomy.

## Active Task

Implement the `strict` approval-mode pause behavior in `scripts/agent_loop.py`. This slice should add the strict-mode human gates before new implementation prompt dispatch, before fix-prompt dispatch, and after Claude completion but before Codex review begins; use the Phase 5A `awaiting_human_for` vocabulary to represent those gates; and preserve the shipped `review`-mode behavior and the existing evidence, verdict, and phase-gating flow.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 5 / 5C as active
- `.agent-loop/phase-plan.md` marks Phase 5B complete history and contains a `## Phase 5C - Strict Mode Pauses` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- `scripts/agent_loop.py` implements the `strict`-mode human pauses before implementation prompt dispatch, before fix-prompt dispatch, and after Claude completion but before Codex review begins
- `awaiting_human_for` uses the Phase 5A gate vocabulary for the implemented strict-mode path, including `pre_claude_prompt`, `pre_fix_prompt`, and `halt_resolution` where applicable
- the shipped `review`-mode behavior from Phase 5B remains unchanged in effect
- `.agent-loop/claude-done.json` continues to be a routing/timing artifact only and integrates correctly with the strict pre-review human gate
- focused tests cover strict-mode pause entry, strict-mode resume behavior after human approval, correct `awaiting_human_for` transitions, and non-regression of the shipped `review` path
- `README.md` reflects that Phase 5C is active and that `strict` is implemented while `autonomous` remains deferred

## Next-Phase Gate

Do not start the next 5x sub-phase after Phase 5C until:

- this Phase 5C slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- implementation of `autonomous` mode runtime behavior
- changing current planner, activator, adapter, or evidence-collection behavior beyond the narrow strict-mode pause logic and its interaction with the shipped review-mode runtime state
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
