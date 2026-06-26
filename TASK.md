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

Phase 10 - Future Product Features

## Active Sub-Phase

Phase 10K - Artifact Dashboard Initial Slice

## Phase Status

Phase 10J is complete. Phase 10K is now active as the next mainline slice focused on implementing the first artifact dashboard and run-history views on top of the approved contract while keeping dashboard data advisory.

## Active Task

Implement Phase 10K for the agent loop. This slice should build the first artifact dashboard and run-history views on top of the approved Phase 10J contract while keeping dashboard data advisory and preserving the canonical-artifact-first model.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10K as active
- `.agent-loop/phase-plan.md` records Phase 10J as closed history and contains a `## Phase 10K - Artifact Dashboard Initial Slice` section with concrete objective, done criteria, and exclusions
- the repository implements the first artifact dashboard and run-history views on top of the approved Phase 10J contract
- the dashboard keeps all rendered dashboard data advisory or clearly attributed canonical mirrors; repo artifacts on disk remain authoritative
- the runtime preserves the existing CLI-first workflow, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, controller-vs-target ownership boundaries, and the Phase 4C activator + `APPROVED_FOR_ACTIVATION` gate
- focused validation proves the first dashboard runtime is bounded, consistent with Phase 10G through 10J, and does not widen into concurrency, MCP, or autonomy work

## Next-Phase Gate

Do not treat the external UI dashboard as an unbounded control plane until:

- Phase 10K receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the first dashboard runtime slice
- any advanced dashboard or concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- advanced dashboard capabilities beyond the initial bounded runtime slice
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any external-workspace target dispatch, concurrent Codex/Claude overlap execution, MCP integration, RAG layer, GitHub integration, or model-policy extensibility work
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 10 advanced dashboard, concurrency, MCP, RAG, GitHub, or policy-pack work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the dashboard runtime surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
