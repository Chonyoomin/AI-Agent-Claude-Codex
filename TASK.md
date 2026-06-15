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

Phase 9 - Fully Autonomous PRD-To-Product Mode

## Active Sub-Phase

Phase 9A - Autonomous Mode Contract And Safety Policy

## Phase Status

Phase 8C (Final README Alignment And Clean-Clone Polish) is closed after Codex review approval and human progression. Phase 9A is now active as the first Phase 9 slice. This sub-phase should define the contract and safety policy for a future selectable fully autonomous PRD-to-product mode while preserving the shipped runtime behavior and avoiding any premature autonomous execution implementation.

## Active Task

Implement the Autonomous Mode Contract And Safety Policy slice for the agent loop. This slice should define what the future fully autonomous PRD-to-product mode is allowed to do, what still requires explicit human approval, how the mode remains auditable from repo artifacts, and which safety boundaries and hard stops are preserved, without yet implementing orchestrator-driven autonomous PRD execution.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 9 / 9A as active
- `.agent-loop/phase-plan.md` records Phase 8C as closed history and contains a `## Phase 9A - Autonomous Mode Contract And Safety Policy` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository defines a concrete contract for the future fully autonomous PRD-to-product mode, including allowed actions, preserved hard stops, audit expectations, and explicit human-approval boundaries
- the contract stays aligned with the shipped CLI-first workflow, artifact ownership model, halt/refusal vocabulary, checkpoint/resume behavior, and repo-artifact source-of-truth model
- the contract distinguishes future autonomous-mode behavior from currently shipped Phase 5 bounded `autonomous` behavior instead of collapsing them together
- focused validation or review coverage proves the new contract/docs match the actual repo state and do not claim unimplemented autonomous execution behavior
- `README.md` reflects that Phase 9A is active and that the autonomy contract / safety-policy definition is now the implementation focus

## Next-Phase Gate

Do not start the next 9x sub-phase after Phase 9A until:

- this Phase 9A slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- any implementation of orchestrator-driven fully autonomous PRD execution before the contract is approved
- any new runtime, planner, activator, evidence-collection, review-routing, checkpoint, continuation, memory, runtime-adapter, LangChain, or VS Code feature work beyond the narrow contract/planning slice
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing behavior the repo does not currently ship just to simplify the docs
- collapsing future roadmap items into present-tense product behavior
- MCP support, external UI, concurrent-agent operation, or implementation of fully autonomous PRD-to-product execution (future phases)
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite to the repository beyond focused doc-alignment coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
