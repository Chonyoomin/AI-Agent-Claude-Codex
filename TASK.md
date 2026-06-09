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

Phase 6C - Selective Memory Retrieval Initial Slice

## Phase Status

Phase 6B (Structured Durable Memory Storage) is closed after Codex review approval and human progression. Phase 6C is now active as the next implementation slice for Phase 6 durable memory. This sub-phase should implement selective memory retrieval on top of the Phase 6A contract and the shipped 6B storage layer: bounded, relevance-scoped memory loading for prompt construction that keeps memory advisory-only and never lets it compete with canonical task and loop-state artifacts.

## Active Task

Implement the Phase 6 selective memory retrieval foundation in code. This slice should read durable memory entries from `.agent-loop/memory/`, validate them against the Phase 6A contract and 6B storage schema, select only relevant bounded subsets for the active phase/task, and expose retrieval helpers that can enrich prompt construction without enabling checkpoint-consumption or token-exhaustion continuation behavior yet.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6C as active
- `.agent-loop/phase-plan.md` records Phase 6B as closed history and contains a `## Phase 6C - Selective Memory Retrieval Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the implementation adds a selective memory retrieval surface on top of the shipped `.agent-loop/memory/` storage layer
- retrieval validates memory entries read from disk and refuses malformed, unknown-category, or unrecognized-`signal_version` entries fail-closed
- retrieval limits results to entries relevant to the active `phase`, `sub_phase`, or `task`, with a hard bounded result set rather than unbounded loading
- retrieved memory is explicitly advisory-only and is never allowed to override canonical task / state artifacts, verdicts, halt statuses, or `awaiting_human_for`
- no checkpoint-consumption on resume, token-exhaustion continuation chaining, or automatic continuation behavior is enabled in this slice
- focused tests cover relevant-entry filtering, bounded result limits, malformed-entry refusal, unknown-category refusal, and preservation of canonical-artifact precedence
- `README.md` reflects that Phase 6C is active and that selective memory retrieval is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6C until:

- this Phase 6C slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing automatic checkpoint creation during live runs, checkpoint-consumption on resume, token-exhaustion continuation chaining, or any other continuation-driving runtime behavior
- implementing phase-boundary memory distillation or repeated-failure memory synthesis beyond the narrow retrieval helpers needed for this slice
- changing current planner, activator, adapter, evidence-collection, review routing, or phase-start prompt-bootstrap behavior beyond the narrow retrieval-layer implementation needed for future Phase 6 work
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
