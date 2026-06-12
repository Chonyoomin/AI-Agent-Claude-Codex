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

Phase 6F - Token Exhaustion Continuation Initial Slice

## Phase Status

Phase 6E (Checkpoint Resume Initial Slice) is closed after Codex review approval and human progression. Phase 6F is now active as the next implementation slice for Phase 6 durable memory. This sub-phase should implement the first token-exhaustion continuation runtime on top of the shipped checkpoint-resume layer: classify token or context exhaustion as an interrupted-run state, persist the required checkpoint continuation metadata, and allow bounded continuation through explicit resume handling while still deferring automatic continuation chaining and broader memory distillation behavior.

## Active Task

Implement the Phase 6 token-exhaustion continuation foundation in code. This slice should treat token or context exhaustion as a resumable interruption, persist and consume the required checkpoint continuation state, enforce bounded continuation attempts, preserve existing Phase 5 approval-mode and strict-gate semantics, and still defer automatic continuation chaining or broader memory distillation behavior.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6F as active
- `.agent-loop/phase-plan.md` records Phase 6E as closed history and contains a `## Phase 6F - Token Exhaustion Continuation Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the implementation classifies token or context exhaustion as an interrupted-run state rather than silent success
- token-exhaustion continuation persists and consumes checkpoint state using the shipped Phase 6D/6E checkpoint surfaces
- bounded continuation attempts are enforced for the active checkpoint and refused fail-closed when exhausted, stale, contradictory, or malformed
- the continuation path preserves the shipped Phase 5 approval-mode and strict-gate routing semantics and does not widen autonomy or bypass human gates
- no automatic continuation chaining or other background continuation behavior is enabled in this slice
- focused tests cover token-exhaustion interruption handling, bounded continuation-budget enforcement, valid continuation resume, exhausted-budget refusal, and preservation of canonical-artifact precedence
- `README.md` reflects that Phase 6F is active and that token-exhaustion continuation handling is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6F until:

- this Phase 6F slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing automatic continuation chaining or any other background continuation-driving runtime behavior beyond the narrow explicit continuation path needed for token-exhaustion recovery
- implementing phase-boundary memory distillation or repeated-failure memory synthesis beyond the narrow token-exhaustion continuation helpers needed for this slice
- changing current planner, activator, adapter, evidence-collection, review routing, or phase-start prompt-bootstrap behavior beyond the narrow token-exhaustion continuation implementation needed for future Phase 6 work
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
