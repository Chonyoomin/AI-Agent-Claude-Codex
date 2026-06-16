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

Phase 9C - Orchestrator-Driven Prompt Handoff

## Phase Status

Phase 9B (PRD Intake And Decomposition) is closed after Codex review approval and human progression. Phase 9C is now active as the next implementation slice under the approved Phase 9 contract. This sub-phase should remove manual prompt transfer by letting the orchestrator drive Codex/Claude prompt handoff from canonical repo artifacts while preserving the shipped planner, activation, review-ownership, and artifact-truth boundaries.

## Active Task

Implement the Orchestrator-Driven Prompt Handoff slice for the agent loop. This slice should let the orchestrator dispatch the active Codex/Claude prompt handoff from canonical prompt artifacts and capture the resulting handoff audit trail without requiring manual copy/paste, while preserving the shipped planner/activation boundary, review ownership model, and per-phase human gate.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 9 / 9C as active
- `.agent-loop/phase-plan.md` records Phase 9B as closed history and contains a `## Phase 9C - Orchestrator-Driven Prompt Handoff` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository ships an orchestrator-driven prompt-handoff surface that can dispatch the active Codex/Claude prompt cycle from canonical prompt artifacts without manual copy/paste
- the handoff layer preserves the shipped prompt/source-of-truth boundary: canonical prompt artifacts remain on disk, `.agent-loop/claude-done.json` remains a routing signal, and the handoff does not replace the review/fix artifact model with transient runtime-only state
- the new surface preserves the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, and repo-artifact source-of-truth model
- focused validation proves missing or malformed prompt artifacts are refused cleanly and successful handoff paths are auditable from repo artifacts and logs
- `README.md` reflects that Phase 9C is active and that orchestrator-driven prompt handoff is now the implementation focus

## Next-Phase Gate

Do not start the next 9x sub-phase after Phase 9C until:

- this Phase 9C slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- autonomous review/fix execution, automatic next-phase activation, long-run completion heuristics, capacity-halt re-probe, or final acceptance automation (Phases 9D-9G)
- any prompt-handoff behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation, or that replaces canonical prompt artifacts with transient runtime-only state
- any new runtime, checkpoint, continuation, memory, runtime-adapter, LangChain, or VS Code feature work unrelated to the narrow prompt-handoff slice
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 9 roadmap items into this slice
- MCP support, external UI, concurrent-agent operation, or implementation of end-to-end fully autonomous PRD-to-product execution (future phases)
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite to the repository beyond focused handoff coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
