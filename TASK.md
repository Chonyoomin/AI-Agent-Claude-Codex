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

Phase 6B - Structured Durable Memory Storage

## Phase Status

Phase 6A (Durable Memory Contract) is closed after Codex review approval and human progression. Phase 6B is now active as the first implementation slice for Phase 6 durable memory. This sub-phase should implement the structured on-disk durable memory storage layer defined by the Phase 6A contract: category-scoped append-mostly entries with required metadata validation under `.agent-loop/memory/`, while preserving the shipped Phase 5 runtime and deferring retrieval, checkpoint-consumption, and continuation-driving behavior to later 6x slices.

## Active Task

Implement the Phase 6 durable memory storage foundation in code. This slice should create the structured `.agent-loop/memory/` storage surface defined by the Phase 6A contract, enforce the five allowed memory categories and required metadata, preserve append-mostly semantics, and keep all writes scoped to the durable memory layer without enabling retrieval into prompts or checkpoint-driven continuation yet.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6B as active
- `.agent-loop/phase-plan.md` records Phase 6A as closed history and contains a `## Phase 6B - Structured Durable Memory Storage` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the implementation creates a structured durable memory storage layer under `.agent-loop/memory/` with support for the five Phase 6A categories: `decision`, `failure`, `preference`, `summary`, and `checkpoint`
- durable memory writes enforce the required Phase 6A metadata fields and refuse unknown categories or malformed entries fail-closed
- durable memory writes remain append-mostly and never modify canonical task / state artifacts
- no prompt retrieval, checkpoint-consumption, or continuation-driving runtime behavior is enabled in this slice
- focused tests cover valid durable memory writes, invalid category rejection, missing-metadata rejection, append-mostly behavior, and memory-layer write-boundary enforcement
- `README.md` reflects that Phase 6B is active and that structured durable memory storage is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6B until:

- this Phase 6B slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing selective memory retrieval into Claude or Codex prompts
- implementing automatic checkpoint creation during live runs, checkpoint-consumption on resume, token-exhaustion continuation chaining, or any other continuation-driving runtime behavior
- changing current planner, activator, adapter, evidence-collection, review routing, or phase-start prompt-bootstrap behavior beyond the narrow storage-layer implementation needed for future Phase 6 work
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
