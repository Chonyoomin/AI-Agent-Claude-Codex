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

Phase 8 - Documentation and Project Polish

## Active Sub-Phase

Phase 8A - Architecture And Usage Docs

## Phase Status

Phase 7C (Status, Reset, And Recovery UX) is closed after Codex review approval and human progression. Phase 8A is now active as the first Phase 8 slice. This sub-phase should explain the end-to-end loop, runtime surfaces, and operator flows from a clean repository clone while preserving the current CLI-first contract, keeping repo artifacts as the source of truth, and avoiding any documentation drift that invents behavior the shipped system does not actually provide.

## Active Task

Implement the Architecture And Usage Docs slice for the agent loop. This slice should document the real shipped workflow from a clean clone, including the end-to-end loop, active CLI/runtime surfaces, artifact ownership model, and practical operator flows, while preserving the current runtime behavior and avoiding any documentation that promises unshipped automation, hidden capabilities, or alternate sources of truth.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 8 / 8A as active
- `.agent-loop/phase-plan.md` records Phase 7C as closed history and contains a `## Phase 8A - Architecture And Usage Docs` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository ships architecture and usage documentation that explains the real end-to-end loop, runtime surfaces, artifact ownership, and operator flows from a clean clone without requiring prior chat context
- documentation stays aligned with the shipped CLI-first workflow, approval semantics, halt/recovery boundaries, and repo-artifact source-of-truth model
- any new docs or doc rewrites distinguish current shipped behavior from future roadmap items instead of collapsing them together
- focused validation or review coverage proves the docs match the actual repo state and do not claim unimplemented behavior
- `README.md` reflects that Phase 8A is active and that architecture/usage documentation is now the implementation focus

## Next-Phase Gate

Do not start the next 8x sub-phase after Phase 8A until:

- this Phase 8A slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any broader autonomy model than the current shipped Phase 5 runtime behavior
- any new runtime, planner, activator, evidence-collection, review-routing, checkpoint, continuation, memory, runtime-adapter, LangChain, or VS Code feature work
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing behavior the repo does not currently ship just to simplify the docs
- collapsing future roadmap items into present-tense product behavior
- MCP support, external UI, concurrent-agent operation, or fully autonomous PRD-to-product mode (future phases)
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite to the repository beyond focused doc-alignment coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
