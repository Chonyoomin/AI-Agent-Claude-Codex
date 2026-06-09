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

Phase 6A - Durable Memory Contract

## Phase Status

Phase 5F (Automatic Phase-Start Claude Prompt Bootstrap) is closed and approved for human review. Phase 6A is now active as the first slice for durable memory and continuation support. This sub-phase should define the durable memory contract before implementation: what belongs in memory versus canonical task/state artifacts, how checkpoint/resume data is structured, how selective retrieval works, and how interruption recovery must preserve the existing safety and approval boundaries. The goal is to establish a precise contract for memory and continuation behavior before any Phase 6 runtime or storage implementation begins.

## Active Task

Define the Phase 6 durable memory contract in `.agent-loop/phase-plan.md`. This slice should specify canonical-vs-memory ownership, durable memory categories, checkpoint/resume rules, token-exhaustion continuation handling, selective retrieval boundaries, refusal behavior, and the allowed future write surfaces for Phase 6 implementation work.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 6 / 6A as active
- `.agent-loop/phase-plan.md` marks Phase 5F complete history and contains a `## Phase 6A - Durable Memory Contract` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the Phase 6A contract specifies what counts as durable memory versus canonical task / loop-state artifacts
- the contract defines durable memory categories and storage shape for future implementation, including decisions, failures, preferences, summaries, and checkpoint state
- the contract defines checkpoint/resume and token-exhaustion continuation behavior without implementing it yet
- the contract defines selective retrieval rules so memory augments prompts without becoming a competing source of truth
- the contract preserves the shipped review, strict, autonomous, reconciliation, and phase-start prompt behavior from Phases 5B through 5F unchanged in effect
- `README.md` reflects that Phase 6A is active and that durable memory contract definition is now the implementation focus

## Next-Phase Gate

Do not start the next 6x sub-phase after Phase 6A until:

- this Phase 6A slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current Phase 5D runtime behavior
- implementing durable memory storage, checkpoint files, retrieval pipelines, or continuation chaining runtime behavior in code during this contract slice
- changing current planner, activator, adapter, evidence-collection, review routing, or phase-start prompt-bootstrap behavior beyond contract-definition wording for future Phase 6 work
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
