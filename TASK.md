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

Phase 10I - Minimal External UI Run/Resume Controls

## Phase Status

Phase 10H is complete. Fix Phase A is complete. Phase 10I is now active as the next mainline slice focused on adding bounded external UI run/resume controls on top of the shipped read-only surface.

## Active Task

Implement Phase 10I for the agent loop. This slice should add bounded run/resume/inspect controls to the external UI on top of the shipped Phase 10H read-only surface, while preserving the CLI-first contract, canonical repo artifacts as the source of truth, and all existing approval and ownership boundaries.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10I as active
- `.agent-loop/phase-plan.md` records Phase 10H and Fix Phase A as closed history and contains a `## Phase 10I - Minimal External UI Run/Resume Controls` section with concrete objective, done criteria, and exclusions
- the repository adds bounded external UI controls for run/resume/inspect on top of the shipped Phase 10H read-only status surface
- the UI preserves the shipped CLI-first and canonical-artifact-first model: repo artifacts on disk remain authoritative, and the UI must not become an unbounded alternate control plane
- the UI preserves the existing approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, controller-vs-target ownership boundaries, and the Phase 4C activator + `APPROVED_FOR_ACTIVATION` gate
- focused validation proves the new control surface is bounded, reflects runtime state accurately, and does not widen into unrelated dashboard, concurrency, MCP, or autonomy work

## Next-Phase Gate

Do not treat the external UI as a general-purpose control plane until:

- Phase 10I receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the bounded run/resume control surface
- any broader dashboard or concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- any mutating external UI control or broader Phase 10 UI expansion
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any external-workspace target dispatch, concurrent Codex/Claude overlap execution, MCP integration, RAG layer, GitHub integration, or model-policy extensibility work
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 10 dashboard, concurrency, MCP, RAG, GitHub, or policy-pack work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the bounded UI control surface
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
