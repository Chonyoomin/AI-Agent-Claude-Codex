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

Phase 6 - Durable Memory and Optional Context Layer

## Active Sub-Phase

Phase 6E - Checkpoint Resume Initial Slice

## Phase Status

Phase 6D (Checkpoint Artifact Storage Initial Slice) is closed after Codex review approval and human progression. Phase 6E is now active as the next implementation slice for Phase 6 durable memory. This sub-phase should implement initial checkpoint consumption on `resume`: validate and read stored checkpoint artifacts during resume handling, refuse stale or contradictory checkpoint context fail-closed, and preserve existing Phase 5 strict-gate semantics while still deferring token-exhaustion continuation chaining and any automatic continuation behavior.

## Active Task

Implement the Phase 6 checkpoint resume foundation in code. This slice should consume and validate stored checkpoint artifacts during resume handling, compare checkpoint context against canonical loop state, preserve existing Phase 5 strict-gate routing semantics, and refuse stale or contradictory checkpoints fail-closed while still deferring token-exhaustion continuation chaining and any automatic continuation behavior.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6E as active
- `.agent-loop/phase-plan.md` records Phase 6D as closed history and contains a `## Phase 6E - Checkpoint Resume Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the implementation consumes stored checkpoint artifacts during `resume` handling using the Phase 6D checkpoint storage layer
- resume-path checkpoint handling validates checkpoint context against canonical loop state and refuses stale, contradictory, or malformed checkpoint records fail-closed
- checkpoint consumption preserves the shipped Phase 5 strict-gate routing semantics and does not widen autonomy or bypass human gates
- no token-exhaustion continuation chaining or other automatic continuation behavior is enabled in this slice
- focused tests cover valid checkpoint-backed resume handling, stale-checkpoint refusal, contradictory-context refusal, malformed-checkpoint refusal, and preservation of canonical-artifact precedence
- `README.md` reflects that Phase 6E is active and that checkpoint-backed resume handling is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6E until:

- this Phase 6E slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing token-exhaustion continuation chaining or any other automatic continuation-driving runtime behavior beyond explicit `resume`
- implementing phase-boundary memory distillation or repeated-failure memory synthesis beyond the narrow checkpoint-resume helpers needed for this slice
- changing current planner, activator, adapter, evidence-collection, review routing, or phase-start prompt-bootstrap behavior beyond the narrow checkpoint-resume implementation needed for future Phase 6 work
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
