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

Phase 9B - PRD Intake And Decomposition

## Phase Status

Phase 9A (Autonomous Mode Contract And Safety Policy) is closed after Codex review approval and human progression. Phase 9B is now active as the first implementation slice under the approved Phase 9 contract. This sub-phase should accept a structured PRD or looser product brief, normalize it into a canonical intake/decomposition surface, and derive bounded internal phases, tasks, risks, and acceptance criteria while preserving the shipped planner, activation, approval, and artifact-truth boundaries.

## Active Task

Implement the PRD Intake And Decomposition slice for the agent loop. This slice should accept a structured PRD or looser product brief, normalize it into a canonical autonomous-run intake surface, and decompose it into bounded internal phases, tasks, risks, and acceptance criteria while preserving the existing planner, activation, approval, and artifact-truth boundaries.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 9 / 9B as active
- `.agent-loop/phase-plan.md` records Phase 9A as closed history and contains a `## Phase 9B - PRD Intake And Decomposition` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository ships a canonical PRD-intake and decomposition surface that accepts both structured PRDs and looser product briefs without requiring prior chat context
- the intake/decomposition layer emits bounded internal phases, tasks, risks, and acceptance criteria that fit the shipped phase/task model rather than inventing a parallel control plane
- the new surface preserves the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, and repo-artifact source-of-truth model
- focused validation proves malformed or underspecified PRD input is refused cleanly and valid intake/decomposition output remains bounded and auditable from repo artifacts
- `README.md` reflects that Phase 9B is active and that PRD intake / decomposition are now the implementation focus

## Next-Phase Gate

Do not start the next 9x sub-phase after Phase 9B until:

- this Phase 9B slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- orchestrator-driven prompt handoff, autonomous review/fix execution, automatic next-phase activation, long-run completion heuristics, capacity-halt re-probe, or final acceptance automation (Phases 9C-9G)
- any PRD intake/decomposition behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation instead of composing with it
- any new runtime, review-routing, checkpoint, continuation, memory, runtime-adapter, LangChain, or VS Code feature work unrelated to the narrow intake/decomposition slice
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
- adding any project-wide CI suite to the repository beyond focused intake/decomposition coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
