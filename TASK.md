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

Phase 6D - Checkpoint Artifact Storage Initial Slice

## Phase Status

Phase 6C (Selective Memory Retrieval Initial Slice) is closed after Codex review approval and human progression. Phase 6D is now active as the next implementation slice for Phase 6 durable memory. This sub-phase should implement durable checkpoint artifact storage on top of the Phase 6A contract and the shipped 6B/6C memory layer: structured checkpoint entries and checkpoint file organization for interrupted Claude/Codex runs, while still deferring resume-path consumption, token-exhaustion continuation chaining, and any automatic continuation behavior.

## Active Task

Implement the Phase 6 checkpoint artifact storage foundation in code. This slice should create structured checkpoint artifacts for interrupted Claude/Codex work, validate them against the Phase 6A checkpoint contract, keep checkpoint writes scoped to dedicated checkpoint storage, and preserve the shipped Phase 5 runtime by deferring checkpoint consumption on resume and token-exhaustion continuation behavior to later 6x slices.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6D as active
- `.agent-loop/phase-plan.md` records Phase 6C as closed history and contains a `## Phase 6D - Checkpoint Artifact Storage Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the implementation creates structured checkpoint artifact storage for interrupted Claude/Codex work under dedicated Phase 6 checkpoint paths
- checkpoint writes enforce the required Phase 6A checkpoint metadata and refuse malformed or out-of-scope checkpoint records fail-closed
- checkpoint artifacts remain additive and never mutate canonical task / state artifacts
- no normal runtime path consumes checkpoint artifacts for resume or token-exhaustion continuation in this slice
- focused tests cover valid checkpoint writes, malformed-checkpoint refusal, checkpoint write-boundary enforcement, and preservation of canonical-artifact precedence
- `README.md` reflects that Phase 6D is active and that checkpoint artifact storage is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6D until:

- this Phase 6D slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing checkpoint-consumption on resume, token-exhaustion continuation chaining, or any other continuation-driving runtime behavior
- implementing phase-boundary memory distillation or repeated-failure memory synthesis beyond the narrow checkpoint storage helpers needed for this slice
- changing current planner, activator, adapter, evidence-collection, review routing, or phase-start prompt-bootstrap behavior beyond the narrow checkpoint-storage implementation needed for future Phase 6 work
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
